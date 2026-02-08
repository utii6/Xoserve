import os, time, sqlite3, requests, telebot, urllib.parse
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم (Keep-Alive) ---
app = Flask('')

@app.route('/')
def home(): 
    return "البوت يعمل بكفاءة ونظام الإحالة نشط ✅"

def run():
    # Render يتطلب جلب المنفذ من متغيرات البيئة
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive(): 
    Thread(target=run, daemon=True).start()

# --- الإعدادات (مطابقة لمتغيرات Render في صورتك) ---
API_TOKEN = os.getenv('BOT_TOKEN') # تأكد أن الاسم في Render هو BOT_TOKEN
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
API_URL = os.getenv('API_URL')
OWNER_ID = 5581457665 

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# الاتصال بقاعدة البيانات (SQLite)
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# تحديث هيكل قاعدة البيانات
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, vip_expiry REAL DEFAULT 0,
                   is_banned INTEGER DEFAULT 0, referred_by INTEGER DEFAULT 0, points INTEGER DEFAULT 0)''')
conn.commit()

# --- الوظائف المساعدة ---
def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return 13485 + cursor.fetchone()[0]

def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None" or CH_ID == "": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: 
        return True # لتجنب التوقف في حال وجود خطأ في الصلاحيات

def check_vip_status(uid):
    cursor.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    if not res: return False
    is_vip, expiry = res[0], res[1]
    if is_vip == 1 and (expiry == 0 or time.time() < expiry): return True
    if is_vip == 1 and expiry > 0 and time.time() > expiry:
        cursor.execute("UPDATE users SET is_vip=0, vip_expiry=0 WHERE user_id=?", (uid,))
        conn.commit()
    return False

# --- لوحة التحكم للإدارة ---
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != OWNER_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔒 حظر", callback_data="adm_ban"),
        types.InlineKeyboardButton("🔓 فك حظر", callback_data="adm_unban"),
        types.InlineKeyboardButton("💎 منح VIP", callback_data="adm_vip"),
        types.InlineKeyboardButton("📢 إذاعة", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 احصائيات", callback_data="adm_sts")
    )
    bot.send_message(message.chat.id, "🛠 *لوحة تحكم السلطان:*", reply_markup=markup)

# --- أمر التشغيل الرئيسي ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    # التفاعل التلقائي 🔥 (يعمل مع مكتبة الإصدار 4.20.0+)
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")])
    except: pass

    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (uid,))
    row = cursor.fetchone()
    if row and row[0] == 1: return

    if row is None:
        referrer = 0
        if len(args) > 1 and args[1].isdigit():
            referrer = int(args[1])
            if referrer != uid:
                cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=?', (referrer,))
                conn.commit()
                cursor.execute('SELECT points, is_vip FROM users WHERE user_id=?', (referrer,))
                ref_data = cursor.fetchone()
                if ref_data and ref_data[0] >= 13 and ref_data[1] == 0:
                    cursor.execute('UPDATE users SET is_vip=1, vip_expiry=?, points=0 WHERE user_id=?', (time.time() + 86400, referrer))
                    conn.commit()
                    try: bot.send_message(referrer, "🎊 *مبروك!* جمعت 13 نقطة وتم تفعيل الـ VIP لك لمدة 24 ساعة مجاناً!")
                    except: pass
                else:
                    try: bot.send_message(referrer, f"🎁 *شخص جديد دخل من رابطك!*\n💰 رصيدك: {ref_data[0]} نقطة.")
                    except: pass

        cursor.execute('INSERT INTO users (user_id, referred_by) VALUES (?, ?)', (uid, referrer))
        conn.commit()
        owner_msg = (f"<< دخول نفـرر جديد لبوتك >>\n"
                     f"• الاسم😂: {message.from_user.first_name}\n"
                     f"• المعرف💁: @{message.from_user.username or 'لا يوجد'}\n"
                     f"• الايدي🆔: `{uid}`\n"
                     f"• عدد مشتركينك الابطال: {get_total_users()}")
        try: bot.send_message(OWNER_ID, owner_msg)
        except: pass

    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اشترك هنا 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ *يجب الاشتراك بالقناة!*", reply_markup=markup)

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓\n*𝚍𝚎𝚟:* @E2E12", reply_markup=markup)

# --- معالجة الأزرار (Callback) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    is_vip = check_vip_status(uid)

    if call.data.startswith("adm_") and uid == OWNER_ID:
        if call.data == "adm_sts":
            bot.answer_callback_query(call.id, f"📊 المشتركين: {get_total_users()}", show_alert=True)
        elif call.data == "adm_bc":
            msg = bot.send_message(call.message.chat.id, "📢 ارسل نص الإذاعة:")
            bot.register_next_step_handler(msg, broadcast_step)
        elif call.data in ["adm_ban", "adm_unban", "adm_vip"]:
            action = call.data.split("_")[1]
            msg = bot.send_message(call.message.chat.id, "👤 ارسل ايدي المستخدم:")
            bot.register_next_step_handler(msg, update_user_status_admin, action)
        return

        if call.data == "my_account":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        points = cursor.fetchone()[0]
        bot_username = bot.get_me().username
        
        # النص الجديد مع المسافات والأسطر
        referral_link = f"https://t.me/{bot_username}?start={uid}"
        share_text = (
            f"{referral_link}\n"
            "🚀 أقوى بوت لزيادة متابعين وتفاعلات تليجرام مجاناً!\n\n"
            "✅ زيادة مشتركين، مشاهدات، وتفاعلات حقيقية.\n"
            "🎁 ادخل من الرابط واحصل على هديتك الآن!"
        )
        
        # ترميز النص ليعمل كرابط مشاركة
        encoded_text = urllib.parse.quote(share_text)
        share_url = f"https://t.me/share/url?url={encoded_text}"
        
        markup = types.InlineKeyboardMarkup(row_width=1).add(
            types.InlineKeyboardButton("🔗 مشاركة رابط الدعوة", url=share_url),
            types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip")
        )
        
        status = "💎 VIP" if is_vip else "👤 عادي"
        bot.send_message(call.message.chat.id, 
                         f"👤 *الايدي:* `{uid}`\n"
                         f"💰 *نقاطك:* {points}\n"
                         f"⭐ *حالتك:* {status}", reply_markup=markup)

    elif call.data == "buy_vip":
        bot.send_message(call.message.chat.id, "الاشتراك يومي بـ 50 نجمه 🌟 أو تجميع 13 إحالة.\nراسل المطور: @e2e12")

    elif call.data.startswith("ser_"):
        service_type, s_id = call.data.split("_")[1], call.data.split("_")[2]
        col = f"last_{service_type}"
        cursor.execute(f"SELECT {col} FROM users WHERE user_id=?", (uid,))
        last_time = cursor.fetchone()[0]

        if not is_vip and (time.time() - last_time) < 43200:
            rem = int(43200 - (time.time() - last_time))
            return bot.answer_callback_query(call.id, f"⏳ متبقي {rem//3600} ساعة", show_alert=True)
        
        msg = bot.send_message(call.message.chat.id, "🔗 *ارسل الرابط الآن:*")
        bot.register_next_step_handler(msg, process_order, s_id, col)

# --- دوال المعالجة المتقدمة ---
def update_user_status_admin(message, action):
    try:
        tid = int(message.text)
        if action == "ban": cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (tid,))
        elif action == "unban": cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (tid,))
        elif action == "vip": cursor.execute("UPDATE users SET is_vip=1, vip_expiry=0 WHERE user_id=?", (tid,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ تم التنفيذ.")
    except: bot.send_message(message.chat.id, "❌ خطأ.")

def broadcast_step(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for (u_id,) in users:
        try: bot.send_message(u_id, message.text)
        except: continue
    bot.send_message(message.chat.id, "✅ تمت الإذاعة.")

def process_order(message, s_id, col):
    if not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ رابط خاطئ.")
    
    payload = {'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': 100}
    try:
        res = requests.post(API_URL, data=payload).json()
        if "order" in res:
            cursor.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (time.time(), message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ *تم الطلب!* رقم: `{res['order']}`")
        else: bot.send_message(message.chat.id, f"❌ خطأ: {res.get('error')}")
    except: bot.send_message(message.chat.id, "⚙️ فشل الاتصال بالمزود.")

# --- التشغيل النهائي ---
if __name__ == "__main__":
    keep_alive() # لتشغيل خادم Flask في الخلفية
    bot.remove_webhook()
    print("🚀 البوت يعمل الآن بنظام Polling...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
