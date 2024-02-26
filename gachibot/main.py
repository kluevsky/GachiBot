import requests
import telebot
from telebot import types

TOKEN = "<token_string>"
BASE_URL = "https://radio.gachibass.us.to/"

user_step = {}
main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

@bot.message_handler(commands=['start'])
def open_main_menu(message):
    # main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    main_menu.row("Какой следующий трек?", "Заказать трек")
    bot.send_message(message.chat.id, "Что хочешь?", reply_markup=main_menu)


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 0, content_types=["text"])
def chose_main_actions(message):
    if message.text == "Какой следующий трек?":
        next_track_name = get_next_track()
        bot.send_message(message.chat.id, next_track_name)

    if message.text == "Заказать трек":
        cid = message.chat.id
        user_step[cid] = 1
        main_menu.keyboard.clear()
        main_menu.row("🔙 Назад")
        bot.send_message(message.chat.id, "Что хочешь?", reply_markup=main_menu)


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1, content_types=["text"])
def handle_search(message):
    if message.text == "🔙 Назад":
        cid = message.chat.id
        user_step[cid] = 0
        main_menu.keyboard.clear()
        main_menu.row("Какой следующий трек?", "Заказать трек")
        bot.send_message(message.chat.id, "Что хочешь?", reply_markup=main_menu)
        return

    result = search_song(message.text)
    if not result['rows']:
        bot.send_message(message.chat.id, "Ниче не найдено, повтори")
    else:
        markup = types.InlineKeyboardMarkup()
        for song in result['rows']:
            markup.add(types.InlineKeyboardButton(text=song['song']['title'], callback_data=song['request_id']))
        bot.send_message(message.chat.id, text="Выбирай", reply_markup=markup)


@bot.callback_query_handler(func=lambda call:True)
def request_song(callback):
    cid = callback.message.chat.id
    endpoint = "api/station/1/request/"
    try:
        request = requests.post(BASE_URL + endpoint + callback.data)
        response = request.json()
    except requests.exceptions.RequestException as e:
        bot.send_message(cid, "СЕЙЧАС НЕЛЬЗЯ ЗАКАЗАТЬ")
        user_step[cid] = 0
        return
    
    if response['success'] == True:
        bot.send_message(cid, "ТРЕК ЗАКАЗАН")
        user_step[cid] = 0


def get_next_track():
    endpoint = "api/nowplaying/gachibass_radio"
    request = requests.get(BASE_URL + endpoint)
    response = request.json()
    return response['playing_next']['song']['title']


def search_song(search_phrase):
    endpoint = "api/station/1/requests"
    params = {
        "internal": "true",
        "rowCount": 10,
        "current": 1,
        "flushCache": "true",
        "searchPhrase": search_phrase,
        "sortOrder": "ASC"
    }
    request = requests.get(BASE_URL + endpoint, params)
    response = request.json()
    return response


def get_user_step(cid):
    if cid in user_step:
        return user_step[cid]
    else:
        return 0


bot.infinity_polling()