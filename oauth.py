from authlib.integrations.requests_client import OAuth1Session
from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.builtin import CommandStart, CommandHelp
from aiogram.dispatcher import FSMContext
from asyncpg import Connection, Record
from asyncpg.exceptions import UniqueViolationError
from config import trello_key, trello_secret
from aiogramcalendar import calendar_callback, create_calendar, process_calendar_selection
from states.date import Date
import socket
import re
from load_all import bot, dp, db
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
    
client_key = trello_key
client_secret = trello_secret
HOST = '84.201.165.21'


class DBCommands:
    pool: Connection = db
    CHECK_OAUTH_USER = "SELECT oauth_token, oauth_token_secret FROM users WHERE my_id=$1"
    GET_TOKEN = "SELECT oauth_token FROM users WHERE my_id=$1"
    GET_SECRET = "SELECT oauth_token_secret FROM users WHERE my_id=$1"
    ADD_NEW_USER = 'INSERT INTO users (my_id, first_name, second_name, oauth_token, oauth_token_secret) values($1, $2, $3, $4, $5) RETURNING my_id'
    async def check_user(self):
        command = self.CHECK_OAUTH_USER
        user = types.User.get_current()
        my_id = int(user.id)
        result = None
        args = (my_id,)
        try:
            result = await self.pool.fetchval(command, *args)
        except:
            print('Возникла ошибка в check_user')
        if result:
            return True
        else:
            return False

    async def oauth(self, oauth_token, oauth_token_secret):
        command = self.ADD_NEW_USER
        user = types.User.get_current()
        my_id = int(user.id)
        first_name = user.first_name
        second_name = user.last_name
        args = (my_id, first_name, second_name, oauth_token, oauth_token_secret)
        try:
            record_id = await self.pool.fetchval(command, *args)
            return record_id
        except UniqueViolationError:
            pass
    
    async def access(self):
        command_1 = self.GET_TOKEN
        command_2 = self.GET_SECRET
        user = types.User.get_current()
        my_id = int(user.id)
        result = None
        args = (my_id,)
        try:
            result_1 = await self.pool.fetchval(command_1, *args)
            result_2 = await self.pool.fetchval(command_2, *args)
            result = (result_1, result_2)
        except:
            print('Возникла ошибка в check_user')
        if result:
            return result
        else:
            return False

db = DBCommands()


@dp.message_handler(Command('oauth'))
async def oauth(message: types.Message):
    global oauth
    #global resource_owner_key
    #global resource_owner_secret
    id_user = message.from_user.id
    id_chat = message.chat.id
    check = await db.check_user()
    if check == False:
        if id_user != id_chat:
            bot_keyboard = types.InlineKeyboardMarkup()
            bot_keyboard.add(types.InlineKeyboardButton(text="Start dialog with bot", url='https://t.me/Shcherbatkin_Bot'))
            await message.answer("Начните диалог с ботом", reply_markup=bot_keyboard)
        else:
            request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
            oauth = OAuth1Session(client_key, client_secret=client_secret)
            oauth.redirect_uri = f'http://84.201.165.21:9090' # перенаправление на сервер
            fetch_response = oauth.fetch_request_token(request_token_url)
            resource_owner_key = fetch_response.get('oauth_token')
            resource_owner_secret = fetch_response.get('oauth_token_secret')
            base_authorization_url = 'https://trello.com/1/OAuthAuthorizeToken'
            authorization_url = oauth.create_authorization_url(base_authorization_url, expiration='never', scope='read,write')
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="Login with Oauth", url=authorization_url))
            await message.answer("Продите процедуру авторизации, после чего введите полученный url", reply_markup=keyboard)
            await Date.D5.set()
            
            @dp.message_handler(state=Date.D5)
            async def add_task(message: types.Message, state: FSMContext):
                global oauth
                redirect_url = message.text
                await state.finish()
                oauth.parse_authorization_response(redirect_url)
                access_token_url = 'https://trello.com/1/OAuthGetAccessToken'
                token = oauth.fetch_access_token(access_token_url)
                oauth_token = token['oauth_token']
                oauth_token_secret = token['oauth_token_secret']
                await db.oauth(oauth_token, oauth_token_secret)
                text = [
                    'Авторизация прошла успешно',
                    'Для получения справки введите /help'
                    ]
                await message.answer('\n'.join(text))    
    else:
        await dp.bot.send_message(message.from_user.id, 'Вы уже авторизированы')
