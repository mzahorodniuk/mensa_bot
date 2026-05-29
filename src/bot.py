import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import logging
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from config.config import (
    TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, LOCATIONS, DEFAULT_LOCATION,
)
from src.menu_parser import (
    get_available_dates, get_menu_for_date, filter_items,
    format_menu_message, day_label, schedule_menu_update,
)
from src.preferences import get_prefs, set_prefs
import sentry_sdk

logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn="https://3dabe0ac5c67ed866c3099d2477b2be6@o4510217887219712.ingest.de.sentry.io/4510217893314640",
    send_default_pii=True,
)

request_count = 0
ADMIN_USER_ID = int(ADMIN_USER_ID) if ADMIN_USER_ID else 0

# location key -> location dict, for quick lookup
LOC_BY_KEY = {loc['key']: loc for loc in LOCATIONS}

DIETS = [('all', '🍽 All'), ('vegan', '🌱 Vegan'), ('veg', '🥦 Veggie')]

# Shown in Telegram's "/" command menu (set via setMyCommands).
BOT_COMMANDS = [
    BotCommand('menu', 'Browse Mensa menus by day'),
    BotCommand('start', 'Welcome screen'),
    BotCommand('help', 'How to use the bot'),
]


async def set_my_commands(bot):
    """Register the command menu so commands autocomplete in Telegram clients."""
    try:
        await bot.set_my_commands(BOT_COMMANDS)
    except Exception:
        logger.exception('set_my_commands failed')

WELCOME = (
    "👋 <b>Welcome to the Magdeburg Mensa Bot!</b>\n\n"
    "Pick a day below to see what's cooking. Then switch between mensas "
    "and filter for 🌱 vegan / 🥦 vegetarian dishes right from the menu.\n\n"
    "Type /help anytime for tips."
)

HELP_TEXT = (
    "🍽 <b>Magdeburg Mensa Bot — Help</b>\n\n"
    "<b>Commands</b>\n"
    "• /menu — browse menus by day\n"
    "• /start — show the welcome screen\n"
    "• /help — this message\n\n"
    "<b>How it works</b>\n"
    "1. Choose a day (today, tomorrow or later this week).\n"
    "2. Switch mensa with the top row of buttons.\n"
    "3. Tap 🌱 Vegan or 🥦 Veggie to filter dishes.\n\n"
    "<b>Locations</b>\n"
    + "\n".join(f"• {loc['label']}" for loc in LOCATIONS) + "\n\n"
    "<b>Legend</b>\n"
    "🌱 vegan  🥦 vegetarian  🐄 beef  🐖 pork  🍗 poultry  🐟 fish  🧄 garlic\n"
    "💶 Student / Staff / Guest price · 🟢🟡🟠 CO₂ footprint\n\n"
    "Menus come from studentenwerk-magdeburg.de and update daily."
)


# ----------------------------- keyboards -----------------------------

def day_keyboard():
    """Buttons for every upcoming day the default location publishes."""
    dates = get_available_dates(LOC_BY_KEY[DEFAULT_LOCATION]['url'])
    rows, row = [], []
    for date_str in dates:
        row.append(InlineKeyboardButton(day_label(date_str), callback_data=f'd:{date_str}'))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if not rows:
        rows.append([InlineKeyboardButton("🔄 Try again", callback_data='back')])
    return InlineKeyboardMarkup(rows)


def menu_keyboard(date_str, loc_key, diet):
    """Location switcher + diet filter + back, with the current choices marked."""
    loc_row = [
        InlineKeyboardButton(
            f'✅ {loc["short"]}' if loc['key'] == loc_key else loc['short'],
            callback_data=f'm:{date_str}:{loc["key"]}:{diet}')
        for loc in LOCATIONS
    ]
    diet_row = [
        InlineKeyboardButton(
            f'• {label}' if key == diet else label,
            callback_data=f'm:{date_str}:{loc_key}:{key}')
        for key, label in DIETS
    ]
    back_row = [InlineKeyboardButton('⬅️ Days', callback_data='back')]
    # Split the four locations across two rows so labels stay readable.
    return InlineKeyboardMarkup([loc_row[:2], loc_row[2:], diet_row, back_row])


# ----------------------------- helpers -----------------------------

async def _edit(query, text, reply_markup):
    """Edit a callback message, ignoring 'not modified' noise."""
    try:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
    except telegram.error.BadRequest as e:
        if 'Message is not modified' not in str(e):
            await query.answer(str(e), show_alert=True)
    except Exception as e:
        logger.exception('edit_message_text failed')
        await query.answer(str(e), show_alert=True)


def _render_menu(date_str, loc_key, diet):
    loc = LOC_BY_KEY.get(loc_key, LOC_BY_KEY[DEFAULT_LOCATION])
    try:
        items = filter_items(get_menu_for_date(loc['url'], date_str), diet)
        return format_menu_message(loc['label'], day_label(date_str), items, diet)
    except Exception as e:
        logger.exception('Failed to build menu for %s %s', loc_key, date_str)
        return f'😕 Sorry, could not load the menu right now.\n<code>{e}</code>'


# ----------------------------- commands -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode='HTML', reply_markup=day_keyboard())


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global request_count
    request_count += 1
    await update.message.reply_text(
        "📅 <b>Choose a day:</b>", parse_mode='HTML', reply_markup=day_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode='HTML', disable_web_page_preview=True)


async def activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return
    await update.message.reply_text(f"Total user requests: {request_count}")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram user ID is: {update.effective_user.id}")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global request_count
    request_count += 1
    query = update.callback_query
    await query.answer()
    data = query.data or ''

    if data == 'back':
        await _edit(query, WELCOME, day_keyboard())
        return

    if data.startswith('d:'):
        # Day chosen -> open the user's saved default location & diet for that day.
        date_str = data[2:]
        prefs = await asyncio.to_thread(get_prefs, query.from_user.id)
        loc_key, diet = prefs['location'], prefs['diet']
        text = _render_menu(date_str, loc_key, diet)
        await _edit(query, text, menu_keyboard(date_str, loc_key, diet))
        return

    if data.startswith('m:'):
        # m:<date>:<loc>:<diet> — also remembered as the user's new default.
        _, date_str, loc_key, diet = data.split(':', 3)
        await asyncio.to_thread(set_prefs, query.from_user.id, loc_key, diet)
        text = _render_menu(date_str, loc_key, diet)
        await _edit(query, text, menu_keyboard(date_str, loc_key, diet))
        return

    await _edit(query, 'Unknown option. Try /menu.', day_keyboard())


async def _post_init(app):
    await set_my_commands(app.bot)


def main():
    for loc in LOCATIONS:
        schedule_menu_update(loc['url'])
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(_post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('menu', menu))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('activity', activity))
    app.add_handler(CommandHandler('myid', myid))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()


if __name__ == '__main__':
    main()
