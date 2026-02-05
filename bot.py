import os
import time
import sqlite3
import requests
import telebot
from flask import Flask, request
from threading import Thread
from telebot import types
import admin_panel

# ================== Flask ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "البوت يعمل بنجاح ✅"

# ================== الإعدادات ==================
API_TOKEN = os.getenv("BOT_TOKEN")
SMM_API_KEY = os.getenv("SMM_API_KEY")
CH_ID = os.getenv("CHANNEL_USERNAME")
API_URL = os.getenv("API_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://your-app.onrender.com

# ================== Telegram Bot ==================
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# ================== قاعدة البيانات ==================
db_path = os.path.join(os.getcwd(), "users.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    last_sub REAL DEFAULT 0,
    last_view REAL DEFAULT 0,
    last_react REAL DEFAULT 0
)
""")
conn.commit()

# ================== لوحة الأدمن ==================
admin_panel.register(bot, cursor, conn)

# ================== وظائف ==================
def get_total_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return 12947 + cursor.fetchone()[0]

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def main_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    )
    return markup

# ================== Handlers ==================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    try:
        bot.set_message_reaction(
            message.chat.id,
            message.message_id,
            [types.ReactionTypeEmoji("🔥")],
            is_big=False
        )
    except:
        pass

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                " مَـدار 📢",
                url=f"https://t.me/{CH_ID.replace('@','')}"
            )
        )
        return bot.send_message(
            message.chat.id,
            "⚠️ *يجب الاشتراك بالقناة أولاً!*",
            reply_markup=markup
        )

    bot.send_message(
        message.chat.id,
        "✨ *أهلاً بك في بوت الخدمات* ✨",
        reply_markup=main_inline_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if call.data == "my_account":
        return bot.send_message(
            call.message.chat.id,
            f"👤 *حسابك:*\n• ايدي: `{user_id}`\n• المشتركين في البوت: {get_total_users()}"
        )

    if call.data.startswith("ser_"):
        _, service_type, service_id = call.data.split("_")
        column_name = f"last_{service_type}"

        cursor.execute(f"SELECT {column_name} FROM users WHERE user_id=?", (user_id,))
        last_time = cursor.fetchone()[0]

        if (time.time() - last_time) < (12 * 3600):
            remaining = int((12 * 3600) - (time.time() - last_time))
            return bot.answer_callback_query(
                call.id,
                f"⏳ متبقي {remaining//3600} ساعة و {(remaining%3600)//60} دقيقة",
                show_alert=True
            )

        msg = bot.send_message(call.message.chat.id, "✅ *ارسل الآن رابط الخدمة المطلوبة:*")
        bot.register_next_step_handler(msg, process_api_request, service_id, column_name)

def process_api_request(message, service_id, column_name):
    if not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ *رابط غير صحيح.*")

    payload = {
        "key": SMM_API_KEY,
        "action": "add",
        "service": service_id,
        "link": message.text,
        "quantity": 100
    }

    try:
        response = requests.post(API_URL, data=payload, timeout=10)
        res = response.json()

        if "order" in res:
            cursor.execute(
                f"UPDATE users SET {column_name}=? WHERE user_id=?",
                (time.time(), message.from_user.id)
            )
            conn.commit()
            bot.send_message(
                message.chat.id,
                f"🔥✅ *تم إرسال طلبك بنجاح!*\n• رقم الطلب: `{res['order']}`"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ *رد الموقع:* {res.get('error', 'خطأ غير معروف')}"
            )
    except:
        bot.send_message(message.chat.id, "⚙️ *فشل الاتصال.*")

# ================== Webhook ==================
@app.route("/webhook", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================== تشغيل ==================
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    run()
