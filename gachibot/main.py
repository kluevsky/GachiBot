import requests
import telebot
import json
from telebot import types
from dotenv import dotenv_values
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
from db_actions import *


settings = dotenv_values(".env")

TOKEN = settings["TOKEN"]
BASE_URL = settings["BASE_URL"]
FAVORITES_FILE = settings["FAVORITES_FILE"]

button_labels = {
    "next_track": "Какой следующий трек?",
    "request_track": "Заказать трек",
    "go_back": "🔙 Назад",
    "star": "⭐"
}

endpoints = {
    "request": "api/station/1/request/",
    "now_playing": "api/nowplaying/gachibass_radio",
    "search": "api/station/1/requests"
}

class SongOperation(Enum):
    request = auto()
    add_favorite = auto()

db_exists = bool()
user_step = dict()
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
        markup = types.InlineKeyboardMarkup(row_width=5)
        for song in result["rows"]:
            markup.row(
                types.InlineKeyboardButton(
                    text=song["song"]["title"], 
                    callback_data=get_song_callback_string(
                        SongOperation.request.value, 
                        song["request_id"]
                    )
                ),
                types.InlineKeyboardButton(
                    text=button_labels["star"], 
                    callback_data=get_song_callback_string(
                        SongOperation.add_favorite.value, 
                        song["song"]["id"]
                    )
                )
            )
        bot.send_message(message.chat.id, "Выбирай", reply_markup=markup)


@bot.callback_query_handler(func=lambda call:True)
def handle_song_callback(callback):
    cid = callback.message.chat.id
    callback_json = json.loads(callback.data)
    if callback_json["operation"] == SongOperation.request.value:
        request_song(callback)
    elif callback_json["operation"] == SongOperation.add_favorite.value:
        add_favorite(callback)


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


def get_song_callback_string(operation, song_id):
    dict = {"operation": operation, "song_id": song_id}
    return str(dict).replace("'", '"')


def request_song(callback):
    #передавать cid сюда
    cid = callback.message.chat.id
    callback_json = json.loads(callback.data)
    endpoint = endpoints["request"]
    headers = {
        "Accept": "application/json",
        "Accept-Language": "ru"
    }
    try:
        request = requests.post(BASE_URL + endpoint + callback_json["song_id"], headers=headers)
        response = request.json()
    except:
        bot.send_message(cid, "КРИТИЧЕСКИЙ СБОЙ")
        user_step[cid] = 0
        return
    
    if response["success"] == True:
        open_main_menu(cid, 0, "ТРЕК ЗАКАЗАН", button_labels["next_track"], button_labels["request_track"])
    else:
        bot.send_message(cid, response["formatted_message"])


def add_favorite(callback):
    #передавать cid сюда
    return


def get_user_step(cid):
    if cid in user_step:
        return user_step[cid]
    else:
        return 0
    

def open_main_menu(cid, step, message, *buttons):
    user_step[cid] = step
    main_menu.keyboard.clear()
    main_menu.row(*buttons)
    bot.send_message(cid, message, reply_markup=main_menu)


def get_all_songs():
    songs = list()
    endpoint = endpoints["search"]
    params = {
        "internal": "true",
        "rowCount": 100,
        "current": 1,
        "flushCache": "true",
        "sortOrder": "ASC"
    }
    request = requests.get(BASE_URL + endpoint, params)
    response = request.json()
    total_pages = response["total_pages"]
    for page in range(1, total_pages + 1):
        params["current"] = page
        request = requests.get(BASE_URL + endpoint, params)
        response = request.json()
        for song in response["rows"]:
            songs.append((song["song"]["id"], song["song"]["title"], song["request_id"]))
    return songs

db_exists = check_db()
if not db_exists:
    db_exists = create_db()

if db_exists:
    song_list_update_time = get_song_list_update_time()
    print(datetime.now(timezone.utc))
    print(song_list_update_time)
    if not song_list_update_time or (datetime.now(timezone.utc) - timedelta(hours=24) >= song_list_update_time):
        songs = get_all_songs()
        update_song_list(songs)
    else:
        print("Last update: " + str(song_list_update_time))
else:
    print("Работаем без базы")


bot.infinity_polling()