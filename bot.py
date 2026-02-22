import os, time, psycopg2, requests, telebot, urllib.parse
from flask import Flask
from threading import Thread
from telebot import types

# --- إعداد الخادم (Keep-Alive) ---
app = Flask('')
@app.route('/')
def home(): return "البوت يعمل بكفاءة ونظام الإحالة نشط ✅"
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

# الاتصال بـ Postgres
def get_db_connection():
    db_url = DATABASE_URL
    if db_url and "?sslmode" in db_url:
        db_url = db_url.split("?")[0]
    return psycopg2.connect(db_url)

# تهيئة الجداول
conn_init = get_db_connection()
cursor_init = conn_init.cursor()
cursor_init.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id BIGINT PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, vip_expiry REAL DEFAULT 0,
                   is_banned INTEGER DEFAULT 0, referred_by BIGINT DEFAULT 0, points INTEGER DEFAULT 0,
                   username TEXT)''')
cursor_init.execute('''CREATE TABLE IF NOT EXISTS auto_channels 
                  (chat_id BIGINT PRIMARY KEY, posts_count INTEGER DEFAULT 0, last_post_date TEXT)''')
conn_init.commit()
cursor_init.close()
conn_init.close()

# --- الوظائف المساعدة ---
def get_total_users():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    res = cursor.fetchone()[0]
    cursor.close(); conn.close()
    return 13485 + res

def is_subscribed(user_id):
    if not CH_ID or CH_ID == "None": return True
    try:
        status = bot.get_chat_member(CH_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def check_vip_status(uid):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT is_vip, vip_expiry FROM users WHERE user_id=%s", (uid,))
    res = cursor.fetchone()
    if not res: 
        cursor.close(); conn.close()
        return False
    is_vip, expiry = res[0], res[1]
    if is_vip == 1 and (expiry == 0 or time.time() < expiry): 
        cursor.close(); conn.close()
        return True
    cursor.close(); conn.close()
    return False

# --- ميزة الـ Forward لكل رسالة تصل للبوت ---

# --- لوحة التحكم للإدارة الكاملة ---
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.from_user.id != OWNER_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قناة إجبارية", callback_data="adm_addch"),
        types.InlineKeyboardButton("❌ حذف قناة إجبارية", callback_data="adm_delch"),
        types.InlineKeyboardButton("💰 شحن نقاط", callback_data="adm_points"),
        types.InlineKeyboardButton("🔒 حظر", callback_data="adm_ban"),
        types.InlineKeyboardButton("🔓 فك حظر", callback_data="adm_unban"),
        types.InlineKeyboardButton("💎 منح VIP", callback_data="adm_vip"),
        types.InlineKeyboardButton("🗑 حذف VIP", callback_data="adm_delvip"),
        types.InlineKeyboardButton("📢 إذاعة", callback_data="adm_bc"),
        types.InlineKeyboardButton("📊 احصائيات", callback_data="adm_sts"),
        types.InlineKeyboardButton("💵 رصيد الموقع", callback_data="adm_balance")
    )
    bot.send_message(message.chat.id, "🛠 *لوحة تحكم الإدارة الكاملة:*", reply_markup=markup)

# --- إشعار إضافة البوت لقناة/مجموعة ---
@bot.my_chat_member_handler()
def bot_added_to_chat(message):
    if message.new_chat_member.status in ['administrator', 'member']:
        chat = message.chat
        user = message.from_user
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO auto_channels (chat_id) VALUES (%s) ON CONFLICT DO NOTHING", (chat.id,))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM auto_channels"); total_ch = cursor.fetchone()[0]
        cursor.close(); conn.close()
        
        info = (f"🆕 **قام مستخدم جديد بإضافة البوت الخاص بك إلى قناته**\n\n"
                f"📌 **معلومات القناه:**\n"
                f"• اسم المجموعة: {chat.title}\n"
                f"• الآيدي: `{chat.id}`\n"
                f"• اسم المستخدم: @{chat.username or 'لا يوجد'}\n\n"
                f"👤 **معلومات العضو الذي قام بالإضافة:**\n"
                f"• الاسم: {user.first_name}\n"
                f"• اسم الحلو: @{user.username or 'لا يوجد'}\n"
                f"• الآيدي: `{user.id}`\n\n"
                f"📊 إجمالي عدد القنوات حتى الآن: {total_ch}")
        try: bot.send_message(OWNER_ID, info)
        except: pass

# --- نظام المشاهدات التلقائي (1300 مشاهدة) ---
@bot.channel_post_handler(content_types=['text', 'photo', 'video'])
def auto_view_posts(message):
    cid = message.chat.id
    today = time.strftime("%Y-%m-%d")
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT posts_count, last_post_date FROM auto_channels WHERE chat_id=%s", (cid,))
    res = cursor.fetchone()
    if res:
        count, last_date = res[0], res[1]
        if last_date != today: count = 0
        if count < 4:
            post_link = f"https://t.me/{message.chat.username}/{message.message_id}" if message.chat.username else None
            if post_link:
                payload = {'key': SMM_API_KEY, 'action': 'add', 'service': '14527', 'link': post_link, 'quantity': 1300}
                requests.post(API_URL, data=payload)
                cursor.execute("UPDATE auto_channels SET posts_count=%s, last_post_date=%s WHERE chat_id=%s", (count+1, today, cid))
                conn.commit()
    cursor.close(); conn.close()

# --- أمر /start (تفاعل 🔥 + إحالات 9) ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()
    
    # ميزة التفاعل بـ 🔥 على رسالة المستخدم
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except: pass

    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id=%s', (uid,))
    row = cursor.fetchone()
    if row and row[0] == 1: 
        cursor.close(); conn.close()
        return

    if row is None:
        referrer = 0
        if len(args) > 1 and args[1].isdigit():
            referrer = int(args[1])
            if referrer != uid:
                cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=%s', (referrer,))
                conn.commit()
                cursor.execute('SELECT points, is_vip FROM users WHERE user_id=%s', (referrer,))
                ref_data = cursor.fetchone()
                if ref_data and ref_data[0] >= 9 and ref_data[1] == 0:
                    cursor.execute('UPDATE users SET is_vip=1, vip_expiry=%s, points=0 WHERE user_id=%s', (time.time() + 86400, referrer))
                    conn.commit()
                    try: bot.send_message(referrer, "🎊 *مبروك!* جمعت 9 إحالات وتم تفعيل الـ VIP!")
                    except: pass
        
        cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', (uid, referrer, message.from_user.username))
        conn.commit()
        
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
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_13894"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="show_react_menu"),
        types.InlineKeyboardButton("👁️ مشاهدات تلقائية", callback_data="auto_views_info"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        types.InlineKeyboardButton("💎 اشتراك VIP", callback_data="vip_menu")
    )
    bot.send_message(message.chat.id, "*أهلاً بك في بوت الخدمات المجانية* 🆓\n*𝚍𝚎𝚟:* @E2E12", reply_markup=markup)

# --- معالجة الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    is_vip = check_vip_status(uid)

    if call.data == "auto_views_info":
        info_text = ("👁️ **خدمة المشاهدات التلقائية:**\n\n"
                    "البوت يرشق 1300 مشاهدة لكل منشور جديد تلقائياً.\n"
                    "فقط أضف البوت مشرفاً في قناتك.")
        return bot.send_message(call.message.chat.id, info_text)

    # أوامر الإدارة الكاملة
    if call.data.startswith("adm_") and uid == OWNER_ID:
        action = call.data.split("_")[1]
        if action == "sts":
            bot.answer_callback_query(call.id, f"📊 عدد المستخدمين: {get_total_users()}", show_alert=True)
        elif action == "bc":
            msg = bot.send_message(call.message.chat.id, "📢 ارسل نص الإذاعة:")
            bot.register_next_step_handler(msg, broadcast_step)
        elif action == "balance":
            try:
                res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'balance'}).json()
                bot.send_message(call.message.chat.id, f"💰 رصيدك الحالي: {res['balance']} {res['currency']}")
            except: pass
        return

    # التفاعلات الاختيارية (الكمية 20)
    if call.data == "show_react_menu":
        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = [
            types.InlineKeyboardButton("🍓", callback_data="ser_react_13953"),
            types.InlineKeyboardButton("🐳", callback_data="ser_react_13949"),
            types.InlineKeyboardButton("❤️‍🔥", callback_data="ser_react_13947"),
            types.InlineKeyboardButton("😍", callback_data="ser_react_13933"),
            types.InlineKeyboardButton("😂", callback_data="ser_react_13932"),
            types.InlineKeyboardButton("🔥", callback_data="ser_react_13931"),
            types.InlineKeyboardButton("❤️", callback_data="ser_react_13930"),
            types.InlineKeyboardButton("👍", callback_data="ser_react_13929"),
            types.InlineKeyboardButton("👎", callback_data="ser_react_13926"),
            types.InlineKeyboardButton("✅", callback_data="ser_react_13925"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start")
        ]
        markup.add(*btns)
        bot.edit_message_text("*اختر نوع التفاعل* ):", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "my_account":
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id=%s", (uid,))
        points = cursor.fetchone()[0]
        cursor.close(); conn.close()
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={uid}"
        share_text = (f"🚀 أقوى بوت لزيادة متابعين وتفاعلات تليجرام مجاناً!\n"
                      f"✅ زيادة مشتركين، مشاهدات، وتفاعلات حقيقية.\n"
                      f"🎁 ادخل من الرابط واحصل على هديتك الآن!\n\n{referral_link}")
        encoded_text = urllib.parse.quote(share_text)
        share_url = f"https://t.me/share/url?url={encoded_text}"
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 رابط الدعوة الخاص بك", url=share_url))
        status = "💎 VIP" if is_vip else "👤 عادي"
        bot.send_message(call.message.chat.id, f"👤 *الايدي:* `{uid}`\n💰 *نقاطك:* {points}\n⭐ *حالتك:* {status}", reply_markup=markup)
    
    elif call.data == "vip_menu":
        markup = types.InlineKeyboardMarkup(row_width=1).add(
            types.InlineKeyboardButton("🌟 اشتراك بـ 20 نجمة (يومي)", callback_data="buy_vip_stars"),
            types.InlineKeyboardButton("💰 اشتراك بـ 9 نقاط (يومي)", callback_data="buy_vip_points"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start")
        )
        msg_text = ("الاشتراك يومي بـ 20 نجمه 🌟 أو 9 إحالة.\nراسلني: @e2e12")
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("ser_"):
        parts = call.data.split("_")
        service_type, s_id = parts[1], parts[2]
        col = f"last_{service_type}"
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute(f"SELECT {col} FROM users WHERE user_id=%s", (uid,))
        last_time = cursor.fetchone()[0]
        cursor.close(); conn.close()

        if not is_vip and (time.time() - last_time) < 5400: # 1.5 ساعة
            rem = int(5400 - (time.time() - last_time))
            return bot.answer_callback_query(call.id, f"⏳ متبقي {rem//3600} ساعة و {(rem%3600)//60} دقيقة", show_alert=True)
        
        msg = bot.send_message(call.message.chat.id, "🔗 *ارسل الرابط الآن:*")
        bot.register_next_step_handler(msg, process_order, s_id, col, service_type)

    elif call.data == "back_start":
        start(call.message)

# --- معالجة الطلبات بالكميات المحددة ---
def process_order(message, s_id, col, s_type):
    if not message.text or not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ الرابط غير صحيح.")
    
    qty = 1300 if s_type == "view" else 20
    payload = {'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': qty}
    try:
        res = requests.post(API_URL, data=payload).json()
        if "order" in res:
            conn = get_db_connection(); cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {col}=%s WHERE user_id=%s", (time.time(), message.from_user.id))
            conn.commit(); cursor.close(); conn.close()
            bot.send_message(message.chat.id, f"✅ تم طلب {qty} بنجاح!\nرقم الطلب: `{res['order']}`")
        else: bot.send_message(message.chat.id, "❌ فشل من المصدر.")
    except: pass

# --- دوال الإدارة ---
def broadcast_step(message):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users"); users = cursor.fetchall()
    cursor.close(); conn.close()
    for (u_id,) in users:
        try: bot.send_message(u_id, message.text)
        except: continue
    bot.send_message(OWNER_ID, "✅ تمت الإذاعة.")

if __name__ == "__main__":
   @bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker'])
def forward_to_owner(message):
    try: bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
    except: pass
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
