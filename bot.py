import os
import time
import sqlite3
import requests
import telebot
from flask import Flask
from threading import Thread

# --- إعداد الخادم لإبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- الإعدادات (Environment Variables) ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME') 
ADMIN_ID = os.getenv('ADMIN_ID')
API_URL = "https://provider-site.com/api/v2"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- قاعدة البيانات ---
db_path = os.path.join(os.getcwd(), 'users.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_request REAL)')
conn.commit()

# --- دالة جلب عدد المشتركين ---
def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return cursor.fetchone()[0]

# --- التحقق من الاشتراك الإجباري ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- أمر الاختبار والتفاعل (/test) ---
@bot.message_handler(commands=['test'])
def test_reaction(message):
    try:
        # إضافة تفاعل 👍 على رسالة المستخدم
        bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji("👍")], is_big=False)
    except: pass
    
    bot.reply_to(message, "welcome", parse_mode="Markdown")

# --- أمر البداية والترحيب وإشعار المطور ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"

    # التحقق مما إذا كان المستخدم جديداً
    cursor.execute('SELECT user_id FROM users WHERE user_id=?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        total = get_total_users()
        
        # إشعار المطور بدخول نفر جديد
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
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("اضغط هنا للاشتراك 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        bot.send_message(message.chat.id, f"⚠️ *عذراً عزيزي،*\n\n*يجب عليك الاشتراك في القناة أولاً*\n*لكي تستطيع استخدام كافة خدمات البوت مجاناً!*", reply_markup=markup)
        return

    # رسالة ترحيب متعددة الأسطر وغامقة
    welcome_text = (f"✨ *أهلاً بك في بوت الخدمات المجانية* ✨\n\n"
                    f"🚀 *يمكنك من خلال البوت زيادة:*\n"
                    f"• *مشاهدات القنوات* 👀\n"
                    f"• *مشتركين حقيقيين* 👥\n"
                    f"• *تفاعلات ومنشورات* ❤️\n\n"
                    f"💡 *ملاحظة:* يمكنك طلب خدمة واحدة كل *12 ساعة* مجاناً.")
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👥 مشتركين", "👀 مشاهدات")
    markup.row("❤️ تفاعلات", "👤 حسابي")
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# --- معالجة طلبات الخدمات ---
@bot.message_handler(func=lambda message: message.text in ["👥 مشتركين", "👀 مشاهدات", "❤️ تفاعلات"])
def handle_services(message):
    user_id = message.from_user.id
    
    # التحقق من وقت الانتظار (Cooldown)
    cursor.execute('SELECT last_request FROM users WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    current_time = time.time()

    if row and row[0] is not None and (current_time - row[0]) < (12 * 3600):
        remaining_seconds = int((12 * 3600) - (current_time - row[0]))
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        bot.reply_to(message, f"⏳ *عذراً! يمكنك الطلب مرة أخرى بعد {hours} ساعة و {minutes} دقيقة.*")
        return

    msg = bot.reply_to(message, "✅ *ارسل رابط القناة أو المنشور الآن:*")
    bot.register_next_step_handler(msg, process_request, message.text)

def process_request(message, service_type):
    # هنا يتم الربط مع API الموقع المذكور سابقاً
    bot.send_message(message.chat.id, "⚙️ *جاري معالجة طلبك، يرجى الانتظار...*")
    # (كود الـ API يوضع هنا كما في الأمثلة السابقة)

# --- تشغيل البوت ---
if __name__ == "__main__":
    keep_alive()
    print("Bot is running...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
