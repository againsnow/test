# Импорты СУКА НЕ ТРОГАТЬ
import asyncio
import json
import os
import random
import ssl
from fileinput import filename
from uuid import uuid4

import certifi
from telebot.apihelper import proxy
from collections import defaultdict
from config import PROXY, phone_text, email_text, default_username, hi_text, answer_text
from telegram_bot import send_if_message_sended, send_to_telegram, send_hi_to_telegram
from loguru import logger
from WallapopParser_ import start_parser
from Misc import Misc, find_emails_with_item_hash, count_read_messages, find_phone_with_item_hash, \
    check_if_mamont_sent_answer
from WebSocketClient import WebSocket
from WallapopClient import WallapopClient
import aiohttp

from service_item import RepositoryHash


class Main:
    def __init__(
            self, main_texts, more_texts, 
            answer, country_code, 
            parser_type, group_size,
            messages_count, repository_hash: RepositoryHash,
            answer_timeout, message_timeout,
            message_count_for_mamonth
        ):
        self.main_texts = main_texts
        self.more_texts = more_texts
        self.answer = answer
        self.country_code = country_code
        self.parser_type = parser_type
        self.group_size = group_size
        self.messages_count = messages_count
        self.bad_accounts = set()
        self.finded_data_ = set()
        self.answered_data = set()
        self.finded_data = defaultdict(dict)
        self.finded_data_path = 'databases/finded_data.json'
        self.proxy = PROXY
        self.ssl_ = ssl.create_default_context(cafile=certifi.where())
        self.headers = {
            "X-Deviceid": f"{uuid4()}",
            "X-Deviceos": "0",
            "Sec-Ch-Ua-Mobile": "?1",
            "Mpid": f"-{random.randrange(1000000000000000000, 9999999999999999999)}",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.6834.78 Mobile/15E148 Safari/604.1",
            # "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/plain, */*",
            "Deviceos": "0",
            "X-Appversion": "82520",
            "Sec-Ch-Ua-Platform": 'iOS',
            "Origin": "https://es.wallapop.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://es.wallapop.com/",
            "Accept-Encoding": "gzip", 
            "Accept-Language": "es-ES,es;q=0.9",
            "Priority": "u=1, i",
            "Connection": "keep-alive"
        }
        self.number_tryies_to_parse = 0
        self.lock = asyncio.Lock()
        self.repository_hash = repository_hash
        self.answer_timeout = answer_timeout
        self.message_timeout = message_timeout
        self.misc = Misc()
        self.responses = {
            "message_1": self.main_texts[1],
            "message_2": self.main_texts[-1], # номер телефона всегда последний в списке
        }
        self.message_count_for_mamonth = message_count_for_mamonth
        self.message_queue = asyncio.Queue()

    async def message_sender_worker(self):
        while True:
            text = await self.message_queue.get()
            await asyncio.sleep(random.uniform(0.5, 3)) 
            try:
                await send_if_message_sended(text=text)
                logger.success("Отправил в тг")
            except Exception as e:
                logger.error(f"ошибка при отправке в тг: {e}")

            self.message_queue.task_done()

    def save_finded_data(self):
        with open(self.finded_data_path, "w", encoding="utf-8") as f:
            json.dump(self.finded_data, f, ensure_ascii=False, indent=4)

    def read_finded_data(self):
        if os.path.exists(self.finded_data_path) and os.path.getsize(self.finded_data_path) > 0:
            with open(self.finded_data_path, "r", encoding="utf-8") as f:
                try:
                    self.finded_data = json.load(f)
                except json.JSONDecodeError:
                    logger.error(f"Файл {self.finded_data_path} поврежден. Перезаписываю пустую структуру.")
                    self.finded_data = {}
                    self.save_finded_data()
        else:
            self.finded_data = {}
            self.save_finded_data()

    async def process_group(self, auth_tokens):

        ws_clients = {token_info['token']: WebSocket(misc.get_all_texts(), self.more_texts, self.answer, self.message_count_for_mamonth) for token_info in auth_tokens}

        responded_items = {token_info['token']: set() for token_info in auth_tokens}
        messages_sent = {token_info['token']: 0 for token_info in auth_tokens}
        good_accounts = set([token_info['token'] for token_info in auth_tokens])
        total_count = 0

        while all(count < self.messages_count for count in messages_sent.values()) and good_accounts:
            if total_count >= self.messages_count:
                break

            item_ids = await start_parser(country=self.country_code, item_count=len(good_accounts))
            self.number_tryies_to_parse += 1
            if self.number_tryies_to_parse >= 100:
                return self.bad_accounts, good_accounts

            print("")
            if len(item_ids) < len(good_accounts):
                logger.warning(f"Ошибка парсинга. Причина: [Было спаршено всего {len(item_ids)}/{len(good_accounts)}]")
                return
            
            tasks = []
            for item, token_info in zip(item_ids, good_accounts):
                for auth_token in auth_tokens:
                    if token_info == auth_token['token']:
                        auth_token_ = auth_token['token']
                        account_name = auth_token['name']
                        tasks.append(asyncio.create_task(
                            self.handle_single_item(auth_token_, account_name, item['item_id'], item['item_url'], item['item_title'], ws_clients[auth_token_], responded_items[auth_token_], good_accounts)
                        ))

            total_count += 1
            try:
                await asyncio.gather(*tasks)
                for token_info in auth_tokens:
                    if token_info['token'] in good_accounts:
                        messages_sent[token_info['token']] += 1
            except Exception as e:
                logger.error(f'Ошибка во время процесса: {str(e)}')

            good_accounts = good_accounts - self.bad_accounts
            logger.info(f'Осталось хороших аккаунтов: {len(good_accounts)}/{len(auth_tokens)}')

            if not good_accounts:
                break

        return self.bad_accounts, good_accounts

    async def handle_single_item(self,
                                 auth_token, account_name,
                                 item_id, item_url, item_title, ws_client,
                                 responded_items, good_accounts):

        sended, all_txt = await ws_client.conncet_to_socket(self.parser_type, auth_token, item_id, account_name)

        if sended and len(all_txt) > 0:
            logger.success(f'[{account_name}] Успешно отправил сообщение на товар: "{item_title}" | Номер: {all_txt[-1] if len(all_txt[-1]) > 3 else '-'.join(all_txt[-3:])}')

            responded_items.add(item_id)
            if self.parser_type == 3:
                text = answer_text.format(
                    account_name=account_name,
                    messages_count=len(self.more_texts) if self.message_count_for_mamonth == 'more' else 1,
                    item_url=item_url, 
                    item_title=item_title
                )
            else:
                text = answer_text.format(
                    account_name=account_name,
                    messages_count=len(self.more_texts) if self.message_count_for_mamonth == 'more' else len(self.main_texts),
                    item_url=item_url, 
                    item_title=item_title
                )
            await self.message_queue.put(text)

            self.repository_hash.add_item_hash_in_file(account_name=account_name, item_hash=item_id)
            logger.info(f'[{account_name}] Запускаю процесс парсинга диалогов')
            good_accounts.add(auth_token)
            
            await self.parse_and_respond(auth_token, [item_id], ws_client,
                                         account_name)
        else:
            self.bad_accounts.add(auth_token)

        return good_accounts, self.bad_accounts

    async def parse_and_respond(self, auth_token, item_ids, ws_client,
                                account_name):
        url = 'https://api.wallapop.com/bff/messaging/inbox?page_size=30&max_messages=30'
        # try:
        async with aiohttp.ClientSession() as session:
            try:
            # Проверка на номера
                if self.parser_type == 1:
                    for index in range(60):
                        await asyncio.sleep(self.message_timeout)
                        headers_local: dict = self.headers
                        headers_local['Authorization'] = f'Bearer {auth_token}'
                        async with session.get(url, headers=headers_local, proxy=self.proxy) as response:
                            if response.status == 200:

                                data = await response.json()
                                read_messages, total_messages = count_read_messages(data)
                                phone_with_items = find_phone_with_item_hash(data, self.country_code)

                                if phone_with_items:
                                    for entry in phone_with_items:
                                        item_hash = entry['item_hash']
                                        email = entry['phone']
                                        item_url = entry['url']
                                        item_in_data = self.repository_hash.is_item_in_txt(account_name=account_name,item_hash=item_hash)

                                        if item_hash in self.finded_data_:
                                            logger.info(
                                                f'[{account_name}] Этот товар уже давал номер телефона: [{item_hash}]')
                                            continue

                                        if item_in_data:
                                            logger.success(
                                                f"[{account_name}] Мамонт отправил номер телефона: [{email}]")
                                            try:
                                                await asyncio.sleep(self.answer_timeout)
                                                sended = await ws_client.conncet_to_socket_(auth_token, item_hash)
                                                if sended:
                                                    logger.success(f'[{account_name}] Успешно отправил ответ на WallaPop')

                                                    text = phone_text.format(email=email, item_url=item_url)
                                                    await send_to_telegram(text)
                                                    self.finded_data_.add(item_hash)
                                                    self.repository_hash.remove_item_hash_from_txt(
                                                        account_name=account_name,
                                                        item_hash=item_hash)
                                            except Exception as e:
                                                logger.error(
                                                    f'[{account_name}] Не удалось отправить ответ на Wallapop | Причина: {str(e)}')
                                        # else:
                                        #     logger.info(
                                        #         f'[{account_name}] НЕТ НОВЫХ СООБЩЕНИЙ! [{index + 1}] | Прочитаных: {read_messages}/{total_messages}')

                                else:
                                    logger.info(
                                        f'[{account_name}] НЕТ НОВЫХ СООБЩЕНИЙ! [{index + 1}] | Прочитаных: {read_messages}/{total_messages}')
                                    continue
                            else:
                                text = await response.text()
                                logger.error(
                                    f'[{account_name}] Запрос на получение диалогов не 200 | Статус: {response.status} | Text: {text}')
                                if response.status == 403:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    moved = self.misc.move_account_with_spamlock(account_name=filename)
                                    if moved:
                                        logger.info(f'Успешно перенес аккаунт в папку "spammed_accounts"')
                                elif response.status == 401:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    if filename:
                                        moved = self.misc.move_bad_account(account_name=filename)
                                        if moved:
                                            logger.warning('Успешно перенес аккаунт в "bad_accounts"!')
                                break

                # Проверка на почты
                elif self.parser_type == 2:
                    for index in range(60):
                        await asyncio.sleep(self.message_timeout)
                        headers_local: dict = self.headers
                        headers_local['Authorization'] = f'Bearer {auth_token}'
                        async with session.get(url, headers=headers_local, ssl=True, proxy=self.proxy) as response:
                            if response.status == 200:
                                data = await response.json()

                                read_messages, total_messages = count_read_messages(data)
                                emails_with_items = find_emails_with_item_hash(data, self.country_code)

                                if emails_with_items:
                                    for entry in emails_with_items:

                                        item_hash = entry['item_hash']
                                        email = entry['email']
                                        item_url = entry['url']

                                        if item_hash in self.finded_data_:
                                            logger.info(f'Этот товар уже давал почту: [{item_hash}]')
                                            continue

                                        item_in_data = self.repository_hash.is_item_in_txt(account_name=account_name, item_hash=item_hash)

                                        if item_in_data:
                                            logger.success(f"[{account_name}] Мамонт отправил почту: [{email}]")
                                            try:
                                                await asyncio.sleep(self.answer_timeout)
                                                sended = await ws_client.conncet_to_socket_(auth_token, item_hash)
                                                if sended:
                                                    logger.success(
                                                        f'[{account_name}] Успешно отправил ответ на WallaPop')
                                                    text = email_text.format(email=email, item_url=item_url)
                                                    self.finded_data_.add(item_hash)
                                                    self.repository_hash.remove_item_hash_from_txt(account_name=account_name,
                                                                                                    item_hash=item_hash)
                                                    await send_to_telegram(text)


                                            except Exception as e:
                                                logger.error(
                                                    f'[{account_name}] Не удалось отправить ответ на Wallapop | Ошибка: {str(e)}')
                                        else:
                                            continue

                                else:
                                    logger.info(
                                        f'[{account_name}] НЕТ НОВЫХ СООБЩЕНИЙ! [{index + 1}] | Прочитаных: {read_messages}/{total_messages}')
                                    continue
                            else:
                                logger.error(
                                    f'[{account_name}] Не удалось получить диалоги | Статус: {response.status}')
                                if response.status == 403:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    moved = self.misc.move_account_with_spamlock(account_name=filename)
                                    if moved:
                                        logger.info(f'Успешно перенес аккаунт в папку "spammed_accounts"')
                                elif response.status == 401:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    if filename:
                                        moved = self.misc.move_bad_account(account_name=filename)
                                        if moved:
                                            logger.warning('Успешно перенес аккаунт в "bad_accounts"!')
                                break

                # Проверка на ответы на хеллоу.
                elif self.parser_type == 3:
                    for index in range(60):
                        await asyncio.sleep(self.message_timeout)
                        headers_local: dict = self.headers
                        headers_local['Authorization'] = f'Bearer {auth_token}'
                        async with session.get(url, headers=headers_local, ssl=True, proxy=self.proxy) as response:
                            if response.status == 200:
                                data = await response.json()

                                read_messages, total_messages = count_read_messages(data)
                                answer_with_items = check_if_mamont_sent_answer(data, self.country_code)

                                if answer_with_items:
                                    for entry in answer_with_items:
                                        self.read_finded_data()
                                        mamont_text = entry['text']
                                        item_hash = entry['item_hash']
                                        item_url = entry['url']
                                        item_ph = entry['item_photo']

                                        dialogue = self.finded_data.get(item_url, {})

                                        if mamont_text in dialogue.values():
                                            # logger.info(f'Этот мамонт уже вам отвечал: [{item_url}]')
                                            continue

                                        message_number = len(dialogue) + 1
                                        message_key = f"message_{message_number}"
                                        dialogue[message_key] = mamont_text

                                        self.finded_data[item_url] = dialogue
                                        self.save_finded_data()

                                        response_key = f"message_{message_number}"
                                        response_text = self.responses.get(response_key)

                                        if response_text:
                                            logger.info(
                                                f'[{account_name}] Подготовка ответа на сообщение мамонта [{item_url}]: [{mamont_text}]')
                                            item_in_data = self.repository_hash.is_item_in_txt(
                                                account_name=account_name,
                                                item_hash=item_hash)
                                            if item_hash not in self.answered_data:
                                                # text = answer_text.format(seller_message=mamont_text, item_url=item_url)
                                                # await send_photo_url_and_messages(text=text, photo=item_ph)
                                                self.answered_data.add(item_hash)
                                            if item_in_data:
                                                try:
                                                    await asyncio.sleep(self.answer_timeout)
                                                    sended = await ws_client.send_answer_to_seller(auth_token, item_hash, response_text)
                                                    if sended:
                                                        logger.success(
                                                            f'[{account_name}] Успешно отправил ответ мамонту [{item_url}]: [{mamont_text}] | Ответ: {response_text}')
                                                except Exception as e:
                                                    logger.error(
                                                        f'[{account_name}] Не удалось отправить ответ на Wallapop | Ошибка: {str(e)}')
                                                    try:
                                                        sended = await ws_client.send_answer_to_seller(auth_token,
                                                                                                        item_hash,
                                                                                                        response_text)
                                                        if sended:
                                                            logger.success(
                                                                f'[{account_name}] Успешно отправил ответ мамонту [{item_hash}]: [{mamont_text}] | Ответ: {response_text}')
                                                    except Exception:
                                                        pass
                                        else:
                                            continue
                                else:
                                    logger.info(
                                        f'[{account_name}] НЕТ НОВЫХ СООБЩЕНИЙ! [{index + 1}] | Прочитано: {read_messages}/{total_messages}')
                                    continue
                            else:
                                logger.error(
                                    f'[{account_name}] Не удалось получить диалоги | Статус: {response.status}')
                                if response.status == 403:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    moved = self.misc.move_account_with_spamlock(account_name=filename)
                                    if moved:
                                        logger.info(f'Успешно перенес аккаунт в папку "spammed_accounts"')
                                elif response.status == 401:
                                    filename = await self.misc.find_token_in_directory(auth_token=auth_token)
                                    if filename:
                                        moved = self.misc.move_bad_account(account_name=filename)
                                        if moved:
                                            logger.warning('Успешно перенес аккаунт в "bad_accounts"!')
                                break
            except Exception as e:
                logger.error(f'Случилась не предвиденная ошибка во время процесса парсинга | Причина: {str(e)}')

    async def run_processes_in_batches(self, auth_tokens, misc_client):
        await send_hi_to_telegram(hi_text)
        for i in range(0, len(auth_tokens), self.group_size):
            token_batch = auth_tokens[i:i + self.group_size]
            logger.info(f"Запускаю процесс для: {len(token_batch)} шт. токенов.")

            bad_accounts, good_accounts = await self.process_group(token_batch)

            good_for_move = await misc_client.search_tokens_on_files(good_accounts)

            is_moved = await misc_client.move_files_to_folders(good_for_move)
            if is_moved:
                logger.success(f'Успешно перенес в папку "spammed_accounts": {len(good_for_move)} шт.')

