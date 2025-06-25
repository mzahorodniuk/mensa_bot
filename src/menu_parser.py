import requests
from bs4 import BeautifulSoup
from datetime import datetime

def fetch_todays_menu():
    url = "https://www.studentenwerk-magdeburg.de/mensen-cafeterien/mensa-unicampus-speiseplan-unten/"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    today = datetime.now().strftime('%d.%m.%Y')
    # Find the section for today
    menu_items = []
    found_today = False
    for section in soup.find_all(['div', 'tr', 'li', 'h3', 'h2', 'h4']):
        if today in section.get_text():
            found_today = True
        elif found_today and section.name in ['h3', 'h4', 'tr', 'div', 'li']:
            text = section.get_text(strip=True)
            if text:
                menu_items.append(text)
        elif found_today and section.name in ['h2']:
            break
    if not menu_items:
        return 'No menu found for today.'
    return '\n'.join(menu_items)
