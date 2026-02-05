# admin_panel.py
import time
from telebot import types

ADMIN_ID = int(__import__("os").getenv("5581457665"))

def register(bot, cursor, conn):

    # ================== قواعد البيانات ==================
    cursor.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS vip_users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS force_channels (channel TEXT PRIMARY KEY)")
    cursor.execute("""CREATE TABLE IF NOT EXISTS service_settings
                      (service_id TEXT PRIMARY KEY, quantity INTEGER)""")
    conn.commit()

    # ================== أدوات ==================
    def is_admin(uid): return uid == ADMIN_ID

    def admin_menu():
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🛑 حظر مستخدم", callback_data="ban"),
            types.InlineKeyboardButton("✅ فك الحظر", callback_data="unban"),
            types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast"),
            types.InlineKeyboardButton("⭐ VIP", callback_data="vip"),
            types.InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
            types.InlineKeyboardButton("📊 إحصائيات", callback_data="stats")
        )
        return kb

    # ================== /admin ==================
    @bot.message_handler(commands=["admin"])
    def admin_cmd(msg):
        if not is_admin(msg.from_user.id): return
        bot.send_message(msg.chat.id, "لوحة تحكم الوالي والمطور:", reply_markup=admin_menu())

    # ================== الأزرار ==================
    @bot.callback_query_handler(func=lambda c: c.data in ["ban","unban","broadcast","vip","settings","stats"])
    def admin_actions(call):
        if not is_admin(call.from_user.id): return
        bot.answer_callback_query(call.id)

        if call.data == "ban":
            m = bot.send_message(call.message.chat.id, "ارسل ID المستخدم للحظر:")
            bot.register_next_step_handler(m, do_ban)

        elif call.data == "unban":
            m = bot.send_message(call.message.chat.id, "ارسل ID المستخدم لفك الحظر:")
            bot.register_next_step_handler(m, do_unban)

        elif call.data == "broadcast":
            m = bot.send_message(call.message.chat.id, "..ارسل رسالة الإذاعة:")
            bot.register_next_step_handler(m, do_broadcast)

        elif call.data == "vip":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("➕ إضافة VIP", callback_data="vip_add"),
                types.InlineKeyboardButton("➖ حذف VIP", callback_data="vip_del")
            )
            bot.send_message(call.message.chat.id, "نظام VIP💎:", reply_markup=kb)

        elif call.data == "settings":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("📦 كمية الطلب", callback_data="set_qty"),
                types.InlineKeyboardButton("📢 قنوات الاشتراك", callback_data="channels")
            )
            bot.send_message(call.message.chat.id, "الإعدادات:", reply_markup=kb)

        elif call.data == "stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vip_users")
            vip = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM banned_users")
            banned = cursor.fetchone()[0]
            bot.send_message(call.message.chat.id, f"{users}\n{vip}\n{banned}")

    # ================== VIP ==================
    @bot.callback_query_handler(func=lambda c: c.data.startswith("vip_"))
    def vip_actions(call):
        if not is_admin(call.from_user.id): return
        m = bot.send_message(call.message.chat.id, "ارسل ID المستخدم:")
        if call.data == "vip_add":
            bot.register_next_step_handler(m, vip_add)
        else:
            bot.register_next_step_handler(m, vip_del)

    def vip_add(m):
        cursor.execute("INSERT OR IGNORE INTO vip_users VALUES (?)", (int(m.text),))
        conn.commit()
        bot.send_message(m.chat.id, "✅😑تمت الإضافة VIP")

    def vip_del(m):
        cursor.execute("DELETE FROM vip_users WHERE user_id=?", (int(m.text),))
        conn.commit()
        bot.send_message(m.chat.id, "😂✅تم حذف VIP")

    # ================== حظر ==================
    def do_ban(m):
        cursor.execute("INSERT OR IGNORE INTO banned_users VALUES (?)", (int(m.text),))
        conn.commit()
        bot.send_message(m.chat.id, "😂✅تم الحظر")

    def do_unban(m):
        cursor.execute("DELETE FROM banned_users WHERE user_id=?", (int(m.text),))
        conn.commit()
        bot.send_message(m.chat.id, "✅تم فك الحظر")

    # ================== إذاعة ==================
    def do_broadcast(m):
        cursor.execute("SELECT user_id FROM users")
        for (uid,) in cursor.fetchall():
            try:
                bot.send_message(uid, m.text)
                time.sleep(0.05)
            except:
                pass
        bot.send_message(m.chat.id, "✅تمت الإذاعة")

    # ================== الإعدادات ==================
    @bot.callback_query_handler(func=lambda c: c.data in ["set_qty","channels"])
    def settings_actions(call):
        if call.data == "set_qty":
            m = bot.send_message(call.message.chat.id, "ارسل: service_id quantity")
            bot.register_next_step_handler(m, set_qty)

        elif call.data == "channels":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("➕ إضافة قناة", callback_data="ch_add"),
                types.InlineKeyboardButton("➖ حذف قناة", callback_data="ch_del")
            )
            bot.send_message(call.message.chat.id, "قنوات الاشتراك:", reply_markup=kb)

    def set_qty(m):
        sid, qty = m.text.split()
        cursor.execute("INSERT OR REPLACE INTO service_settings VALUES (?,?)", (sid, int(qty)))
        conn.commit()
        bot.send_message(m.chat.id, "تم التحديث")

    @bot.callback_query_handler(func=lambda c: c.data in ["ch_add","ch_del"])
    def channel_actions(call):
        m = bot.send_message(call.message.chat.id, "ارسل @channel")
        if call.data == "ch_add":
            bot.register_next_step_handler(m, ch_add)
        else:
            bot.register_next_step_handler(m, ch_del)

    def ch_add(m):
        cursor.execute("INSERT OR IGNORE INTO force_channels VALUES (?)", (m.text,))
        conn.commit()
        bot.send_message(m.chat.id, "✅تمت الإضافة")

    def ch_del(m):
        cursor.execute("DELETE FROM force_channels WHERE channel=?", (m.text,))
        conn.commit()
        bot.send_message(m.chat.id, "👍❌تم الحذف")
