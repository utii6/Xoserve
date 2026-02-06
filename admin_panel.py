from telebot import types

def register(bot, cursor, conn):
    OWNER_ID = 5581457665 

    @bot.message_handler(commands=["admin"])
    def admin_panel(message):
        if message.from_user.id == OWNER_ID:
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔒 حظر مستخدم", callback_data="ban_user"),
                types.InlineKeyboardButton("🔓 رفع الحظر", callback_data="unban_user"),
                types.InlineKeyboardButton("⭐ VIP", callback_data="vip_user"),
                types.InlineKeyboardButton("📢 إذاعة", callback_data="broadcast_msg"),
                types.InlineKeyboardButton("📊 احصائيات", callback_data="stats")
            )
            bot.send_message(message.chat.id, "🛠 لوحة التحكم:", reply_markup=markup)

    # تحديد أزرار الإدارة فقط
    @bot.callback_query_handler(func=lambda call: call.data in ["ban_user", "unban_user", "vip_user", "broadcast_msg", "stats"])
    def admin_actions(call):
        if call.from_user.id != OWNER_ID: return
        
        if call.data == "stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            total = cursor.fetchone()[0]
            bot.answer_callback_query(call.id, f"📊 المشتركين: {total}", show_alert=True)
        
        elif call.data == "broadcast_msg":
            msg = bot.send_message(call.message.chat.id, "ارسل رسالة الإذاعة:")
            bot.register_next_step_handler(msg, send_broadcast, bot, cursor)
            
        # إضافة بقية الشروط (ban, unban, vip) هنا بنفس الطريقة
        bot.answer_callback_query(call.id)

def send_broadcast(message, bot, cursor):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for (u_id,) in users:
        try: bot.send_message(u_id, message.text)
        except: continue
    bot.send_message(message.chat.id, "✅ تمت الإذاعة.")
