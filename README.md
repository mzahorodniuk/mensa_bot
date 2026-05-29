# Mensa Telegram Bot

A Telegram bot for the [Studentenwerk Magdeburg](https://www.studentenwerk-magdeburg.de/mensen-cafeterien/)
canteens. Browse menus by day, switch between locations, and filter for
vegan/vegetarian dishes — all from inline buttons.

## Features
- 📅 **Full week** — today, tomorrow and the rest of the week (whatever the site publishes).
- 🏠 **Multiple locations** — UniCampus Oben & Unten, Herrenkrug, Kellercafé. Switch inline.
- 🌱 **Diet filter** — show all dishes, or only vegan / vegetarian.
- 💶 **Clear prices** — Student / Staff / Guest tiers (student price highlighted).
- 🟢 **Climate rating** — per-dish CO₂ footprint, plus diet icons (🐄🐖🍗🐟🧄).
- ⚡ **Fast** — menus are cached per process and refreshed daily at ~03:00.
- 💾 **Remembers you** — your last-used mensa and diet filter become your defaults next time.
- ⌨️ **Command menu** — `/menu`, `/start`, `/help` autocomplete in Telegram.

## Commands
- `/menu` — browse menus by day
- `/start` — welcome screen
- `/help` — usage, locations and the emoji legend

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file (see below).
3. Run locally: `python src/bot.py` (or `python autoreload.py` to auto-restart on changes).

### Environment variables (`.env`)
```
TELEGRAM_BOT_TOKEN=...
TESTING_TELEGRAM_BOT_TOKEN=...      # used when ENVIRONMENT=testing
ADMIN_USER_ID=...                   # who may run /activity
# Menu URLs are optional — sensible defaults are baked into config/config.py:
MENSA_OBEN_MENU_URL=...
MENSA_UNTER_MENU_URL=...
MENSA_HERRENKRUG_MENU_URL=...
MENSA_KELLERCAFE_MENU_URL=...
```

## Deployment
Runs as an Azure Function (`function_app.py`) handling the Telegram webhook at
`/api/webhook`, with a `/api/health` check and a keep-alive timer. Set the
Telegram webhook to `https://<your-function-app>.azurewebsites.net/api/webhook`.

User preferences are stored in **Azure Table Storage** using the Function App's
built-in `AzureWebJobsStorage` connection (table `mensaprefs`). When that
connection isn't set (e.g. local polling), preferences fall back to an in-memory
store automatically — no extra setup required.

## Project structure
- `src/bot.py` — Telegram handlers, keyboards and navigation
- `src/menu_parser.py` — scraping, caching and message formatting
- `config/config.py` — tokens and the list of `LOCATIONS`
- `function_app.py` — Azure Functions entry points

## Adding a location
Add an entry to `LOCATIONS` in `config/config.py` with a unique `key`, a `short`
button label, a header `label`, and the Speiseplan `url`. The location must use
the day-table layout (PIER 16 uses a different format and isn't supported).
