import re
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)

# Map dietary/symbol alt texts (from the website's <img alt="Symbol ...">) to emojis.
# Keys are matched case-insensitively as substrings of the image's alt/title text.
DIET_EMOJI = {
    'vegan': '🌱',
    'vegetarisch': '🥦',
    'rind': '🐄',
    'schwein': '🐖',
    'geflügel': '🍗',
    'gefl': '🍗',          # guards against the "ü" mangling seen in some alt texts
    'fisch': '🐟',
    'knoblauch': '🧄',
    'alkohol': '🍷',
}

# Climate (CO₂) rating shown per dish on the website ("Klimabewusst essen").
CO2_EMOJI = {
    'a': '🟢',
    'b': '🟡',
    'c': '🟠',
    'd': '🔴',
}

# Canonical dietary tags used by the /menu diet filter.
TAG_VEGAN = 'vegan'
TAG_VEGETARIAN = 'vegetarisch'

WEEKDAYS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

_DATE_RE = re.compile(r'(\d{2}\.\d{2}\.\d{4})')


def _clean(text: str) -> str:
    """Collapse whitespace and tidy spacing around punctuation."""
    text = re.sub(r'\s+', ' ', text or '').strip()
    text = re.sub(r'\s+([,.;:])', r'\1', text)
    return text


def _parse_dish_row(tds):
    """Parse one <tr> of dish cells into a structured dict, or None if empty."""
    cell = tds[0]

    price_span = cell.find('span', class_='mensapreis')
    price_raw = price_span.get_text(strip=True) if price_span else ''

    grau = cell.find('span', class_='grau')
    english = grau.get_text(separator=' ', strip=True) if grau else ''

    full = cell.get_text(separator=' ', strip=True)
    german = full
    if english:
        german = german.replace(english, '')
    if price_raw:
        german = german.replace(price_raw, '')
    german = _clean(german)
    english = _clean(english)

    if not german:
        return None

    # Three price tiers: "(3,40 | 5,10 | 6,50)" -> ["3,40 €", "5,10 €", "6,50 €"]
    prices = []
    if price_raw:
        for p in price_raw.strip('()').split('|'):
            p = p.strip()
            if p:
                prices.append(p if '€' in p else f'{p} €')

    # Dietary symbols + climate rating live in the remaining cells (td[1], td[2]).
    tags = []
    emojis = ''
    climate = ''
    for td in tds[1:]:
        for img in td.find_all('img'):
            label = f"{img.get('alt', '')} {img.get('title', '')}".lower()
            co2 = re.search(r'co2 stufe ([a-d])', label)
            if co2:
                climate = CO2_EMOJI.get(co2.group(1), '')
            for key, emoji in DIET_EMOJI.items():
                if key in label:
                    canonical = TAG_VEGAN if key == 'vegan' else (
                        TAG_VEGETARIAN if key == 'vegetarisch' else key)
                    if canonical not in tags:
                        tags.append(canonical)
                    if emoji not in emojis:
                        emojis += emoji

    return {
        'german': german,
        'english': english,
        'prices': prices,
        'tags': tags,
        'emojis': emojis,
        'climate': climate,
    }


def parse_all_days(url):
    """Fetch the page once and return {date_str: [dish, ...]} for every day shown."""
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    days = {}
    for table in soup.find_all('table'):
        header = table.find('strong')
        if not header:
            continue
        m = _DATE_RE.search(header.get_text())
        if not m:
            continue
        date_str = m.group(1)
        items = []
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 2:  # the date-header row has a single cell
                continue
            dish = _parse_dish_row(tds)
            if dish:
                items.append(dish)
        days[date_str] = items
    return days


def filter_items(items, diet='all'):
    """Filter dishes by diet: 'all', 'vegan', or 'veg' (vegan + vegetarian)."""
    if diet == 'vegan':
        return [i for i in items if TAG_VEGAN in i['tags']]
    if diet == 'veg':
        return [i for i in items if TAG_VEGAN in i['tags'] or TAG_VEGETARIAN in i['tags']]
    return items


