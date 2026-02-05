import os, time, sqlite3, requests, telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم لـ Render ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive ✅"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- الإعدادات ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
API_URL = os.getenv('API_URL')
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

def get_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn, conn.cursor()

def get_settings():
    conn, cursor = get_db()
    cursor.execute('SELECT force_channel, quantity, welcome_msg FROM settings WHERE id=1')
    return cursor.fetchone()

def is_subscribed(user_id):
    settings = get_settings()
    if not settings or not settings[0] or settings[0] == "None": return True
    try:
        status = bot.get_chat_member(settings[0], user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    conn, cursor = get_db()
    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (user_id,))
    res = cursor.fetchone()
    if res and res[0] == 1: return bot.send_message(message.chat.id, "❌ محظور.")
    if res is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("مَـدار 📢", url=f"https://t.me/{get_settings()[0].replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ اشترك بالقناة أولاً!", reply_markup=markup)

    bot.send_message(message.chat.id, get_settings()[2], reply_markup=main_menu())

def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="account")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("ser_") or call.data == "account")
def handle_user_calls(call):
    user_id = call.from_user.id
    conn, cursor = get_db()
    if call.data == "account":
        cursor.execute('SELECT is_vip FROM users WHERE user_id=?', (user_id,))
        v = "💎 VIP" if cursor.fetchone()[0] == 1 else "👤 عادي"
        bot.send_message(call.message.chat.id, f"👤 ايدي: `{user_id}`\nالحالة: {v}")
    else:
        stype, sid = call.data.split("_")[1], call.data.split("_")[2]
        col = f"last_{stype}"
        cursor.execute(f'SELECT {col}, is_vip FROM users WHERE user_id=?', (user_id,))
        ltime, vip = cursor.fetchone()
        if vip == 0 and (time.time() - ltime) < 43200:
            return bot.answer_callback_query(call.id, "⏳ انتظر 12 ساعة!", show_alert=True)
        msg = bot.send_message(call.message.chat.id, "✅ ارسل الرابط:")
        bot.register_next_step_handler(msg, process_order, sid, col, vip)

def process_order(message, sid, col, vip):
    if not message.text.startswith("http"): return bot.send_message(message.chat.id, "❌ رابط خطأ.")
    qty = get_settings()[1]
    try:
        res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': sid, 'link': message.text, 'quantity': qty}).json()
        if "order" in res:
            if vip == 0:
                conn, cursor = get_db()
                cursor.execute(f'UPDATE users SET {col}=? WHERE user_id=?', (time.time(), message.from_user.id))
                conn.commit()
            bot.send_message(message.chat.id, f"✅ تم الطلب! رقم: {res['order']}")
        else: bot.send_message(message.chat.id, f"❌ خطأ: {res.get('error')}")
    except: bot.send_message(message.chat.id, "⚙️ خطأ.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
