from authlib.integrations.requests_client import OAuth1Session

from aiogram import types
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.builtin import CommandStart, CommandHelp
from aiogram.dispatcher import FSMContext
from asyncpg import Connection, Record
from asyncpg.exceptions import UniqueViolationError
from config import trello_key, trello_secret
from aiogramcalendar import calendar_callback, create_calendar, process_calendar_selection
import socket

client_key = trello_key
client_secret = trello_secret

from load_all import bot, dp, db
from config import host


# Первый хендлер
oauth = None
oauth_id = None
boards = None
boards_dict = None
# Второй хендлер
board_id = None
board_name = None
lists = None
lists_dict = None
# Третий хендлер
list_id = None
list_name = None
# del
cards_dict = None
d = None
# del (Второй)
card_id = None
task = None
date = None
members = None
memberships_name_list = None
name_member = None
member_id = None


class DBCommands:
    CHECK_OAUTH_USER = "SELECT oauth_token, oauth_token_secret FROM users WHERE my_id=?"
    ADD_NEW_USER = 'INSERT INTO users (my_id, first_name, second_name, oauth_token, oauth_token_secret) values(?, ?, ?, ?, ?) RETURNING my_id'
    async def check_user(self):
        command = self.CHECK_OAUTH_USER
        user = types.User.get_current()
        my_id = int(user.id)
        result = None
        args = (my_id,)
        try:
            result = self.pool.fetchval(command, *args)
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
        args = my_id, first_name, second_name
        try:
            record_id = await self.pool.fetchval(command, *args)
            return record_id
        except UniqueViolationError:
            pass
    
    async def access(self):
        command = self.CHECK_OAUTH_USER
        user = types.User.get_current()
        my_id = int(user.id)
        result = None
        args = (my_id,)
        try:
            result = self.pool.fetchval(command, *args)
        except:
            print('Возникла ошибка в check_user')
        if result:
            return result
        else:
            return False

db = DBCommands()


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    user_in_db = await db.check_user()
    if user_in_db:
        text = [
            f'Здравствуйте, {message.from_user.full_name}!',
            'Для получения справки по коммандам введите комманду /help'
        ]
    else:
        text = [
            f'Здравствуйте, {message.from_user.full_name}!',
            'Для получения полного функционала вам необходимо авторизоваться /oauth',
        ]
    await message.answer('\n'.join(text))


@dp.message_handler(CommandHelp())
async def bot_help(message: types.Message):
    user_in_db = await db.check_user()
    if user_in_db:
        text = [
            'Список команд: ',
            '/cards - Работа с карточками',
            '/help - Получить справку'
        ]
    else:
        text = [
            'Для получения полного функционала вам необходимо авторизоваться /oauth',
        ]
    await message.answer('\n'.join(text))


@dp.message_handler(Command('oauth'))
async def oauth(message: types.Message):
    check = await db.check_user()
    if check == False:
        request_token_url = 'https://trello.com/1/OAuthGetRequestToken'
        oauth = OAuth1Session(client_key, client_secret=client_secret)
        oauth.redirect_uri = f'http://{host}:3000' # перенаправление на сервер
        fetch_response = oauth.fetch_request_token(request_token_url)
        resource_owner_key = fetch_response.get('oauth_token')
        resource_owner_secret = fetch_response.get('oauth_token_secret')
        base_authorization_url = 'https://trello.com/1/OAuthAuthorizeToken'
        authorization_url = oauth.create_authorization_url(base_authorization_url, expiration='never', scope='read,write')
        #print(authorization_url)

        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Login with Oauth", url=authorization_url))
        await message.answer("Продите процедуру авторизации", reply_markup=keyboard)

        # Магия обработки url
        sock = socket.socket()
        sock.connect((host, 9090))
        data = sock.recv(1024)
        sock.close()
        await message.answer(data)
        """
        print('Здесь происходить обработка перенаправленного url')
        print('connected:', addr)
        data = conn.recv(4096)
        b = data.decode('utf-8').split(' ')[1]
        url = f'http://{host}:3000' + b
        conn.send('Success oauth!')
        conn.close()
        print('connection close:')
        # конец магии


        # Парсинг url и получение токенов
        oauth.parse_authorization_response(url)
        access_token_url = 'https://trello.com/1/OAuthGetAccessToken'
        token = oauth.fetch_access_token(access_token_url)
        print('Получаем наши любименькие токены :)')
        print(token)
        #save_access_token(token)
        oauth_token = token['oauth_token']
        oauth_token_secret = token['oauth_token_secret']
        await db.oauth(oauth_token, oauth_token_secret)
        #balance = await database.check_money()
        text = [
            'Авторизация прошла успешно',
            'Для получения справки введите /help'
            ]
        await message.answer('\n'.join(text))
    else:
        await message.answer('Вы уже авторизированы')
        """

