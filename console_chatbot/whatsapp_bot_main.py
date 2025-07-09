import os
import sys # Import sys module at the very top

# Add the project root directory to the Python path
# This is crucial for imports like 'integrations.crm_router' and 'parsers.lead_parser'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

import logging
import json
from flask import Flask, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import requests # For making requests to Meta's WhatsApp API

# Import your existing bot logic and session manager
from chat_session import ChatSession # Still needed for individual session objects within BotHandler
from gemini_bot import GeminiBot
from ollama_bot import OllamaBot
from web_rag_utils import create_vector_store_from_web, retrieve_context_from_vector_store

# NEW: Import BotHandler and Zoho Auth Manager
from bot_handler import BotHandler # BotHandler now encapsulates CRM/RAG logic
from console_chatbot.zoho_auth_manager import ZohoAuthManager # Import the new ZohoAuthManager class
from utils.tenant_loader import load_all_tenants_config # To load tenants.json

# Load environment variables
load_dotenv()
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN")

# Define the ID of the tenant this bot instance should serve
# For testing, you might set this to "lifecode" or "genetics"
# Or, if you only have one tenant, you can just pick the first one from tenants.json
BOT_ACTIVE_TENANT_ID = os.getenv("BOT_ACTIVE_TENANT_ID", None) # Default to None, pick first if not set

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Global Storage ---
user_bot_handlers = {} # {user_id: BotHandler object}
llm_bots = { # LLM instances are global as they don't change per user
    "gemini": GeminiBot(),
    "ollama": OllamaBot()
}

# --- Tenant Configuration ---
all_tenants_config = load_all_tenants_config()
active_tenant_config = None

if BOT_ACTIVE_TENANT_ID:
    active_tenant_config = next((t for t in all_tenants_config.get('tenants', []) if t['tenant_id'] == BOT_ACTIVE_TENANT_ID), None)
    if not active_tenant_config:
        logger.error(f"Configured BOT_ACTIVE_TENANT_ID '{BOT_ACTIVE_TENANT_ID}' not found in tenants.json. Please check your configuration.")
        exit(1)
else:
    # If no specific ID is set, use the first tenant found in tenants.json
    if all_tenants_config.get('tenants'):
        active_tenant_config = all_tenants_config['tenants'][0]
        logger.warning(f"BOT_ACTIVE_TENANT_ID not set. Defaulting to first tenant: '{active_tenant_config.get('tenant_id', 'N/A')}' from tenants.json.")
    else:
        logger.error("No tenants found in tenants.json and BOT_ACTIVE_TENANT_ID is not set. Cannot start bot.")
        exit(1)

# Extract Zoho credentials for the active tenant for the /authorize_zoho route
# These will be used to instantiate ZohoAuthManager for the authorization flow
ZOHO_CLIENT_ID = active_tenant_config.get('zoho', {}).get('client_id')
ZOHO_CLIENT_SECRET = active_tenant_config.get('zoho', {}).get('client_secret')
ZOHO_ACCOUNTS_URL = active_tenant_config.get('zoho', {}).get('accounts_url')
ZOHO_API_URL = active_tenant_config.get('zoho', {}).get('api_url') # Also needed for ZohoCRM class

# The redirect URI path must match what's configured in Zoho API Console
ZOHO_REDIRECT_URI_PATH = "/zoho-oauth-callback"


