import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread

# --- إعداد الخادم الصغير ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    # Render يطلب المنفذ من متغير بيئة اسمه PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- إعدادات البوت ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
API_URL = "https://provider-site.com/api/v2" 
CH_ID = os.getenv('CHANNEL_USERNAME') 

bot = telebot.TeleBot(API_TOKEN)

# إنشاء قاعدة البيانات في المجلد الحالي
db_path = os.path.join(os.getcwd(), 'users.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_request REAL)')
conn.commit()

# (بقية الدوال: is_subscribed, main_menu, handle_services, process_request تبقى كما هي في الكود السابق)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "أهلاً بك! البوت يعمل بنجاح.")

if __name__ == "__main__":
    keep_alive()
    print("Bot started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
