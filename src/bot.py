import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config.config import TELEGRAM_BOT_TOKEN, MENSA_MENU_URL
from src.menu_parser import fetch_todays_menu

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send /menu to get today\'s Mensa menu.')

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        menu_text = fetch_todays_menu()
    except Exception:
        menu_text = 'Sorry, could not fetch the menu.'
    await update.message.reply_text(menu_text)

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('menu', menu))
    app.run_polling()

if __name__ == '__main__':
    main()
