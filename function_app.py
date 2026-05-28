import azure.functions as func
import logging
import json
import asyncio
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config.config import TELEGRAM_BOT_TOKEN
from src.bot import start, menu, activity, myid, button, schedule_menu_update
from config.config import MENSA_OBEN_MENU_URL, MENSA_UNTER_MENU_URL

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Warm the menu cache once per worker process.
schedule_menu_update(MENSA_OBEN_MENU_URL)
schedule_menu_update(MENSA_UNTER_MENU_URL)


def build_application():
    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler('start', start))
    telegram_app.add_handler(CommandHandler('menu', menu))
    telegram_app.add_handler(CommandHandler('activity', activity))
    telegram_app.add_handler(CommandHandler('myid', myid))
    telegram_app.add_handler(CallbackQueryHandler(button))
    return telegram_app


@app.route(route="webhook", methods=["POST"])
async def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    This function handles incoming webhook updates from Telegram.
    Set your webhook URL to: https://<your-function-app>.azurewebsites.net/api/webhook
    """
    logging.info('Telegram webhook triggered.')

    try:
        req_body = req.get_json()
    except ValueError as e:
        logging.error(f"Invalid JSON: {e}")
        return func.HttpResponse("Invalid request", status_code=400)

    # Build and initialize a fresh Application bound to the current event loop.
    # Azure Functions starts a new asyncio loop per invocation, so caching the
    # Application across calls leaves ExtBot's HTTP client bound to a dead loop.
    telegram_app = build_application()
    try:
        await telegram_app.initialize()
        update = Update.de_json(req_body, telegram_app.bot)
        await telegram_app.process_update(update)
        return func.HttpResponse("OK", status_code=200)
    except Exception as e:
        logging.exception(f"Error processing update: {e}")
        return func.HttpResponse("Internal server error", status_code=500)
    finally:
        try:
            await telegram_app.shutdown()
        except Exception:
            logging.exception("Error during telegram_app.shutdown()")


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint to verify the function is running.
    """
    return func.HttpResponse("Mensa Bot is running!", status_code=200)


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def keep_alive_timer(timer: func.TimerRequest) -> None:
    """
    Timer trigger that runs every 5 minutes to keep the function app warm.
    The schedule uses CRON expression: "0 */5 * * * *" (every 5 minutes)
    
    CRON format: {second} {minute} {hour} {day} {month} {day-of-week}
    """
    if timer.past_due:
        logging.info('The keep-alive timer is past due!')
    
    try:
        # Ping the health endpoint to keep the app warm
        # Replace with your actual function app URL when deployed
        function_app_url = "mensabot-function-app.azurewebsites.net"
        
        # For local development, you can use localhost
        # function_app_url = "http://localhost:7071/api/health"
        
        response = requests.get(function_app_url, timeout=10)
        logging.info(f'Keep-alive ping successful: {response.status_code}')
    except Exception as e:
        logging.warning(f'Keep-alive ping failed: {e}')
    
    logging.info('Keep-alive timer trigger executed.')