import os
import json
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN', '7831438453:AAHsy0VR8qg2FUAPoBPE6MQzQDctZqqzgmQ')

# Initialize managers
from maps import MapManager
map_manager = MapManager()

from halls.hall_manager import HallManager
hall_manager = HallManager()

from favorites import FavoritesManager
favorites_manager = FavoritesManager()

from analytics import AnalyticsManager
analytics_manager = AnalyticsManager()

async def start(update: Update, context):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(f'Welcome {user.first_name}! I am your Book Fair guide. Use /help to see available commands.')
    analytics_manager.log_command('start', user.id)

async def help_command(update: Update, context):
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/search <query> - Search for halls or publishers
    """
    await update.message.reply_text(help_text)
    analytics_manager.log_command('help', update.effective_user.id)

async def search(update: Update, context):
    """Handle the /search command."""
    if not context.args:
        await update.message.reply_text("Please provide a search query. Example: /search publisher_name")
        return

    query = ' '.join(context.args)
    results = hall_manager.search(query)
    
    if not results:
        await update.message.reply_text("No results found.")
        return

    response = "Search results:\n\n"
    for result in results:
        response += f"- {result}\n"
    
    await update.message.reply_text(response)
    analytics_manager.log_search(query, update.effective_user.id)

async def handle_message(update: Update, context):
    """Handle incoming messages."""
    text = update.message.text
    user_id = update.effective_user.id
    
    logging.info(f"Received message from {user_id}: {text}")
    await update.message.reply_text("Please use /help to see available commands.")
    analytics_manager.log_message(user_id)

async def handle_callback_query(update: Update, context):
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    analytics_manager.log_callback_query(query.data, query.from_user.id)

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 