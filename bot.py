import os
import telebot
from flask import Flask, request
import psycopg2

# --- جلب البيانات من Render (تطابق الأسماء في صورتك) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN") # تم التغيير من API_TOKEN
DATABASE_URL = os.environ.get("DATABASE_URL")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")

# فحص أمان للتأكد من القراءة
if not BOT_TOKEN:
    raise ValueError("❌ خطأ: BOT_TOKEN مفقود في إعدادات Render!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# --- ميزة التفاعل (Reactions) ---
def add_reaction(chat_id, message_id):
    try:
        # إضافة تفاعل "👍"
        bot.set_message_reaction(chat_id, message_id, [telebot.types.ReactionTypeEmoji("👍")], is_big=False)
    except Exception as e:
        print(f"Reaction error: {e}")

# --- معالج الرسائل ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    add_reaction(message.chat.id, message.message_id)
    bot.reply_to(message, "تم تحديث الكود بنجاح! التفاعل شغال والقاعدة متصلة. 🚀")

# --- دالة الويب هوك ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Forbidden', 403

# إعداد الويب هوك عند التشغيل
bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