async def handle_refresh_all_tokens_task(token):
    client = WallapopClient(token)
    await client.refresh_access_and_ref_token()


async def handle_task(token, username):
    client = WallapopClient(token)
    we_in_acc = await client.CheckIfWeInAccount()
    if we_in_acc:
        logger.success(f'[{token[:10]}] Успешно авторизировался в аккаунт')
        city = await client.AddAddress()
        if city:
            logger.success(f'[{token[:10]}] Успешно установил адресс')
        else:
            logger.error(f'[{token[:10]}] Не удалось установить аддресс.')
        name = await client.ChangeUsername(username)
        if name:
            logger.success(f'[{token[:10]}] Успешно установил новый ник-нейм')
        else:
            logger.error(f'[{token[:10]}] Не удалось установить новый ник-нейм')
        ava = await client.UpdloadAvatar()
        if ava:
            logger.success(f'[{token[:10]}] Успешно установил аватарку!')
        else:
            logger.error(f'[{token[:10]}] Не удалось установить аватарку')
    else:
        logger.error('Не удалось войти в аккаунт!')

async def execute_proccess_refresh_tokens(tokens):
    tasks = []
    for item in tokens:
        token = item['token']
        tasks.append(handle_refresh_all_tokens_task(token))

    await asyncio.gather(*tasks)

