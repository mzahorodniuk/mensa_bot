import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def fetch_menu_for_day(url, day: str = 'today'):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    if day == 'today':
        date_obj = datetime.now()
    elif day == 'tomorrow':
        date_obj = datetime.now() + timedelta(days=1)
    else:
        raise ValueError('day must be "today" or "tomorrow"')
    date_str = date_obj.strftime('%d.%m.%Y')

    tables = soup.find_all('table')
    menu_items = []
    for table in tables:
        header = table.find('strong')
        if header and date_str in header.get_text():
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if not tds:
                    continue
                # Main text (German)
                main_text = tds[0].get_text(separator=' ', strip=True)
                price = ''
                price_span = tds[0].find('span', class_='mensapreis')
                if price_span:
                    price = price_span.get_text(strip=True)
                if price:
                    main_text = main_text.replace(price, '').strip()
                # English text (in span.grau, after <br/>)
                english = ''
                grau_span = tds[0].find('span', class_='grau')
                if grau_span:
                    english = grau_span.get_text(separator=' ', strip=True)
                if main_text:
                    menu_items.append({'text': main_text, 'english': english, 'price': price})
            break
    return menu_items

def format_menu_message(mensa_location,menu_items, day_label):
    if not menu_items:
        return f'No menu found for {day_label}.'
    msg = f'<b>Mensa {mensa_location} Menu for {day_label}:</b>\n\n'
    for item in menu_items:
        msg += f'• <b>{item["text"]}</b>'
        if item['english']:
            msg += f'\n{item["english"]}'
        if item['price']:
            msg += f'\n<i>{item["price"]}</i>'
        msg += '\n\n'
    return msg