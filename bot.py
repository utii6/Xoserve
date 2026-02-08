import os
import telebot
from flask import Flask, request
import psycopg2

# جلب الإعدادات من Render (تأكد من مطابقتها لصورتك)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# دالة التفاعل مع الرسالة (Reaction)
def add_reaction(chat_id, message_id):
    try:
        # إضافة إيموجي "👍" على رسالة المستخدم
        bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji("👍")])
    except Exception as e:
        print(f"Reaction error: {e}")

# معالجة أمر البداية
@bot.message_handler(commands=['start'])
def start(message):
    # تفاعل مع رسالة المستخدم
    add_reaction(message.chat.id, message.message_id)
    # الرد برسالة
    bot.reply_to(message, "✅ تم التحديث بنجاح!\n\nالبوت الآن متصل بقاعدة البيانات ويدعم التفاعل مع الرسائل.")

# دالة الاستقبال (Webhook Handler)
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# ضبط الويب هوك تلقائياً عند التشغيل
try:
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("✅ Webhook is ready!")
except Exception as e:
    print(f"❌ Webhook Error: {e}")