"""/cards"""
# Получение списка досок
@dp.message_handler(Command('cards'))
async def oauth(message: types.Message):
    user_in_db = await db.check_user()
    if user_in_db:
        global oauth
        global oauth_id
        global boards
        global boards_dict
        oauth_token, oauth_token_secret = await db.access()
        oauth = OAuth1Session(
            client_key,
            client_secret,
            token = oauth_token,
            token_secret = oauth_token_secret
            )
        url = 'https://api.trello.com/1/members/me'
        oauth_id = oauth.get(url).json()['id']
        url_board = f'https://api.trello.com/1/members/{oauth_id}/boards'
        boards = oauth.get(url_board).json()
        boards_dict = {} # словарь name-id досок
        for board in boards:
            boards_dict[board['id']] = board['name']
        boards_keyboard = types.InlineKeyboardMarkup() # Создаем кнопки
        for board_id in boards_dict.keys():
            bt_board = types.InlineKeyboardButton(boards_dict[board_id], callback_data=board_id)
            boards_keyboard.add(bt_board)
        await message.answer("Выберите доску:", reply_markup=boards_keyboard)
    else:
        await message.answer('Для получения полного функционала вам необходимо авторизоваться /oauth')


# Получение списка списков (тыкнули на какую-то доску)
@dp.callback_query_handler(lambda c: c.data in boards_dict.keys())
async def process_callback(call: types.CallbackQuery):
    global board_id
    global board_name
    global lists
    global lists_dict
    await dp.bot.answer_callback_query(call.id)
    board_id = call.data
    board_name = boards_dict[board_id]
    url_lists = f'https://api.trello.com/1/boards/{board_id}/lists'
    lists = oauth.get(url_lists).json()
    lists_dict = {}
    for l in lists:
        lists_dict[l['id']] = l['name']
    lists_keyboard = types.InlineKeyboardMarkup()
    for list_id in lists_dict.keys():
        bt_list = types.InlineKeyboardButton(lists_dict[list_id], callback_data=list_id)
        lists_keyboard.add(bt_list)
    await dp.bot.send_message(call.from_user.id, "Выберите список:", reply_markup=lists_keyboard)


# Получение action (тыкнули на какой-то список)
@dp.callback_query_handler(lambda c: c.data in lists_dict.keys())
async def process_callback(call: types.CallbackQuery):
    global list_id
    global list_name
    await dp.bot.answer_callback_query(call.id)
    list_id = call.data
    list_name = lists_dict[list_id]
    kb_action_1 = InlineKeyboardButton('Посмотреть текущие задачи', callback_data='read')
    kb_action_2 = InlineKeyboardButton('Переместить карточку', callback_data='cd')
    kb_action_3 = InlineKeyboardButton('Загрузить новую задачу', callback_data='write')
    kb_action_4 = InlineKeyboardButton('Удалить карточку', callback_data='del')
    action_keyboard = InlineKeyboardMarkup()
    action_keyboard.add(kb_action_1)
    action_keyboard.add(kb_action_2)
    action_keyboard.add(kb_action_3)
    action_keyboard.add(kb_action_4)

    await dp.bot.send_message(call.from_user.id, "Что вы хотите сделать?", reply_markup=action_keyboard)


# (тыкнули на read)
@dp.callback_query_handler(lambda c: c.data == 'read')
async def process_callback(call: types.CallbackQuery):
    await dp.bot.answer_callback_query(call.id)
    url_cards = f'https://api.trello.com/1/lists/{list_id}/cards'
    cards = oauth.get(url_cards).json()
    text_cards = [
        f'Ваши карточки на доске "{board_name}" в списке "{list_name}":',
        ]
    for card in cards:
        text_cards.append(card['name'])
    text = f'{text_cards[0]}\n' + ';\n'.join(text_cards[1:]) + '.'
    await dp.bot.send_message(call.from_user.id, text)


