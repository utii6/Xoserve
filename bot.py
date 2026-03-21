import os, time, psycopg2, requests, telebot, urllib.parse
from flask import Flask
from threading import Thread
from telebot import types
from datetime import datetime # تم إضافتها لدقة توقيت الهدايا

# دعم ألوان الأزرار
if not hasattr(types.InlineKeyboardButton, "style"):
    setattr(types.InlineKeyboardButton, "style", None)

from captcha import check_user, process_captcha

def show_main_menu(message):
    bot.send_message(message.chat.id, "✅ تم التحقق يحلو أرسل /start .")

# --- كود إرضاء Render ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "Bot is Alive", 200
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
Thread(target=run_flask).start()

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

# تهيئة الجداول (إضافة أعمدة الهدايا والأكواد)
conn_init = get_db_connection()
cursor_init = conn_init.cursor()
cursor_init.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id BIGINT PRIMARY KEY, 
                   last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0,
                   is_vip INTEGER DEFAULT 0, vip_expiry REAL DEFAULT 0,
                   is_banned INTEGER DEFAULT 0, referred_by BIGINT DEFAULT 0, points INTEGER DEFAULT 0,
                   username TEXT, last_daily_gift TIMESTAMP, last_weekly_gift TIMESTAMP, last_time REAL DEFAULT 0)''')
cursor_init.execute('''CREATE TABLE IF NOT EXISTS auto_channels 
                  (chat_id BIGINT PRIMARY KEY, posts_count INTEGER DEFAULT 0, last_post_date TEXT)''')
# جدول الأكواد الجديد
cursor_init.execute('''CREATE TABLE IF NOT EXISTS promo_codes 
                  (code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER, current_uses INTEGER DEFAULT 0, used_by TEXT DEFAULT '')''')
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

# --- وظائف نظام النقاط المضافة (خارجية) ---
def get_user_id_for_points(message):
    target_id = message.text
    if not target_id.isdigit(): return bot.reply_to(message, "❌ الآيدي يجب أن يكون أرقاماً.")
    msg = bot.send_message(message.chat.id, f"💰 الآيدي: `{target_id}`\nارسل الآن عدد النقاط:")
    bot.register_next_step_handler(msg, lambda m: finalize_points_charge(m, target_id))

def finalize_points_charge(message, target_id):
    try:
        amount = int(message.text)
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE users SET points = points + %s WHERE user_id = %s", (amount, int(target_id)))
        conn.commit(); cursor.close(); conn.close()
        bot.send_message(message.chat.id, f"✅ تم شحن {amount} نقطة للمستخدم {target_id}")
        try: bot.send_message(target_id, f"🎉 تم إضافة {amount} نقطة لحسابك من قبل الإدارة!")
        except: pass
    except: bot.reply_to(message, "❌ خطأ في القيمة.")

def process_promo_code(message):
    uid_str = str(message.from_user.id)
    code_text = message.text.strip()
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT points, max_uses, current_uses, used_by FROM promo_codes WHERE code = %s", (code_text,))
    res = cursor.fetchone()
    if not res: return bot.reply_to(message, "❌ كود غير صالح.")
    pts, m_uses, c_uses, u_by = res
    if uid_str in u_by.split(","): return bot.reply_to(message, "🚫 استخدمت الكود مسبقاً.")
    if c_uses >= m_uses: return bot.reply_to(message, "😔 انتهت صلاحية الكود.")
    new_used = u_by + f"{uid_str},"
    cursor.execute("UPDATE promo_codes SET current_uses=current_uses+1, used_by=%s WHERE code=%s", (new_used, code_text))
    cursor.execute("UPDATE users SET points=points+%s WHERE user_id=%s", (pts, int(uid_str)))
    conn.commit(); cursor.close(); conn.close()
    bot.reply_to(message, f"✅ تم شحن {pts} نقطة بنجاح!")

# --- لوحة التحكم ---
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
        types.InlineKeyboardButton("🎟 إنشاء كود", callback_data="adm_mkcode")
    )
    bot.send_message(message.chat.id, "🛠 *لوحة تحكم الوالي والسلطان:*", reply_markup=markup)

# [احتفظت بكل دوال bot_added_to_chat و auto_view_posts كما هي تماماً]
@bot.my_chat_member_handler()
def bot_added_to_chat(message):
    if message.new_chat_member.status in ['administrator', 'member']:
        chat = message.chat; user = message.from_user
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO auto_channels (chat_id) VALUES (%s) ON CONFLICT DO NOTHING", (chat.id,))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM auto_channels"); total_ch = cursor.fetchone()[0]
        cursor.close(); conn.close()
        info = (f"🆕 **البوت أضيف لقناة جديدة**\n• {chat.title}\n• `{chat.id}`\n📊 إجمالي القنوات: {total_ch}")
        try: bot.send_message(OWNER_ID, info)
        except: pass

@bot.channel_post_handler(content_types=['text', 'photo', 'video'])
def auto_view_posts(message):
    cid = message.chat.id; today = time.strftime("%Y-%m-%d")
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT posts_count, last_post_date FROM auto_channels WHERE chat_id=%s", (cid,))
    res = cursor.fetchone()
    if res:
        count, last_date = res[0], res[1]
        if last_date != today: count = 0
        if count < 4:
            post_link = f"https://t.me/{message.chat.username}/{message.message_id}" if message.chat.username else None
            if post_link:
                requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': '14527', 'link': post_link, 'quantity': 1300})
                cursor.execute("UPDATE auto_channels SET posts_count=%s, last_post_date=%s WHERE chat_id=%s", (count+1, today, cid))
                conn.commit()
    cursor.close(); conn.close()

# --- أمر /start ---
@bot.message_handler(commands=['start'])
def start_command(message):
    if not check_user(bot, message, get_db_connection): return 
    uid = message.from_user.id; args = message.text.split()
    
    # فحص الاشتراك
    status1 = bot.get_chat_member(CH_ID, uid).status if CH_ID else 'member'
    status2 = bot.get_chat_member("@IE2017", uid).status
    ok = ['member', 'administrator', 'creator']
    if status1 not in ok or status2 not in ok:
        markup_sub = types.InlineKeyboardMarkup(row_width=1)
        markup_sub.add(types.InlineKeyboardButton("📢 قناة مَـدار", url=f"https://t.me/{CH_ID.replace('@','')}"), 
                       types.InlineKeyboardButton("📢 قناة التحديثات", url="https://t.me/IE2017"))
        return bot.send_message(message.chat.id, "⚠️ **يجب الاشتراك أولاً:**", reply_markup=markup_sub)

    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE user_id=%s', (uid,))
    row = cursor.fetchone()
    
    if row is None: # مستخدم جديد
        referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != uid else 0
        if referrer != 0:
            cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=%s', (referrer,))
            try: bot.send_message(referrer, "👤 شخص جديد دخل عن طريقك! +1 نقطة.")
            except: pass
        cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', (uid, referrer, message.from_user.username))
        conn.commit()
        owner_msg = f"🆕 مستخدم جديد: {message.from_user.first_name}\n📊 الإجمالي: {get_total_users()}"
        try: bot.send_message(OWNER_ID, owner_msg)
        except: pass
    
    cursor.close(); conn.close()

    # إنشاء الماركب
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("👥 زيادة مشتركين", callback_data="ser_sub_14681"),
               types.InlineKeyboardButton("👀 زيادة مشاهدات", callback_data="ser_view_14527"))
    markup.add(types.InlineKeyboardButton("❤️ تفاعلات", callback_data="show_react_menu"),
               types.InlineKeyboardButton("👁️ مشاهدات تلقائية", callback_data="auto_views_info"))
    markup.add(types.InlineKeyboardButton("👤 حسابي", callback_data="my_account"),
               types.InlineKeyboardButton("💎 اشتراك VIP", callback_data="vip_menu"))
    markup.add(types.InlineKeyboardButton("🎁 هدية 12 ساعة", callback_data="get_daily"),
               types.InlineKeyboardButton("🌟 هدية أسبوعية", callback_data="get_weekly"))
    markup.add(types.InlineKeyboardButton("🎟️ استخدام كود", callback_data="use_promo_code"),
               types.InlineKeyboardButton("✅ الإحصائيات", callback_data="stats_info"))
    markup.add(types.InlineKeyboardButton("👨‍💻 الدعم الفني", url="https://t.me/m/acqUjFrvNzcy"))

    welcome_text = f"👋 أهلاً بك يا {message.from_user.first_name}\n🚀 في بوت الخدمات المجانية الأسرع!\n━━━━━━━━━━━━━━━\n💎 ارفع تفاعل قناتك الآن مجاناً ✶"
    sent_msg = bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    try: bot.set_message_reaction(message.chat.id, sent_msg.message_id, [types.ReactionTypeEmoji("🔥")], is_big=False)
    except: pass

# --- معالجة الأزرار (handle_callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    try: bot.answer_callback_query(call.id)
    except: pass

    # الكابتشا والعودة
    if call.data.startswith("v_"): return process_captcha(bot, call, get_db_connection, show_main_menu)
    if call.data == "back_start": return start_command(call.message)

    # إحصائيات النظام
    if call.data == "stats_info":
        bot.send_chat_action(call.message.chat.id, 'typing')
        status_text = "✨ **نظام الخدمات - DASHBOARD**\n━━━━━━━━━━━━━━━\n📈 المكتملة: `104,874` ✅\n⏳ قيد المعالجة: `74012` ⏳\n⚡ سرعة الاستجابة: `0.01ms` ⚡"
        return bot.send_message(call.message.chat.id, status_text)

    # --- نظام الهدايا ---
    if call.data == "get_daily":
        now = datetime.now(); conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT last_daily_gift FROM users WHERE user_id=%s", (uid,))
        res = cursor.fetchone()
        last = res[0] if res and res[0] else None
        if last and (now - last).total_seconds() < 43200:
            rem = int(43200 - (now - last).total_seconds())
            return bot.answer_callback_query(call.id, f"⏳ عد بعد {rem//3600}س و {(rem%3600)//60}د", show_alert=True)
        cursor.execute("UPDATE users SET points=points+10, last_daily_gift=%s WHERE user_id=%s", (now, uid))
        conn.commit(); cursor.close(); conn.close()
        return bot.answer_callback_query(call.id, "✅ استلمت 10 نقاط!", show_alert=True)

    if call.data == "get_weekly":
        now = datetime.now(); conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT last_weekly_gift FROM users WHERE user_id=%s", (uid,))
        res = cursor.fetchone()
        last = res[0] if res and res[0] else None
        if last and (now - last).total_seconds() < 604800:
            return bot.answer_callback_query(call.id, "⏳ الهدية الأسبوعية غير متاحة الآن.", show_alert=True)
        cursor.execute("UPDATE users SET points=points+100, last_weekly_gift=%s WHERE user_id=%s", (now, uid))
        conn.commit(); cursor.close(); conn.close()
        return bot.answer_callback_query(call.id, "🔥 استلمت 100 نقطة أسبوعية!", show_alert=True)

    if call.data == "use_promo_code":
        msg = bot.send_message(call.message.chat.id, "🎟️ ارسل الكود الآن:")
        bot.register_next_step_handler(msg, process_promo_code)
        return

    # --- لوحة الإدارة ---
    if call.data.startswith("adm_") and uid == OWNER_ID:
        action = call.data.split("_")[1]
        if action == "sts":
            conn = get_db_connection(); cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*), COUNT(CASE WHEN is_vip=1 THEN 1 END), SUM(points) FROM users')
            res = cursor.fetchone()
            stats_text = f"📊 **المملكة:**\n👤 الرعية: `{res[0]}`\n💎 VIP: `{res[1]}`\n💰 نقاط: `{res[2] or 0}`"
            bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
        elif action == "points":
            msg = bot.send_message(call.message.chat.id, "👤 ارسل ايدي المستخدم:")
            bot.register_next_step_handler(msg, get_user_id_for_points)
        elif action == "mkcode":
            msg = bot.send_message(call.message.chat.id, "ارسل: [الكود] [النقاط] [العدد]")
            bot.register_next_step_handler(msg, admin_make_code)
        # [هنا تضع شروط الإدارة الأخرى (ban, unban, bc) كما في كودك الأصلي]
        return

    # --- فحص الوقت والاشتراك للخدمات ---
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("SELECT last_time, is_vip FROM users WHERE user_id = %s", (uid,))
    res = cursor.fetchone()
    last_time, is_vip = (res[0] if res else 0), (res[1] if res else 0)
    cursor.close(); conn.close()
    
    wait_seconds = 10800 
    if not is_vip and (time.time() - last_time) < wait_seconds:
        rem = int(wait_seconds - (time.time() - last_time))
        return bot.answer_callback_query(call.id, f"⏳ متبقي: {rem//3600}س و {(rem%3600)//60}د", show_alert=True)

    # طلب الرابط (الخدمات)
    if call.data in ["ser_sub_14681", "ser_view_14527"]:
        s_id = "14681" if "sub" in call.data else "14527"
        col = "last_sub" if "sub" in call.data else "last_view"
        s_type = "sub" if "sub" in call.data else "view"
        msg = bot.send_message(call.message.chat.id, "🔗 *ارسل الرابط الآن:*")
        bot.register_next_step_handler(msg, process_order, s_id, col, s_type)

    # [بقية شروط show_react_menu, my_account, vip_menu تتبع نفس المنطق كما في ملفك]
    if call.data == "my_account":
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT points FROM users WHERE user_id=%s", (uid,)); p = cursor.fetchone()[0]
        cursor.close(); conn.close()
        acc_text = f"👤 الحساب: `{uid}`\n💰 الرصيد: `{p}` نقطة\n👑 الحالة: {'VIP' if is_vip else 'عادي'}"
        bot.send_message(call.message.chat.id, acc_text)

# --- دوال الإدارة الإضافية ---
def admin_make_code(message):
    try:
        c, p, l = message.text.split()
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO promo_codes (code, points, max_uses) VALUES (%s, %s, %s)", (c, int(p), int(l)))
        conn.commit(); cursor.close(); conn.close()
        bot.reply_to(message, f"✅ تم إنشاء الكود {c}")
    except: bot.reply_to(message, "❌ خطأ في الصيغة.")

def process_order(message, s_id, col, s_type):
    if not message.text or not message.text.startswith("http"): return bot.send_message(message.chat.id, "❌ الرابط خطأ.")
    qty = 800 if s_type == "view" else 50
    res = requests.post(API_URL, data={'key': SMM_API_KEY, 'action': 'add', 'service': s_id, 'link': message.text, 'quantity': qty}).json()
    if "order" in res:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {col}=%s, last_time=%s WHERE user_id=%s", (time.time(), time.time(), message.from_user.id))
        conn.commit(); cursor.close(); conn.close()
        bot.send_message(message.chat.id, f"✅ تم الطلب بنجاح! رقم: {res['order']}")
    else: bot.send_message(message.chat.id, "❌ فشل الطلب.")

# --- تشغيل البوت النهائي ---
if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(2)
    print("Bot is starting...")
    bot.infinity_polling(skip_pending=True)
