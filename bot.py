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

# متغيرات اقتراحاتي (الأكواد)
gift_settings = {"code": None, "val": 0, "limit": 0, "users": []}

def get_db_connection():
    db_url = DATABASE_URL
    if db_url and "?sslmode" in db_url:
        db_url = db_url.split("?")[0]
    return psycopg2.connect(db_url)

# --- لوحة التحكم الشاملة (طلباتك + اقتراحاتي) ---
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != OWNER_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قناة إجبارية", callback_data="adm_addch"),
        types.InlineKeyboardButton("❌ حذف قناة إجبارية", callback_data="adm_delch"),
        types.InlineKeyboardButton("💰 شحن نقاط", callback_data="adm_points"),
        types.InlineKeyboardButton("🎁 صنع كود هدية", callback_data="adm_gift"), # اقتراح
        types.InlineKeyboardButton("🔒 حظر", callback_data="adm_ban"),
        types.InlineKeyboardButton("🔓 فك حظر", callback_data="adm_unban"),
        types.InlineKeyboardButton("💎 منح VIP", callback_data="adm_vip"),
        types.InlineKeyboardButton("🗑 حذف VIP", callback_data="adm_delvip"),
        types.InlineKeyboardButton("📢 إذاعة", callback_data="adm_bc"),
        types.InlineKeyboardButton("💵 رصيد SMM", callback_data="adm_smm"), # اقتراح
        types.InlineKeyboardButton("📊 احصائيات", callback_data="adm_sts")
    )
    bot.send_message(message.chat.id, "🛠 *لوحة التحكم المتكاملة (المالك):*", reply_markup=markup)

# --- أمر التشغيل الرئيسي مع إشعار "الفقراء" ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id=%s', (uid,))
    row = cursor.fetchone()
    
    if row and row[0] == 1: return
    
    if row is None:
        referrer = 0
        if len(args) > 1 and args[1].isdigit():
            referrer = int(args[1])
            cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=%s', (referrer,))
            conn.commit()

        cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', (uid, referrer, message.from_user.username))
        conn.commit()
        
        # إشعار الدخول الأصلي (الفقراء)
        owner_msg = (f"<< دخول نفـرر جديد لبوتك >>\n"
                     f"• الاسم😂: {message.from_user.first_name}\n"
                     f"• المعرف💁: @{message.from_user.username or 'لا يوجد'}\n"
                     f"• الايدي🆔: `{uid}`\n"
                     f"• عدد مشتركينك الفقراء: {get_total_users()}")
        bot.send_message(OWNER_ID, owner_msg)
    
    cursor.close(); conn.close() 

    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("مَـدار📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, f"⚠️ *يجب الاشتراك هنا {CH_ID} !*", reply_markup=markup)

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        types.InlineKeyboardButton("💎 اشتراك VIP", callback_data="vip_menu"),
        types.InlineKeyboardButton("🎁 استخدام كود هدية", callback_data="use_gift") # اقتراح
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓\n*𝚍𝚎𝚟:* @E2E12", reply_markup=markup)

# --- معالجة الضغطات ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    if call.data == "use_gift": # اقتراح
        msg = bot.send_message(call.message.chat.id, "ارسل كود الهدية الآن 🎁:")
        bot.register_next_step_handler(msg, process_gift_use)

    elif call.data == "adm_gift": # اقتراح
        msg = bot.send_message(call.message.chat.id, "ارسل الكود:القيمة:العدد (مثال: `GIFT:10:50`)")
        bot.register_next_step_handler(msg, make_gift_code)

    elif call.data == "adm_smm": # اقتراح
        try:
            res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'balance'}).json()
            bot.send_message(OWNER_ID, f"💰 رصيدك في موقع SMM هو: {res['balance']} {res['currency']}")
        except: bot.send_message(OWNER_ID, "❌ فشل الاتصال بالموقع.")

    # (بقية أوامر الإدارة والحساب والخدمات مع وقت 3 ساعات كما في الرد السابق)

# --- اقتراح: وظيفة معالجة كود الهدية ---
def make_gift_code(message):
    try:
        c, v, l = message.text.split(":")
        gift_settings.update({"code": c, "val": int(v), "limit": int(l), "users": []})
        bot.send_message(OWNER_ID, f"✅ تم تفعيل الكود `{c}` لـ {l} شخص بقيمة {v} نقطة.")
    except: bot.send_message(OWNER_ID, "❌ خطأ في الصيغة.")

def process_gift_use(message):
    uid = message.from_user.id
    code = message.text
    if code == gift_settings["code"] and uid not in gift_settings["users"] and len(gift_settings["users"]) < gift_settings["limit"]:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + %s WHERE user_id=%s", (gift_settings["val"], uid))
        conn.commit(); cursor.close(); conn.close()
        gift_settings["users"].append(uid)
        bot.send_message(uid, f"✅ مبروك! حصلت على {gift_settings['val']} نقطة من كود الهدية.")
    else:
        bot.send_message(uid, "❌ الكود غير صحيح، انتهى، أو استخدمته مسبقاً.")

# (الدوال المساعدة: get_total_users, check_vip_status, etc.)
# الوقت المحدث: 10800 ثانية (3 ساعات) موجود في دالة handle_services

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
