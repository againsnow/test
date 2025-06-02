import json
import uuid
import aiohttp
from loguru import logger
from Misc import Misc
from config import PROXY


class WallapopClient:
    def __init__(self, token):
        self.session = aiohttp.ClientSession()
        self.proxy = PROXY
        self.device_id = str(uuid.uuid4())
        self.token = token
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Connection": "keep-alive",
            "Host": "api.wallapop.com",
            "Origin": "https://it.wallapop.com",
            "Referer": "https://it.wallapop.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "accept-language": "it,en;q=0.9,en-US;q=0.8",
            "authorization": f"Bearer {self.token}",
            "deviceos": "0",
            "mpid": "-6589998697460227517",
            "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "x-appversion": "83090",
            "x-deviceid": self.device_id,
            "x-deviceos": "0"
        }
        self.misc = Misc()

    async def CheckIfWeInAccount(self) -> bool:
        url = 'https://api.wallapop.com/api/v3/users/me'
        re = await self.session.get(url=url, headers=self.headers, proxy=self.proxy)
        if re.status == 200:
            return True
        else:
            return False


    async def refresh_access_and_ref_token(self):
        try:
            filename = await self.misc.find_token_in_directory(auth_token=self.token)
            cookie_string = self.misc.reformat_cookie_to_string(filename=f'cookies/{filename}')
        except Exception:
            logger.error(f'Случилась ошибка во времия получения исходных куки файлов.')
            await self.session.close()
            return False
        url = 'https://es.wallapop.com/wall'
        headers = {
            "host": "es.wallapop.com",
            "connection": "keep-alive",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "sec-fetch-site": "none",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
            "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "cookie": f"{cookie_string}"
        }
        try:
            async with self.session.get(url=url, headers=headers, proxy=self.proxy) as resp:
                if resp.status == 200:
                    try:
                        set_cookie_headers = resp.headers.getall('Set-Cookie')
                    except Exception:
                        logger.error(f'[{filename}] Не удалось получить новые куки из значения [Set-Cookie] | Возможно вы обновляли уже куки перед этим. Обновлять можно только 1 раз!')
                        await self.session.close()
                        return False
                    access_token = None
                    refresh_token = None

                    for cookie in set_cookie_headers:
                        if 'refreshToken' in cookie:
                            refresh_token = cookie.split(';')[0].split('=')[1]
                        if 'accessToken' in cookie:
                            access_token = cookie.split(';')[0].split('=')[1]

                    if access_token and refresh_token:
                        file_path = f'cookies/{filename}'
                        with open(file_path, 'r', encoding='utf-8') as file:
                            cookies = json.load(file)

                        for cookie in cookies:
                            if cookie['name'] == 'accessToken':
                                cookie['value'] = access_token
                            if cookie['name'] == 'refreshToken':
                                cookie['value'] = refresh_token
                        cookies_string = json.dumps(cookies, ensure_ascii=False)

                        with open(file_path, 'w', encoding='utf-8') as file:
                            file.write(cookies_string)
                        await self.session.close()
                        logger.success(f'[{filename}] Успешно обновил куки в файле!')
                        return True
                    else:
                        logger.error(f'[{filename}] Не нашел акссесс токен либо рефреш токен в ответе запроса!')
                        await self.session.close()
                        return False
                else:
                    logger.error(f'[{filename}] Запрос на обновление куки не 200 | Статус-код: [{resp.status}]')
                    self.misc.move_bad_account(filename)
                    await self.session.close()
                    return False
        except Exception:
            logger.error(f'[{filename}] Аккаунт невалдиный')
            self.misc.move_bad_account(filename)
            await self.session.close()
            return False
    # 39.4702393&longitude=-0.3768049
    async def AddAddress(self) -> bool:
        url = 'https://api.wallapop.com/api/v3/users/me/location'
        data = {"latitude": 39.4702393, "longitude": -0.3768049}
        self.headers.update({"content-type": "application/json"})
        re = await self.session.put(url=url, headers=self.headers,
                                    json=data, proxy=self.proxy)
        if re.status == 200:
            return True
        else:
            print(re.status)
            return False

    async def ChangeUsername(self, username) -> bool:
        url = 'https://api.wallapop.com/api/v3/users/me/'
        data = {
            "first_name": f"{username}",
            "birth_date": "1930-01-01",
            "gender": "U"
        }
        re = await self.session.post(url=url, headers=self.headers, json=data, proxy=self.proxy)
        if re.status == 200:
            data = await re.json()
            micro_name = data['micro_name']
            return micro_name
        else:
            print('Смена ника не 200')
            print(re.status)
            return False

    async def UpdloadAvatar(self) -> bool:
        self.headers.update({"content-type": "multipart/form-data; boundary=----WebKitFormBoundaryZz7KAALXJtq7Kqhx"})
        url = "https://api.wallapop.com/api/v3/users/me/image"

        boundary = "----WebKitFormBoundaryZz7KAALXJtq7Kqhx"
        payload = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="image"; filename="images1.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8')

        with open('avatar/images1.jpg', 'rb') as f:
            payload += f.read()

        payload += f'\r\n--{boundary}--\r\n'.encode('utf-8')

        re = await self.session.post(url, headers=self.headers, data=payload, proxy=self.proxy)
        if re.status == 204:
            await self.session.close()
            return True
        else:
            await self.session.close()
            print(re.status)
            return False