import os, time, sqlite3, requests, telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- خادم إبقاء البوت حياً ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بكفاءة ✅"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
def keep_alive():
    t = Thread(target=run); t.daemon = True; t.start()

# --- الإعدادات من Render ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
API_URL = os.getenv('API_URL')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- إدارة قاعدة البيانات ---
db_path = 'users.db'
def get_db():
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn, conn.cursor()

# إنشاء الجداول والقيم الافتراضية عند التشغيل
conn, cursor = get_db()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0, is_vip INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, force_channel TEXT, quantity INTEGER DEFAULT 100, welcome_msg TEXT)')
cursor.execute('SELECT COUNT(*) FROM settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('INSERT INTO settings (id, force_channel, quantity, welcome_msg) VALUES (1, "None", 100, "✨ أهلاً بك في البوت!")')
conn.commit()

# --- الدوال المساعدة ---
def get_settings():
    _, c = get_db()
    c.execute('SELECT force_channel, quantity, welcome_msg FROM settings WHERE id=1')
    return c.fetchone()

# --- لوحة التحكم (Admin Panel) ---
def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 إذاعة", callback_data="adm_bc"),
        types.InlineKeyboardButton("🚫 حظر/فك", callback_data="adm_ban"),
        types.InlineKeyboardButton("💎 إدارة VIP", callback_data="adm_vip"),
        types.InlineKeyboardButton("🔢 كمية الطلب", callback_data="adm_qty"),
        types.InlineKeyboardButton("📢 قناة الاشتراك", callback_data="adm_chn"),
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_sts")
    )
    return markup

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🛠 * لوحة تحكم المطور والسلطان الوالي:*", reply_markup=admin_keyboard())

# --- أوامر المستخدم ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    conn, c = get_db()
    c.execute('SELECT is_banned FROM users WHERE user_id=?', (uid,))
    res = c.fetchone()
    if res and res[0] == 1: return bot.send_message(message.chat.id, "😂❌ أنت محظور.")
    if res is None:
        c.execute('INSERT INTO users (user_id) VALUES (?)', (uid,))
        conn.commit()
    
    sets = get_settings()
    # فحص الاشتراك
    if sets[0] != "None":
        try:
            status = bot.get_chat_member(sets[0], uid).status
            if status not in ['member', 'administrator', 'creator']:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("مَـدار 🪐", url=f"https://t.me/{sets[0].replace('@','')}"))
                return bot.send_message(message.chat.id, "⚠️ يجب الاشتراك أولاً!", reply_markup=markup)
        except: pass

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_acc")
    )
    bot.send_message(message.chat.id, sets[2], reply_markup=markup)

# --- معالجة الضغطات ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_calls(call):
    uid = call.from_user.id
    conn, c = get_db()

    if call.data.startswith("adm_") and uid == ADMIN_ID:
        if call.data == "adm_sts":
            c.execute('SELECT COUNT(*) FROM users'); count = c.fetchone()[0]
            bot.answer_callback_query(call.id, f"المستخدمين: {count}", show_alert=True)
        elif call.data == "adm_bc":
            msg = bot.send_message(call.message.chat.id, "ارسل نص الإذاعة:")
            bot.register_next_step_handler(msg, broadcast_step)
        elif call.data == "adm_qty":
            msg = bot.send_message(call.message.chat.id, "ارسل الكمية الجديدة:")
            bot.register_next_step_handler(msg, qty_step)
        elif call.data == "adm_chn":
            msg = bot.send_message(call.message.chat.id, "ارسل معرف القناة (مثلاً @e2e12) أو None:")
            bot.register_next_step_handler(msg, chn_step)

    elif call.data == "my_acc":
        c.execute('SELECT is_vip FROM users WHERE user_id=?', (uid,))
        v = "💎 VIP" if c.fetchone()[0] == 1 else "👤 عادي"
        bot.send_message(call.message.chat.id, f"👤 ايدي: `{uid}`\nحالتك: {v}")

    elif call.data.startswith("ser_"):
        stype, sid = call.data.split("_")[1], call.data.split("_")[2]
        col = f"last_{stype}"
        c.execute(f'SELECT {col}, is_vip FROM users WHERE user_id=?', (uid,))
        lt, vip = c.fetchone()
        if vip == 0 and (time.time() - lt) < 43200:
            return bot.answer_callback_query(call.id, "⏳ متبقي وقت للانتظار!", show_alert=True)
        msg = bot.send_message(call.message.chat.id, "🔗 ارسل الرابط:")
        bot.register_next_step_handler(msg, order_step, sid, col, vip)

# --- دوال الخطوات (Next Step Handlers) ---
def broadcast_step(m):
    conn, c = get_db()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    for u in users:
        try: bot.send_message(u[0], m.text)
        except: continue
    bot.send_message(m.chat.id, "😂✅ تمت الإذاعة.")

def qty_step(m):
    if m.text.isdigit():
        conn, c = get_db(); c.execute('UPDATE settings SET quantity=? WHERE id=1', (int(m.text),)); conn.commit()
        bot.send_message(m.chat.id, "✅ تم التحديث.")

def chn_step(m):
    conn, c = get_db(); c.execute('UPDATE settings SET force_channel=? WHERE id=1', (m.text,)); conn.commit()
    bot.send_message(m.chat.id, "✅ تم تحديث القناة.")

def order_step(m, sid, col, vip):
    if not m.text.startswith("http"): return bot.send_message(m.chat.id, "❌ رابط خطأ.")
    sets = get_settings()
    try:
        res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': sid, 'link': m.text, 'quantity': sets[1]}).json()
        if "order" in res:
            if vip == 0:
                conn, c = get_db(); c.execute(f'UPDATE users SET {col}=? WHERE user_id=?', (time.time(), m.from_user.id)); conn.commit()
            bot.send_message(m.chat.id, f"✅ تم الطلب! رقم: {res['order']}")
        else: bot.send_message(m.chat.id, f"❌ رد الموقع: {res.get('error')}")
    except: bot.send_message(m.chat.id, "⚙️ فشل.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
