import os, time, sqlite3, requests, telebot, urllib.parse
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running..."
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
def keep_alive(): Thread(target=run, daemon=True).start()

# --- الإعدادات ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
API_URL = os.getenv('API_URL')
OWNER_ID = 5581457665 

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# اتصال قاعدة البيانات مع التأكد من الحفظ المستمر
def get_db_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, vip_expiry REAL DEFAULT 0,
                   is_banned INTEGER DEFAULT 0, referred_by INTEGER DEFAULT 0, points INTEGER DEFAULT 0)''')
conn.commit()

# --- الوظائف ---
def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def check_vip(uid):
    cursor.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    if res and res['is_vip'] == 1:
        if res['vip_expiry'] == 0 or time.time() < res['vip_expiry']: return True
        else:
            cursor.execute("UPDATE users SET is_vip=0, vip_expiry=0 WHERE user_id=?", (uid,))
            conn.commit()
    return False

# --- التعامل مع الرسائل ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    
    # ✅ حل مشكلة التفاعل: كتابة الكود بطريقة تضمن التنفيذ
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except Exception as e:
        print(f"Reaction error: {e}")

    cursor.execute('SELECT is_banned FROM users WHERE user_id=?', (uid,))
    user = cursor.fetchone()
    
    if user and user['is_banned'] == 1: return

    if user is None:
        # نظام الإحالة
        args = message.text.split()
        referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
        
        cursor.execute('INSERT OR IGNORE INTO users (user_id, referred_by) VALUES (?, ?)', (uid, referrer))
        conn.commit()
        
        if referrer != 0 and referrer != uid:
            cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=?', (referrer,))
            conn.commit()
            # فحص الـ 13 نقطة
            cursor.execute('SELECT points FROM users WHERE user_id=?', (referrer,))
            p = cursor.fetchone()['points']
            if p >= 13:
                cursor.execute('UPDATE users SET is_vip=1, vip_expiry=?, points=0 WHERE user_id=?', (time.time() + 86400, referrer))
                conn.commit()
                try: bot.send_message(referrer, "🎊 مبروك! وصلت لـ 13 نقطة وتم تفعيل VIP لـ 24 ساعة!")
                except: pass

        # إشعار المالك
                # --- كود إشعار المالك عند دخول مستخدم جديد ---
        cursor.execute('SELECT COUNT(*) FROM users')
        total_count = 14274 + cursor.fetchone()[0]
        
        owner_msg = (f"👤 **دخول مستخدم جديد لبوتك**\n\n"
                     f"• **الاسم:** {message.from_user.first_name}\n"
                     f"• **المعرف:** @{message.from_user.username or 'لا يوجد'}\n"
                     f"• **الايدي:** `{uid}`\n"
                     f"• **الإجمالي:** {total_count} مشترك 🚀")
        
        try:
            bot.send_message(OWNER_ID, owner_msg)
        except:
            pass

    if not is_subscribed(uid):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(" مَـدار📢", url=f"https://t.me/{CH_ID.replace('@','')}"))
        return bot.send_message(message.chat.id, "⚠️ اشترك بالقناة أولاً!", reply_markup=markup)

    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="ser_react_13925"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account")
    )
    bot.send_message(message.chat.id, "أهلاً بك في بوت الخدمات المجانية 🆓", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    is_vip = check_vip(uid)

    if call.data == "my_account":
        cursor.execute("SELECT points FROM users WHERE user_id=?", (uid,))
        pts = cursor.fetchone()['points']
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        txt = urllib.parse.quote(f"🚀 أقوى بوت زيادة متابعين مجاناً!\n🎁 ادخل وجرب بنفسك:\n{link}")
        
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔗 رابط دعوتك", url=f"https://t.me/share/url?url={link}&text={txt}"),
            types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip")
        )
        bot.send_message(call.message.chat.id, f"👤 ايديك: `{uid}`\n💰 نقاطك: {pts}\n⭐ حالتك: {'VIP' if is_vip else 'عادي'}", reply_markup=markup)

    elif call.data.startswith("ser_"):
        col = f"last_{call.data.split('_')[1]}"
        cursor.execute(f"SELECT {col} FROM users WHERE user_id=?", (uid,))
        last = cursor.fetchone()[0]
        
        if not is_vip and (time.time() - last) < 43200:
            rem = int(43200 - (time.time() - last))
            return bot.answer_callback_query(call.id, f"⏳ متبقي {rem//3600} ساعة", show_alert=True)
            
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔗 ارسل الرابط:")
        bot.register_next_step_handler(msg, send_order, call.data.split('_')[2], col)

def send_order(message, s_id, col):
    if not message.text.startswith("http"): return bot.send_message(message.chat.id, "❌ رابط خطأ.")
    res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': 100}).json()
    if "order" in res:
        cursor.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (time.time(), message.from_user.id))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ تم الطلب: `{res['order']}`")
    else: bot.send_message(message.chat.id, f"❌ خطأ: {res.get('error')}")

# --- الإدارة ---
@bot.message_handler(commands=["admin"])
def admin(message):
    if message.from_user.id == OWNER_ID:
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📊 إحصائيات", callback_data="adm_sts"))
        bot.send_message(message.chat.id, "لوحة الإدارة", reply_markup=markup)

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling(timeout=20)
