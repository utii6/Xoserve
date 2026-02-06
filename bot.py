import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot import types
import admin_panel  # استدعاء لوحة الإدارة

# --- إعداد الخادم لإبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home():
    return "البوت يعمل بنجاح ✅"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- الإعدادات ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
ADMIN_ID = 5581457665  # الآيدي الخاص بك
API_URL = os.getenv('API_URL')

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- قاعدة البيانات ---
db_path = os.path.join(os.getcwd(), 'users.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, 
                   last_view REAL DEFAULT 0, 
                   last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0,
                   is_banned INTEGER DEFAULT 0)''')
conn.commit()

# --- استدعاء تسجيل لوحة الإدارة (يجب أن يكون هنا لضمان الأولوية) ---
admin_panel.register(bot, cursor, conn)

# --- احصائيات ---
def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return 13485 + cursor.fetchone()[0]

def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
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

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # فحص الحظر أولاً
    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (user_id,))
    res = cursor.fetchone()
    if res and res[0] == 1:
        return bot.send_message(message.chat.id, "❌ *أنت محظور من استخدام البوت.*")

    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except:
        pass

    if res is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        bot.send_message(
            ADMIN_ID,
            f"دخول نفـرر جديد لبوتك 😎\n"
            f"• الاسم😂: {message.from_user.first_name}\n"
            f"• المعرف💁: @{message.from_user.username or 'غير موجود'}\n"
            f"• الايدي🆔: {user_id}\n"
            f"• عدد مشتركينك الابطال: {get_total_users()}"
        )

    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("مَـدار 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ *يجب الاشتراك بالقناة أولاً!*", reply_markup=markup)

    bot.send_message(
        message.chat.id,
        "*اهلا بك في بوت الخدمات المجانية* 🆓\n"
        "*البوت سيساعدك في زيادة تفاعل قناتك* ✅\n"
        "--- \n"
        "• *𝚍𝚎𝚟:* @E2E12",
        reply_markup=main_inline_menu()
    )

# --- معالج أزرار المستخدم (تم استثناء أزرار الأدمن منه ليعمل الملفان معاً) ---
@bot.callback_query_handler(func=lambda call: call.data in ["ser_sub_14681", "ser_view_14527", "ser_react_13925", "my_account", "buy_vip"])
def handle_query(call):
    user_id = call.from_user.id
    
    if call.data == "my_account":
        cursor.execute("SELECT is_vip FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        is_vip = row[0] if row else 0
        vip_status = "💎 VIP" if is_vip else "👤 حساب عادي"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("شارك البوت 🔗", url=f"https://t.me/share/url?url=@{bot.get_me().username}"),
            types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip")
        )
        bot.send_message(
            call.message.chat.id,
            f"👤 الايدي: `{user_id}`\n"
            f"👥 عدد المستخدمين: {get_total_users()}\n"
            f"⭐ الحالة: {vip_status}",
            reply_markup=markup
        )

    # --- هذا هو الجزء الجديد للرد على زر اشتراك VIP ---
    elif call.data == "buy_vip":
        text = (
            "💎⭐ *مميزات اشتراك VIP:*\n"
            "1️⃣ إلغاء وقت الانتظار (طلب بدون توقف).\n"
            "2️⃣ أولوية في تنفيذ الطلبات.\n"
            "3️⃣ دعم فني مباشر.\n\n"
            "💳 *للاشتراك تواصل مع المطور:* @E2E12"
        )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        bot.answer_callback_query(call.id) # لإخفاء علامة التحميل من الزر

    elif call.data.startswith("ser_"):
        # ... بقية كود الخدمات كما هو ...
        pass


    elif call.data.startswith("ser_"):
        data = call.data.split("_")
        service_type = data[1]
        service_id = data[2]
        column_name = f"last_{service_type}"
        
        cursor.execute(f'SELECT {column_name}, is_vip FROM users WHERE user_id=?', (user_id,))
        res = cursor.fetchone()
        last_time = res[0]
        is_vip = res[1]

        # فحص الوقت فقط لغير الـ VIP
        if is_vip == 0 and (time.time() - last_time) < (12 * 3600):
            remaining = int((12 * 3600) - (time.time() - last_time))
            return bot.answer_callback_query(call.id, f"⏳ متبقي لهذه الخدمة {remaining//3600} ساعة و {(remaining%3600)//60} دقيقة", show_alert=True)

        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, f"✅ *ارسل الآن رابط الخدمة المطلوبة:*")
        bot.register_next_step_handler(msg, process_api_request, service_id, column_name)

def process_api_request(message, service_id, column_name):
    if not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ *رابط غير صحيح.*")

    payload = {'key': SMM_API_KEY, 'action': 'add', 'service': service_id, 'link': message.text, 'quantity': 100}

    try:
        response = requests.post(API_URL, data=payload, timeout=10)
        res = response.json()
        if "order" in res:
            cursor.execute(f'UPDATE users SET {column_name}=? WHERE user_id=?', (time.time(), message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ *تم إرسال طلبك بنجاح!*\n• رقم الطلب: `{res['order']}`")
        else:
            bot.send_message(message.chat.id, f"❌ *رد الموقع:* {res.get('error', 'خطأ غير معروف')}")
    except:
        bot.send_message(message.chat.id, "⚙️ *فشل الاتصال بموقع الخدمات.*")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    time.sleep(1)
    print("🚀 البوت يعمل الآن ولوحة التحكم مفعلة!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
