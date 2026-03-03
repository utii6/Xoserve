import os, time, psycopg2, requests, telebot, urllib.parse, security
from flask import Flask
from threading import Thread
from telebot import types

# --- كود إرضاء Render (يجب أن يبدأ فوراً) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is Alive", 200

def run_flask():
    # هذا الجزء يفتح المنفذ الذي يبحث عنه Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# تشغيل السيرفر في خلفية منفصلة قبل أي شيء آخر
Thread(target=run_flask).start()
# ------------------------------------------

# بعد ذلك يكمل كود البوت الخاص بك...
# API_TOKEN = '...'


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
CH_ID_2 = "@IE2017"
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
    bot.send_message(message.chat.id, "🛠 *لوحة تحكم الوالي والسلطان:*", reply_markup=markup)

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
def is_subscribed(uid):
    try:
        # فحص القناتين (تأكد من وجود CH_ID و المعرف الثاني)
        status1 = bot.get_chat_member(CH_ID, uid).status
        status2 = bot.get_chat_member("@IE2017", uid).status
        
        ok = ['member', 'administrator', 'creator']
        return status1 in ok and status2 in ok
    except:
        return False

@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.from_user.id
    args = message.text.split() # تعريف الأرجومنت لنظام الإحالة
    
    # 1. فحص الاشتراك الإجباري
    if not is_subscribed(uid):
        markup_sub = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("📢 قناة مَـدار", url=f"https://t.me/{CH_ID.replace('@','')}")
        btn2 = types.InlineKeyboardButton("📢 قناة التحديثات", url="https://t.me/IE2017")
        markup_sub.add(btn1, btn2)
        bot.send_message(message.chat.id, "⚠️ **يجب الاشتراك في القناه أولاً:**", reply_markup=markup_sub, parse_mode="Markdown")
        return 

    # 2. التفاعل التلقائي (القلب)
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("❤️‍🔥")], is_big=False)
    except: pass

    # 3. معالجة قاعدة البيانات (باند + إحالات + تسجيل)
    conn = get_db_connection()
    cursor = conn.cursor()
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
                    import time
                    cursor.execute('UPDATE users SET is_vip=1, vip_expiry=%s, points = points - 9 WHERE user_id=%s', (time.time() + 86400, referrer))
                    conn.commit()
                    try: bot.send_message(referrer, "🎊 *مبروك!* جمعت 9 إحالات وتم تفعيل الـ VIP!")
                    except: pass
        
        cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', (uid, referrer, message.from_user.username))
        conn.commit()
        
        owner_msg = (f"<< دخول نفـرر جديد لبوتك >>\n"
                     f"• الاسم😂: {message.from_user.first_name}\n"
                     f"• المعرف💁: @{message.from_user.username or '😂💔فقير وبلا يوزر'}\n"
                     f"• الايدي🆔: `{uid}`\n"
                     f"• *عدد مشتركيني الفقراء*🥹: {get_total_users()}")
        try: bot.send_message(OWNER_ID, owner_msg)
        except: pass
    
    cursor.close(); conn.close() 

    # 4. رسالة الترحيب النهائية وأزرار الخدمات
    markup = types.InlineKeyboardMarkup(row_width=2).add(
        types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
        types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"),
        types.InlineKeyboardButton("❤️ تفاعلات", callback_data="show_react_menu"),
        types.InlineKeyboardButton("👁️ مشاهدات تلقائية", callback_data="auto_views_info"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
        types.InlineKeyboardButton("💎 اشتراك VIP", callback_data="vip_menu")
    )
    
    bot.send_message(
        message.chat.id, 
        "*أهلاً بك في بوت الخدمات المجانية* 🆓\n 𝚍𝚎𝚟: *@E2E12* ✶ 𝙲𝙷: *@QD3QD* ", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

# --- معالجة الأزرار ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # أضف هذين السطرين هنا مباشرة:
    try: 
        bot.answer_callback_query(call.id)
    except: 
        pass

    # ثم تبدأ بقية شروط الأزرار الخاصة بك:
    if call.data == "back_start":
        start_command(call.message)
    # ... بقية الـ elif الخاصة بك ...

    uid = call.from_user.id
    is_vip = check_vip_status(uid)

    if call.data == "auto_views_info":
        info_text = ("👁️ **خدمة المشاهدات التلقائية:**\n\n"
                    "البوت يرشق مشاهدات لكل منشور جديد تلقائياً.\n"
                    "فقط أضف البوت مشرفاً في قناتك✅.")
        return bot.send_message(call.message.chat.id, info_text)

    if call.data.startswith("v_"):
        return security.process_captcha(bot, call, get_db_connection, show_main_menu)

    # استجابة أزرار الإدارة
    if call.data.startswith("v_"):
        return security.process_captcha(bot, call, get_db_connection, show_main_menu)

    # استجابة أزرار الإدارة (يجب أن تكون على نفس مستوى الـ if السابقة)
    if call.data.startswith("adm_") and uid == OWNER_ID:
        action = call.data.split("_")[1]
        
        # هنا كان الخطأ! يجب أن يكون 'if' تحت 'action' مباشرة بـ 4 مسافات
        if action == "sts":
            conn = get_db_connection()
            cursor = conn.cursor()
            # ... باقي الكود الخاص بالإحصائيات ...

            # 1. إجمالي المستخدمين
            cursor.execute('SELECT COUNT(*) FROM users')
            total = cursor.fetchone()[0]
            
            # 2. عدد المحظورين
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
            banned = cursor.fetchone()[0]
            
            # 3. عدد مستخدمي VIP
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1')
            vips = cursor.fetchone()[0]
            
            # 4. إجمالي النقاط المتداولة
            cursor.execute('SELECT SUM(points) FROM users')
            all_points = cursor.fetchone()[0] or 0
            
            cursor.close(); conn.close()

            stats_text = (
                "📊 **إحصائيات البوت الشاملة**\n"
                "━━━━━━━━━━━━━━━\n"
                f"👥 *إجمالي الفقراء والمساكين* : `{total}`\n"
                f"💎 *المشتركين والمتعافين* VIP: `{vips}`\n"
                f"🚫 *المحظورين الزنادقه* : `{banned}`\n"
                f"💰 *إجمالي نقاط المملكه* : `{all_points}`\n"
                "━━━━━━━━━━━━━━━\n"
                "✅ *الحالة: *تعمل بكفاءة"
            )
            
            # تعديل الرسالة لإظهار التفاصيل كاملة
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=call.message.reply_markup, parse_mode="Markdown")

        elif action == "bc":
            msg = bot.send_message(call.message.chat.id, "📢 ارسل نص الإذاعة:")
            bot.register_next_step_handler(msg, broadcast_step)
        elif action in ["ban", "unban", "vip", "delvip", "points"]:
            msg = bot.send_message(call.message.chat.id, "👤 ارسل ايدي المستخدم المطلوب:")
            bot.register_next_step_handler(msg, admin_action_step, action)
        elif action == "addch":
            msg = bot.send_message(call.message.chat.id, "ارسل يوزر القناة الجديد مع @:")
            bot.register_next_step_handler(msg, lambda m: globals().update(CH_ID=m.text) or bot.send_message(OWNER_ID, "✅ تم التحديث"))
        elif action == "delch":
            globals().update(CH_ID="None")
            bot.send_message(call.message.chat.id, "✅ تم حذف القناة الإجبارية")
        elif action == "balance":
            res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'balance'}).json()
            bot.send_message(call.message.chat.id, f"💰 الرصيد: {res.get('balance')} {res.get('currency')}")
        return

    if call.data == "buy_vip_stars":
        try:
            bot.send_invoice(call.message.chat.id, "اشتراك VIP يومي", "تفعيل وضع VIP لمدة 24 ساعة", "stars_pay", "", "XTR", [types.LabeledPrice("VIP", 20)])
        except: bot.answer_callback_query(call.id, "⚠️ خطأ في بوابة النجوم")

    elif call.data == "buy_vip_points":
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id=%s", (uid,))
        p = cursor.fetchone()[0]
        if p >= 9:
            cursor.execute("UPDATE users SET points = points - 9, is_vip=1, vip_expiry=%s WHERE user_id=%s", (time.time() + 86400, uid))
            conn.commit()
            bot.send_message(call.message.chat.id, "✅ تم خصم 9 نقاط وتفعيل VIP بنجاح!")
        else:
            bot.answer_callback_query(call.id, f"❌ نقاطك لا تكفي، لديك {p} نقاط فقط", show_alert=True)
        cursor.close(); conn.close()

    # تأكد أن المسافة هنا (قبل if) هي نفس المسافة قبل الأوامر السابقة
    if call.data == "show_react_menu":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [
            types.InlineKeyboardButton("🍓 فراولة", callback_data="ser_react_13953"),
            types.InlineKeyboardButton("🐳 حوت", callback_data="ser_react_13949"),
            types.InlineKeyboardButton("❤️‍🔥 قلب نار", callback_data="ser_react_13947"),
            types.InlineKeyboardButton("😍 حب", callback_data="ser_react_13933"),
            types.InlineKeyboardButton("😂 ضحك", callback_data="ser_react_13932"),
            types.InlineKeyboardButton("🔥 حريق", callback_data="ser_react_13931"),
            types.InlineKeyboardButton("❤️ قلب", callback_data="ser_react_13930"),
            types.InlineKeyboardButton("👍 إيجابي", callback_data="ser_react_13929"),
            types.InlineKeyboardButton("👎 سلبي", callback_data="ser_react_13926"),
            types.InlineKeyboardButton("✅ تأكيد", callback_data="ser_react_13925"),
        ]
        markup.add(*btns)
        markup.row(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start"))
        
        try:
            bot.edit_message_text(
                "🎭 *قائمة التفاعلات المتاحة:*\nالكمية: +99 تفاعل لكل طلب.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except:
            pass

    elif call.data == "my_account":
        # هذا القسم أيضاً يجب أن يكون على نفس مستوى محاذاة if السابقة
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id=%s", (uid,))
        res = cursor.fetchone()
        points = res[0] if res else 0
        cursor.close(); conn.close()
        
        total_users = get_total_users()
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={uid}"
        status = "💎 VIP" if is_vip else "👤 عادي"
        
        share_text = f"🚀 أقوى بوت خدمات مجانية!\n{referral_link}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 مشاركة رابط الدعوة", url=f"https://t.me/share/url?url={urllib.parse.quote(share_text)}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start"))

        account_msg = (
            f"🆔 *الايدي:* `{uid}`\n"
            f"💰 *نقاطك:* {points}\n"
            f"❤️‍🔥 *حالتك:* {status}\n"
            f"👥 *عدد المستخدمين الكلي:* {total_users}\n\n"
            f"🔗 *رابط الدعوة الخاص بك:*\n"
            f"{referral_link}"
        )
        try:
            bot.edit_message_text(account_msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        except:
            bot.send_message(call.message.chat.id, account_msg, reply_markup=markup)


    elif call.data == "vip_menu":
        markup = types.InlineKeyboardMarkup(row_width=1).add(
            types.InlineKeyboardButton("🌟 اشتراك بـ 20 نجمة (يومي)", callback_data="buy_vip_stars"),
            types.InlineKeyboardButton("💰 اشتراك بـ 9 نقاط (يومي)", callback_data="buy_vip_points"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="back_start")
        )
        bot.edit_message_text("الاشتراك يومي بـ 20 نجمه 🌟 أو 9 إحالة.", call.message.chat.id, call.message.message_id, reply_markup=markup)

elif call.data.startswith("ser_"):
    parts = call.data.split("_")
    service_type, s_id = parts[1], parts[2]
    col = f"last_{service_type}"

    # الاتصال بقاعدة البيانات وجلب last_time
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {col} FROM users WHERE user_id=%s", (uid,))
    res = cursor.fetchone()
    last_time = res[0] if res and res[0] is not None else 0
    cursor.close()
    conn.close()

    # مدة الانتظار بالثواني (1.5 ساعة)
    wait_seconds = 5400
    elapsed = time.time() - last_time

    if not is_vip and elapsed < wait_seconds:
        rem = int(wait_seconds - elapsed)
        try:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text=f"⏳ لا يمكنك طلب الخدمة بعدك {rem // 3600} ساعة و {(rem % 3600) // 60} دقيقة",
                show_alert=True
            )
        except Exception as e:
            print("Error showing popup:", e)
        return

    # السماح بالطلب إذا انتهى الوقت أو كان VIP
    msg = bot.send_message(
        call.message.chat.id,
        "🔗 *ارسل الرابط الآن:*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_order, s_id, col, service_type)

# --- منطق لوحة الإدارة ---
def admin_action_step(message, action):
    try:
        tid = int(message.text)
        conn = get_db_connection(); cursor = conn.cursor()
        if action == "ban": cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=%s", (tid,))
        elif action == "unban": cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=%s", (tid,))
        elif action == "vip": cursor.execute("UPDATE users SET is_vip=1, vip_expiry=%s WHERE user_id=%s", (time.time() + 86400, tid))
        elif action == "delvip": cursor.execute("UPDATE users SET is_vip=0, vip_expiry=0 WHERE user_id=%s", (tid,))
        elif action == "points":
            bot.send_message(OWNER_ID, "كم عدد النقاط؟")
            bot.register_next_step_handler(message, lambda m: give_points_final(m, tid))
            cursor.close(); conn.close(); return
        conn.commit(); cursor.close(); conn.close()
        bot.send_message(OWNER_ID, f"✅ تم تنفيذ {action} للمستخدم {tid}")
    except: bot.send_message(OWNER_ID, "❌ خطأ في البيانات")

def give_points_final(message, tid):
    try:
        p = int(message.text)
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + %s WHERE user_id=%s", (p, tid))
        conn.commit(); cursor.close(); conn.close()
        bot.send_message(OWNER_ID, "✅ تم إضافة النقاط")
    except: pass

def process_order(message, s_id, col, s_type):
    if not message.text or not message.text.startswith("http"):
        return bot.send_message(message.chat.id, "❌ الرابط غير صحيح.")
    qty = 1300 if s_type == "view" else 20
    try:
        res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': qty}).json()
        if "order" in res:
            order_id = res["order"]  # جلب رقم الطلب من استجابة الموقع
            conn = get_db_connection(); cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {col}=%s WHERE user_id=%s", (time.time(), message.from_user.id))
            conn.commit(); cursor.close(); conn.close()
            
            # تعديل رسالة النجاح لإظهار رقم الطلب
            success_msg = (f"✅ **تم الطلب بنجاح!**\n\n"
                           f"🔢 رقم الطلب: `{order_id}`\n"
                           f"📦 الكمية: +99\n"
                           f"⏳ حالة الطلب: قيد المعالجة")
            
            bot.send_message(message.chat.id, success_msg, parse_mode="Markdown")
        else: 
            bot.send_message(message.chat.id, "❌ فشل راجع @IE2017 .")


    except Exception as e:
        print(f"Error: {e}")

def broadcast_step(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    for (u_id,) in users:
        try:
            bot.send_message(u_id, message.text)
        except:
            continue


    bot.send_message(message.chat.id, "✅ *تم الانتهاء من الإرسال للجميع*.")


# --- دفع النجوم ---
@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q): bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_vip=1, vip_expiry=%s WHERE user_id=%s", (time.time() + 86400, message.from_user.id))
    conn.commit(); cursor.close(); conn.close()
    bot.send_message(message.chat.id, "💎 مبروك! تم تفعيل الـ VIP")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != OWNER_ID, content_types=['text', 'photo', 'video', 'voice', 'sticker'])
def forward_to_owner(message):
    try: bot.forward_message(OWNER_ID, message.chat.id, message.message_id)
    except: pass

import time
if __name__ == "__main__":
    # 1. إزالة أي ويب هوك قديم (للتأكد من نظافة الاتصال)
    bot.remove_webhook()
    
    # 2. انتظار لمدة 3 ثوانٍ للسماح لتليجرام بإنهاء الجلسات العالقة
    import time
    time.sleep(3)
    
    print("Bot is starting after cleanup...")
    
    # 3. التشغيل مع تجاهل الرسائل القديمة
    bot.infinity_polling(skip_pending=True)