# (тыкнули на cd)
@dp.callback_query_handler(lambda c: c.data == 'cd')
async def process_callback(call: types.CallbackQuery):
    global cards_dict
    global d
    await dp.bot.answer_callback_query(call.id)
    url_cards = f'https://api.trello.com/1/lists/{list_id}/cards'
    cards = oauth.get(url_cards).json()
    cards_dict = {}
    d = {}
    i = 0
    for card in cards:
        cards_dict[card['id']] = card['name']
        d[i] = card['id']
        i += 1
    keyboard_cards = types.InlineKeyboardMarkup()
    for key in d:
        bt_cards = InlineKeyboardButton(cards_dict[d[key]], callback_data=str(key))
        keyboard_cards.add(bt_cards)
    text = [
        f'Ваши карточки на доске "{board_name}" в списке "{list_name}":',
        'Выберите карточку которую хотите переместить'
        ]
    await dp.bot.send_message(call.from_user.id, '\n'.join(text), reply_markup=keyboard_cards)


    @dp.callback_query_handler(lambda c: c.data in map(str, d.keys()))
    async def process_callback(call: types.CallbackQuery):
        global card_id
        await dp.bot.answer_callback_query(call.id)
        key_d = int(call.data)
        card_id = d[key_d]
        lists_keyboard = types.InlineKeyboardMarkup()
        for name in lists_dict.values():
            bt_list = types.InlineKeyboardButton(name, callback_data=name)
            lists_keyboard.add(bt_list)
        await dp.bot.send_message(call.from_user.id, "Выберите список куда переместить карточку:", reply_markup=lists_keyboard)
        

    @dp.callback_query_handler(lambda c: c.data in lists_dict.values())
    async def process_callback(call: types.CallbackQuery):
        global card_id
        cd_url = f'https://api.trello.com/1/cards/{card_id}'
        await dp.bot.answer_callback_query(call.id)
        list_name = call.data # Не меняем предыдущий лист
        list_id = []
        for key in lists_dict.keys():
            if lists_dict[key] == list_name:
                list_id.append(key)
        list_id = list_id[0]
        query = {
                    'idList': list_id,
                }
        cd = oauth.put(cd_url, data=query)
        await dp.bot.send_message(call.from_user.id, f"Карточка перемещена")


# (тыкнули на del)
@dp.callback_query_handler(lambda c: c.data == 'del')
async def process_callback(call: types.CallbackQuery):
    global cards_dict
    await dp.bot.answer_callback_query(call.id)
    url_cards = f'https://api.trello.com/1/lists/{list_id}/cards'
    cards = oauth.get(url_cards).json()
    cards_dict = {}
    for card in cards:
        cards_dict[card['id']] = card['name']
    keyboard_cards = types.InlineKeyboardMarkup()
    for card_id in cards_dict.keys():
        bt_cards = InlineKeyboardButton(cards_dict[card_id], callback_data=card_id)
        keyboard_cards.add(bt_cards)
    text = [
        f'Ваши карточки на доске "{board_name}" в списке "{list_name}":',
        'Выберите карточку которую хотите удалить'
        ]
    await dp.bot.send_message(call.from_user.id, '\n'.join(text), reply_markup=keyboard_cards)

    
    @dp.callback_query_handler(lambda c: c.data in cards_dict.keys())
    async def process_callback(call: types.CallbackQuery):
        global card_id
        await dp.bot.answer_callback_query(call.id)
        card_id = call.data
        del_url = f'https://api.trello.com/1/cards/{card_id}'
        oauth.delete(del_url)
        await dp.bot.send_message(call.from_user.id, 'Карточка удалена')
        card_id = None


