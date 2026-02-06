import os, time, sqlite3, requests, telebot
from flask import Flask
from threading import Thread
from telebot import types
import admin_panel 

# إعداد السيرفر
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل ✅"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
Thread(target=run, daemon=True).start()

# الإعدادات
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
API_URL = os.getenv('API_URL')
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0, is_vip INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)')
conn.commit()

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (uid,))
    res = cursor.fetchone()
    if res and res[0] == 1: return
    if res is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (uid,))
        conn.commit()

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓", reply_markup=markup)

# معالج أزرار المستخدم حصراً
@bot.callback_query_handler(func=lambda call: call.data in ["ser_sub_14681", "ser_view_14527", "ser_react_13925", "my_account", "buy_vip"])
def handle_user(call):
    uid = call.from_user.id
    if call.data == "my_account":
        cursor.execute("SELECT is_vip FROM users WHERE user_id=?", (uid,))
        is_vip = cursor.fetchone()[0]
        msg = f"👤 ايدي: `{uid}`\n⭐ الحالة: {'💎 VIP' if is_vip else 'عادي'}"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip"))
        bot.send_message(call.message.chat.id, msg, reply_markup=markup)
    
    elif call.data == "buy_vip":
        bot.send_message(call.message.chat.id, "⭐ للاشتراك في VIP، تواصل مع: @E2E12")

    elif call.data.startswith("ser_"):
        service_id = call.data.split("_")[2]
        col = f"last_{call.data.split('_')[1]}"
        msg = bot.send_message(call.message.chat.id, "🔗 ارسل الرابط الآن:")
        bot.register_next_step_handler(msg, process_order, service_id, col)
    bot.answer_callback_query(call.id)

def process_order(message, s_id, col):
    if not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ رابط غير صحيح.")
    
    payload = {'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': 100}
    try:
        res = requests.post(API_URL, data=payload).json()
        if "order" in res:
            cursor.execute(f'UPDATE users SET {col}=? WHERE user_id=?', (time.time(), message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ تم الطلب بنجاح! رقم: {res['order']}")
        else:
            bot.send_message(message.chat.id, f"❌ خطأ: {res.get('error')}")
    except:
        bot.send_message(message.chat.id, "⚙️ فشل الاتصال بالمزود.")

# تسجيل لوحة الإدارة
admin_panel.register(bot, cursor, conn)

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
