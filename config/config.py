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

_BASE = 'https://www.studentenwerk-magdeburg.de/mensen-cafeterien'

# Menu URLs. Env vars win; otherwise fall back to the known public pages so the
# bot keeps working even before the new locations are added to the deployment env.
MENSA_OBEN_MENU_URL = os.getenv(
    'MENSA_OBEN_MENU_URL', f'{_BASE}/mensa-unicampus-speiseplan-oben/')
MENSA_UNTER_MENU_URL = os.getenv(
    'MENSA_UNTER_MENU_URL', f'{_BASE}/mensa-unicampus-speiseplan-unten/')
MENSA_HERRENKRUG_MENU_URL = os.getenv(
    'MENSA_HERRENKRUG_MENU_URL', f'{_BASE}/mensa-herrenkrug-speiseplan/')
MENSA_KELLERCAFE_MENU_URL = os.getenv(
    'MENSA_KELLERCAFE_MENU_URL', f'{_BASE}/mensa-kellercafe-speiseplan/')

# Single source of truth for the locations the bot offers. `key` is used in
# callback data, `short` on inline buttons, `label` in message headers.
LOCATIONS = [
    {'key': 'oben',       'short': 'Oben',       'label': 'UniCampus · Oben',  'url': MENSA_OBEN_MENU_URL},
    {'key': 'unter',      'short': 'Unter',      'label': 'UniCampus · Unten', 'url': MENSA_UNTER_MENU_URL},
    {'key': 'herrenkrug', 'short': 'Herrenkrug', 'label': 'Herrenkrug',        'url': MENSA_HERRENKRUG_MENU_URL},
    {'key': 'kellercafe', 'short': 'Keller',     'label': 'Kellercafé',        'url': MENSA_KELLERCAFE_MENU_URL},
]

DEFAULT_LOCATION = 'oben'

ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')