import telebot
from telebot import types
import requests
import psycopg2
import configparser
import random
import string

# Токен Telegram-бота
TOKEN = '6428653572:AAFPTjLsRNUDTjOTt7oRyPS11FF3aw2sAgg'
bot = telebot.TeleBot(TOKEN)

# Создание объекта ConfigParser
config = configparser.ConfigParser()

# Загрузка конфигурации из файла cursach.ini
config.read('cursach.ini')

# Получение параметров подключения из секции [postgresql]
db_params = config['postgresql']

# Настройка подключения к PostgreSQL
conn = psycopg2.connect(
    dbname=db_params['dbname'],
    user=db_params['user'],
    password=db_params['password'],
    host=db_params['host'],
    port=db_params['port']
)
cur = conn.cursor()

# Создание таблиц files и users_to_telegram с необходимыми колонками если их нет
cur.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id SERIAL PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        telegram_login TEXT NOT NULL
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS users_to_telegram (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        telegram_login TEXT UNIQUE,
        token TEXT,
        is_authenticated BOOLEAN DEFAULT FALSE,
        awaiting_auth BOOLEAN DEFAULT FALSE
    )
""")
conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Начать диалог')
    item2 = types.KeyboardButton('Вход')
    item3 = types.KeyboardButton('Загрузить курсовую')
    markup.add(item1, item2, item3)

    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Начать диалог")
def handle_start_dialog(message):
    bot.send_message(message.chat.id, 'Диалог начат! Чем могу помочь?')

@bot.message_handler(func=lambda message: message.text == "Вход")
def login(message):
    user_login = message.from_user.username
    cur.execute("SELECT is_authenticated FROM users_to_telegram WHERE telegram_login = %s", (user_login,))
    result = cur.fetchone()

    if result and result[0]:  # Пользователь уже авторизован
        bot.send_message(message.chat.id, "Вы уже авторизованы в системе.")
    else:
        token = generate_token()
        auth_link = f"http://localhost/uploads/telegram_checker.php?t={token}"

        # Вставка или обновление токена в базе данных
        cur.execute("""
            INSERT INTO users_to_telegram (telegram_login, token, is_authenticated, awaiting_auth)
            VALUES (%s, %s, FALSE, TRUE)
            ON CONFLICT (telegram_login)
            DO UPDATE SET token = EXCLUDED.token, is_authenticated = FALSE, awaiting_auth = TRUE
        """, (user_login, token))
        conn.commit()

        bot.send_message(message.chat.id, "Перейдите по следующей ссылке для авторизации:")
        bot.send_message(message.chat.id, auth_link)
        bot.send_message(message.chat.id, "Ждем вашей авторизации...")

def generate_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def check_authorization(user_login):
    cur.execute("SELECT user_id FROM users_to_telegram WHERE telegram_login = %s AND awaiting_auth = TRUE", (user_login,))
    result = cur.fetchone()
    if result and result[0] is not None:
        cur.execute("UPDATE users_to_telegram SET is_authenticated = TRUE, awaiting_auth = FALSE WHERE telegram_login = %s", (user_login,))
        conn.commit()
        return True
    return False

@bot.message_handler(func=lambda message: message.text == "Загрузить курсовую")
def upload_course(message):
    user_login = message.from_user.username
    if check_authorization(user_login):
        bot.send_message(message.chat.id, "Вы успешно авторизованы!")

    cur.execute("SELECT is_authenticated FROM users_to_telegram WHERE telegram_login = %s", (user_login,))
    result = cur.fetchone()
    if result and result[0]:
        bot.send_message(message.chat.id, "Отправьте курсовую работу")
        bot.register_next_step_handler(message, save_course)
    else:
        bot.send_message(message.chat.id, "Вы не авторизованы. Пожалуйста, войдите, чтобы загрузить курсовую работу.")
        print(f"Пользователь {user_login} не авторизован.")

def save_course(message):
    if message.document:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        file_name = message.document.file_name
        user_login = message.from_user.username  # Получение логина Telegram пользователя

        # Загрузка файла
        response = requests.get(file_url)
        if response.status_code == 200:
            file_data = response.content

            # Отправка файла на сервер XAMPP
            files = {'file': (file_name, file_data)}
            upload_response = requests.post("http://localhost/uploads/upload.php", files=files)
            if upload_response.status_code == 200 and "успешно загружен" in upload_response.text:
                # Сохранение информации о файле в базе данных
                file_size = len(file_data)
                cur.execute("INSERT INTO files (file_name, file_size, telegram_login) VALUES (%s, %s, %s)",
                            (file_name, file_size, user_login))
                conn.commit()
                bot.send_message(message.chat.id, "Курсовая работа успешно загружена!")
                print(f"File {file_name} uploaded successfully by {user_login}.")  # Отладочное сообщение
            else:
                bot.send_message(message.chat.id, "Ошибка при загрузке файла на сервер. Пожалуйста, попробуйте еще раз.")
                print(f"Error uploading file {file_name} by {user_login}.")  # Отладочное сообщение
        else:
            bot.send_message(message.chat.id, "Ошибка при загрузке файла. Пожалуйста, попробуйте еще раз.")
            print(f"Error downloading file {file_name} from Telegram.")  # Отладочное сообщение
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте документ.")
        print("No document received.")  # Отладочное сообщение

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        cur.close()
        conn.close()