@dp.callback_query_handler(lambda c: c.data == 'write')
async def process_callback(call: types.CallbackQuery):
    await dp.bot.answer_callback_query(call.id)
    await dp.bot.send_message(call.from_user.id, 'Введите имя задачи')
    await Date.D1.set()


    # Ввели имя задачи
    @dp.message_handler(state=Date.D1)
    async def process_callback(message: types.Message, state: FSMContext):
        global task
        task = message.text
        await state.finish()
        kb_date_yes = InlineKeyboardButton('Установить дату', callback_data='date_yes')
        kb_date_no = InlineKeyboardButton('Не ставить дату', callback_data='date_no')
        date_keyboard = InlineKeyboardMarkup()
        date_keyboard.add(kb_date_yes)
        date_keyboard.add(kb_date_no)
        await message.answer("Хотите установить дату?", reply_markup=date_keyboard)


    @dp.callback_query_handler(lambda c: c.data == 'date_no')
    async def process_callback(call: types.CallbackQuery):
        global date
        await dp.bot.answer_callback_query(call.id)
        date = None
        await Date.D2.set()
        bt = KeyboardButton('Подтвердить')
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(bt)
        await dp.bot.send_message(call.from_user.id, 'Подтвердите данное действие', reply_markup=keyboard)


    @dp.callback_query_handler(lambda c: c.data == 'date_yes')
    async def process_callback(call: types.CallbackQuery):
        await dp.bot.send_message(call.from_user.id, "Пожалуйста, выберите дату: ", reply_markup=create_calendar())


    @dp.callback_query_handler(calendar_callback.filter()) 
    async def process_name(call: CallbackQuery, callback_data: dict):
        global date
        selected, date = await process_calendar_selection(call, callback_data)
        if selected:
            await dp.bot.answer_callback_query(call.id)
            await dp.bot.send_message(call.from_user.id, 'Введите время в формате hour:minut:second')
            await Date.D2.set()


    @dp.message_handler(state=Date.D2)
    async def add_task(message: types.Message, state: FSMContext):
        global date
        time = message.text
        if time != 'Подтвердить':
            date = date.strftime("%Y-%m-%d") + ' ' + time
        else:
            pass
        await state.finish()

        kb_members_yes = InlineKeyboardButton('Назначить исполнителя', callback_data='members')
        kb_members_no = InlineKeyboardButton('Не назначать исполнителя', callback_data='no_members')
        members_keyboard_lists = InlineKeyboardMarkup()
        members_keyboard_lists.add(kb_members_yes)
        members_keyboard_lists.add(kb_members_no)

        await message.answer("Хотите назначить исполнителя?", reply_markup=members_keyboard_lists)


    @dp.callback_query_handler(lambda c: c.data == 'no_members')
    async def process_callback(call: types.CallbackQuery):
        await dp.bot.answer_callback_query(call.id)
        await Date.D3.set()
        bt_member_confirm = KeyboardButton('Подтвердить')
        keyboard_confirm = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard_confirm.add(bt_member_confirm)
        await dp.bot.send_message(call.from_user.id, 'Подтвердите данное действие', reply_markup=keyboard_confirm)
        await Date.D3.set()


    @dp.callback_query_handler(lambda c: c.data == 'members')
    async def process_callback(call: types.CallbackQuery):
        global members
        global memberships_name_list
        await dp.bot.answer_callback_query(call.id)
        members_url = f'https://api.trello.com/1/boards/{board_id}/members'
        members = oauth.get(members_url).json()
        memberships_name_list = []
        for membership in members:
            memberships_name_list.append(membership['fullName']) 
        memberships_keyboard = types.InlineKeyboardMarkup()
        for name in memberships_name_list:
            bt_member = InlineKeyboardButton(name, callback_data=name)
            memberships_keyboard.add(bt_member)
        await dp.bot.send_message(call.from_user.id, 'Выберите исполнителя', reply_markup=memberships_keyboard)


        @dp.callback_query_handler(lambda c: c.data in memberships_name_list)
        async def process_callback(call: types.CallbackQuery):
            global name_member
            global member_id
            await dp.bot.answer_callback_query(call.id)
            name_member = call.data
            members_id = []
            for member in members:
                ans = {i: member[i] for i in member if member['fullName'] == name_member}
                try:
                    members_id.append(ans['id'])
                except:
                    pass
            member_id = members_id[0]

            bt_member_yes_confirm = KeyboardButton('Да')
            keyboard_yes_confirm = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard_yes_confirm.add(bt_member_yes_confirm)
            await dp.bot.send_message(call.from_user.id, 'Подтвердите данное действие', reply_markup=keyboard_yes_confirm)
            await Date.D3.set()


    @dp.message_handler(state=Date.D3)
    async def add_task(message: types.Message, state: FSMContext):
        global list_id
        global task
        global date
        global member_id

        url_cards = f'https://api.trello.com/1/cards'
        confirm = message.text
        if confirm != 'Подтвердить':
            query = {
                    'idList': list_id,
                    'name': task,
                    'due': date,
                    'idMembers': member_id
                }
        else:
            query = {
                    'idList': list_id,
                    'name': task,
                    'due': date
                }   
        cards = oauth.post(url_cards, data=query)
        await message.answer(f'Карточка "{task}" добавлена')
        task = None
        date = None
        member_id = None
        await state.finish()
