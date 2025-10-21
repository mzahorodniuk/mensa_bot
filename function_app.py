import azure.functions as func
import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config.config import TELEGRAM_BOT_TOKEN
from src.bot import start, menu, activity, myid, button, schedule_menu_update
from config.config import MENSA_OBEN_MENU_URL, MENSA_UNTER_MENU_URL

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Initialize the bot application
telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# Add handlers
telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CommandHandler('menu', menu))
telegram_app.add_handler(CommandHandler('activity', activity))
telegram_app.add_handler(CommandHandler('myid', myid))
telegram_app.add_handler(CallbackQueryHandler(button))

# Start background cache update for both locations (runs once when function app initializes)
schedule_menu_update(MENSA_OBEN_MENU_URL)
schedule_menu_update(MENSA_UNTER_MENU_URL)

@app.route(route="webhook", methods=["POST"])
async def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    This function handles incoming webhook updates from Telegram.
    Set your webhook URL to: https://<your-function-app>.azurewebsites.net/api/webhook
    """
    logging.info('Telegram webhook triggered.')
    
    try:
        # Get the JSON payload from Telegram
        req_body = req.get_json()
        logging.info(f"Received update: {req_body}")
        
        # Create Update object from JSON
        update = Update.de_json(req_body, telegram_app.bot)
        
        # Process the update
        await telegram_app.process_update(update)
        
        return func.HttpResponse("OK", status_code=200)
    
    except ValueError as e:
        logging.error(f"Invalid JSON: {e}")
        return func.HttpResponse("Invalid request", status_code=400)
    
    except Exception as e:
        logging.error(f"Error processing update: {e}")
        return func.HttpResponse("Internal server error", status_code=500)


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint to verify the function is running.
    """
    return func.HttpResponse("Mensa Bot is running!", status_code=200)