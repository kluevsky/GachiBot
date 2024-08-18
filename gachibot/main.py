import requests
import telebot
import json
import random
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import dotenv_values
from enum import Enum, auto
from datetime import datetime, timedelta, timezone
from db_actions import *
from time import sleep


settings = dotenv_values(".env")

TOKEN = settings["TOKEN"]
BASE_URL = settings["BASE_URL"]

button_labels = {
    "next_track": "Какой следующий трек?",
    "request_track": "Заказать трек",
    "go_back": "🔙 Назад",
    "add_favorites": "⭐ В избранное",
    "delete_favorites": "❌ Удалить",
    "get_favorites": "⭐ Избранное",
    "request_song": "🎶 Заказать",
    "random_song": "❓ Случайный трек",
    "song_requested": "✅ Трек заказан"
}

endpoints = {
    "request": "api/station/1/request/",
    "now_playing": "api/nowplaying/gachibass_radio",
    "search": "api/station/1/requests",
    "queue": "api/station/gachibass_radio/queue"
}

class SongOperation(Enum):
    request = auto()
    add_favorite = auto()
    delete_favorite = auto()
    already_requested = auto()

db_exists = False
user_step = dict()
main_menu = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)

bot = telebot.TeleBot(TOKEN, parse_mode=None)

@bot.message_handler(commands=["start"])
def handle_start(message):
    open_main_menu(message.chat.id, 0, "Выбери действие", button_labels["next_track"], button_labels["request_track"])


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 0, content_types=["text"])
def chose_main_actions(message):
    cid = message.chat.id
    if message.text == button_labels["next_track"]:
        next_track = get_next_track()
        bot.send_photo(cid, next_track["art"], next_track["title"])

    if message.text == button_labels["request_track"]:
        open_main_menu(cid, 1, "Какой трек ищем?", button_labels["get_favorites"], button_labels["random_song"], button_labels["go_back"])


@bot.message_handler(func=lambda message: get_user_step(message.chat.id) == 1, content_types=["text"])
def handle_search(message):
    cid = message.chat.id
    if message.text == button_labels["go_back"]:
        open_main_menu(cid, 0, "Выбери действие", button_labels["next_track"], button_labels["request_track"])
        return
    
    elif message.text == button_labels["get_favorites"]:
        if not db_exists:
            bot.send_message(cid, "Нет подключения к базе")
            return
        
        favorites = get_favorites(cid)
        if not favorites:
            bot.send_message(cid, "Список избранных треков пуст")
        else:
            for song in favorites:
                markup = InlineKeyboardMarkup(row_width=5)
                markup.row(
                    InlineKeyboardButton(
                        text=button_labels["request_song"], 
                        callback_data=get_song_callback_string(
                            SongOperation.request.value, 
                            song[2] #request_id
                        )
                    ),
                    InlineKeyboardButton(
                        text=button_labels["delete_favorites"],
                        callback_data=get_song_callback_string(
                            SongOperation.delete_favorite.value, 
                            song[0] #id
                        )
                    )
                )
                bot.send_message(cid, song[1], reply_markup=markup)
        return
    
    elif message.text == button_labels["random_song"]:
        if db_exists:
            song = get_random_song_from_db()
        else:
            song = get_random_song()
        markup = InlineKeyboardMarkup(row_width=5)
        markup.row(
                InlineKeyboardButton(
                    text=button_labels["request_song"], 
                    callback_data=get_song_callback_string(
                        SongOperation.request.value, 
                        song[2]
                    )
                ),
                InlineKeyboardButton(
                    text=button_labels["add_favorites"],
                    callback_data=get_song_callback_string(
                        SongOperation.add_favorite.value, 
                        song[0]
                    )
                )
            )
        bot.send_message(cid, song[1], reply_markup=markup)
        return
    
    else:
        if db_exists:
            result = search_song_from_db(message.text)
        else:
            result = search_song(message.text)

        if not result:
            bot.send_message(cid, "Ниче не найдено, повтори")
        else:
            for song in result:
                markup = InlineKeyboardMarkup(row_width=5)
                markup.row(
                    InlineKeyboardButton(
                        text=button_labels["request_song"], 
                        callback_data=get_song_callback_string(
                            SongOperation.request.value, 
                            song[2]
                        )
                    ),
                    InlineKeyboardButton(
                        text=button_labels["add_favorites"], 
                        callback_data=get_song_callback_string(
                            SongOperation.add_favorite.value, 
                            song[0]
                        )
                    )
                )
                bot.send_message(cid, song[1], reply_markup=markup)


