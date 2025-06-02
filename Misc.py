import asyncio
import glob
import random
import re
from typing import List
import aiofiles
import os
import shutil
import json

from loguru import logger
from telebot.apihelper import proxy


class Misc:
    def __init__(self):
        self.cookie_path = 'cookies'
        self.message_text_path = 'Texts/first.txt'
        self.all_texts = 'Texts/main.txt'
        self.answer_message_path = 'Texts/answer.txt'
        self.message_text_path_ = 'Texts/second.txt'
        self.message_text_path__ = 'Texts/third.txt'
        self.message_text_path___ = 'Texts/four.txt'
        self.more_text_path = 'Texts/more.txt'
        self.items_hash_path = 'databases/item_hash.txt'

    def return_tokens_from_files(self):
        access_tokens = []
        if not os.path.exists(self.cookie_path):
            return access_tokens
        for filename in os.listdir(self.cookie_path):
            file_path = os.path.join(self.cookie_path, filename)
            account_name = file_path.split("\\")[1]
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()
                        try:
                            cookies_data = json.loads(file_content)
                            for cookie in cookies_data:
                                if cookie.get('name') == 'accessToken':
                                    access_token = cookie.get('value')
                                    access_tokens.append({"token": access_token, "name": account_name})
                        except json.JSONDecodeError:
                            print(f"File {filename} does not contain valid JSON")
                except Exception as e:
                    print(f"Error reading file {filename}: {e}")

        return access_tokens

    def move_accounts_without_tokens(self):
        bad = []
        if not os.path.exists(self.cookie_path):
            return

        without_tokens_folder = os.path.join(os.path.dirname(self.cookie_path), 'without_tokens')
        os.makedirs(without_tokens_folder, exist_ok=True)

        for filename in os.listdir(self.cookie_path):
            file_path = os.path.join(self.cookie_path, filename)

            if os.path.isfile(file_path):
                has_access_token = False
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        file_content = file.read()

                        try:
                            cookies_data = json.loads(file_content)

                            for cookie in cookies_data:
                                if cookie.get('name') == 'accessToken':
                                    has_access_token = True
                                    break

                        except json.JSONDecodeError:
                            print(f"File {filename} does not contain valid JSON")

                except Exception as e:
                    print(f"Error reading file {filename}: {e}")

                if not has_access_token:
                    bad.append(filename)
                    shutil.move(file_path, os.path.join(without_tokens_folder, filename))
        return bad

    async def search_tokens_on_files(self, good):
        good_move = []

        if not os.path.exists(self.cookie_path):
            return good_move

        for filename in os.listdir(self.cookie_path):
            file_path = os.path.join(self.cookie_path, filename)

            if os.path.isfile(file_path):
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                        file_content = await file.read()

                        try:
                            cookies_data = json.loads(file_content)
                            for cookie in cookies_data:
                                if cookie.get('name') == 'accessToken':
                                    access_token = cookie.get('value')

                                    if access_token in good:
                                        good_move.append(file_path)
                                    break

                        except json.JSONDecodeError:
                            print(f"File {filename} does not contain valid JSON")

                except Exception as e:
                    print(f"Error reading file {filename}: {e}")

        return good_move


    def reformat_cookie_to_string(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
            cookie_list = []
            for cookie in cookies:
                name = cookie['name']
                value = cookie['value']
                cookie_list.append(f'{name}={value}')

            final_cookie_string = '; '.join(cookie_list)
            return final_cookie_string

    async def move_files_to_folders(self, good_move):
        spammed_folder = 'spammed_accounts'
        os.makedirs(spammed_folder, exist_ok=True)
        for file in good_move:
            destination = os.path.join(spammed_folder, os.path.basename(file))
            shutil.move(file, destination)
        return True

    def get_text_for_message(self):
        with open(self.message_text_path, 'r', encoding='utf-8') as f:
            text = f.read()
            return text
##############
    def get_all_texts(self):
        with open(self.all_texts, 'r', encoding='utf-8') as f:
            og_texts = f.read().strip().splitlines()
            phone_numbers = []
            phone_list = []
            for text in og_texts:
                if any(char.isnumeric() for char in text):
                    if len(text) <= 3:
                        phone_list.append(text)
                    else:
                        phone_numbers.append(text)
            
            if len(phone_list) > 0:
                filtered_list = [item for item in og_texts if item not in phone_list]
                for phone in phone_list:
                    filtered_list.append(phone)
                return filtered_list
            else:
            # print(phone_list)
                random.shuffle(phone_numbers)
                filtered_list = [item for item in og_texts if item not in phone_numbers]
                filtered_list.append(phone_numbers[0])
                return filtered_list


    def get_text_for_message_second(self):
        with open(self.message_text_path_, 'r', encoding='utf-8') as f:
            text = f.read()
            return text

    def get_text_for_message_third(self):
        with open(self.message_text_path__, 'r', encoding='utf-8') as f:
            text = f.read()
            return text

    def get_text_for_message_four(self):
        with open(self.message_text_path___, 'r', encoding='utf-8') as f:
            text = f.read()
            return text
        
    def get_more_texts_for_message(self):
        with open(self.more_text_path, 'r', encoding='utf-8') as f:
            return f.read().splitlines()
        
    def get_answer_message(self):
        with open(self.answer_message_path, 'r', encoding='utf-8') as f:
            text = f.read()
            return text

    async def find_token_in_directory(self, auth_token, directory_path='cookies'):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                        file_content = await file.read()
                        cookies = json.loads(file_content)

                        for cookie in cookies:
                            if cookie.get('name') == 'accessToken' and cookie.get('value') == auth_token:
                                return filename
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
        return None

    def move_bad_account(self, account_name):
        bad_folder = 'bad_accounts'
        os.makedirs(bad_folder, exist_ok=True)
        try:
            destination = os.path.join(bad_folder, os.path.basename(f'cookies/' + account_name))
            shutil.move(f'cookies/' + account_name, destination)
            return True
        except Exception as e:
            logger.error(f"Error moving account {account_name}: {e}")
            return False

    def move_account_with_spamlock(self, account_name):
        bad_folder = 'spammed_accounts'
        os.makedirs(bad_folder, exist_ok=True)
        try:
            destination = os.path.join(bad_folder, os.path.basename(f'cookies/' + account_name))
            shutil.move(f'cookies/' + account_name, destination)
            return True
        except Exception as e:
            logger.error(f"Error moving account {account_name}: {e}")
            return False

    def add_item_hash_in_txt(self, item_hash):
        with open(self.items_hash_path, 'a') as f:
            f.write(f"{item_hash}\n")

    def remove_item_hash_from_txt(self, item_hash):
        with open(self.items_hash_path, 'r') as f:
            lines = f.readlines()
        lines = [line for line in lines if line.strip() != item_hash]
        with open(self.items_hash_path, 'w') as f:
            f.writelines(lines)

    def is_item_in_txt(self, item_hash):
        with open(self.items_hash_path, 'r') as f:
            for line in f:
                if line.strip() == str(item_hash):
                    return True
        return False


def count_read_messages(data):
    total_messages = 0
    read_messages = 0

    for conversation in data['conversations']:
        messages = conversation.get('messages', {}).get('messages', [])
        if messages:
            for message in messages:
                from_self = message.get('from_self')
                if from_self:
                    total_messages += 1
                    if message.get('status') == 'read':
                        read_messages += 1
                else:
                    continue

    return read_messages, total_messages


mails = [
    'a.baccolini944 gmail.com', 'edoardogiovinazzogmail.com', 'Miae-mailedoluciniYahoo.it',
    'iaia1988erica hotmail.it', 'ariannalalli hotmail.it', 'laspinaalessia@hotmail.it', 'puslin@libero.it',
    'spacebasis38.yahoo.it', 'Veronikandreyeva Hotmail.com', 'isabella.sfregola27 gmail.com',
    'Gladietor77gmail.com', 'lauramari67libero.it', 'paolo.vitalis gmail com', 'Grafichesangiorgio.libero',
    'Melonikatiagmail.com', 'annalisaleone1427 gmail.com', 'elenagrassi03 icloud.com', 'Melonikatiagmail.com',
    'annalisaleone1427 gmail.com', 'elenagrassi03 icloud.com', 'a.baccolini944 gmail.com',
    'edoardogiovinazzogmail.com', 'Miae-mailedoluciniYahoo.it', 'iaia1988erica hotmail.it',
    'ariannalalli hotmail.it', 'laspinaalessia@hotmail.it', 'puslin@libero.it', 'spacebasis38.yahoo.it',
    'Veronikandreyeva Hotmail.com', 'isabella.sfregola27 gmail.com', 'Gladietor77gmail.com',
    'lauramari67libero.it', 'paolo.vitalis gmail com', 'Grafichesangiorgio.libero',
    'rossellaautiero2000icloud.it', 'Dr.claudio.turcoVirgilio.it',
    'fede.y13zGmail.com', 'Andyone774@gmail.com'
]

known_domains = [
    'gmail.com', 'gmail.co.uk', 'gmail.de', 'gmail.fr', 'gmail.it', 'gmail.es',
    'gmail.ca', 'gmail.com.au', 'gmail.com.br', 'gmail.com.mx', 'gmail.co.in',
    'gmail.com.sg', 'gmail.com.hk', 'gmail.com.tw', 'gmail.co.jp',

    'yahoo.com', 'yahoo.co.uk', 'yahoo.de', 'yahoo.fr', 'yahoo.it', 'yahoo.es',
    'yahoo.ca', 'yahoo.com.au', 'yahoo.com.br', 'yahoo.com.mx', 'yahoo.co.in',
    'yahoo.com.sg', 'yahoo.com.hk', 'yahoo.com.tw', 'yahoo.co.jp',

    'hotmail.com', 'hotmail.co.uk', 'hotmail.de', 'hotmail.fr', 'hotmail.it', 'hotmail.es',
    'hotmail.ca', 'hotmail.com.au', 'hotmail.com.br', 'hotmail.com.mx', 'hotmail.co.in',
    'hotmail.com.sg', 'hotmail.com.hk', 'hotmail.com.tw', 'hotmail.co.jp',
    'outlook.com', 'outlook.co.uk', 'outlook.de', 'outlook.fr', 'outlook.it', 'outlook.es',
    'outlook.ca', 'outlook.com.au', 'outlook.com.br', 'outlook.com.mx', 'outlook.co.in',
    'outlook.com.sg', 'outlook.com.hk', 'outlook.com.tw', 'outlook.co.jp',

    'libero.it', 'libero.com',

    'icloud.com', 'icloud.it',

    'aol.com', 'aol.co.uk', 'aol.de', 'aol.fr', 'aol.it', 'aol.es',
    'aol.ca', 'aol.com.au', 'aol.com.br', 'aol.com.mx', 'aol.co.in',
    'aol.com.sg', 'aol.com.hk', 'aol.com.tw', 'aol.co.jp',

    'protonmail.com', 'protonmail.ch',

    'zoho.com', 'zoho.eu', 'zoho.in',

    'gmx.com', 'gmx.net', 'gmx.de',

    'yandex.com', 'yandex.ru', 'yandex.net',

    'mail.com', 'mail.net', 'mail.de', 'mail.fr', 'mail.it', 'mail.es',

    'example.com', 'example.net', 'example.org', 'example.co.uk', 'example.de',
    'example.fr', 'example.it', 'example.es', 'example.ca', 'example.com.au',
    'example.com.br', 'example.com.mx', 'example.co.in', 'example.com.sg',
    'example.com.hk', 'example.com.tw', 'example.co.jp',

    'virgilio.it', 'live.com', 'live.co.uk', 'live.de', 'live.fr', 'live.it', 'live.es',
    'live.ca', 'live.com.au', 'live.com.br', 'live.com.mx', 'live.co.in',
    'live.com.sg', 'live.com.hk', 'live.com.tw', 'live.co.jp',

    'edu.au', 'edu.cn', 'edu.de', 'edu.fr', 'edu.in', 'edu.it', 'edu.ru',
    'ac.uk', 'ac.jp', 'ac.in', 'ac.nz', 'ac.za', 'ac.kr',

    'gov.uk', 'gov.au', 'gov.cn', 'gov.de', 'gov.fr', 'gov.in', 'gov.it',
    'gov.ru', 'gov.sg',

    'hotmail.be', 'hotmail.gr', 'hotmail.nl', 'hotmail.no', 'hotmail.pl',
    'hotmail.se', 'hotmail.ch', 'hotmail.be', 'hotmail.gr', 'hotmail.nl',
    'hotmail.no', 'hotmail.pl', 'hotmail.se', 'hotmail.ch',

    'mailinator.com', 'dispostable.com', 'temporary-mail.net',
    'trashmail.com', '10minutemail.com', 'guerrillamail.com',
    'getnada.com', 'temp-mail.org',

    'hotmail.co.za', 'hotmail.co.kr', 'hotmail.co.nz', 'hotmail.co.in',
    'hotmail.co.id', 'hotmail.co.th', 'hotmail.com.tr', 'hotmail.com.sa',

    'business.com', 'enterprise.com', 'corporate.com', 'company.com',
]

def preprocess_email(mail):
    mail = re.sub(r'\s*\(?\b[Aa][Tt]\b\)?\s*', '@', mail)
    mail = re.sub(r'\s*\(?\b[Dd][Oo][Tt]\b\)?\s*', '.', mail)
    mail = re.sub(r'\s+', '.', mail)
    return mail

def insert_at_if_missing(mail):
    if '@' in mail:
        return mail

    for domain in known_domains:
        pattern = re.compile(re.escape(domain), re.IGNORECASE)
        match = pattern.search(mail)
        if match:
            index = match.start()
            new_mail = mail[:index] + '@' + mail[index:]
            new_mail = new_mail.replace('.@', '@')
            return new_mail

    known_domains_without_tld = set(domain.split('.')[0] for domain in known_domains)
    for domain in known_domains_without_tld:
        pattern = re.compile(r'\.' + re.escape(domain) + r'\b', re.IGNORECASE)
        match = pattern.search(mail)
        if match:
            index = match.start()
            new_mail = mail[:index] + '@' + mail[index:] + '.com'
            new_mail = new_mail.replace('.@', '@')
            return new_mail

    return mail

def check_mail_ended_gmail(mail: str):
    if mail[-5:].lower() == 'gmail':
        mail += '.com'
        return mail
    else:
        return None

def extract_email(mail):
    check_end_mail = check_mail_ended_gmail(mail=mail)
    if check_end_mail is not None:
        cleaned_mail = preprocess_email(check_end_mail)
        cleaned_mail = insert_at_if_missing(cleaned_mail)
        match = re.search(r'\b[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}\b', cleaned_mail)
        if match:
            return match.group()
        else:
            return None
    else:
        cleaned_mail = preprocess_email(mail)
        cleaned_mail = insert_at_if_missing(cleaned_mail)
        match = re.search(r'\b[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}\b', cleaned_mail)
        if match:
            return match.group()
        else:
            return None

def check_if_mamont_sent_answer(data, country):
    results = []

    for conversation in data['conversations']:
        # print(conversation)
        item_hash = conversation['item']['hash']
        item_slug = conversation['item']['slug']
        item_ph_url = conversation['item']['image_url']
        item_url = f'https://{country.lower()}.wallapop.com/item/{item_slug}'
        messages = conversation['messages']['messages']

        for message in messages:
            if not message.get('from_self', False):
                text = message.get('text', '')
                # logger.info(f'Сообщение от мамонта: {text}')
                # logger.info(f'Сообщение без пробелов: {text_no_spaces}')
                results.append({'text': text, 'item_hash': item_hash, 'url': item_url, 'item_photo': item_ph_url})

    return results


def find_emails_with_item_hash(data, country):
    results = []

    for conversation in data['conversations']:
        item_hash = conversation['item']['hash']
        item_slug = conversation['item']['slug']
        item_url = f'https://{country.lower()}.wallapop.com/item/{item_slug}'
        messages = conversation['messages']['messages']

        for message in messages:
            if not message.get('from_self', False):
                text = message.get('text', '')
                # logger.info(f'Сообщение от мамонта: {text}')
                text_no_spaces = text.replace(" ", "")
                # logger.info(f'Сообщение без пробелов: {text_no_spaces}')

                mail = extract_email(text)
                if not mail:
                    mail = extract_email(text_no_spaces)

                if mail:
                    results.append({'email': mail, 'item_hash': item_hash, 'url': item_url})

    return results


def find_phone_with_item_hash(data, country):
    phone_pattern = r'\+?\d{1,2}[/-]?\d{3}[/-]?\d{3}[/-]?\d{3}|\+?\d{1,2}[/-]?\d{2}[/-]?\d{2}[/-]?\d{2}[/-]?\d{2}|\d{3}[/-]?\d{3}[/-]?\d{3}'

    phone_regex = re.compile(phone_pattern)

    results = []

    for conversation in data['conversations']:
        item_hash = conversation['item']['hash']
        item_slug = conversation['item']['slug']
        item_url = f'https://{country.lower()}.wallapop.com/item/{item_slug}'
        messages = conversation['messages']['messages']

        for message in messages:
            if not message.get('from_self', False):
                text = message.get('text', '')
                text_no_spaces = text.replace(" ", "")
                # logger.info(f'Сообщение от мамонта: {text_no_spaces}')
                found_phones = set()

                matches = phone_regex.findall(text_no_spaces)
                found_phones.update(matches)

                if found_phones:
                    for phone in found_phones:
                        results.append({'phone': phone, 'item_hash': item_hash, 'url': item_url})

    return results
