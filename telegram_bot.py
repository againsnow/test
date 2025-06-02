import asyncio
from io import BytesIO
import ssl
from dotenv import load_dotenv
import os
from aiogram.types import BufferedInputFile
from aiogram import Bot, Dispatcher, types
import requests
import aiohttp


load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("USER_ID")
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def send_to_telegram(text):
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')

async def send_hi_to_telegram(text):
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

def ignore_ssl_errors():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


async def send_if_message_sended(text):
    import random
    await asyncio.sleep(random.uniform(0.5, 3))
    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML", disable_web_page_preview=False)
