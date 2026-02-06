import os, time, sqlite3, requests, telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم لإبقاء البوت حياً ---
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
OWNER_ID = 5581457665 

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
db_path = 'users.db'
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجدول
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)''')
conn.commit()

# --- الوظائف المساعدة ---
def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return 13485 + cursor.fetchone()[0]

def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

# --- لوحة التحكم ---
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
    bot.send_message(message.chat.id, "🛠 *لوحة تحكم الإدارة:*", reply_markup=markup)

# --- أوامر المستخدم ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (uid,))
    row = cursor.fetchone()
    
    if row and row[0] == 1:
        return bot.send_message(message.chat.id, "❌ *أنت محظور من استخدام البوت.*")

    if row is None:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (uid,))
        conn.commit()
        # إشعار المالك بالتنسيق المطلوب
        owner_msg = (
            f"<< دخول نفـرر جديد لبوتك >>\n"
            f"• الاسم😂: {message.from_user.first_name}\n"
            f"• المعرف💁: @{message.from_user.username or 'لا يوجد'}\n"
            f"• الايدي🆔: `{uid}`\n"
            f"• عدد مشتركينك الابطال: {get_total_users()}"
        )
        try: bot.send_message(OWNER_ID, owner_msg)
        except: pass

    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("اشترك هنا 📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ *يجب الاشتراك بالقناة أولاً!*", reply_markup=markup)

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓\n*𝚍𝚎𝚟:* @E2E12", reply_markup=markup)

# --- معالجة الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    
    # أزرار الإدارة
    if call.data.startswith("adm_") and uid == OWNER_ID:
        if call.data == "adm_sts":
            bot.answer_callback_query(call.id, f"📊 المشتركين: {get_total_users()}", show_alert=True)
        elif call.data == "adm_bc":
            msg = bot.send_message(call.message.chat.id, "📢 ارسل نص الإذاعة:")
            bot.register_next_step_handler(msg, broadcast_step)
        elif call.data in ["adm_ban", "adm_unban", "adm_vip"]:
            action = call.data.split("_")[1]
            msg = bot.send_message(call.message.chat.id, "👤 ارسل ايدي المستخدم:")
            bot.register_next_step_handler(msg, update_user, action)
        return

    # أزرار المستخدم
    if call.data == "my_account":
        cursor.execute("SELECT is_vip FROM users WHERE user_id=?", (uid,))
        is_vip = cursor.fetchone()[0]
        status = "💎 VIP" if is_vip else "👤 حساب عادي"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("شارك البوت 🔗", url="https://t.me/share/url?url=@t3tbbot"),
            types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip")
        )
        bot.send_message(call.message.chat.id, 
                         f"👤 *الايدي:* `{uid}`\n"
                         f"👥 *عدد المشتركين:* {get_total_users()}\n"
                         f"⭐ *حالتك:* {status}", reply_markup=markup)
    
    elif call.data == "buy_vip":
        text = ("اهلا صديقي اشتراك vip يمنحك فرصة التخلص من الوقت والانتظار وكمية كبيرة في الطلبات وأعداد المتابعين\n\n"
                "الاشتراك سيكون يومي بـ 50 نجمه 🌟\n"
                "راسلني اذا حاب تكتشف مميزات احلى @e2e12")
        bot.send_message(call.message.chat.id, text)

    elif call.data.startswith("ser_"):
        # (منطق طلبات الـ API كما هو في الكود السابق)
        pass
    bot.answer_callback_query(call.id)

# --- دوال الإدارة المتقدمة ---
def update_user(message, action):
    try:
        target_id = int(message.text)
        if action == "ban":
            cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target_id,))
            bot.send_message(target_id, "🚫 *عذراً، لقد تمت إضافتك إلى قائمة المحظورين.*")
        elif action == "unban":
            cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target_id,))
            bot.send_message(target_id, "✅ *تهانينا، تم رفع الحظر عنك يمكنك استخدام البوت الآن.*")
        elif action == "vip":
            cursor.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (target_id,))
            bot.send_message(target_id, "💎 *مبروك! تم منحك صلاحيات VIP بنجاح.*")
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم تنفيذ {action} للايدي {target_id}")
    except: bot.send_message(message.chat.id, "❌ خطأ في الايدي.")

def broadcast_step(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for (u_id,) in users:
        try: bot.send_message(u_id, message.text)
        except: continue
    bot.send_message(message.chat.id, "✅ تمت الإذاعة.")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
