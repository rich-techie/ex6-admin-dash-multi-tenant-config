import google.generativeai as genai
import os
import time # NEW: Import time for duration tracking

# Removed: from dotenv import load_dotenv # Load dotenv only in main entry point

class GeminiBot:
    """
    Handles interactions with the Gemini 1.5 Flash API.
    Manages API key configuration and response generation with chat history.
    """
    def __init__(self, model_name='gemini-1.5-flash'):
        self.model_name = model_name
        self.model = None
        self._configure_gemini()

    def _configure_gemini(self):
        """
        Configures the Gemini API with the key from environment variables.
        Initializes the GenerativeModel.
        """
        try:
            api_key = os.getenv("GEMINI_API_KEY") # Get API key from already loaded env
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file in the project root.")

            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"[Gemini 1.5 Flash bot initialized.]")
        except ValueError as ve:
            print(f"Error configuring Gemini API: {ve}")
            self.model = None
        except Exception as e:
            print(f"An unexpected error occurred during Gemini API configuration: {e}")
            self.model = None

    def get_response(self, chat_history: list, context: str = None) -> tuple[str, float, int, int, str | None]:
        """
        Gets a response from the Gemini model based on the provided chat history and optional context.
        Args:
            chat_history (list): A list of message dictionaries representing the conversation.
            context (str, optional): Additional context to prepend to the last user message.
        Returns:
            tuple: (response_text, duration_seconds, input_tokens, output_tokens, error_message)
        """
        if self.model is None:
            return "Gemini model is not configured. Please check your API key in the .env file.", 0, 0, 0, "Model not configured"

        start_time = time.time() # Start timer
        try:
            # Prepare the messages list for the LLM
            messages_for_llm = []

            # Add all historical messages except the very last one (which is the current user query)
            # We assume chat_history already has the current user message as the last entry
            historical_messages = chat_history[:-1] # All messages except the last user query

            for msg in historical_messages:
                messages_for_llm.append({'role': msg['role'], 'parts': [{'text': msg['content']}]})

            # Get the current user's actual query
            current_user_query = chat_history[-1]['content']

            # Construct the final user message with context if provided
            if context:
                final_user_message_content = f"Context: {context}\n\nQuestion: {current_user_query}"
            else:
                final_user_message_content = current_user_query

            messages_for_llm.append({'role': 'user', 'parts': [{'text': final_user_message_content}]})

            print("\n[DEBUG] Messages sent to Gemini LLM:")
            for msg in messages_for_llm:
                print(f"  Role: {msg['role']}, Content: {msg['parts'][0]['text'][:100]}...") # Print first 100 chars
            print("[DEBUG] End LLM messages.\n")

            # Count tokens for the input prompt
            input_tokens = 0
            try:
                # Gemini's count_tokens expects a list of Content objects, not raw dicts
                # Reconstruct content objects for token counting
                contents_for_token_count = []
                for msg in messages_for_llm:
                    parts = [genai.types.Part(text=p['text']) for p in msg['parts']]
                    contents_for_token_count.append(genai.types.Content(role=msg['role'], parts=parts))

                input_tokens_response = self.model.count_tokens(contents_for_token_count)
                input_tokens = input_tokens_response.total_tokens if hasattr(input_tokens_response, 'total_tokens') else 0
            except Exception as token_e:
                print(f"[WARNING] Error counting input tokens for Gemini: {token_e}")


            response = self.model.generate_content(messages_for_llm)

            end_time = time.time() # End timer
            duration = end_time - start_time

            if response.text:
                output_tokens = 0
                try:
                    output_tokens_response = self.model.count_tokens([genai.types.Content(role="model", parts=[genai.types.Part(text=response.text)])])
                    output_tokens = output_tokens_response.total_tokens if hasattr(output_tokens_response, 'total_tokens') else 0
                except Exception as token_e:
                    print(f"[WARNING] Error counting output tokens for Gemini: {token_e}")

                return response.text, duration, input_tokens, output_tokens, None
            else:
                return "No text response received from Gemini.", duration, input_tokens, 0, "No text response"
        except Exception as e:
            end_time = time.time() # End timer even on error
            duration = end_time - start_time
            return f"Error communicating with Gemini: {e}", duration, 0, 0, str(e)

