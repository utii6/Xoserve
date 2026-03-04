import random
from telebot import types

# 1. دالة فحص المستخدم (التي يطلبها سطر 141 في bot.py)
def check_user(bot, message, get_db_connection):
    uid = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # التأكد هل المستخدم مسجل فعلاً في القاعدة؟
    cursor.execute('SELECT user_id FROM users WHERE user_id=%s', (uid,))
    user_exists = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if user_exists:
        return True  # المستخدم مسجل، اسمح له بالدخول (سيكمل تنفيذ دالة start)
    else:
        # المستخدم جديد، استخرج معرف الداعي إن وجد ثم أرسل الكابتشا
        args = message.text.split()
        referrer = 0
        if len(args) > 1 and args[1].isdigit():
            referrer = int(args[1])
            
        send_captcha(bot, message, referrer)
        return False # توقف هنا ولا تكمل دالة start حتى يحل الكابتشا

# 2. دالة إرسال اختبار التحقق
def send_captcha(bot, message, referrer):
    correct_code = str(random.randint(10000, 99999))
    wrong_1 = str(random.randint(10000, 99999))
    wrong_2 = str(random.randint(10000, 99999))
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    # نضع الرقم الصحيح والداعي في الكول باك
    btn_correct = types.InlineKeyboardButton(correct_code, callback_data=f"v_{correct_code}_{correct_code}_{referrer}")
    btn_w1 = types.InlineKeyboardButton(wrong_1, callback_data=f"v_{wrong_1}_{correct_code}_{referrer}")
    btn_w2 = types.InlineKeyboardButton(wrong_2, callback_data=f"v_{wrong_2}_{correct_code}_{referrer}")
    
    btns = [btn_correct, btn_w1, btn_w2]
    random.shuffle(btns)
    markup.add(*btns)
    
    captcha_text = (f"♨️ | *يجب التحقق أنك لست روبوت*\n"
                    f"✅ | *اختر الكود من الزر حتى نعرفك* : `{correct_code}`")
    
    return bot.send_message(message.chat.id, captcha_text, reply_markup=markup, parse_mode="Markdown")

# 3. دالة معالجة الإجابة وتسجيل المستخدم
def process_captcha(bot, call, get_db_connection, show_main_menu):
    uid = call.from_user.id
    parts = call.data.split("_") # v_pressed_correct_ref
    pressed, correct, ref_id = parts[1], parts[2], int(parts[3])
    
    if pressed == correct:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التأكد أن المستخدم غير موجود مسبقاً قبل إضافة النقاط للداعي
        cursor.execute('SELECT user_id FROM users WHERE user_id=%s', (uid,))
        if not cursor.fetchone():
            # إضافة نقطة للداعي إذا وجد وكان شخصاً آخر
            if ref_id != 0 and ref_id != uid:
                cursor.execute('UPDATE users SET points = points + 1 WHERE user_id=%s', (ref_id,))
                try: 
                    bot.send_message(ref_id, "🔔💰 | *حصلت على 1 نقطة لدخول مستخدم جديد*!")
                except: 
                    pass
            
            # تسجيل المستخدم الجديد في القاعدة
            cursor.execute('INSERT INTO users (user_id, referred_by, username) VALUES (%s, %s, %s)', 
                           (uid, ref_id, call.from_user.username))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        # حذف رسالة الكابتشا وإظهار القائمة الرئيسية
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message) 
    else:
        bot.answer_callback_query(call.id, "❌ يمعود الكود خطأ! حاول بعد /start", show_alert=True)
