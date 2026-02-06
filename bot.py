import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot import types

# ================= Flask (Keep Alive) =================
app = Flask(__name__)

@app.route('/')
def home():
    return "BOT IS RUNNING"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    Thread(target=run, daemon=True).start()

# ================= Config =================
API_TOKEN = os.getenv("BOT_TOKEN")
SMM_API_KEY = os.getenv("SMM_API_KEY")
API_URL = os.getenv("API_URL")
CH_ID = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = 5581457665  # ايديك مباشرة

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
import admin_panel
admin_panel.register(bot, cursor, conn)
# ================= Database =================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_vip INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    last_sub REAL DEFAULT 0,
    last_view REAL DEFAULT 0,
    last_react REAL DEFAULT 0
)
""")
conn.commit()

# ================= Helpers =================
def get_total_users():
    cursor.execute("SELECT COUNT(*) FROM users")
    return 13473 + cursor.fetchone()[0]

def is_subscribed(user_id):
    try:
        s = bot.get_chat_member(CH_ID, user_id).status
        return s in ["member", "administrator", "creator"]
    except:
        return False

def is_vip(user_id):
    cursor.execute("SELECT is_vip FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r and r[0] == 1

def is_banned(user_id):
    cursor.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r and r[0] == 1

# ================= Keyboards =================
def main_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
    )
    return m

def account_menu(user_id):
    vip_status = "VIP 🌟" if is_vip(user_id) else "عادي"
    m = types.InlineKeyboardMarkup()
    m.add(
        types.InlineKeyboardButton(
            "🔗 مشاركة البوت",
            url="https://t.me/share/url?url=@t3tbbot"
        )
    )
    m.add(
        types.InlineKeyboardButton(
            "🌟 اشترك VIP",
            callback_data="vip_info"
        )
    )
    return vip_status, m

# ================= Start =================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()

    if not exists:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        bot.send_message(
            ADMIN_ID,
            f"""دخول نفـرر جديد لبوتك 😎
• الاسم😂:: {message.from_user.first_name}
• معرف💁: @{message.from_user.username or 'بدون'}
• الايدي🆔: {user_id}
• عدد مشتركينك الابطال: {get_total_users()}"""
        )

    if is_banned(user_id):
        return bot.send_message(message.chat.id, "🚫😂 *أنت محظور من استخدام البوت*")

    if not is_subscribed(user_id):
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("📢مَـدار", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ اشترك بالقناة أولاً", reply_markup=m)

    bot.send_message(
        message.chat.id,
        "**اهلا بك في بوت الخدمات المجانية 🆓**\n"
        "**البوت سيساعدك في زيادة تفاعل قناتك ✅**\n"
        "**- 𝚍𝚎𝚟: @E2E12**",
        reply_markup=main_menu()
    )

# ================= Callbacks =================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    user_id = call.from_user.id

    if is_banned(user_id):
        return bot.answer_callback_query(call.id, "😂🚫 محظور", show_alert=True)

    if call.data == "my_account":
        status, markup = account_menu(user_id)
        return bot.send_message(
            call.message.chat.id,
            f"👤 حسابك:\n"
            f"• الايدي: `{user_id}`\n"
            f"• عدد المشتركين: {get_total_users()}\n"
            f"• نوع الحساب: {status}",
            reply_markup=markup
        )

    if call.data == "vip_info":
        return bot.send_message(
            call.message.chat.id,
            "🌟 **اشتراك VIP**\n\n"
            "• بدون انتظار ⏱\n"
            "• كميات أكبر 🔥\n"
            "• أولوية عالية 🚀\n\n"
            "💰 السعر: 50 نجمة / يوم\n"
            "📩 راسلني: @e2e12"
        )

    if call.data.startswith("ser_"):
        if not is_vip(user_id):
            column = f"last_{call.data.split('_')[1]}"
            cursor.execute(f"SELECT {column} FROM users WHERE user_id=?", (user_id,))
            last = cursor.fetchone()[0] or 0
            if time.time() - last < 43200:
                return bot.answer_callback_query(call.id, "⏳ انتظر انتهاء الوقت", show_alert=True)

        service_id = call.data.split("_")[2]
        msg = bot.send_message(call.message.chat.id, "🔗 ارسل الرابط")
        bot.register_next_step_handler(msg, process_order, service_id)

# ================= Orders =================
def process_order(message, service_id):
    if not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ رابط غير صالح")

    qty = 1000 if is_vip(message.from_user.id) else 100

    payload = {
        "key": SMM_API_KEY,
        "action": "add",
        "service": service_id,
        "link": message.text,
        "quantity": qty
    }

    try:
        r = requests.post(API_URL, data=payload, timeout=10).json()
        if "order" in r:
            bot.send_message(message.chat.id, f"✅ تم الطلب\nرقم: `{r['order']}`")
        else:
            bot.send_message(message.chat.id, f"❌ خطأ: {r.get('error')}")
    except:
        bot.send_message(message.chat.id, "⚙️ فشل الاتصال")

# ================= Admin Notify Functions =================
def notify_vip(user_id):
    bot.send_message(user_id, "🌟✅ تم منحك اشتراك VIP بنجاح")

def notify_ban(user_id):
    bot.send_message(user_id, "😂🚫 تم حظرك من استخدام البوت")

# ================= Run =================
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(skip_pending=True)
