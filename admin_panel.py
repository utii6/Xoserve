from telebot import types
import time

# قائمة القنوات الإجباري الاشتراك فيها
mandatory_channels = []

# تخزين كمية الطلب لكل خدمة
service_quantity = {
    "sub": 100,
    "view": 100,
    "react": 100
}

def register(bot, cursor, conn):

    @bot.message_handler(commands=["admin"])
    def admin_panel(message):
        if message.from_user.id != 5581457665:  # رقم المالك
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔒 حظر مستخدم", callback_data="admin_ban"),
            types.InlineKeyboardButton("🔓 رفع الحظر", callback_data="admin_unban"),
            types.InlineKeyboardButton("⭐️ VIP", callback_data="admin_vip"),
            types.InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add"),
            types.InlineKeyboardButton("📊 احصائيات", callback_data="admin_stats")
        )
        bot.send_message(message.chat.id, "لوحة التحكم الخاصة بالمالك والسلطان الوالي:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
    def admin_actions(call):
        if call.from_user.id != 5581457665:
            return

        action = call.data.split("_")[1]

        if action == "ban":
            msg = bot.send_message(call.message.chat.id, "ادخل ايدي المستخدم لحظره:")
            bot.register_next_step_handler(msg, ban_user)
        elif action == "unban":
            msg = bot.send_message(call.message.chat.id, "ادخل ايدي المستخدم لرفع الحظر:")
            bot.register_next_step_handler(msg, unban_user)
        elif action == "vip":
            msg = bot.send_message(call.message.chat.id, "ادخل ايدي المستخدم لمنحه VIP:")
            bot.register_next_step_handler(msg, vip_user)
        elif action == "broadcast":
            msg = bot.send_message(call.message.chat.id, "اكتب الرسالة للإرسال لجميع المستخدمين:")
            bot.register_next_step_handler(msg, broadcast_message)
        elif action == "add":
            msg = bot.send_message(call.message.chat.id, "ادخل معرف القناة لإضافتها للاشتراك الاجباري:")
            bot.register_next_step_handler(msg, add_channel)
        elif action == "stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
            total_vip = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
            total_banned = cursor.fetchone()[0]
            bot.send_message(call.message.chat.id, f"📊 عدد المستخدمين الكلي: {total}\n⭐ عدد VIP: {total_vip}\n🔒 عدد المحظورين: {total_banned}")

    # ======== دوال الإدارة ========
    def ban_user(message):
        try:
            user_id = int(message.text)
            cursor.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅😂 تم حظر المستخدم {user_id}")
            try: bot.send_message(user_id, "⚠️ تم حظرك من استخدام البوت")
            except: pass
        except:
            bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

    def unban_user(message):
        try:
            user_id = int(message.text)
            cursor.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅😑 تم رفع الحظر عن المستخدم {user_id}")
            try: bot.send_message(user_id, "✅ تم رفع الحظر عنك، يمكنك استخدام البوت الآن")
            except: pass
        except:
            bot.send_message(message.chat.id, "❌ خطأ في الإدخال.")

    def vip_user(message):
        try:
            user_id = int(message.text)
            cursor.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (user_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅💎 تم منح VIP للمستخدم {user_id}")
            try: bot.send_message(user_id, "🎉 تم منحك حالة VIP! استمتع بالميزات الخاصة")
            except: pass
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
        bot.send_message(message.chat.id, f"✅ تم إرسال الرسالة إلى {count} مستخدمين.")

    def add_channel(message):
        channel = message.text.strip()
        if not channel.startswith("@"):
            channel = f"@{channel}"
        mandatory_channels.append(channel)
        bot.send_message(message.chat.id, f"✅ تم إضافة القناة {channel} للاشتراك الاجباري.")
