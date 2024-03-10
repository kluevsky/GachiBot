import requests
import telebot
from telebot import types
from dotenv import dotenv_values

settings = dotenv_values(".env")

TOKEN = settings["TOKEN"]
BASE_URL = settings["BASE_URL"]

button_labels = {
    "next_track": "Какой следующий трек?",
    "request_track": "Заказать трек",
    "go_back": "🔙 Назад"
}

endpoints = {
    "request": "api/station/1/request/",
    "now_playing": "api/nowplaying/gachibass_radio",
    "search": "api/station/1/requests"

}

user_step = {}
main_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

@bot.message_handler(commands=["start"])
def handle_start(message):
    open_main_menu(message.chat.id, 0, "Что хочешь?", button_labels["next_track"], button_labels["request_track"])


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 0, content_types=["text"])
def chose_main_actions(message):
    cid = message.chat.id
    if message.text == button_labels["next_track"]:
        next_track = get_next_track()
        bot.send_photo(cid, next_track["art"], next_track["title"])

    if message.text == button_labels["request_track"]:
        open_main_menu(cid, 1, "Какой трек ищем?", button_labels["go_back"])


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1, content_types=["text"])
def handle_search(message):
    if message.text == button_labels["go_back"]:
        open_main_menu(message.chat.id, 0, "Что хочешь?", button_labels["next_track"], button_labels["request_track"])
        return

    result = search_song(message.text)
    if not result["rows"]:
        bot.send_message(message.chat.id, "Ниче не найдено, повтори")
    else:
        markup = types.InlineKeyboardMarkup()
        for song in result["rows"]:
            markup.add(types.InlineKeyboardButton(text=song["song"]["title"], callback_data=song["request_id"]))
        bot.send_message(message.chat.id, "Выбирай", reply_markup=markup)


@bot.callback_query_handler(func=lambda call:True)
def request_song(callback):
    cid = callback.message.chat.id
    endpoint = endpoints["request"]
    headers = {
        "Accept": "application/json",
        "Accept-Language": "ru"
    }
    try:
        request = requests.post(BASE_URL + endpoint + callback.data, headers=headers)
        response = request.json()
    except requests.exceptions.RequestException as e:
        bot.send_message(cid, "КРИТИЧЕСКИЙ СБОЙ")
        user_step[cid] = 0
        return
    
    if response["success"] == True:
        open_main_menu(cid, 0, "ТРЕК ЗАКАЗАН", button_labels["next_track"], button_labels["request_track"])
    else:
        bot.send_message(cid, response["formatted_message"])


def get_next_track():
    endpoint = endpoints["now_playing"]
    next_track = {}
    request = requests.get(BASE_URL + endpoint)
    response = request.json()
    next_track["art"] = response["playing_next"]["song"]["art"]
    next_track["title"] = response["playing_next"]["song"]["title"]
    return next_track


def search_song(search_phrase):
    endpoint = endpoints["search"]
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
    

def open_main_menu(cid, step, message, *buttons):
    user_step[cid] = step
    main_menu.keyboard.clear()
    for button in buttons:
        main_menu.add(button)
    bot.send_message(cid, message, reply_markup=main_menu)


bot.infinity_polling()