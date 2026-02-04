import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread

# --- إعدادات الخادم لإبقاء البوت حياً على Render ---
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- إعدادات البوت (تأخذ قيمها من Environment Variables) ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
API_URL = "https://kd1s.com/api/v2" # استبدله برابط API موقعك
CH_ID = os.getenv('CHANNEL_USERNAME') 
COOLDOWN_HOURS = 12

bot = telebot.TeleBot(API_TOKEN)

# --- قاعدة بيانات SQLite ---
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_request REAL)')
conn.commit()

# --- التحقق من الاشتراك الإجباري ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# --- لوحة الأزرار ---
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👥 مشتركين", "👀 مشاهدات")
    markup.row("❤️ تفاعلات", "👤 حسابي")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اضغط للاشتراك", url=f"https://t.me/{CH_ID.replace('@','')}")
        markup.add(btn)
        bot.send_message(message.chat.id, f"⚠️ يجب الاشتراك في قناة البوت أولاً لتستطيع استخدامه مجاناً 👇", reply_markup=markup)
        return
    
    bot.send_message(message.chat.id, "✅ أهلاً بك! اختر الخدمة المجانية التي تريدها (كل 12 ساعة مرة):", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text in ["👥 مشتركين", "👀 مشاهدات", "❤️ تفاعلات"])
def handle_services(message):
    user_id = message.from_user.id
    
    # تحقق من الوقت
    cursor.execute('SELECT last_request FROM users WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    current_time = time.time()

    if row and (current_time - row[0]) < (COOLDOWN_HOURS * 3600):
        remaining_seconds = int((COOLDOWN_HOURS * 3600) - (current_time - row[0]))
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        bot.reply_to(message, f"⏳ عذراً! يمكنك الطلب مرة أخرى بعد {hours} ساعة و {minutes} دقيقة.")
        return

    msg = bot.reply_to(message, "ارسل رابط القناة أو المنشور الآن:")
    bot.register_next_step_handler(msg, process_request, message.text)

def process_request(message, service_type):
    link = message.text
    user_id = message.from_user.id

    # تحديد رقم الخدمة (تأكد من مطابقة الأرقام مع موقع SMM الخاص بك)
    service_id = 100 
    if "مشتركين" in service_type: service_id = 14681 # مثال
    elif "مشاهدات" in service_type: service_id = 14527 # مثال

    payload = {
        'key': SMM_API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': 50 # كمية بسيطة مجانية
    }

    try:
        response = requests.post(API_URL, data=payload).json()
        if "order" in response:
            cursor.execute('INSERT OR REPLACE INTO users (user_id, last_request) VALUES (?, ?)', (user_id, time.time()))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ تم إرسال طلبك بنجاح! رقم الطلب: {response['order']}")
        else:
            bot.send_message(message.chat.id, "❌فشل طلبك.")
    except:
        bot.send_message(message.chat.id, "⚙️ خطأ في الاتصال.")

# --- تشغيل البوت والخادم ---
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
