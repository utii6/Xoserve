import os, time, psycopg2, requests, telebot, urllib.parse
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بكفاءة ✅"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
def keep_alive(): Thread(target=run, daemon=True).start()

# --- الإعدادات ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
API_URL = os.getenv('API_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
OWNER_ID = 5581457665 

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

def get_db_connection():
    db_url = DATABASE_URL
    if db_url and "?sslmode" in db_url:
        db_url = db_url.split("?")[0]
    return psycopg2.connect(db_url)

# --- إشعار إضافة البوت لقناة أو مجموعة ---
@bot.my_chat_member_handler()
def bot_added_to_chat(message):
    if message.new_chat_member.status in ['administrator', 'member']:
        chat = message.chat
        user = message.from_user
        
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (chat_id, owner_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (chat.id, user.id))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM channels"); total_ch = cursor.fetchone()[0]
        cursor.close(); conn.close()
        
        info = (f"🆕 **قام مستخدم جديد بإضافة البوت الخاص بك إلى مجموعة**\n\n"
                f"📌 **معلومات القناه:**\n"
                f"• اسم المجموعة: {chat.title}\n"
                f"• الآيدي: `{chat.id}`\n"
                f"• اسم المستخدم: @{chat.username or 'لا يوجد'}\n\n"
                f"👤 **معلومات العضو الذي قام بالإضافة:**\n"
                f"• الاسم: {user.first_name}\n"
                f"• اسم المستخدم: @{user.username or 'لا يوجد'}\n"
                f"• الآيدي: `{user.id}`\n\n"
                f"📊 إجمالي عدد القنوات حتى الآن: {total_ch}")
        bot.send_message(OWNER_ID, info)

# --- أمر التشغيل الرئيسي ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id=%s', (uid,))
    row = cursor.fetchone()
    if row and row[0] == 1: 
        cursor.close(); conn.close(); return

    if row is None:
        referrer = 0
        if len(args) > 1 and args[1].isdigit():
            referrer = int(args[1])
            if referrer != uid:
                cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=%s', (referrer,))
                conn.commit()

        cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', (uid, referrer, message.from_user.username))
        conn.commit()
        
        # إشعار الدخول بصيغتك الأصلية
        owner_msg = (f"<< دخول نفـرر جديد لبوتك >>\n"
                     f"• الاسم😂: {message.from_user.first_name}\n"
                     f"• المعرف💁: @{message.from_user.username or 'لا يوجد'}\n"
                     f"• الايدي🆔: `{uid}`\n"
                     f"• عدد مشتركينك الفقراء: {get_total_users()}")
        try: bot.send_message(OWNER_ID, owner_msg)
        except: pass
    
    cursor.close(); conn.close() 

    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("مَـدار📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, f"⚠️ *يجب الاشتراك هنا {CH_ID} !*", reply_markup=markup)

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        types.InlineKeyboardButton("⭐ اشتراك VIP", callback_data="vip_options")
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓\n*𝚍𝚎𝚟:* @E2E12", reply_markup=markup)

# --- خيارات الـ VIP ---
@bot.callback_query_handler(func=lambda call: call.data == "vip_options")
def vip_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton("🌟 اشتراك بـ 50 نجمة (يومي)", callback_data="buy_vip_stars"),
        types.InlineKeyboardButton("💰 اشتراك بـ 13 نقطة (يومي)", callback_data="buy_vip_points"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start")
    )
    msg_text = ("اهلا صديقي اشتراك vip يمنحك فرصة التخلص من الوقت والانتظار وكمية كبيرة في الطلبات وأعداد المتابعين.\n\n"
                "الاشتراك سيكون يومي بـ 50 نجمه 🌟 أو تجميع 13 إحالة لليوم الواحد.\n"
                "راسلني اذا حاب تكتشف مميزات احلى @e2e12")
    bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- معالجة الطلبات مع تقليل الوقت لـ 3 ساعات ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("ser_"))
def handle_services(call):
    uid = call.from_user.id
    service_type, s_id = call.data.split("_")[1], call.data.split("_")[2]
    col = f"last_{service_type}"
    
    is_vip = check_vip_status(uid)
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute(f"SELECT {col} FROM users WHERE user_id=%s", (uid,))
    last_time = cursor.fetchone()[0]
    cursor.close(); conn.close()

    # الوقت الجديد: 3 ساعات = 10800 ثانية
    if not is_vip and (time.time() - last_time) < 10800:
        rem = int(10800 - (time.time() - last_time))
        return bot.answer_callback_query(call.id, f"⏳ متبقي {rem//3600} ساعة و {(rem%3600)//60} دقيقة", show_alert=True)
    
    msg = bot.send_message(call.message.chat.id, "🔗 *ارسل الرابط الآن:*")
    bot.register_next_step_handler(msg, process_order, s_id, col)

# (أكمل بقية الدوال مثل get_total_users, process_order, check_vip_status من الكود السابق)

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
