import os
import logging
from dotenv import load_dotenv

from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# Import your existing bot logic and session manager
from chat_session import ChatSession
from gemini_bot import GeminiBot
from ollama_bot import OllamaBot
# Import web RAG utilities if you want to include web RAG in Telegram (Optional for this exercise, but good to have)
from web_rag_utils import create_vector_store_from_web, retrieve_context_from_vector_store

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Set up logging for easier debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Global Storage for User Sessions and LLM Choices ---
# This dictionary will store a ChatSession object for each user_id
user_sessions = {}
# This dictionary will store the chosen LLM for each user_id
user_llm_choice = {} # {user_id: "gemini" or "ollama"}
# This dictionary will store the LLM bot instances (to avoid re-initializing)
llm_bots = {
    "gemini": GeminiBot(),
    "ollama": OllamaBot()
}
# Optional: Web RAG vector store and state per user
user_rag_state = {} # {user_id: {"enabled": bool, "url": str, "vector_store": FAISS_object}}

# --- Helper Functions ---
async def send_typing_action(update: Update):
    """Sends a typing action to the user."""
    await update.effective_chat.send_chat_action(action="typing")

async def get_user_session(user_id: int) -> ChatSession:
    """Gets or creates a chat session for a user."""
    if user_id not in user_sessions:
        user_sessions[user_id] = ChatSession()
    return user_sessions[user_id]

# --- Telegram Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message and prompts user to choose LLM."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    keyboard = [
        [
            InlineKeyboardButton("Gemini API", callback_data="set_llm_gemini"),
            InlineKeyboardButton("Ollama (phi3:mini)", callback_data="set_llm_ollama"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        f"Hi {user.mention_html()}! Welcome to the LifeCode Chatbot.\n\n"
        "Please choose your preferred Large Language Model (LLM) to start chatting:",
        reply_markup=reply_markup,
    )
    # Reset history for new session if started via /start
    session = await get_user_session(user.id)
    session.clear_history()
    if user.id in user_rag_state: # Clear RAG state on start
        del user_rag_state[user.id]

async def choose_llm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback query for LLM selection."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query

    user_id = query.from_user.id
    choice = query.data.split('_')[-1] # Extracts 'gemini' or 'ollama'

    user_llm_choice[user_id] = choice
    logger.info(f"User {user_id} chose LLM: {choice}")

    await query.edit_message_text(text=f"You've selected **{choice.upper()}**. You can now start chatting!\n\n"
                                        "Type `/reset` to clear chat history.\n"
                                        "Type `/enable_rag` to connect to a website for context.\n"
                                        "Type `/disable_rag` to stop using website context.",
                                  parse_mode='Markdown')

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the chat history for the user."""
    user_id = update.effective_user.id
    session = await get_user_session(user_id)
    session.clear_history()
    if user_id in user_rag_state:
        del user_rag_state[user_id] # Also clear RAG state on reset
    await update.message.reply_text("Your chat history and RAG context (if any) have been cleared.")
    logger.info(f"User {user_id} cleared chat history and RAG state.")

async def enable_rag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts user for URL to enable Web RAG."""
    user_id = update.effective_user.id
    await update.message.reply_text("Please reply to this message with the URL you want to use for Web RAG. "
                                    "For example: `https://www.lifecode.life`")
    context.user_data['awaiting_url'] = True # Set a flag to expect URL in next message
    logger.info(f"User {user_id} initiated Web RAG setup.")

async def disable_rag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disables Web RAG for the user."""
    user_id = update.effective_user.id
    if user_id in user_rag_state:
        del user_rag_state[user_id]
        await update.message.reply_text("Web RAG has been disabled for this session.")
        logger.info(f"User {user_id} disabled Web RAG.")
    else:
        await update.message.reply_text("Web RAG is not currently enabled.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages from users."""
    user_id = update.effective_user.id
    user_text = update.message.text
    logger.info(f"User {user_id} message: {user_text}")

    # Check if we are awaiting a URL for RAG setup
    if context.user_data.get('awaiting_url'):
        url = user_text.strip()
        context.user_data['awaiting_url'] = False # Reset flag

        await send_typing_action(update)
        await update.message.reply_text(f"Processing content from {url} for RAG. This might take a moment...")

        vector_store, error = create_vector_store_from_web(url)
        if vector_store:
            user_rag_state[user_id] = {"enabled": True, "url": url, "vector_store": vector_store}
            await update.message.reply_text(f"Knowledge base from {url} loaded successfully! You can now ask questions related to it.")
            logger.info(f"User {user_id} successfully loaded RAG from {url}.")
        else:
            await update.message.reply_text(f"Failed to load knowledge base from {url}: {error}. Web RAG remains disabled.")
            if user_id in user_rag_state:
                del user_rag_state[user_id]
            logger.warning(f"User {user_id} failed to load RAG from {url}: {error}")
        return # Stop processing, as this message was a URL input

    # Ensure LLM is chosen before processing messages
    if user_id not in user_llm_choice:
        await update.message.reply_text("Please choose an LLM first by typing /start.")
        return

    llm_type = user_llm_choice[user_id]
    current_bot = llm_bots[llm_type]
    session = await get_user_session(user_id)

    # Add user message to history
    session.add_message("user", user_text)

    # Retrieve context if RAG is enabled for this user
    context_text = None
    if user_id in user_rag_state and user_rag_state[user_id]["enabled"]:
        vector_store = user_rag_state[user_id]["vector_store"]
        if vector_store:
            await send_typing_action(update) # Show typing while retrieving context
            retrieved_context = retrieve_context_from_vector_store(vector_store, user_text)
            if retrieved_context:
                context_text = retrieved_context
                logger.info(f"Context retrieved for user {user_id}: {retrieved_context[:100]}...")
            else:
                await update.message.reply_text("[No highly relevant context found from the website for this query.]")
                logger.info(f"No relevant context found for user {user_id}.")

    # Send typing indicator while LLM processes
    await send_typing_action(update)

    # Get response from the selected bot, passing context if available
    response_text = current_bot.get_response(session.get_history(), context=context_text)

    # Add bot's response to history if it's not an error message
    if not response_text.startswith("Error"):
        session.add_message("model", response_text)

    await update.message.reply_text(response_text)
    logger.info(f"Bot responded to {user_id} ({llm_type}): {response_text[:100]}...")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.warning(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again or type /reset.")


def main() -> None:
    """Starts the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set. Please add it to your .env file.")
        return

    # Create the Application and pass your bot's token.
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("enable_rag", enable_rag_command))
    application.add_handler(CommandHandler("disable_rag", disable_rag_command))
    application.add_handler(CallbackQueryHandler(choose_llm_callback, pattern="^set_llm_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot started! Polling for updates...")
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

