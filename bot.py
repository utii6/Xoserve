import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد خادم Flask لإبقاء البوت حياً على Render ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Status: Running Successfully!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- جلب الإعدادات من متغيرات البيئة ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME') 
ADMIN_ID = os.getenv('ADMIN_ID')
API_URL = "https://provider-site.com/api/v2" # تأكد من رابط API موقعك

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- إدارة قاعدة البيانات ---
db_path = os.path.join(os.getcwd(), 'users.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_request REAL)')
conn.commit()

# --- الدوال المساعدة ---

def get_total_users():
    """حساب المستخدمين: يبدأ من 300 + المسجلين في القاعدة"""
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    return 8283 + count

def is_subscribed(user_id):
    """التحقق من عضوية المستخدم في القناة"""
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def main_inline_menu():
    """إنشاء الأزرار الشفافة"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="service_sub"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="service_view"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="service_react"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    ]
    markup.add(*btns)
    return markup

# --- معالجة الأوامر ---

@bot.message_handler(commands=['test'])
def test_command(message):
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("👍")], is_big=False)
    except: pass
    bot.reply_to(message, "welcome")

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    # 1. التفاعل بـ 👍 على رسالة المستخدم
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except: pass

    # 2. تسجيل المستخدم وإشعار المطور
    cursor.execute('SELECT user_id FROM users WHERE user_id=?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        total = get_total_users()
        
        admin_msg = (f"*دخول نفـرر جديد لبوتك 😎*\n"
                     f"-----------------------\n"
                     f"• *الاسم😂:* {name}\n"
                     f"• *معرف💁:* {username}\n"
                     f"• *الايدي🆔:* `{user_id}`\n"
                     f"-----------------------\n"
                     f"• *عدد مشتركينك الابطال:* {total}")
        bot.send_message(ADMIN_ID, admin_msg)

    # 3. التحقق من الاشتراك الإجباري
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("اشترك هنا أولاً 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        bot.send_message(message.chat.id, f"⚠️ *عذراً عزيزي،*\n\n*يجب عليك الاشتراك في القناة أولاً*\n*لكي تستطيع استخدام كافة خدمات البوت مجاناً!*", reply_markup=markup)
        return

    # 4. رسالة الترحيب
    welcome_text = (f"✨ *أهلاً بك في بوت الخدمات المجانية* ✨\n\n"
                    f"🚀 *يمكنك من خلال البوت زيادة:*\n"
                    f"• *مشاهدات القنوات* 👀\n"
                    f"• *مشتركين حقيقيين* 👥\n"
                    f"• *تفاعلات ومنشورات* ❤️\n\n"
                    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_inline_menu())

# --- معالجة الأزرار الشفافة ---

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if call.data == "my_account":
        total = get_total_users()
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"👤 *معلومات حسابك:*\n\n• الايدي الخاص بك: `{user_id}`\n• إجمالي مستخدمي البوت: {total}")
        return

    if call.data.startswith("service_"):
        # التحقق من وقت الانتظار (12 ساعة)
        cursor.execute('SELECT last_request FROM users WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        current_time = time.time()

        if row and row[0] is not None and (current_time - row[0]) < (12 * 3600):
            remaining = int((12 * 3600) - (current_time - row[0]))
            hours, minutes = remaining // 3600, (remaining % 3600) // 60
            bot.answer_callback_query(call.id, f"⏳ متبقي لك {hours} ساعة و {minutes} دقيقة", show_alert=True)
            return

        service_map = {"service_sub": "👥 مشتركين", "service_view": "👀 مشاهدات", "service_react": "❤️ تفاعلات"}
        selected = service_map.get(call.data)
        
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, f"✅ *اخترت خدمة: {selected}*\n\n*ارسل الآن رابط القناة أو المنشور:*")
        bot.register_next_step_handler(msg, process_request, selected)

def process_request(message, service_type):
    # هنا تضع كود requests.post للموقع المزود كما شرحنا سابقاً
    bot.send_message(message.chat.id, "⚙️ *جاري الطلب...*")
    # بعد نجاح الطلب، يتم تحديث الوقت:
    # cursor.execute('UPDATE users SET last_request=? WHERE user_id=?', (time.time(), message.from_user.id))
    # conn.commit()

# --- تشغيل البوت ---
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
