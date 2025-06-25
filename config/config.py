import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MENSA_MENU_URL = os.getenv('MENSA_MENU_URL')
