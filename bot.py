import telebot
from telebot import types
import sqlite3

# توكن البوت والأيدي الخاص بك
TOKEN = "8484153342:AAGjKMq5VfK55ShWDOZRxfcfdcYV3hGG85s"
ADMIN_GROUP_ID = 1114444431  # الأيدي الخاص بك لاستلام الطلبات

bot = telebot.TeleBot(TOKEN)

# إعداد قاعدة البيانات المحلية لتخزين رصيد المستخدمين
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_balance(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]
    else:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        conn.close()
        return 0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# لوحة المفاتيح الرئيسية أسفل الشاشة
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("شحن رصيد 💳", "رصيدي 💰")
    markup.add("الأسعار 💵")
    return markup

# أزرار الباقات
def get_packages_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1 Link - 10 EGP", callback_data="pkg_1"))
    markup.add(types.InlineKeyboardButton("2 Link - 15 EGP", callback_data="pkg_2"))
    markup.add(types.InlineKeyboardButton("6 Link - 45 EGP", callback_data="pkg_6"))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    get_user_balance(message.from_user.id)
    bot.send_message(message.chat.id, "أهلاً بيك 👋", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: message.text == "رصيدي 💰")
def check_balance(message):
    balance = get_user_balance(message.from_user.id)
    bot.send_message(message.chat.id, f"رصيدك: {balance} 🪙")

@bot.message_handler(func=lambda message: message.text == "الأسعار 💵")
def show_prices(message):
    prices_text = (
        "📢 أسعار الشحن:\n\n"
        "🔹 1 Link = 10 EGP\n"
        "🔹 2 Link = 15 EGP\n"
        "🔹 6 Link = 45 EGP\n"
        "🔹 12 Link = 90 EGP\n"
        "🔹 24 Link = 180 EGP\n"
        "🔹 36 Link = 270 EGP\n"
        "🔹 48 Link = 360 EGP\n"
        "🔹 60 Link = 450 EGP\n"
        "🔹 120 Link = 900 EGP\n\n"
        "📢 تنبيه:\n"
        "🔹 ١ رصيد بيحسب ٣٠ دعوة بس\n"
        "🔹 في حاله عايز تكمل لـ ٦٠ دعوة هيخصم ٢ رصيد"
    )
    bot.send_message(message.chat.id, prices_text)

@bot.message_handler(func=lambda message: message.text == "شحن رصيد 💳")
def top_up_start(message):
    bot.send_message(message.chat.id, "اختر الباقة 📦", reply_markup=get_packages_keyboard())

user_states = {}

@bot.callback_query_handler(func=lambda call: call.data.startswith("pkg_"))
def process_package(call):
    user_states[call.from_user.id] = {"package": call.data}
    msg_text = (
        "📱 حول على رقم فودافون كاش:\n\n"
        "<code>01068299537</code>\n\n"
        "ثم ابعت الرقم اللي حولت منه:"
    )
    bot.send_message(call.message.chat.id, msg_text, parse_mode="HTML")
    user_states[call.from_user.id]["step"] = "waiting_for_phone"
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get("step") == "waiting_for_phone")
def receive_phone(message):
    user_states[message.from_user.id]["phone"] = message.text
    user_states[message.from_user.id]["step"] = "waiting_for_screenshot"
    bot.send_message(message.chat.id, "📸 ابعت صورة الوصل (سكرين شوت التحويل):")

@bot.message_handler(content_types=['photo'])
def receive_screenshot(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    if state.get("step") == "waiting_for_screenshot":
        phone = state.get("phone")
        package = state.get("package")
        photo_id = message.photo[-1].file_id

        admin_msg = (
            f"🔔 طلب شحن جديد!\n"
            f"👤 المستخدم: {message.from_user.full_name} (`{user_id}`)\n"
            f"📞 رقم التحويل: `{phone}`\n"
            f"📦 الباقة: {package}"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}_1"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        )

        bot.send_photo(ADMIN_GROUP_ID, photo_id, caption=admin_msg, reply_markup=markup, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ تم إرسال طلبك بنجاح\n⏳ في انتظار تأكيد الدفع\nإذا تأخر التأكيد تواصل مع الدعم")
        user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def handle_admin_decision(call):
    parts = call.data.split("_")
    action = parts[0]
    user_id = int(parts[1])

    if action == "accept":
        amount = int(parts[2])
        update_user_balance(user_id, amount)
        bot.send_message(user_id, f"✅ تم قبول طلب الشحن\n🎁 تمت إضافة {amount} رصيد")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n✅ **تم قبول الطلب وإضافة الرصيد**", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "تم القبول بنجاح!")
    elif action == "reject":
        bot.send_message(user_id, "❌ عذراً، تم رفض طلب الشحن الخاص بك. يرجى التأكد من صحة البيانات.")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ **تم رفض الطلب**", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "تم الرفض.")

bot.infinity_polling()
