import asyncio
import os
import random
import ssl
from datetime import datetime
import uuid
import base64

import aiohttp
import certifi
import websockets
from loguru import logger

from Misc import Misc
from config import PROXY




class WebSocket:
    def __init__(self, main_text, more_texts, answer_message, messages_count_for_mamonth):
        self.websocket_headers = {
            "Host": "mongooseimprotool-prod.wallapop.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.6834.78 Mobile/15E148 Safari/604.1",
            "Upgrade": "websocket",
            "Origin": "https://es.wallapop.com",
            "Sec-Websocket-Version": "13",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "es-ES,es;q=0.9",
            "Sec-Websocket-Key": "GceFbYlSokSAghHb+Ts21w==",
            "Sec-Websocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Sec-Websocket-Protocol": "xmpp",

        }
        self.timestamp = datetime.utcnow().isoformat() + 'Z'
        self.proxy = PROXY
        self.client = aiohttp.ClientSession()
        self.resource = self.generate_resource()
        self.cerf = ssl.create_default_context(cafile=certifi.where())
        self.cert_path = '_wallapop.com.pem'
        self.answer_message = answer_message
        self.messages_count_for_mamonth = messages_count_for_mamonth
        self.more_texts = more_texts
        self.main_texts = main_text

    def encode_base_auth(self, my_user_id: str, token: str):
        string_with_nulls = f'\x00{my_user_id}\x00{token}'
        byte_array = string_with_nulls.encode('utf-8')
        base64_encoded = base64.b64encode(byte_array)
        base64_string = base64_encoded.decode('utf-8')
        return base64_string

    def generate_resource(self):
        import random
        # return f'v{random.randrange(100, 999)}_iPhone{random.randrange(6, 16)},{random.randrange(1, 12)}_iOS{random.randrange(14, 18)}.{random.randrange(1, 9)}.{random.randrange(1, 9)}_{random.randrange(1, 9)}XR{random.randrange(1, 9)}N'
        return f'{random.randrange(1000000000000, 9999999999999)}'


    async def get_my_user_id(self, client_headers):
        url = 'https://api.wallapop.com/api/v3/users/me/'
        async with self.client.get(
            url=url, 
            headers=client_headers, 
            ssl=self.cerf,
            proxy=self.proxy
            ) as response:
            if response.status == 401:
                # logger.error(f'Причина: [Акккаунт слетел/забанен]')
                return None
            elif response.status == 200:
                data = await response.json()
                user_id = data['id']
                return user_id
            else:
                return None

    async def get_info(self, item_id: str, client_headers, auth_token):
        """Функция возращает айди чата и так же айди юзера с которым мы общаемся
        Если происходит ошибка то функция возращает False.
        """
        url_conversations = 'https://api.wallapop.com/api/v3/conversations'
        data = {"item_id": item_id}

        async with self.client.post(
                url=url_conversations,
                headers=client_headers,
                json=data, ssl=self.cerf,
                proxy=self.proxy
        ) as response:
            if response.status == 200:
                response_data = await response.json()
                conversation_id = response_data.get("conversation_id")
                other_user_id = response_data.get("other_user_id")
                if conversation_id and other_user_id:
                    return conversation_id, other_user_id
                else:
                    return False
            elif response.status == 401:
                data = await response.text()
                file_name = await Misc().find_token_in_directory(auth_token=auth_token)
                logger.error(f'[{file_name}] Причина: [Акккаунт слетел] | Статус-Код: [{response.status}] | 401 - Аккаунт слетел | Data: {data}')
                Misc().move_bad_account(account_name=file_name)
                logger.warning(f'Успешно перенес аккаунт в "bad_accounts"!')
                await self.client.close()
                return False

            elif response.status == 403:
                file_name = await Misc().find_token_in_directory(auth_token=auth_token)
                logger.error(f'[{file_name}] Причина: [Cпамлок] | Статус-Код: [{response.status}] | 403 - Спам-Лок')
                Misc().move_account_with_spamlock(account_name=file_name)
                logger.warning(f'Успешно перенес аккаунт в "spammed_accounts"!')
                await self.client.close()
                return False

            elif response.status == 429:
                file_name = await Misc().find_token_in_directory(auth_token=auth_token)
                logger.error(f'[{file_name}] Причина: [Прокси] | Статус-код: [{response.status}] | 429 - Ограничение запросов на 1 ип')
                Misc().move_account_with_spamlock(account_name=file_name)
                logger.warning(f'Успешно перенес аккаунт в "spammed_accounts"!')
                await self.client.close()
                return False
            else:
                data = await response.json()
                logger.warning(f'ОШИБКА ПОЛУЧЕНИЯ АЙДИШКИ ДИАЛОГА: {response.status} | Data: {data}')

    # async def send_and_receive(self, ws, message):
    #     # print(f'Отправил: {message}')
    #     await ws.send(message)
    #     # await ws.send(message)
    #     async for msg in ws:
    #         # print(f'Получил: {msg}')
    #         if "<stream:error>" in msg:
    #             return False
    #         else:
    #             return True

    async def send_and_receive(self, ws: aiohttp.ClientWebSocketResponse, message: str) -> bool:
        await asyncio.sleep(0.25)
        await ws.send_str(message)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                if "<stream:error>" in msg.data:
                    return False
                else:
                    return True
            elif msg.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                return False

    async def send_message_(self, ws, account_name, my_user_id, other_user_id, conversation_id, msg_id, message):
        messages_two = [
            f'<r xmlns="urn:xmpp:sm:3"/>',
            f'''<message xmlns="jabber:client" id="{msg_id}" to="{other_user_id}@wallapop.com" from="{my_user_id}@wallapop.com/WEB_{self.resource}" type="chat">
            <thread>{conversation_id}</thread>
            <request xmlns="urn:xmpp:receipts"/>
            <body>{message}</body>
            </message>'''
        ]
        for message_ in messages_two:
            response = await self.send_and_receive(ws, message_)
            if not response:
                logger.error(f"[{account_name}] Причина [Ошибка во время отправки сообщения через WebSocket]")
                return False
        return True


    async def conncet_to_socket(self, messages_parser_type, auth_token, item_id, account_name):
        from uuid import uuid4
        import random
        try:
            client_headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Deviceid": f"{uuid4()}",
                "X-Deviceos": "0",
                "Sec-Ch-Ua-Mobile": "?1",
                "Mpid": f"-{random.randrange(1000000000000000000, 9999999999999999999)}",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.6834.78 Mobile/15E148 Safari/604.1",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/plain, */*",
                "Deviceos": "0",
                "X-Appversion": "82520",
                "Sec-Ch-Ua-Platform": '"Android"',
                "Origin": "https://es.wallapop.com",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://es.wallapop.com/",
                "Accept-Encoding": "gzip, deflate, br", 
                "Accept-Language": "es-ES,es;q=0.9",
                "Priority": "u=1, i",
                "Connection": "keep-alive"
            }
            try:
                conversation_id, other_user_id = await self.get_info(item_id, client_headers, auth_token)
                if not conversation_id or not other_user_id:
                    logger.error(f"[{account_name}] Не смог получить информацию об диалоге")
                    return False, []
            except Exception as e:
                logger.error(f'[{account_name}] Ошибка при получение айдишки диалога | {str(e)}')
                return False, []
            try:
                my_user_id = await self.get_my_user_id(client_headers)
                if not my_user_id:
                    logger.error(f"[{account_name}] Не получилось получить мой ид")
                    return False, []
            except Exception:
                logger.error(f'[{account_name}] Ошибка во время получения айдишки нашего акка')
                return False, []
            try:
            
                url_inbox = 'https://api.wallapop.com/bff/messaging/inbox?page_size=30&max_messages=30'
                # url_inbox = 'http://httpbin.org/ip'
                async with self.client.get(url_inbox, 
                                           headers=client_headers, 
                                           ssl=self.cerf, 
                                           proxy=self.proxy
                                        ) as response:
                    if response.status == 200:
                        os.environ['http_proxy'] = self.proxy
                        os.environ['https_proxy'] = self.proxy
                        base64_string = self.encode_base_auth(my_user_id, auth_token)
                        url = 'wss://mongooseimprotool-prod.wallapop.com/ws-xmpp'
                        misc = Misc()
                        try:
                            msg_id = str(uuid.uuid4())
                            ssl_context = ssl.SSLContext()
                            async with aiohttp.ClientSession() as session:
                                async with session.ws_connect(
                                    url,
                                    protocols=['xmpp'],
                                    headers=self.websocket_headers,
                                    ssl=ssl_context,
                                    proxy=self.proxy
                                ) as ws:
                            # async with websockets.connect(url, ping_interval=20, ping_timeout=None, subprotocols=['xmpp'],
                            #                               extra_headers=self.websocket_headers, ssl=ssl_context) as ws:
                            # async with proxy_connect(url, proxy=self.pr, subprotocols=['xmpp'], extra_headers=self.websocket_headers) as ws:
                                    messages = [
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{base64_string}</auth>''',
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{msg_id}"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>WEB_{self.resource}</resource></bind></iq>''',
                                        f'<enable xmlns="urn:xmpp:sm:3" resume="1"/>',
                                        f'<r xmlns="urn:xmpp:sm:3"/>',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></iq>''',
                                        f'''<presence xmlns="jabber:client" id="{str(uuid.uuid4())}"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><enable xmlns="urn:xmpp:carbons:2"/></iq>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><default name="public"/></query></iq>''',
                                        f'''<iq xmlns="jabber:client" type="get" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><list name="public"/></query></iq>''',
                                    ]
                                    for message in messages:
                                        response = await self.send_and_receive(ws, message)

                                        if not response:
                                            logger.error(f"[{account_name}] Причина [Ошибка во время отправки сообщения через WebSocket]")
                                            return False, []
                                        
                                    # Отправка мамонту только 1 сообщения
                                    if self.messages_count_for_mamonth == 'main':
                                        if messages_parser_type == 3:
                                            sended = await self.send_message_(ws=ws, account_name=account_name,
                                            my_user_id=my_user_id,
                                            other_user_id=other_user_id,
                                            conversation_id=conversation_id,
                                            msg_id=msg_id,
                                            message=self.main_texts[0])
                                        else:
                                            for index, text in enumerate(self.main_texts):
                                                sended = await self.send_message_(ws=ws, account_name=account_name,
                                                my_user_id=my_user_id,
                                                other_user_id=other_user_id,
                                                conversation_id=conversation_id,
                                                msg_id=str(uuid.uuid4()) if index > 0 else msg_id,
                                                message=text)

                                        if not sended:
                                            return False, []

                                    elif self.messages_count_for_mamonth == 'more':
                                        for index, text in enumerate(self.more_texts): 
                                            await self.send_message_(
                                                ws=ws,
                                                account_name=account_name,
                                                my_user_id=my_user_id,
                                                other_user_id=other_user_id,
                                                conversation_id=conversation_id,
                                                msg_id=str(uuid.uuid4()) if index > 0 else msg_id,
                                                message=text
                                            )

                                return True, self.main_texts
                        except websockets.InvalidHandshake as e:
                            logger.error(f"[{account_name}] Ошибка при рукопожатии WebSocket: {e}")
                            return False, []
                        except ssl.SSLError as e:
                            logger.error(f"[{account_name}] Ошибка SSL: {e}")
                            return False, []
                        except Exception:
                            return False, []

                    else:
                        logger.error(f"[{account_name}] Причина: [{response.status}] статус код. Если статус код: 403 то значит что на аккаунт накинули спамлок.")
                        return False, []
            except Exception as e:
                logger.error(f'[{account_name}] Ошибка в запросе на диалоги: {e}')
                return False, []

        except Exception as e:
            logger.error(f'Ошибка: {e}')
            return False, []

    async def conncet_to_socket_(self, auth_token, item_id):
        from uuid import uuid4
        try:
            client_headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Deviceid": f"{uuid4()}",
                "X-Deviceos": "0",
                "Sec-Ch-Ua-Mobile": "?1",
                "Mpid": f"-{random.randrange(1000000000000000000, 9999999999999999999)}",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.6834.78 Mobile/15E148 Safari/604.1",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/plain, */*",
                "Deviceos": "0",
                # "X-Appversion": "82520",
                # "Sec-Ch-Ua-Platform": '"Android"',
                "Origin": "https://es.wallapop.com",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://es.wallapop.com/",
                "Accept-Encoding": "gzip, deflate, br", 
                "Accept-Language": "es-ES,es;q=0.9",
                "Priority": "u=1, i",
                "Connection": "keep-alive"
            }
            try:
                conversation_id, other_user_id = await self.get_info(item_id, client_headers, auth_token)
                if not conversation_id or not other_user_id:
                    logger.error(f"[{item_id}] Не смог получить информацию об диалоге")
                    return False
            except Exception:
                logger.error('Ошибка при получение айдишки диалога')
            try:
                my_user_id = await self.get_my_user_id(client_headers)
                if not my_user_id:
                    logger.error(f"[{item_id}] Не получилось получить мой ид")
                    return False
            except Exception:
                logger.error('Ошибка во время получения айдишки нашего акка')
            try:
                msg_id = str(uuid.uuid4())

                url_inbox = 'https://api.wallapop.com/bff/messaging/inbox?page_size=15&max_messages=15'
                # url_inbox = 'http://httpbin.org/ip'
                async with self.client.get(
                    url_inbox, 
                    headers=client_headers, 
                    ssl=self.cerf, 
                    proxy=self.proxy
                    ) as response:
                    if response.status == 200:
                        os.environ['http_proxy'] = self.proxy
                        os.environ['https_proxy'] = self.proxy
                        base64_string = self.encode_base_auth(my_user_id, auth_token)
                        url = 'wss://mongooseimprotool-prod.wallapop.com/ws-xmpp'
                        try:
                            ssl_context = ssl.SSLContext()
                            async with aiohttp.ClientSession() as session:
                                async with session.ws_connect(
                                    url,
                                    protocols=['xmpp'],
                                    headers=self.websocket_headers,
                                    ssl=ssl_context,
                                    proxy=self.proxy
                                ) as ws:
                                    messages = [
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{base64_string}</auth>''',
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>WEB_{self.resource}</resource></bind></iq>''',
                                        f'<enable xmlns="urn:xmpp:sm:3" resume="1"/>',
                                        f'<r xmlns="urn:xmpp:sm:3"/>',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></iq>''',
                                        f'''<presence xmlns="jabber:client" id="{str(uuid.uuid4())}"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><enable xmlns="urn:xmpp:carbons:2"/></iq>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><default name="public"/></query></iq>''',
                                        f'''<iq xmlns="jabber:client" type="get" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><list name="public"/></query></iq>''',
                                    ]
                                    for message in messages:
                                        response = await self.send_and_receive(ws, message)

                                        if not response:
                                            logger.error(f"Причина [Ошибка во время отправки сообщения через WebSocket]")
                                            return False
                                    messages_two = [
                                        f'<r xmlns="urn:xmpp:sm:3"/>',
                                        f'''<message xmlns="jabber:client" id="{str(uuid.uuid4())}" to="{other_user_id}@wallapop.com" from="{my_user_id}@wallapop.com/WEB_{self.resource}" type="chat">
                                        <thread>{conversation_id}</thread>
                                        <request xmlns="urn:xmpp:receipts"/>
                                        <body>{self.answer_message}</body>
                                        </message>'''
                                    ]
                                    for message in messages_two:
                                        logger.info('Ответ отправлен')
                                        response = await self.send_and_receive(ws, message)

                                        if not response:
                                            logger.error(f"Причина [Ошибка во время отправки сообщения через WebSocket]")
                                            return False

                                return True
                        except websockets.InvalidHandshake as e:
                            logger.error(f"Ошибка при рукопожатии WebSocket: {e}")
                            return False
                        except ssl.SSLError as e:
                            logger.error(f"Ошибка SSL: {e}")
                            return False
                        except Exception as e:
                            logger.error(f"Неожиданная ошибка в WebSocket соединении: {e}")
                            return False

                    else:
                        logger.error(f"Причина: [{response.status}] статус код. Если статус код: 403 то значит что на аккаунт накинули спамлок.")
                        return False
            except Exception:
                logger.error('Ошибка в запросе на диалоги')
                return False

        except Exception as e:
            logger.error(f'Ошибка: {e}')
            return False

    async def send_answer_to_seller(self, auth_token, item_id, response_text):
        from uuid import uuid4
        try:
            client_headers = {
                "Authorization": f"Bearer {auth_token}",
                "X-Deviceid": f"{uuid4()}",
                "X-Deviceos": "0",
                "Sec-Ch-Ua-Mobile": "?1",
                "Mpid": f"-{random.randrange(1000000000000000000, 9999999999999999999)}",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/132.0.6834.78 Mobile/15E148 Safari/604.1",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, text/plain, */*",
                "Deviceos": "0",
                # "X-Appversion": "82520",
                # "Sec-Ch-Ua-Platform": '"Android"',
                "Origin": "https://es.wallapop.com",
                "Sec-Fetch-Site": "same-site",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://es.wallapop.com/",
                "Accept-Encoding": "gzip, deflate, br", 
                "Accept-Language": "es-ES,es;q=0.9",
                "Priority": "u=1, i",
                "Connection": "keep-alive"
            }
            try:
                conversation_id, other_user_id = await self.get_info(item_id, client_headers, auth_token)
                if not conversation_id or not other_user_id:
                    # logger.error(f"[{item_id}] Не смог получить информацию об диалоге")
                    return False
            except Exception:
                logger.error('Ошибка при получение айдишки диалога')
            try:
                my_user_id = await self.get_my_user_id(client_headers)
                if not my_user_id:
                    # logger.error(f"[{item_id}] Не получилось получить мой ид")
                    return False
            except Exception:
                logger.error('Ошибка во время получения айдишки нашего акка')
            try:
                msg_id = str(uuid.uuid4())

                url_inbox = 'https://api.wallapop.com/bff/messaging/inbox?page_size=30&max_messages=30'
                # url_inbox = 'http://httpbin.org/ip'
                async with self.client.get(
                    url_inbox, 
                    headers=client_headers, 
                    ssl=self.cerf, 
                    proxy=self.proxy
                    ) as response:
                    if response.status == 200:
                        os.environ['http_proxy'] = self.proxy
                        os.environ['https_proxy'] = self.proxy
                        base64_string = self.encode_base_auth(my_user_id, auth_token)
                        url = 'wss://mongooseimprotool-prod.wallapop.com/ws-xmpp'
                        try:
                            ssl_context = ssl.SSLContext()
                            # async with websockets.connect(url, ping_interval=20, ping_timeout=None, subprotocols=['xmpp'],
                            #                               extra_headers=self.websocket_headers, ssl=ssl_context,) as ws:
                            async with aiohttp.ClientSession() as session:
                                async with session.ws_connect(
                                    url,
                                    protocols=['xmpp'],
                                    headers=self.websocket_headers,
                                    ssl=ssl_context,
                                    proxy=self.proxy
                                ) as ws:
                                    messages = [
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<auth xmlns="urn:ietf:params:xml:ns:xmpp-sasl" mechanism="PLAIN">{base64_string}</auth>''',
                                        f'''<open xmlns="urn:ietf:params:xml:ns:xmpp-framing" version="1.0" xml:lang="en" to="wallapop.com"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><bind xmlns="urn:ietf:params:xml:ns:xmpp-bind"><resource>WEB_{self.resource}</resource></bind></iq>''',
                                        f'<enable xmlns="urn:xmpp:sm:3" resume="1"/>',
                                        f'<r xmlns="urn:xmpp:sm:3"/>',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><session xmlns="urn:ietf:params:xml:ns:xmpp-session"/></iq>''',
                                        f'''<presence xmlns="jabber:client" id="{str(uuid.uuid4())}"/>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><enable xmlns="urn:xmpp:carbons:2"/></iq>''',
                                        f'''<iq xmlns="jabber:client" type="set" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><default name="public"/></query></iq>''',
                                        f'''<iq xmlns="jabber:client" type="get" id="{str(uuid.uuid4())}"><query xmlns="jabber:iq:privacy"><list name="public"/></query></iq>''',
                                    ]
                                    for message in messages:
                                        response = await self.send_and_receive(ws, message)

                                        if not response:
                                            logger.error(f"Причина [Ошибка во время отправки сообщения через WebSocket]")
                                            return False
                                    messages_two = [
                                        f'<r xmlns="urn:xmpp:sm:3"/>',
                                        f'''<message xmlns="jabber:client" id="{str(uuid.uuid4())}" to="{other_user_id}@wallapop.com" from="{my_user_id}@wallapop.com/WEB_{self.resource}" type="chat">
                                        <thread>{conversation_id}</thread>
                                        <request xmlns="urn:xmpp:receipts"/>
                                        <body>{response_text}</body>
                                        </message>'''
                                    ]
                                    for message in messages_two:
                                        response = await self.send_and_receive(ws, message)

                                        if not response:
                                            logger.error(f"Причина [Ошибка во время отправки сообщения через WebSocket]")
                                            return False

                                return True
                        except websockets.InvalidHandshake as e:
                            logger.error(f"Ошибка при рукопожатии WebSocket: {e}")
                            return False
                        except ssl.SSLError as e:
                            logger.error(f"Ошибка SSL: {e}")
                            return False
                        except Exception as e:
                            logger.error(f"Неожиданная ошибка в WebSocket соединении: {e}")
                            return False

                    else:
                        logger.error(f"Причина: [{response.status}] статус код. Если статус код: 403 то значит что на аккаунт накинули спамлок.")
                        return False
            except Exception:
                logger.error('Ошибка в запросе на диалоги')
                return False

        except Exception as e:
            logger.error(f'Ошибка: {e}')
            return False


# async def main():
#     c = WebSocket('', '', '', 10, 2)
#     cl = c.generate_resource()
#     print(cl)


# asyncio.run(main())