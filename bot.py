import os
import telebot
from flask import Flask, request
import psycopg2

# --- الإعدادات ---
API_TOKEN = os.environ.get("API_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # https://xoserve.onrender.com
DATABASE_URL = os.environ.get("DATABASE_URL")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME") # @Madar_ch

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# --- الاتصال بقاعدة البيانات ---
def get_db_connection():
    # المنفذ 6543 مع تنظيف الرابط من أي بارامترات زائدة
    clean_url = DATABASE_URL.split('?')[0]
    return psycopg2.connect(clean_url)

# --- نظام الويب هوك (الاستقبال) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# --- ميزة التفاعل مع الرسالة (Message Reaction) ---
def add_reaction(chat_id, message_id):
    try:
        # إضافة تفاعل "👍" (تحتاج إصدار حديث من المكتبة وتلجرام)
        bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji("👍")])
    except Exception as e:
        print(f"Reaction error: {e}")

# --- الأوامر (Handlers) ---
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    # إضافة التفاعل فوراً
    add_reaction(chat_id, message.message_id)
    
    # رسالة ترحيبية بسيطة للتأكد من العمل
    bot.reply_to(message, "أهلاً بك! تم الاتصال بنجاح والتفاعل مع رسالتك. 🚀")

# --- تفعيل الويب هوك عند تشغيل السيرفر ---
try:
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook is set and ready")
except Exception as e:
    print(f"❌ Webhook Error: {e}")

# ملاحظة: لا نضع app.run هنا لأن Gunicorn يتولى ذلك