@bot.callback_query_handler(func=lambda call:True)
def handle_song_callback(callback):
    cid = callback.message.chat.id
    cbid = callback.id
    callback_json = json.loads(callback.data)
    if callback_json["operation"] == SongOperation.request.value:
        is_requested = request_song(cid, callback_json["song_id"])
        if is_requested:
            bot.answer_callback_query(cbid, "Трек заказан", True)
            markup = InlineKeyboardMarkup(row_width=5)
            markup.row(
                InlineKeyboardButton(
                    text=button_labels["song_requested"], 
                    callback_data=get_song_callback_string(
                        SongOperation.already_requested.value,
                        str()
                    )
                )
            )
            bot.edit_message_reply_markup(cid, callback.message.id, reply_markup=markup)
        else:
            bot.answer_callback_query(cbid, "Не удалось заказать трек, см. ошибку ниже в чате", True)

    elif callback_json["operation"] == SongOperation.add_favorite.value:
        if not db_exists:
            bot.answer_callback_query(cbid, "Нет подключения к базе", True)
            return
        elif add_favorites(cid, callback_json["song_id"]):
            bot.answer_callback_query(cbid, "Трек добавлен в избранное", True)
        else:
            bot.answer_callback_query(cbid, "Не удалось добавить в избранное. Возможно, такой трек уже добавлен.", True)

    elif callback_json["operation"] == SongOperation.delete_favorite.value:
        if delete_favorites(cid, callback_json["song_id"]):
            bot.answer_callback_query(cbid, "Трек удален из избранного", True)
        else:
            bot.answer_callback_query(cbid, "Не удалось удалить трек", True)

    elif callback_json["operation"] == SongOperation.already_requested.value:
        bot.answer_callback_query(cbid, "Трек уже был заказан", True)


def get_next_track():
    endpoint = endpoints["now_playing"]
    next_track = {}
    request = requests.get(BASE_URL + endpoint)
    response = request.json()
    next_track["art"] = response["playing_next"]["song"]["art"]
    next_track["title"] = response["playing_next"]["song"]["title"]
    return next_track


def search_song(search_phrase):
    songs = list()
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
    for row in response["rows"]:
        song = (
            row["song"]["id"],
            row["song"]["title"],
            row["request_id"]
        )
        songs.append(song)
    return songs


def get_song_callback_string(operation, song_id):
    dict = {"operation": operation, "song_id": song_id}
    return str(dict).replace("'", '"')


def request_song(cid, song_id):
    result = False
    endpoint = endpoints["request"]
    headers = {
        "Accept": "application/json",
        "Accept-Language": "ru"
    }
    try:
        request = requests.post(BASE_URL + endpoint + song_id, headers=headers)
        response = request.json()
    except:
        bot.send_message(cid, "Произошла неизвестная ошибка")
        user_step[cid] = 0
        return
    
    if response["success"] == True:
        result = True
        queue = check_queue(song_id)
        if queue["song_count"] == 0:
            text = "Трек заказан (очереди нет)"
        else:
            wait_time = datetime.fromtimestamp(queue["time"], timezone.utc) - datetime.now(timezone.utc)
            text = f"Трек заказан (очередь: {queue["song_count"]}, ожидание: {int(wait_time.total_seconds() / 60)} мин)"
        open_main_menu(cid, 0, text, button_labels["next_track"], button_labels["request_track"])
    else:
        bot.send_message(cid, response["formatted_message"])
    return result


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


def get_random_song():
    endpoint = endpoints["search"]
    params = {
        "internal": "true",
        "rowCount": 1,
        "current": 1,
        "flushCache": "true",
        "sortOrder": "ASC"
    }
    request = requests.get(BASE_URL + endpoint, params)
    response = request.json()
    total_pages = response["total_pages"]
    params["current"] = random.randint(1, total_pages)
    request = requests.get(BASE_URL + endpoint, params)
    response = request.json()
    song = (
        response["rows"][0]["song"]["id"],
        response["rows"][0]["song"]["title"],
        response["rows"][0]["request_id"]
    )
    return song


def check_queue(song_id):
    result = {
        "song_count": 0,
        "time": 0
    }
    endpoint = endpoints["queue"]
    params = {
        "rowCount": 0
    }
    request = requests.get(BASE_URL + endpoint, params)
    response = request.json()
    if response["total"] == 3:
        return result
    result["song_count"] = response["total"] - 3 #Минус 3, т.к. всегда есть две незаказанные записи плюс одна, которая заказана сейчас
    result["time"] = response["rows"][response["total"] - 4]["played_at"] + response["rows"][response["total"] - 4]["duration"]
    return result


db_exists = check_db()
if not db_exists:
    db_exists = create_db()

if db_exists:
    song_list_update_time = get_song_list_update_time()
    if not song_list_update_time or (datetime.now(timezone.utc) - timedelta(hours=24) >= song_list_update_time):
        songs = get_all_songs()
        update_song_list(songs)
    else:
        print("Last update: " + str(song_list_update_time))
else:
    print("Работаем без базы")

bot.infinity_polling()