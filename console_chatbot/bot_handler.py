import logging
import json
from chat_session import ChatSession
from gemini_bot import GeminiBot
from ollama_bot import OllamaBot
from web_rag_utils import create_vector_store_from_web, retrieve_context_from_vector_store

from parsers.lead_parser import LeadParser
from integrations.crm_router import CRMRouter

logger = logging.getLogger(__name__)

# Define conversation states
STATE_INITIAL = "initial"
STATE_AWAITING_NAME = "awaiting_name"
STATE_AWAITING_EMAIL = "awaiting_email"
STATE_LEAD_COLLECTED = "lead_collected"
STATE_RAG_AWAITING_URL = "rag_awaiting_url"

class BotHandler:
    def __init__(self, user_id: str, llm_bots: dict, active_tenant_config: dict):
        self.user_id = user_id
        self.session = ChatSession()
        self.llm_bots = llm_bots
        self._current_llm = None
        self.active_tenant_config = active_tenant_config # Store the active tenant config

        self.rag_state = {
            "enabled": False,
            "url": None,
            "vector_store": None,
            "awaiting_url": False
        }

        self.crm_state = { # Renamed from zoho_state for agnosticism
            "state": STATE_INITIAL,
            "name": None, # Full name provided by user
            "email": None,
            "phone": user_id, # WhatsApp user ID is used as phone for initial search
            "lead_id": None,
            "lead_found_name": None # Name of lead found in CRM
        }

        self.lead_parser = LeadParser()
        try:
            # Pass the active_tenant_config to CRMRouter
            self.crm_router = CRMRouter(active_tenant_config=self.active_tenant_config)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            logger.error(f"Failed to initialize CRMRouter for tenant {self.active_tenant_config.get('tenant_id', 'N/A')}: {e}")
            self.crm_router = None # Indicate that CRM is not available
            print(f"[BotHandler ERROR] CRM integration not available due to: {e}")

    def _get_llm_response(self, user_query: str, context: str = None) -> str:
        """
        Helper to get response from chosen LLM, with enhanced error handling.
        Returns:
            str: The LLM's response or an error message.
        """
        if not self._current_llm:
            return "Please choose an LLM first by typing /set_llm gemini or /set_llm ollama."

        llm_type = self._current_llm
        bot_instance = self.llm_bots[llm_type]

        # The chat_history passed to bot.get_response should already include the current user_query
        # as the last message. So, we don't append it here.
        # The bot.get_response method is expected to handle the context augmentation internally.

        logger.debug(f"[DEBUG] _get_llm_response: History being sent to LLM: {json.dumps(self.session.get_history(), indent=2)}")

        try:
            response_tuple = bot_instance.get_response(self.session.get_history(), context=context)

            # Check if the response is in the expected (text, duration, in_tokens, out_tokens, error) format
            if isinstance(response_tuple, tuple) and len(response_tuple) == 5:
                response_text = response_tuple[0]
                llm_error = response_tuple[4]

                if llm_error:
                    logger.error(f"LLM (Type: {llm_type}) returned an error: {llm_error}")
                    return f"I apologize, but there was an issue processing your request with {llm_type.upper()}. Please try again or rephrase your question. Error: {llm_error}"

                if not response_text:
                    return f"I'm sorry, {llm_type.upper()} did not provide a response. Could you please try again?"

                # Add bot's response to history
                self.session.add_message("model", response_text)
                return response_text
            else:
                # Fallback if get_response doesn't return the expected tuple (e.g., older bot versions)
                logger.error(f"LLM (Type: {llm_type}) get_response returned unexpected format: {response_tuple}")
                # Assume the response_tuple itself is the string response if not a tuple of 5
                response_text = str(response_tuple)
                if not response_text.startswith("Error"): # Avoid adding error messages to history
                    self.session.add_message("model", response_text)
                return response_text

        except Exception as e:
            logger.error(f"An unexpected error occurred while getting LLM ({llm_type}) response: {e}")
            return f"I'm really sorry, but I'm having trouble connecting with {llm_type.upper()} right now. Please try again in a moment."

    def _personalize_greeting(self, lead_name: str) -> str:
        """Generates a personalized greeting using LLM."""
        llm_type = self._current_llm
        if not llm_type:
             return "Welcome back! It's great to hear from you."

        bot_instance = self.llm_bots[llm_type]
        personal_prompt = f"The user's name is {lead_name}. Greet them warmly and ask how you can help them today. Keep it concise."

        # For a one-off prompt like this, we can use a temporary history
        temp_history = [{'role': 'user', 'content': personal_prompt}]

        try:
            response_tuple = bot_instance.get_response(temp_history) # Pass temporary history
            if isinstance(response_tuple, tuple) and len(response_tuple) == 5:
                response_text = response_tuple[0]
                error = response_tuple[4]
            else:
                response_text = response_tuple
                error = None

            return response_text if response_text and not error else f"Welcome back, {lead_name}! How can I assist you today?"
        except Exception as e:
            logger.error(f"Error personalizing greeting with LLM ({llm_type}): {e}")
            return f"Welcome back, {lead_name}! How can I assist you today?"


    def handle_message(self, user_message: str) -> str:
        """
        Processes an incoming user message based on conversation state.
        Returns the bot's response.
        """
        logger.info(f"User {self.user_id} (State: {self.crm_state['state']}) received: {user_message}")

        # --- Handle core commands first (always available) ---
        if user_message.lower() == "/reset":
            self.session.clear_history()
            self._current_llm = None
            self.rag_state = {"enabled": False, "url": None, "vector_store": None, "awaiting_url": False}
            self.crm_state = {
                "state": STATE_INITIAL, "name": None, "email": None,
                "phone": self.user_id, "lead_id": None, "lead_found_name": None
            }
            return "Chat reset. Please use /set_llm to choose an LLM."

        elif user_message.lower().startswith("/set_llm "):
            parts = user_message.lower().split()
            if len(parts) == 2 and parts[1] in ["gemini", "ollama"]:
                self._current_llm = parts[1]

                if self.crm_router: # Check if CRM Router was successfully initialized
                    lead_record = self.crm_router.search_lead(self.crm_state['phone'])
                else:
                    lead_record = None
                    logger.warning("CRM Router not initialized, skipping lead search.")

                if lead_record:
                    self.crm_state['state'] = STATE_LEAD_COLLECTED
                    self.crm_state['lead_id'] = lead_record.get('id')
                    # Use common keys from normalized data if available, otherwise CRM-specific
                    # HubSpot uses 'firstname', 'lastname'; Zoho uses 'First_Name', 'Last_Name', 'Full_Name'
                    self.crm_state['lead_found_name'] = lead_record.get('Full_Name') or \
                                                         lead_record.get('firstname') or \
                                                         lead_record.get('First_Name') or \
                                                         "valued customer" # Fallback

                    # Add a dummy user message to history to prime the LLM for greeting
                    self.session.add_message("user", "Start conversation with a greeting.")
                    personalized_greeting = self._personalize_greeting(self.crm_state['lead_found_name'])
                    return f"You've selected {self._current_llm.upper()}. {personalized_greeting}"
                else:
                    self.crm_state['state'] = STATE_AWAITING_NAME
                    return f"You've selected {self._current_llm.upper()}. Hello! Before we proceed, could you please tell me your full name?"
            return "Invalid LLM choice. Please use /set_llm gemini or /set_llm ollama."

        elif user_message.lower() == "/enable_rag":
            if self.rag_state["enabled"]:
                return f"Web RAG is already enabled using {self.rag_state['url']}. Use /disable_rag to change it."
            self.rag_state["awaiting_url"] = True # Use this flag as the state
            self.crm_state['state'] = STATE_RAG_AWAITING_URL # Set main state for clarity
            return "Please reply to this message with the URL you want to use for Web RAG. For example: https://www.example.com"

        elif user_message.lower() == "/disable_rag":
            if self.rag_state["enabled"]:
                self.rag_state = {"enabled": False, "url": None, "vector_store": None, "awaiting_url": False}
                # Reset main state if it was RAG awaiting URL
                if self.crm_state['state'] == STATE_RAG_AWAITING_URL:
                    self.crm_state['state'] = STATE_LEAD_COLLECTED if self.crm_state['lead_id'] else STATE_INITIAL
                return "Web RAG has been disabled for this session."
            return "Web RAG is not currently enabled."

        # --- Handle Web RAG URL input ---
        if self.rag_state["awaiting_url"] and self.crm_state['state'] == STATE_RAG_AWAITING_URL:
            url = user_message.strip()
            self.rag_state["awaiting_url"] = False # Reset flag

            # Reset main state to normal chat after URL is provided
            self.crm_state['state'] = STATE_LEAD_COLLECTED if self.crm_state['lead_id'] else STATE_INITIAL

            response_message = f"Processing content from {url} for RAG. This might take a moment..."

            vector_store, error = create_vector_store_from_web(url)
            if vector_store:
                self.rag_state["enabled"] = True
                self.rag_state["url"] = url
                self.rag_state["vector_store"] = vector_store
                return f"{response_message}\nKnowledge base from {url} loaded successfully! You can now ask questions related to it."
            else:
                self.rag_state["enabled"] = False
                self.rag_state["url"] = None
                self.rag_state["vector_store"] = None
                return f"{response_message}\nFailed to load knowledge base from {url}: {error}. Web RAG remains disabled."

        # --- Zoho Lead Capture Flow (now uses LeadParser and CRMRouter) ---
        if self.crm_state['state'] == STATE_AWAITING_NAME:
            full_name = user_message.strip()
            self.crm_state['name'] = full_name

            self.crm_state['state'] = STATE_AWAITING_EMAIL
            return f"Thanks, {self.crm_state['name']}! Now, please provide your email address."

        elif self.crm_state['state'] == STATE_AWAITING_EMAIL:
            self.crm_state['email'] = user_message.strip()

            # Use LeadParser to normalize data
            normalized_data = self.lead_parser.normalize_lead_data(
                self.crm_state['name'],
                self.crm_state['email'],
                self.crm_state['phone']
            )

            # Use CRMRouter to create lead
            if self.crm_router:
                created_lead_details = self.crm_router.create_lead(normalized_data)
            else:
                created_lead_details = None
                logger.error("CRM Router not initialized, cannot create lead.")


            if created_lead_details:
                self.crm_state['lead_id'] = created_lead_details.get('id')
                self.crm_state['state'] = STATE_LEAD_COLLECTED

                # Use the normalized first/last name for the confirmation message
                display_name = normalized_data.get('first_name')
                if normalized_data.get('last_name'):
                    display_name += f" {normalized_data['last_name']}"

                confirmation_message_prompt = (
                    f"A new lead has been created for {display_name} "
                    f"with email {normalized_data['email']} and phone {normalized_data['phone']} "
                    f"in our CRM. Respond with a polite confirmation message to the user, "
                    f"thanking them and asking how you can help them now. "
                    f"Keep it concise and friendly."
                )
                # Add user message to history before getting LLM response
                self.session.add_message("user", confirmation_message_prompt)
                return self._get_llm_response(confirmation_message_prompt)
            else:
                self.crm_state['state'] = STATE_INITIAL
                return "I apologize, but there was an issue creating your lead in our system. Please try again or contact support."

        # --- Normal Chat with RAG and LLM ---
        context = None
        if self.rag_state["enabled"] and self.rag_state["vector_store"]:
            context = retrieve_context_from_vector_store(self.rag_state["vector_store"], user_message)
            if not context:
                logger.info(f"No relevant context found for user {self.user_id} from the URL.")
                pass # LLM will handle lack of context

        self.session.add_message("user", user_message) # Add user message to history before getting LLM response
        response_text = self._get_llm_response(user_message, context=context)
        return response_text