def format_menu_message(location_label, date_label, items, diet='all'):
    """Render a dish list as an HTML Telegram message."""
    diet_note = {
        'all': '',
        'vegan': ' · 🌱 vegan only',
        'veg': ' · 🥦 vegetarian only',
    }.get(diet, '')

    header = f'🍽 <b>{location_label}</b> — {date_label}{diet_note}\n\n'

    if not items:
        if diet in ('vegan', 'veg'):
            return header + 'No matching dishes for this filter. Try “All”.'
        return header + '🚪 No menu published for this day (the Mensa may be closed).'

    lines = []
    for item in items:
        prefix = item['emojis'] or '•'
        line = f'{prefix} <b>{item["german"]}</b>'
        if item['english']:
            line += f'\n<i>{item["english"]}</i>'

        meta = []
        if item['prices']:
            # Student price is the first tier and the one most users care about.
            student = item['prices'][0]
            rest = ' / '.join(item['prices'][1:])
            meta.append(f'💶 <b>{student}</b>' + (f' <i>({rest})</i>' if rest else ''))
        if item['climate']:
            meta.append(item['climate'])
        if meta:
            line += '\n' + '  '.join(meta)
        lines.append(line)

    footer = '\n\n<i>💶 Student / Staff / Guest · 🟢🟡🟠 CO₂ footprint</i>'
    return header + '\n\n'.join(lines) + footer


# ---------------------------------------------------------------------------
# In-memory cache. One entry per URL holding every day the page exposes.
# Refreshed lazily on access and by a daily background thread (warm at 03:00).
# ---------------------------------------------------------------------------
menu_cache = {}
_cache_lock = threading.Lock()


def _today_str():
    return datetime.now().strftime('%d.%m.%Y')


def refresh_cache(url):
    """(Re)fetch all days for a URL into the cache."""
    days = parse_all_days(url)
    with _cache_lock:
        menu_cache[url] = {'fetched_on': _today_str(), 'days': days}
    return menu_cache[url]


def _get_cache(url):
    entry = menu_cache.get(url)
    if not entry or entry['fetched_on'] != _today_str():
        try:
            entry = refresh_cache(url)
        except Exception:
            logger.exception('Failed to refresh menu cache for %s', url)
            entry = entry or {'fetched_on': _today_str(), 'days': {}}
    return entry


def get_available_dates(url):
    """Return upcoming menu dates (today onward) as a sorted list of 'DD.MM.YYYY'."""
    days = _get_cache(url)['days']
    today = datetime.now().date()
    dated = []
    for date_str in days:
        try:
            d = datetime.strptime(date_str, '%d.%m.%Y').date()
        except ValueError:
            continue
        if d >= today:
            dated.append((d, date_str))
    dated.sort()
    return [s for _, s in dated]


def get_menu_for_date(url, date_str):
    """Return the dish list for a specific 'DD.MM.YYYY', or [] if absent."""
    return _get_cache(url)['days'].get(date_str, [])


def day_label(date_str):
    """Human label for a date, e.g. 'Today · Fri 30.05' or 'Mon 01.06'."""
    try:
        d = datetime.strptime(date_str, '%d.%m.%Y').date()
    except ValueError:
        return date_str
    today = datetime.now().date()
    wd = WEEKDAYS_EN[d.weekday()]
    base = f'{wd} {d.strftime("%d.%m")}'
    if d == today:
        return f'Today · {base}'
    if d == today + timedelta(days=1):
        return f'Tomorrow · {base}'
    return base


def schedule_menu_update(url):
    """Background thread that keeps the cache warm and refreshes daily at ~03:00."""
    def update_loop():
        while True:
            try:
                refresh_cache(url)
            except Exception:
                logger.exception('Background menu refresh failed for %s', url)
            now = datetime.now()
            next_update = (now + timedelta(days=1)).replace(
                hour=3, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_update - now).total_seconds()
            time.sleep(max(sleep_seconds, 3600))

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
