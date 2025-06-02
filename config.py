import asyncio
import ssl
import time

import aiohttp
import certifi
from aiohttp import TCPConnector
from loguru import logger

from Misc import preprocess_email

list_for_patoki = []

new_ids = []

PROXY = 'http://username:password@ip:port'

default_username = 'Wꜹllapop'

hi_text = '<b>🟢 Спамер был запущен!</b>'

phone_text = """<b>
📮 Новое сообщение от мамонта!

💌 Номер телефона: <code>{email}</code>

🛍 Ссылка на обьявление: <code>{item_url}</code>
</b>"""

email_text = """<b>
📮 Новое сообщение от мамонта!

💌 Почта: <code>{email}</code>

🛍 Ссылка на обьявление: <code>{item_url}</code>
</b>"""

answer_text ="""<b>
❇️ Отправил {messages_count} сообщений-(я)!
🛍 Товар: <a href="{item_url}">{item_title}</a>

👤 Аккаунт: <code>{account_name}</code>
</b>"""

# black_list_of_ad = []
black_list_of_ad = [
    "card",
    "carta",
    "pokemon",
    "fifa",
    "playstation",
    "carte",
    "biciclette",
    "moneta",
    "funko pop",
    "trapstar",
    "rolex",
    "samba",
    "ps3",
    "hot wheels",
    "play station",
    "figura",
    "pley5",
    "play5",
    "play4",
    "play3",
    "play2",
    "pikachu",
    "𝐒𝐚𝐦𝐛𝐚",
    "funko",
    "perfume",
    "parfume",
    "hot",
    "wheels",
    "audi",
    "moneda",
    "bicicleta",
    "futbol",
    "ps5",
    "spiderman",
    "mario",
    "playmobil",
    "figuras",
    "hotwheels",
    "wwe",
    "puzzles",
    "funko",
    "puzzle",
    "fútbol",
    "perfumes",
    "ram",
    "xbox",
    "𝒑𝒐𝒅𝒔",
    "𝒂𝒊𝒓",
    "ssd",
    "pinko",
    "akami",
    "nintendo",
    "switch",
    "hp",
    "yves",
    "jordan",
    "shock",
    "s24",
    "doll",
    "g-shock",
    "bacarat",
    "mavic",
    "guess",
    "lenovo",
    "dunk",
    "high",
    "futsal",
    "mtb",
    "pc",
    "amazon",
    "ford",
    "tv",
    "ps4",
    "ps2",
    "psp",
    "harry",
    "marionetas",
    "minecraft",
    "thermos",
    "lampada",
    "bambole",
    "peluche",
    "gatti",
    "pokémon",
    "2€",
    "vaino",
    "warhammer",
    "irps",
    "pro",
    "airpods",
    "monete",
    "madrid",
    "slim",
    "tb",
    "appel",
    "wacht",
    "computer",
    "wireless",
    "galaxy",
    "pixel",
    "drone",
    "campus",
    "dayson",
    "mistery"
]

certifi_fil = ssl.create_default_context(cafile=certifi.where())

async def check_proxy_speed(proxy):
    url = "https://es.wallapop.com"
    try:
        start_time = time.time()
        connector = aiohttp.TCPConnector(ssl=certifi_fil)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, proxy=proxy, timeout=5) as response:
                if response.status == 200:
                    latency = time.time() - start_time
                    return proxy, latency
                else:
                    print(f"Прокси {proxy} не отвечает (статус {response.status}).")
                    return proxy, float('inf')
    except Exception:
        logger.error(f"Прокси: {proxy} сдох нахуй")
        return proxy, float('inf')

async def filter_fast_proxies(proxy_list, max_latency=1.0):
    tasks = [check_proxy_speed(proxy) for proxy in proxy_list]
    results = await asyncio.gather(*tasks)
    for proxy, latency in results:
        if latency < max_latency:
            fast_proxy_list.append(proxy)

    result = fast_proxy_list.copy()
    fast_proxy_list.clear()
    return result


def check_match(item_word):
    for word in item_word:
        if word.lower() in black_list_of_ad:
            return True
        else:
            continue
    return False

def get_proxy_from_file():
    with open('parser_proxy.txt', 'r', encoding='utf-8') as file:
        data = file.read().split()
        proxies = [f"http://{line}" for line in data]
    return proxies

shipping_list = []
fast_proxy_list = []
viewed_ads = []