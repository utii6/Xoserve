import os, time, sqlite3, requests, telebot
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بنظام الإحالة المؤقت ✅"
def run(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
def keep_alive(): Thread(target=run, daemon=True).start()

# --- الإعدادات ---
API_TOKEN = os.getenv('BOT_TOKEN')
SMM_API_KEY = os.getenv('SMM_API_KEY')
CH_ID = os.getenv('CHANNEL_USERNAME')
API_URL = os.getenv('API_URL')
OWNER_ID = 5581457665 

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

# تحديث الجدول لدعم النقاط ووقت انتهاء الـ VIP
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, vip_expiry REAL DEFAULT 0,
                   is_banned INTEGER DEFAULT 0, referred_by INTEGER DEFAULT 0, points INTEGER DEFAULT 0)''')
conn.commit()

def get_total_users():
    cursor.execute('SELECT COUNT(*) FROM users')
    return 13485 + cursor.fetchone()[0]

def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def check_vip_status(uid):
    """فحص هل المستخدم VIP حالياً (دائم أو مؤقت لم ينتهِ)"""
    cursor.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    if not res: return False
    is_vip, expiry = res[0], res[1]
    
    # إذا كان VIP دائم
    if is_vip == 1 and expiry == 0: return True
    # إذا كان VIP مؤقت ولم ينتهِ الوقت بعد
    if is_vip == 1 and time.time() < expiry: return True
    # إذا انتهى الوقت، نقوم بإلغاء الـ VIP في القاعدة
    if is_vip == 1 and expiry > 0 and time.time() > expiry:
        cursor.execute("UPDATE users SET is_vip=0, vip_expiry=0 WHERE user_id=?", (uid,))
        conn.commit()
        return False
    return False

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    # تفاعل 🔥
    try: bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")])
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
                
                # فحص الوصول لـ 13 نقطة
                cursor.execute('SELECT points, is_vip FROM users WHERE user_id=?', (referrer,))
                ref_data = cursor.fetchone()
                if ref_data and ref_data[0] >= 13 and ref_data[1] == 0:
                    expiry_time = time.time() + 86400 # 24 ساعة
                    cursor.execute('UPDATE users SET is_vip=1, vip_expiry=?, points=0 WHERE user_id=?', (expiry_time, referrer))
                    conn.commit()
                    try: bot.send_message(referrer, "🎊 *مبروك!* جمعت 13 نقطة وتم تفعيل الـ VIP لك لمدة 24 ساعة مجاناً! استمتع بالخدمات الآن بدون انتظار. ⭐")
                    except: pass
                else:
                    try: bot.send_message(referrer, f"🎁 *شخص جديد دخل من رابطك!*\n💰 رصيدك: {ref_data[0]} نقطة.\n🎯 اجمع {13 - ref_data[0]} نقطة إضافية للحصول على VIP يوم كامل.")
                    except: pass

        cursor.execute('INSERT INTO users (user_id, referred_by) VALUES (?, ?)', (uid, referrer))
        conn.commit()
        
        owner_msg = f"<< دخول نفـرر جديد لبوتك >>\n• الاسم😂: {message.from_user.first_name}\n• المعرف💁: @{message.from_user.username or 'لا يوجد'}\n• الايدي🆔: `{uid}`\n• عدد مشتركينك الابطال: {get_total_users()}"
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
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    is_vip = check_vip_status(uid)

    if call.data == "my_account":
        cursor.execute("SELECT points, vip_expiry FROM users WHERE user_id=?", (uid,))
        res = cursor.fetchone()
        points, expiry = res[0], res[1]
        
        status_text = "💎 VIP (مؤقت)" if (is_vip and expiry > 0) else ("💎 VIP (دائم)" if is_vip else "👤 عادي")
        if is_vip and expiry > 0:
            rem = int(expiry - time.time())
            status_text += f"\n⏳ ينتهي بعد: {rem//3600} ساعة"

        ref_link = f"https://t.me/{bot.get_me().username}?start={uid}"
        markup = types.InlineKeyboardMarkup(row_width=1).add(
            types.InlineKeyboardButton("🔗 رابط الدعوة الخاص بك", url=f"https://t.me/share/url?url={ref_link}&text=افضل بوت خدمات مجاني!"),
            types.InlineKeyboardButton("اشترك VIP ⭐", callback_data="buy_vip")
        )
        bot.send_message(call.message.chat.id, f"👤 *الايدي:* `{uid}`\n👥 *المستخدمين:* {get_total_users()}\n💰 *نقاطك:* {points}\n⭐ *حالتك:* {status_text}", reply_markup=markup)
    
    elif call.data == "buy_vip":
        bot.send_message(call.message.chat.id, "اهلا صديقي اشتراك vip يمنحك فرصة التخلص من الوقت والانتظار\n\n*الاشتراك اليومي بـ 50 نجمه 🌟 أو *تجميع 13 إحالة لليوم الواحد.\nراسلني @e2e12")

    elif call.data.startswith("ser_"):
        # فحص وقت الانتظار (إلا إذا كان VIP)
        service_type = call.data.split("_")[1]
        column = f"last_{service_type}"
        cursor.execute(f"SELECT {column} FROM users WHERE user_id=?", (uid,))
        last_time = cursor.fetchone()[0]

        if not is_vip and (time.time() - last_time) < 43200:
            rem = int(43200 - (time.time() - last_time))
            return bot.answer_callback_query(call.id, f"⏳ متبقي {rem//3600} ساعة و {(rem%3600)//60} دقيقة", show_alert=True)
        
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔗 *ارسل الرابط الآن:*")
        bot.register_next_step_handler(msg, process_order, call.data.split("_")[2], column)

def process_order(message, s_id, col):
    if not message.text.startswith("http"): return bot.send_message(message.chat.id, "❌ رابط خطأ.")
    payload = {'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': 100}
    try:
        res = requests.post(API_URL, data=payload).json()
        if "order" in res:
            cursor.execute(f"UPDATE users SET {col}=? WHERE user_id=?", (time.time(), message.from_user.id))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ تم الطلب! رقم: `{res['order']}`")
        else: bot.send_message(message.chat.id, f"❌ خطأ الموقع: {res.get('error')}")
    except: bot.send_message(message.chat.id, "⚙️ فشل الاتصال.")

if __name__ == "__main__":
    keep_alive()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20)
