from telebot import types

# قائمة القنوات للاشتراك الإجباري
mandatory_channels = []

def register(bot, cursor, conn):
    OWNER_ID = 5581457665  # رقم المالك

    @bot.message_handler(commands=["admin"])
    def admin_panel(message):
        if message.from_user.id != OWNER_ID:
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔒 حظر مستخدم", callback_data="ban_user"),
            types.InlineKeyboardButton("🔓 رفع الحظر", callback_data="unban_user"),
            types.InlineKeyboardButton("⭐ VIP", callback_data="vip_user"),
            types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast_msg"),
            types.InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel"),
            types.InlineKeyboardButton("📊 احصائيات", callback_data="stats")
        )
        bot.send_message(message.chat.id, "لوحة التحكم الخاصة بالوالي السلطان:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data in ["ban_user", "unban_user", "vip_user", "broadcast_msg", "add_channel", "stats"])
    def admin_actions(call):
        if call.from_user.id != OWNER_ID:
            return

        chat_id = call.message.chat.id

        if call.data == "ban_user":
            msg = bot.send_message(chat_id, "ادخل ايدي المستخدم لحظره:")
            bot.register_next_step_handler(msg, lambda m: update_user_status(m, "ban"))
        elif call.data == "unban_user":
            msg = bot.send_message(chat_id, "ادخل ايدي المستخدم لرفع الحظر:")
            bot.register_next_step_handler(msg, lambda m: update_user_status(m, "unban"))
        elif call.data == "vip_user":
            msg = bot.send_message(chat_id, "ادخل ايدي المستخدم لمنحه VIP:")
            bot.register_next_step_handler(msg, lambda m: update_user_status(m, "vip"))
        elif call.data == "broadcast_msg":
            msg = bot.send_message(chat_id, "اكتب الرسالة للإرسال لجميع المستخدمين:")
            bot.register_next_step_handler(msg, broadcast_message)
        elif call.data == "add_channel":
            msg = bot.send_message(chat_id, "ادخل معرف القناة لإضافتها للاشتراك الإجباري:")
            bot.register_next_step_handler(msg, add_channel)
        elif call.data == "stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            bot.send_message(chat_id, f"📊 عدد المستخدمين: {total}")

    def update_user_status(message, action):
        try:
            user_id = int(message.text)
            if action == "ban":
                cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
                bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id}")
            elif action == "unban":
                cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
                bot.send_message(message.chat.id, f"✅ تم رفع الحظر عن المستخدم {user_id}")
            elif action == "vip":
                cursor.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (user_id,))
                bot.send_message(message.chat.id, f"💎 تم منح VIP للمستخدم {user_id}")
            conn.commit()
        except:
            bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

    def broadcast_message(message):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        count = 0
        for (user_id,) in users:
            try:
                bot.send_message(user_id, message.text)
                count += 1
            except:
                continue
        bot.send_message(message.chat.id, f"✅ تم إرسال الرسالة إلى {count} مستخدم.")

    def add_channel(message):
        channel = message.text.strip()
        if not channel.startswith("@"):
            channel = f"@{channel}"
        mandatory_channels.append(channel)
        bot.send_message(message.chat.id, f"✅ تم إضافة القناة {channel} للاشتراك الإجباري.")