async def execute_proccess_username_avatar(tokens, username):
    tasks = []
    for item in tokens:
        token = item['token']
        tasks.append(handle_task(token, username))

    await asyncio.gather(*tasks)


class Questions:
    def __init__(self):
        pass


    def global_question(self):
        user_input = int(input(f'Что будем делать? [1] - Установка аватарок и никнеймов | [2] - Обновить куки всех аккаунтов | [3] - Ничего из выше перечисленного:\n'))
        return user_input

    def custom_username_or_not(self):
        user_input = int(input(f'Какой никнейм используем?\n[1] Дефолтный (Wꜹllapop)\n[2] Кастомный (ваш)\n: '))
        return user_input

    def insert_custom_username(self):
        user_input = str(input(f'Укажите никнейм который желаете указать:\n'))
        return user_input

    def base_account_check(self):
        user_input = int(input(f'Желаете сделать базовую проверку аккаунтов перед запуском?\n[1] Да\n[2] Нет:\n'))
        return user_input



async def main():
    misc = Misc()
    all_texts = misc.get_all_texts()
    first_message = misc.get_text_for_message()
    second_message = misc.get_text_for_message_second()
    third_message = misc.get_text_for_message_third()
    fours_message = misc.get_text_for_message_four()
    more_texts = misc.get_more_texts_for_message()
    answer_message = misc.get_answer_message()
    auth_tokens = misc.return_tokens_from_files()
    repos_hash  = RepositoryHash()

    # Задержка в минутах между отправкой сообщений
    message_timeout = 3
    # IT - Италия, ES - Испания, PT - Португалия
    country_code = 'ES'

    # 1 - Чекаем на номер телефона. 2 - Чекаем на почту. 3 - Что-бы отправлять сообщения только после ответа мамонта
    parser_type = 1

    # Количество одновроменных сообщений 1 мамонту, например одна паста разбита на 3 части, соотвественно отправляем 3 текста. "more" - отправляет то количесчтво текстов, которое вы укажите в more.txt
    message_count_for_mamonth = 'main'

    # Количество одновременных аккаунтов которые отрабатываються. По дефолту 4!
    parallel_spam_count = 100

    # Количество отписок которые нужно сделать на 1 аккаунте.
    messages_count = 100

    # Время задержки (в секундах перед отправкой ответа мамонту на почту или номер телефона)
    answer_timeout = 5

    main_cl = Main(main_texts=all_texts, more_texts=more_texts, 
                   answer=answer_message, country_code=country_code, parser_type=parser_type, group_size=parallel_spam_count, messages_count=messages_count, repository_hash=repos_hash, answer_timeout=answer_timeout,message_timeout=message_timeout,
                   message_count_for_mamonth=message_count_for_mamonth)

    if len(auth_tokens) > 0:
        asyncio.create_task(main_cl.message_sender_worker())
        await main_cl.run_processes_in_batches(auth_tokens, misc_client=misc)
    else:
        logger.warning(f'У вас закончились куки! Закиньте их в папку "cookies"!')

async def all_proccess(misc):
    q = Questions()
    g = q.global_question()
    bad = misc.move_accounts_without_tokens()
    if len(bad) > 0:
        logger.info(f'Перед запуском удалил все невалидные куки: [{len(bad)}]')
    else:
        logger.info('Все аккаунты валидны')

    tokens = misc.return_tokens_from_files()
    if g == 1:
        cn = q.custom_username_or_not()
        username = q.insert_custom_username() if cn == 2 else default_username
        logger.info(f'Запускаю процесс с ником: {username}, для аккаунтов: {len(tokens)} шт.')
        await execute_proccess_username_avatar(tokens=tokens, username=username)
        logger.success('Успешно установил автараки + ники')
    elif g == 2:
        d = await execute_proccess_refresh_tokens(tokens=tokens)
        if d:
            logger.success('Успешно обновил куки у всех аккаунтов!')
    else:
        logger.info('Запускаю спамер!')
    await main()
    await asyncio.sleep(1)


if __name__ == "__main__":
    misc = Misc()
    asyncio.run(all_proccess(misc))