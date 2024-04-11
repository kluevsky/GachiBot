from dotenv import dotenv_values
import psycopg2
from datetime import datetime, timezone

settings = dotenv_values(".env")

DB_SERVER = settings["DB_SERVER"]
DB_PORT = settings["DB_PORT"]
DB_USER = settings["DB_USER"]
DB_PASSWORD = settings["DB_PASSWORD"]
DB_NAME = settings["DB_NAME"]

def create_db():
    try:
        #Create database
        conn = psycopg2.connect(
            database="postgres",
            host=DB_SERVER,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.autocommit = True
        cursor = conn.cursor()
        sql = f"CREATE database {DB_NAME}"
        cursor.execute(sql)
        conn.close()

        #Create tables
        conn = psycopg2.connect(
            database=DB_NAME,
            host=DB_SERVER,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.autocommit = True
        # cursor = conn.cursor()
        with conn.cursor() as cursor:
            cursor.execute(open("./sql/db.sql", "r").read())
        conn.close()
        print("Database created successfully")
        return True
    except:
        print("Unable to create database")
        return False


def check_db():
    # обработать ошибку коннекта
    try:
        conn = psycopg2.connect(
            database="postgres",
            host=DB_SERVER,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT datname FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        result = cursor.fetchone()
        conn.close()
        if not result:
            return False
        else:
            return True
    except:
        return False


def update_song_list(songs):
    conn = psycopg2.connect(
        database=DB_NAME,
        host=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    values = ','.join(cursor.mogrify("(%s,%s,%s)", song).decode('utf-8') for song in songs)
    cursor.execute(f"INSERT INTO songs VALUES {values} ON CONFLICT (id) DO NOTHING")

    song_list_update_time = get_song_list_update_time()
    current_datetime = datetime.now(timezone.utc)
    if not song_list_update_time:
        query = f"INSERT INTO settings VALUES ('{current_datetime}')"
    else:
        query = f"UPDATE settings SET last_update = '{current_datetime}'"
    cursor.execute(query)
    print("Songs added: " + str(len(songs)))
    conn.close()
    return


def get_song_list_update_time():
    conn = psycopg2.connect(
        database=DB_NAME,
        host=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT last_update FROM settings")
    result = cursor.fetchone()
    conn.close()
    if not result:
        return None
    else:
        return result[0]


def get_favorites(cid):
    conn = psycopg2.connect(
        database=DB_NAME,
        host=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT s.id, s.title, s.request_id FROM favorites f JOIN songs s on s.id = f.song_id WHERE f.cid = '{cid}'")
    result = cursor.fetchall()
    conn.close()
    return result


def add_favorites(cid, song_id):
    is_added = False
    conn = psycopg2.connect(
        database=DB_NAME,
        host=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM favorites WHERE cid = '{cid}' AND song_id = '{song_id}'")
    result = cursor.fetchone()
    if not result:
        try:
            cursor.execute(f"INSERT INTO favorites VALUES ('{cid}', '{song_id}')")
            is_added = True
        except:
            is_added = False
    else:
        is_added = False
    conn.close()
    return is_added


def delete_favorites(cid, song_id):
    return


def search_song(search_string):
    return

def get_random_song_from_db():
    conn = psycopg2.connect(
        database=DB_NAME,
        host=DB_SERVER,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM songs ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result