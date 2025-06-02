import asyncio
import random
import ssl
import time
import aiofiles
import aiofiles.os
import uuid
from fake_useragent import UserAgent
import certifi
from datetime import datetime
from config import check_match, shipping_list, fast_proxy_list, get_proxy_from_file, viewed_ads
from datetime import datetime
import bs4
import aiohttp
from curl_cffi.requests import AsyncSession
import os
from loguru import logger
import time
from loguru import logger
from config import PROXY, filter_fast_proxies
from random import shuffle, choice

# towns = [-3.7003454, 40.4166909, -1.129905, 37.9835334, -5.9962951, 37.38264, 2.1699187, 41.387917, -0.3768049,
#           39.4702393, -7.5558311, 43.0120963, -8.7124252, 42.2313601, 2.8236112, 41.9816465, -4.4200007,
#           36.7196292, -2.4679043, 36.8400939, -0.48149, 38.34517, -2.9234602, 43.2569608, -3.67975, 40.42972]

# towns = [-3.7003454, 40.4166909]

# towns = [-3.7003454, 40.4166909, -1.129905, 37.9835334, -5.9962951, 37.38264, 2.1699187, 41.387917, -0.3768049, 39.4702393, -7.5558311, 43.0120963]


towns = [-3.7003454, 40.4166909, -1.129905, 37.9835334, -5.9962951, 37.38264, 2.1699187, 41.387917]
class WallaPopScraper:
    fake_ua = UserAgent()
    headers = {
        'Host': 'api.wallapop.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US;q=0.7,en;q=0.6',
        'Connection': 'keep-alive',
        'DeviceOS': '0',
        'MPID': f'{random.randint(1000000000000000000, 9000000000000000000)}',
        'X-LocationAccuracy': '10',
        'X-LocationLatitude': '0',
        'X-LocationLongitude': '0',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Origin': 'https://es.wallapop.com',
        'Referer': 'https://es.wallapop.com/',
        'User-Agent': f'{fake_ua.safari}',
        'X-DeviceID': f'{uuid.uuid4()}',
        'X-DeviceOS': '0',
        'X-AppVersion': '85050',
        'sec-ch-ua-mobile': '?0'
    }

    def __init__(self, tag_country, categorie, min_price: int, max_price: int, max_item_count: int,
                 max_reviews: int, max_buying_items: int, max_selling_items: int, proxy_list):
        self.tag_country = tag_country
        self._headers = self.headers
        self._categorie = categorie
        self._min_price = min_price
        self._max_price = max_price
        self.max_item_count = max_item_count
        self.max_reviews = max_reviews
        self.max_buying_items = max_buying_items
        self.max_selling_items = max_selling_items
        self.database_file = 'databases/sellers_database.txt'
        self.database_for_url_full = 'databases/ad_urls.txt'
        self.ssl_ = ssl.create_default_context(cafile=certifi.where())
        self._proxy_list = proxy_list
        self._proxy_index = 0
        self.finded_urls = set()
        self.finded_sellers = set()
        self._curl_session = AsyncSession(impersonate='chrome')

        if not os.path.exists(self.database_file):
            with open(self.database_file, 'w') as f:
                pass

        if not os.path.exists(self.database_for_url_full):
            with open(self.database_for_url_full, 'w') as f:
                pass

    def _get_current_proxy(self):
        return self._proxy_list[self._proxy_index]

    def _switch_to_next_proxy(self):
        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_list)


    async def _get_ads(self, limit, latitude, longitutde):
        self._headers.update({
            'X-LocationLatitude': str(latitude),
            'X-LocationLongitude': str(longitutde),
        })
        #max_sale_price={self._max_price}&min_sale_price={self._min_price}
        response = await self._curl_session.get(f'https://api.wallapop.com/api/v3/search?category_id={self._categorie}&source=side_bar_filters&longitude={longitutde}&latitude={latitude}&order_by=newest&max_sale_price={self._max_price}&min_sale_price={self._min_price}', headers=self._headers)
        if response.status_code == 200:
            data = response.json()
            # await session.close()
            next_page = data['meta'].get('next_page')
            return data, next_page
        else:
            print(f'Ошибка при запросе на дату и некст токен')

    async def _close_session(self):
        await self._curl_session.close()

    async def _get_info_user(self, user_id):
        while True:
            try:
                # print(f'Использую прокси: {current_proxy}')
                self._switch_to_next_proxy()
                current_proxy = self._get_current_proxy()
                response = await self._curl_session.get(
                    f'https://api.wallapop.com/api/v3/users/{user_id}/stats',
                    headers=self._headers, proxy=current_proxy
                )
                if response.status_code == 200:
                    data = response.json()
                    # await session.close()
                    return data
                elif response.status_code == 429:
                    self._switch_to_next_proxy()
                    continue
                elif response.status_code == 502:
                    self._switch_to_next_proxy()
                    continue
                else:
                    self._switch_to_next_proxy()
                    print(response.status_code)
                    continue
            except Exception as e:
                logger.error(f'user_info_error: {str(e)}')
                self._switch_to_next_proxy()
                continue

    async def _parse_next_page(self, next_token):
        response = await self._curl_session.get(f'https://api.wallapop.com/api/v3/search?next_page={next_token}',
                                headers=self._headers)
        if response.status_code == 200:
            data = response.json()
            # await session.close()
            return data
        else:
            print('НЕКСТ ТОКЕН НЕ 200')

    @staticmethod
    async def _set_utc_time(unix_time: str):
        return unix_time

    async def _is_user_in_database(self, user_id):
        try:
            async with aiofiles.open(self.database_file, mode='r') as f:
                async for line in f:
                    if line.strip() == str(user_id):
                        return True
        except FileNotFoundError:
            return False
        return False

    # def _is_user_in_database(self, user_id):
    #     with open(self.database_file, 'r') as f:
    #         for line in f:
    #             if line.strip() == str(user_id):
    #                 return True
    #     return False

    # def _add_user_to_database(self, user_id):
    #     with open(self.database_file, 'r+', encoding='utf-8') as f:
    #         users = f.read().splitlines()
    #         if str(user_id) not in users:
    #             f.write(f"{user_id}\n")
    #             f.close()

    # def _add_ad_url_to_database(self, item_url):
    #     with open(self.database_for_url_full, 'r+', encoding='utf-8') as f:
    #         urls = f.read().splitlines()
    #         if str(item_url) not in urls:
    #             f.write(f"{item_url}\n")
                # f.close()

    async def start_scraping(self, limit, latitude, longitutde):
        list_ads, next_page = await self._get_ads(limit, latitude=latitude, longitutde=longitutde)
        items = await self._process_ads(list_ads, next_page)
        # logger.info(f'len items: {items}')
        return items, next_page

    async def start_scraping_next_page(self, next_token):
        # logger.info(f'Next token: {next_token}')
        next_page_data = await self._parse_next_page(next_token)
        next_page = next_page_data['meta'].get('next_page')
        # logger.info(f'Next page: {next_page}')
        items = await self._process_ads(next_page_data, next_page)
        # logger.info(f'Cобрано обьявлений за эту интерацию: {len(items)}')
        return items, next_page

    async def _process_ads(self, list_ads, next_page):
        tasks = []
        items = []

        for i, ads in enumerate(list_ads['data']['section']['payload']['items']):
            task = asyncio.create_task(self._process_single_ad(i, ads))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        for result in results:
            if result:
                items.append(result)
        return items

    async def get_item_info(self, item_id):
        self._switch_to_next_proxy()
        current_proxy = self._get_current_proxy()
        # print(f'Current_proxy: {current_proxy}')
        async with AsyncSession(impersonate='chrome') as session:
            response = session.get(
                f'https://api.wallapop.com/api/v3/items/{item_id}', headers=self._headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # await session.close()
                counters = data['counters']
                locality = data['location']
                views = counters['views']
                favorites = counters['favorites']
                convertsation = counters['conversations']
                location = locality['city']
                return views, favorites, convertsation, location
            else:
                print(response.status_code)
                self._switch_to_next_proxy()
                return False
                

    async def _process_single_ad(self, i, ads):
        # print(ads)
        location = ads['location']
        web_slug = ads['web_slug']
        item_url = f'https://{self.tag_country.lower()}.wallapop.com/item/{web_slug}'
        user_id = ads['user_id']
        location_ = ads['location']['country_code']
        title_ = ads['title'].lower()
        price = int(ads['price']['amount'])
        title = title_.split()
        item_id = ads['id']
        shippable = bool(ads['shipping']['item_is_shippable'])
        reserved = bool(ads['reserved']['flag'])
        # print(reserved)
        checked = check_match(title)

        # logger.info(f'{title_} | {location_} | Bad: {checked} | {item_id} | {price} eur')

        if await self._is_user_in_database(user_id):
            return None

        if checked:
            return None


        now = datetime.now()
        creation_unix = round(ads['created_at'] / 1000)
        creation_date = datetime.fromtimestamp(creation_unix)
        time_stamp = creation_date.strftime('%Y-%m-%d %H:%M:%S')

        time_difference = now - creation_date
        difference_min = round(time_difference.total_seconds() / 60, 2)
        if difference_min >= 15:
            return None

        user_info = await self._get_info_user(user_id)

        item_amount_buys_items = user_info['counters'][1]['value']
        item_amount_selling_complete = user_info['counters'][2]['value']
        item_geo = location['country_code']
        # print(item_geo)
        item_shipping = f'https://{self.tag_country.lower()}.wallapop.com/app/chat/checkout/{item_id}/shipping'
        item_amount_ads_in_seller = user_info['counters'][0]['value']
        item_amount_feedback_seller = user_info['counters'][3]['value']
        # vi, fav, conv, location = await self.get_item_info(item_id=item_id)
        # logger.info(f'item_geo: {item_geo} | item_amount_ads_in_seller: {item_amount_ads_in_seller} | item_amount_feedback_seller: {item_amount_feedback_seller} | item_amount_buys_items: {item_amount_buys_items} | price: {price} | title: {title_} | id: {user_id} | Reserved: {reserved} | Ship: {shippable} | Time: {time_stamp}')
        


        if item_geo != self.tag_country or item_amount_ads_in_seller > self.max_item_count or item_amount_feedback_seller > self.max_reviews or item_amount_buys_items > self.max_buying_items or item_amount_selling_complete > self.max_selling_items or reserved or price > self._max_price:
            return None
        # print(f'Date: {time_stamp} | Shippable: {shippable} | Views: {vi} | Favorites: {fav} | Conversations: {conv} | Location: {location}')

        # print(viewed_ads)
        if item_url not in viewed_ads and item_id not in self.finded_sellers:
            viewed_ads.append(item_url)
            self.finded_sellers.add(item_id)
            logger.success(f'Date: {time_stamp} | Shippable: {shippable} | Location: {item_geo} | Differance: {difference_min}')
            return {
                'user_id': user_id,
                'item_id': item_id,
                'item_title': title_,
                'item_url': item_url,
                'item_geo': item_geo,
                'item_shipping': item_shipping,
                'item_amount_ads_in_seller': item_amount_ads_in_seller,
                'item_amount_feedback_seller': item_amount_feedback_seller,
                'item_amount_buys_items': item_amount_buys_items,
                'item_amount_selling_complete': item_amount_selling_complete,
                'item_shippable': shippable,
                'item_reserved': reserved
            }
        # else:
        #     logger.warning(f'[{item_url}] Уже находжиться в списке: viewed_ads')


async def start_parser(country: str, item_count: int):
    shipping_list.clear()
    proxy_list_for_parser = get_proxy_from_file()
    proxy_list = await filter_fast_proxies(proxy_list_for_parser)
    logger.info(f'Количество быстрых прокси (до 1 с.): {len(proxy_list)}')
    start_time = time.time()
    limit = 70

    # 100 - Cars
    # 14000 - Motorbike
    # 12800 - Motors & accessories
    # 12465 - Fashion & accessories
    # 200 - Real Estate
    # 24200 - Technology & electronics
    # 12579 - Sports & leisure
    # 17000 - Bikes
    # 12467 - Home & garden
    # 13100 - Appliances
    # 12463 - Movies, books & music
    # 12461 - Baby & child
    # 18000 - Collectibles & Art
    # 19000 - Construction
    # 20000 - Agriculture & industrial
    # 21000 - Jobs
    # 13200 - Services
    # 12485 - Other

    categories = [12465, 24200, 12579, 12461, 12463] # Указываем как тут через запятую!!!!!
    async def parse_category_partial(category):
        return await parse_category(country, item_count, category, limit, proxy_list)

    tasks = [asyncio.create_task(parse_category_partial(category)) for category in categories]

    await asyncio.gather(*tasks)

    end_time = time.time()
    zatracheno_time = end_time - start_time
    logger.success(f'Объявления были спаршены за: {zatracheno_time:.2f} сек.')

    if len(shipping_list) < item_count:
        logger.warning(f"Собрано только: {len(shipping_list)} объявлений из {item_count}.")

    result = shipping_list[:item_count]

    return result
    # Додавання користувача до бази

async def add_user_to_database(user_id):
    try:
        async with aiofiles.open('databases/sellers_database.txt', mode='r', encoding='utf-8') as f:
            users = await f.read()
            users = users.splitlines()
    except FileNotFoundError:
        users = []

    if str(user_id) not in users:
        async with aiofiles.open('databases/sellers_database.txt', mode='a', encoding='utf-8') as f:
            await f.write(f"{user_id}\n")

# Додавання URL до бази
async def add_ad_url_to_database(item_url):
    try:
        async with aiofiles.open('databases/ad_urls.txt', mode='r', encoding='utf-8') as f:
            urls = await f.read()
            urls = urls.splitlines()
    except FileNotFoundError:
        urls = []

    if str(item_url) not in urls:
        async with aiofiles.open('databases/ad_urls.txt', mode='a', encoding='utf-8') as f:
            await f.write(f"{item_url}\n")


async def parse_category(country: str, item_count: int, category: int, limit: int, proxy_list):
    scraper = WallaPopScraper(
        tag_country=f'{country.upper()}',  # НЕ ТРОГАТЬ!!!!!!
        categorie=category,  # НЕ ТРОГАТЬ!!!!!!
        max_price=3000,  # Максимальная цена за товар
        min_price=1,  # Минимальная цена
        max_item_count=10,  # Макс. количество товаров у продавца
        max_reviews=0,  # Макс. отзывов у продавца
        max_buying_items=0,  # Макс. купленных
        max_selling_items=0,  # Макс. проданных
        proxy_list=proxy_list  # НЕ ТРОГАТЬ!!!!!!
    )

    next_page_token = None
    reset_counter = 0
    max_pages = 35

    quantity_towns = int(len(towns) / 2)
    index_town = 0

    while len(shipping_list) < item_count:
        print(f'len shipping_list: {len(shipping_list)}')
        tasks = []

        for _ in range(quantity_towns):
            if next_page_token:
                task = asyncio.create_task(scraper.start_scraping_next_page(next_page_token))
            else:
                try:
                    task = asyncio.create_task(scraper.start_scraping(limit=item_count, latitude=towns[index_town],longitutde=towns[index_town + 1]))
                except IndexError:
                    index_town = 0
                    task = asyncio.create_task(scraper.start_scraping(limit=item_count, latitude=towns[index_town], longitutde=towns[index_town + 1]))
                # logger.info(f'Актуальные координаты: Категория: {category} | {towns[index_town]} | {towns[index_town + 1]}')
            index_town += 2

            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        for items, next_token in results:
            next_page_token = next_token
            for item in items:
                if item['item_id'] not in shipping_list:
                    if len(shipping_list) >= item_count:
                        break

                    shipping_list.append(item)
                    await add_user_to_database(item['user_id'])
                    await add_ad_url_to_database(item['item_url'])
                    # await _add_user_to_database(item['item_id'])
                    # await _add_ad_url_to_database(item["item_url"])

        if len(shipping_list) >= item_count:
            break

        reset_counter += 1
        if reset_counter == max_pages:
            reset_counter = 0
            logger.info(f"Категория {category} достигла {max_pages} страниц, начинаем заново")
            next_page_token = None


# async def main():
#     for i in range(1):
#         logger.info(f'Interation: {i + 1}')
#         p = await start_parser(country='es', item_count=40)
#         print(p)


# asyncio.run(main())