import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import azure.functions as func
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import telegram
from config.config import TELEGRAM_BOT_TOKEN, MENSA_UNTER_MENU_URL, MENSA_OBEN_MENU_URL, ADMIN_USER_ID
from src.menu_parser import fetch_menu_for_day_with_cache as fetch_menu_for_day, format_menu_message, schedule_menu_update
import sentry_sdk

# sentry_sdk
sentry_sdk.init(
    dsn="https://3dabe0ac5c67ed866c3099d2477b2be6@o4510217887219712.ingest.de.sentry.io/4510217893314640",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

# Global variable to count user requests
request_count = 0
ADMIN_USER_ID=int(ADMIN_USER_ID)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data='choose_day_today'),
            InlineKeyboardButton("Tomorrow", callback_data='choose_day_tomorrow')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome! Choose a day to get the Mensa menu:",
        reply_markup=reply_markup
    )

async def send_location_buttons(chat_or_query, day, day_label, show_as_edit=False):
    keyboard = [
        [
            InlineKeyboardButton("Oben", callback_data=f'show_menu_{day}_oben'),
            InlineKeyboardButton("Unter", callback_data=f'show_menu_{day}_unter')
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data='back_to_day')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Choose a location for {day_label}:"
    if show_as_edit:
        # Only edit if text or markup is different
        try:
            current_text = chat_or_query.message.text or ''
            current_markup = chat_or_query.message.reply_markup
            if current_text != text or current_markup != reply_markup:
                await chat_or_query.edit_message_text(text, reply_markup=reply_markup)
        except telegram.error.BadRequest as e:
            if 'Message is not modified' not in str(e):
                await chat_or_query.answer(str(e), show_alert=True)
        except Exception as e:
            await chat_or_query.answer(str(e), show_alert=True)
    else:
        await chat_or_query.reply_text(text, reply_markup=reply_markup)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global request_count
    request_count += 1
    # For /menu, just show the day selection buttons
    keyboard = [
        [
            InlineKeyboardButton("Today", callback_data='choose_day_today'),
            InlineKeyboardButton("Tomorrow", callback_data='choose_day_tomorrow')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Choose a day to get the Mensa menu:",
        reply_markup=reply_markup
    )

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
    data = query.data
    print(data)
    if data == 'choose_day_today':
        await send_location_buttons(query, 'today', 'Today', show_as_edit=True)
        return
    elif data == 'choose_day_tomorrow':
        await send_location_buttons(query, 'tomorrow', 'Tomorrow', show_as_edit=True)
        return
    elif data.startswith('show_menu_'):
        # data format: show_menu_{day}_{location}, e.g. show_menu_today_oben
        parts = data.split('_')
        # join all after 2nd as location (in case location contains underscores)
        day = parts[2]
        location = '_'.join(parts[3:])
        if location == 'oben':
            url = MENSA_OBEN_MENU_URL
            mensa_location = 'Oben'
        else:
            url = MENSA_UNTER_MENU_URL
            mensa_location = 'Unter'
        day_label = 'Today' if day == 'today' else 'Tomorrow'
        try:
            menu_items = fetch_menu_for_day(url, day)
            menu_text = format_menu_message(mensa_location, menu_items, day_label)
        except Exception as e:
            menu_text = f'Sorry, could not fetch the menu.\n{e}'
        await send_location_buttons(query, day, day_label, show_as_edit=True)
        # Only update if menu_text or reply_markup is different from current message
        try:
            current_text = query.message.text or ''
            location_keyboard = [
                [
                    InlineKeyboardButton("Oben", callback_data=f'show_menu_{day}_oben'),
                    InlineKeyboardButton("Unter", callback_data=f'show_menu_{day}_unter')
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data='back_to_day')
                ]
            ]
            new_markup = InlineKeyboardMarkup(location_keyboard)
            # Compare markup objects directly
            markup_changed = query.message.reply_markup != new_markup
            if current_text != menu_text or markup_changed:
                await query.edit_message_text(menu_text, parse_mode='HTML', reply_markup=new_markup)
        except telegram.error.BadRequest as e:
            if 'Message is not modified' not in str(e):
                await query.answer(str(e), show_alert=True)
        except Exception as e:
            await query.answer(str(e), show_alert=True)
        return
    elif data == 'back_to_day':
        # Go back to day selection
        keyboard = [
            [
                InlineKeyboardButton("Today", callback_data='choose_day_today'),
                InlineKeyboardButton("Tomorrow", callback_data='choose_day_tomorrow')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Welcome! Choose a day to get the Mensa menu:",
            reply_markup=reply_markup
        )
        return
    else:
        await query.edit_message_text('Unknown option.')
        return


def main():
    # Start background cache update for both locations
    schedule_menu_update(MENSA_OBEN_MENU_URL)
    schedule_menu_update(MENSA_UNTER_MENU_URL)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('menu', menu))
    app.add_handler(CommandHandler('activity', activity))
    app.add_handler(CommandHandler('myid', myid))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == '__main__':
    main()
