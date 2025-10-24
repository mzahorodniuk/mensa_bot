import os
from dotenv import load_dotenv

load_dotenv()

# Determine which environment we're running in
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')  # defaults to production

# Select the appropriate bot token based on environment
if ENVIRONMENT == 'testing':
    TELEGRAM_BOT_TOKEN = os.getenv('TESTING_TELEGRAM_BOT_TOKEN')
else:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Keep both tokens accessible if needed
PRODUCTION_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TESTING_BOT_TOKEN = os.getenv('TESTING_TELEGRAM_BOT_TOKEN')

MENSA_UNTER_MENU_URL = os.getenv('MENSA_UNTER_MENU_URL')
MENSA_OBEN_MENU_URL = os.getenv('MENSA_OBEN_MENU_URL')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')