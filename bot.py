import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم لإبقاء البوت حياً على Render ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بنجاح ✅"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات (جلب القيم من إعدادات Render) ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME') 
ADMIN_ID = os.getenv('ADMIN_ID')
API_URL = os.getenv('API_URL') # يفضل وضعه في Render (مثال: https://smm-site.com/api/v2)

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- قاعدة البيانات ---
db_path = os.path.join(os.getcwd(), 'users.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_request REAL)')
conn.commit()

# --- الدوال المساعدة ---
def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return 8463 + cursor.fetchone()[0]

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def main_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="service_14681")
    btn2 = types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="service_14527")
    btn3 = types.InlineKeyboardButton("❤️ تفاعلات", callback_data="service_13925")
    btn4 = types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# --- الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    # التفاعل التلقائي 👍
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except: pass

    # تسجيل المستخدم وإشعار المطور
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

    # التحقق من الاشتراك الإجباري
    if not is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(" مَـدار 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        bot.send_message(message.chat.id, f"⚠️ *عذراً عزيزي،*\n\n*يجب عليك الاشتراك في القناة أولاً*\n*!*", reply_markup=markup)
        return

    welcome_text = (f"✨ * أهلاً بك في بوت الخدمات المجانية* ✨\n\n"
                    f"🚀 *يمكنك من خلال البوت زيادة:*\n"
                    f"• *تفاعل قناتك مجاناً 🆓* \n"
                    f"• *ارسله لصاحبك يستفاد مثلك ↗️* \n"
                    f"• *Dev: @E2E12 👨🏼‍💻* \n\n"
                      )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_inline_menu())

# --- معالجة الضغط على الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id

    if call.data == "my_account":
        total = get_total_users()
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"👤 *معلومات حسابك:*\n\n• ايدي الحساب: `{user_id}`\n• عدد المشتركين الابطال: {total}")
        return

    if call.data.startswith("service_"):
        service_id = call.data.split("_")[1]
        
        # تحقق من وقت الانتظار (12 ساعة)
        cursor.execute('SELECT last_request FROM users WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        if row and row[0] and (time.time() - row[0]) < (12 * 3600):
            remaining = int((12 * 3600) - (time.time() - row[0]))
            bot.answer_callback_query(call.id, f"⏳ متبقي {remaining//3600} ساعة و {(remaining%3600)//60} دقيقة", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "✅ *ارسل الآن رابط القناة أو المنشور:*")
        bot.register_next_step_handler(msg, process_api_request, service_id)

def process_api_request(message, service_id):
    link = message.text
    user_id = message.from_user.id

    if not link.startswith("http"):
        bot.send_message(message.chat.id, "❌ *الرابط غير صحيح، حاول مجدداً.*")
        return

    # إعداد الطلب بالكمية الثابتة 100
    payload = {
        'key': SMM_API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': 100  # الكمية الموحدة لجميع الطلبات
    }

    try:
        response = requests.post(API_URL, data=payload)
        res_json = response.json()
        
        if "order" in res_json:
            # تحديث الوقت في قاعدة البيانات بعد نجاح الطلب
            cursor.execute('UPDATE users SET last_request=? WHERE user_id=?', (time.time(), user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ *تم إرسال طلبك بنجاح!*\n• رقم الطلب: `{res_json['order']}`\n• الكمية: `100`")
        elif "error" in res_json:
            bot.send_message(message.chat.id, f"❌ *خطأ من المصدر:* {res_json['error']}")
        else:
            bot.send_message(message.chat.id, "❌ *فشلت العملية، تأكد من الرابط  .*")
    except Exception as e:
        bot.send_message(message.chat.id, "⚙️ *خطأ في الاتصال.*")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
