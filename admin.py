import os, sqlite3, telebot, time
from telebot import types

API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

def get_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn, conn.cursor()

# إنشاء الجداول والقيم الافتراضية
conn, cursor = get_db()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, last_sub REAL DEFAULT 0, last_view REAL DEFAULT 0, last_react REAL DEFAULT 0, is_vip INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)')
cursor.execute('CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, force_channel TEXT, quantity INTEGER DEFAULT 100, welcome_msg TEXT)')
cursor.execute('SELECT COUNT(*) FROM settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('INSERT INTO settings (id, force_channel, quantity, welcome_msg) VALUES (1, "None", 100, "أهلاً بك في البوت!")')
conn.commit()

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📢 إذاعة", callback_data="bc"),
            types.InlineKeyboardButton("🚫 حظر", callback_data="ban"),
            types.InlineKeyboardButton("💎 VIP", callback_data="vip"),
            types.InlineKeyboardButton("🔢 كمية", callback_data="qty"),
            types.InlineKeyboardButton("📢 قناة", callback_data="chn"),
            types.InlineKeyboardButton("📊 إحصائيات", callback_data="stats")
        )
        bot.send_message(message.chat.id, "🛠 *لوحة التحكم:*", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def admin_actions(call):
    if call.data == "bc":
        msg = bot.send_message(call.message.chat.id, "ارسل نص الإذاعة:")
        bot.register_next_step_handler(msg, do_bc)
    elif call.data == "stats":
        conn, cursor = get_db()
        cursor.execute('SELECT COUNT(*) FROM users')
        bot.answer_callback_query(call.id, f"المستخدمين: {cursor.fetchone()[0]}", show_alert=True)
    elif call.data == "ban":
        msg = bot.send_message(call.message.chat.id, "ارسل ايدي المحظور:")
        bot.register_next_step_handler(msg, lambda m: update_user(m, "is_banned"))
    elif call.data == "vip":
        msg = bot.send_message(call.message.chat.id, "ارسل ايدي الـ VIP:")
        bot.register_next_step_handler(msg, lambda m: update_user(m, "is_vip"))
    elif call.data == "qty":
        msg = bot.send_message(call.message.chat.id, "ارسل الكمية:")
        bot.register_next_step_handler(msg, set_qty)

def do_bc(message):
    conn, cursor = get_db()
    cursor.execute('SELECT user_id FROM users')
    for u in cursor.fetchall():
        try: bot.send_message(u[0], message.text)
        except: continue
    bot.send_message(message.chat.id, "✅ تمت الإذاعة.")

def update_user(message, field):
    conn, cursor = get_db()
    uid = int(message.text)
    cursor.execute(f'UPDATE users SET {field} = CASE WHEN {field}=1 THEN 0 ELSE 1 END WHERE user_id=?', (uid,))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم التحديث.")

def set_qty(message):
    conn, cursor = get_db()
    cursor.execute('UPDATE settings SET quantity=? WHERE id=1', (int(message.text),))
    conn.commit()
    bot.send_message(message.chat.id, "✅ تم تحديث الكمية.")

bot.infinity_polling()
