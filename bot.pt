import os
import time
import psycopg2
import requests
import telebot
from flask import Flask, request
from telebot import types

# ================== الإعدادات ==================
# هذه القيم سيجلبها البوت تلقائياً من Environment Variables في Render
API_TOKEN = os.getenv("BOT_TOKEN")
SMM_API_KEY = os.getenv("SMM_API_KEY")
CH_ID = os.getenv("CHANNEL_USERNAME")
API_URL = os.getenv("API_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# ================== قاعدة البيانات (Supabase) ==================
def get_db_connection():
    # إصلاح الرابط ليتوافق مع مكتبة psycopg2
    url = DATABASE_URL.replace("postgres://", "postgresql://")
    return psycopg2.connect(url)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # إنشاء جدول المستخدمين إذا لم يكن موجوداً
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            last_sub DOUBLE PRECISION DEFAULT 0,
            last_view DOUBLE PRECISION DEFAULT 0,
            last_react DOUBLE PRECISION DEFAULT 0
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# تهيئة القاعدة عند بدء التشغيل
try:
    init_db()
    print("✅ Database connected & initialized")
except Exception as e:
    print(f"❌ Database error: {e}")

# ================== الوظائف المساعدة ==================
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ["member", "administrator", "creator"]
    except:
        return False

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_acc")
    )
    return markup

# ================== التعامل مع الرسائل ==================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # حفظ المستخدم في Supabase
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    if not is_subscribed(user_id):
        btn = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("مَـدار📢", url=f"https://t.me/{CH_ID.strip('@')}")
        )
        return bot.send_message(message.chat.id, "⚠️ *يجب الاشتراك لاستخدام البوت!*", reply_markup=btn)

    bot.send_message(message.chat.id, "✨ *مرحباً بك في بوت الخدمات المميز*", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_queries(call):
    user_id = call.from_user.id

    if call.data == "my_acc":
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = 10987 + cur.fetchone()[0]
        cur.close()
        conn.close()
        return bot.send_message(call.message.chat.id, f"👤 *حسابك:*\n• ايدي: `{user_id}`\n• عدد مستخدمي البوت: {total}")

    if call.data.startswith("ser_"):
        _, service_type, service_id = call.data.split("_")
        column = f"last_{service_type}"

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT {column} FROM users WHERE user_id = %s", (user_id,))
        last_time = cur.fetchone()[0]
        cur.close()
        conn.close()

        # تحقق من مرور 12 ساعة
        if (time.time() - last_time) < 43200:
            remaining = int(43200 - (time.time() - last_time))
            return bot.answer_callback_query(call.id, f"⏳ متبقي {remaining//3600} ساعة و {(remaining%3600)//60} دقيقة", show_alert=True)

        msg = bot.send_message(call.message.chat.id, "🔗 *ارسل رابط الخدمه الآن:*")
        bot.register_next_step_handler(msg, process_order, service_id, column)

def process_order(message, service_id, column):
    if not message.text or "http" not in message.text:
        return bot.send_message(message.chat.id, "❌ *الرابط غير صحيح.*")

    payload = {
        "key": SMM_API_KEY,
        "action": "add",
        "service": service_id,
        "link": message.text,
        "quantity": 100
    }

    try:
        response = requests.post(API_URL, data=payload, timeout=15).json()
        if "order" in response:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE users SET {column} = %s WHERE user_id = %s", (time.time(), message.from_user.id))
            conn.commit()
            cur.close()
            conn.close()
            bot.send_message(message.chat.id, f"✅ *تم إرسال الطلب!*\n• رقم الطلب: `{response['order']}`")
        else:
            bot.send_message(message.chat.id, f"❌ *خطأ من @E2E12 :* {response.get('error')}")
    except:
        bot.send_message(message.chat.id, "⚙️ *فشل الاتصال.*")

# ================== تشغيل الـ Webhook ==================
@app.route("/webhook", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