# --- WhatsApp API Constants ---
WHATSAPP_API_URL = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# --- Helper Functions ---
def send_whatsapp_message(to_number: str, message_body: str) -> None:
    """Sends a text message back to the user via WhatsApp Cloud API."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"body": message_body},
    }
    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        logger.info(f"Message sent to {to_number}: {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending WhatsApp message to {to_number}: {e}")
        if response and response.text:
            logger.error(f"WhatsApp API Error Response: {response.text}")

def send_whatsapp_image(to_number: str, image_url: str, caption: str = None) -> None:
    """Sends an image message back to the user via WhatsApp Cloud API."""
    if not image_url:
        logger.warning(f"Attempted to send WhatsApp image to {to_number} but image_url was empty.")
        return

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "image",
        "image": {
            "link": image_url
        }
    }
    if caption:
        payload["image"]["caption"] = caption

    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Image sent to {to_number}: {response.json()}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending WhatsApp image to {to_number} from URL {image_url}: {e}")
        if response and response.text:
            logger.error(f"WhatsApp API Error Response: {response.text}")


# --- Flask Webhook Endpoints ---

@app.route("/")
def index():
    """Simple route to confirm the Flask server is running."""
    return "WhatsApp Chatbot Flask server is running. Webhook configured at /webhook", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Endpoint for Meta to verify the webhook."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Verification token mismatch", 403
    return "Missing parameters", 400

@app.route("/webhook", methods=["POST"])
def handle_whatsapp_messages():
    """Endpoint for incoming WhatsApp messages."""
    data = request.get_json()
    logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")

    if data and "object" in data and "entry" in data:
        for entry in data["entry"]:
            for change in entry["changes"]:
                if "messages" in change["value"]:
                    for message in change["value"]["messages"]:
                        if message["type"] == "text":
                            from_number = message["from"]
                            user_text = message["text"]["body"]
                            logger.info(f"Message from {from_number}: {user_text}")

                            if from_number not in user_bot_handlers:
                                # Pass the active_tenant_config to the BotHandler
                                user_bot_handlers[from_number] = BotHandler(from_number, llm_bots, active_tenant_config)
                                logger.info(f"New BotHandler created for user: {from_number} with tenant {active_tenant_config.get('tenant_id', 'N/A')}")

                            response_from_bot_handler = user_bot_handlers[from_number].handle_message(user_text)
                            send_whatsapp_message(from_number, response_from_bot_handler)

                            # --- NEW: Send Logo after initial LLM selection and greeting ---
                            # This logic should ideally be within bot_handler.py's _personalize_greeting
                            # or _set_llm logic, but for direct testing and simplicity, we'll
                            # add it here to ensure it's sent after the first interaction.
                            # We'll send it if an LLM has just been set or if a lead was found.

                            # Check if the bot just finished the initial setup (LLM selected, potentially lead found)
                            # This is a heuristic. A more robust way would be to have BotHandler return a flag.
                            bot_handler_instance = user_bot_handlers[from_number]
                            if bot_handler_instance._current_llm and \
                                (bot_handler_instance.crm_state['state'] == 'lead_collected' or \
                                 bot_handler_instance.crm_state['state'] == 'initial'): # Initial state after LLM set if no CRM

                                logo_url = active_tenant_config.get('branding', {}).get('logo_url')
                                if logo_url:
                                    # Send the logo with a small delay or after the text message
                                    # For simplicity, sending immediately after the text message.
                                    # WhatsApp will deliver them in order.
                                    send_whatsapp_image(from_number, logo_url, caption=f"{active_tenant_config.get('name', 'Your Company')} Logo")
                                    logger.info(f"Sent logo for tenant {active_tenant_config.get('tenant_id', 'N/A')} to {from_number}")
                                else:
                                    logger.info(f"No logo URL configured for tenant {active_tenant_config.get('tenant_id', 'N/A')}.")

    return "OK", 200

@app.route(ZOHO_REDIRECT_URI_PATH, methods=["GET"])
def zoho_oauth_callback():
    """
    Handles the redirect from Zoho after user authorizes the app.
    Exchanges the authorization code for access and refresh tokens for the active tenant.
    """
    auth_code = request.args.get("code")
    if not auth_code:
        error = request.args.get("error")
        logger.error(f"Zoho OAuth Callback Error: {error}")
        return "Zoho OAuth failed. Please check logs.", 400

    # The full redirect URI that Zoho used to send the code
    current_ngrok_url = request.host_url.replace('http://', 'https://') # Ensure HTTPS
    full_redirect_uri = f"{current_ngrok_url.rstrip('/')}{ZOHO_REDIRECT_URI_PATH}"

    # Instantiate ZohoAuthManager for the active tenant to handle the code exchange
    if not all([ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_ACCOUNTS_URL, ZOHO_API_URL, active_tenant_config.get('tenant_id')]):
        logger.error("Missing Zoho credentials or tenant ID for ZohoAuthManager instantiation in callback.")
        return "Zoho CRM authorization failed: Incomplete configuration.", 500

    zoho_auth_manager_for_callback = ZohoAuthManager(
        client_id=ZOHO_CLIENT_ID,
        client_secret=ZOHO_CLIENT_SECRET,
        accounts_url=ZOHO_ACCOUNTS_URL,
        api_url=ZOHO_API_URL,
        tenant_id=active_tenant_config['tenant_id']
    )

    if zoho_auth_manager_for_callback.exchange_authorization_code_for_tokens(auth_code, full_redirect_uri):
        logger.info(f"Zoho CRM authorization successful for tenant {active_tenant_config['tenant_id']}! Refresh token obtained and saved.")
        return "Zoho CRM integration authorized successfully! You can now close this page and return to WhatsApp.", 200
    else:
        logger.error(f"Failed to exchange Zoho authorization code for tokens for tenant {active_tenant_config['tenant_id']}.")
        return "Zoho CRM authorization failed. Please check server logs.", 500


@app.route("/authorize_zoho")
def authorize_zoho():
    """
    Provides a link to initiate Zoho CRM OAuth authorization for the active tenant.
    User needs to open this link in their browser.
    """
    if not all([ZOHO_CLIENT_ID, ZOHO_ACCOUNTS_URL, active_tenant_config.get('tenant_id')]):
        return "Missing Zoho Client ID, Accounts URL, or active tenant ID in configuration for authorization.", 500

    return f"""
    <h1>Zoho CRM Authorization for Tenant: {active_tenant_config.get('name', 'N/A')} ({active_tenant_config.get('tenant_id', 'N/A')})</h1>
    <p>To authorize this application to access your Zoho CRM, please click the link below:</p>
    <p><b>Important:</b> Before clicking, ensure your ngrok tunnel is running and note its HTTPS forwarding URL.</p>
    <p>Then, replace `YOUR_NGROK_HTTPS_URL` in the link below with your actual ngrok URL.</p>
    <p>Example Ngrok URL: <code>https://abcdef12345.ngrok-free.app</code></p>
    <p>
        <a href="#" id="authLink">Click here to authorize Zoho CRM</a>
    </p>
    <p>After clicking, you will be redirected to Zoho for authorization. Once authorized, you will be redirected back to this server, and the refresh token will be saved.</p>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const authLink = document.getElementById('authLink');
            const ngrokUrlPrompt = prompt("Please enter your current ngrok HTTPS forwarding URL (e.g., https://abcdef12345.ngrok-free.app):");

            if (ngrokUrlPrompt) {{
                // Correctly embed Python variables as JavaScript strings
                const zohoRedirectUriPath = "{ZOHO_REDIRECT_URI_PATH}";
                const zohoAccountsUrl = "{ZOHO_ACCOUNTS_URL}";
                const zohoClientId = "{ZOHO_CLIENT_ID}";

                const redirectUri = `${{ngrokUrlPrompt.replace(/\\/$/, '')}}${{zohoRedirectUriPath}}`;
                const authUrl = `${{zohoAccountsUrl}}/oauth/v2/auth?` +
                                `scope=ZohoCRM.modules.ALL&` + // Or specific scopes like ZohoCRM.modules.leads.CREATE,ZohoCRM.modules.leads.READ
                                `client_id=${{zohoClientId}}&` +
                                `response_type=code&` +
                                `access_type=offline&` + // Request refresh token
                                `redirect_uri=${{encodeURIComponent(redirectUri)}}`;
                authLink.href = authUrl;
                authLink.textContent = "Click here to authorize Zoho CRM (configured)";
            }} else {{
                authLink.textContent = "Please refresh and enter ngrok URL to generate link.";
                authLink.href = "#";
            }}
        }});
    </script>
    """


if __name__ == "__main__":
    if not all([WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_WEBHOOK_VERIFY_TOKEN]):
        logger.error("Missing WhatsApp environment variables. Please check your .env file.")
        exit(1)

    # Check if the active_tenant_config has Zoho credentials if Zoho is the chosen CRM
    if active_tenant_config.get('crm') == 'zoho' and \
       not all([ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_ACCOUNTS_URL, ZOHO_API_URL]):
        logger.error(f"Active tenant '{active_tenant_config.get('tenant_id', 'N/A')}' uses Zoho, but Zoho CRM credentials (client_id, client_secret, accounts_url, api_url) are incomplete in tenants.json. Please configure them via Streamlit UI.")
        exit(1)

    # Check if the active_tenant_config has HubSpot credentials if HubSpot is the chosen CRM
    if active_tenant_config.get('crm') == 'hubspot' and \
       not active_tenant_config.get('hubspot', {}).get('api_key'):
        logger.error(f"Active tenant '{active_tenant_config.get('tenant_id', 'N/A')}' uses HubSpot, but HubSpot API Key is incomplete in tenants.json. Please configure it via Streamlit UI.")
        exit(1)

    logger.info("WhatsApp Bot Flask app starting...")
    app.run(debug=True, port=5000)
