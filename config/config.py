import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MENSA_UNTER_MENU_URL = os.getenv('MENSA_UNTER_MENU_URL')
MENSA_OBEN_MENU_URL = os.getenv('MENSA_OBEN_MENU_URL')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')