import telebot
from telebot import types
import io

TOKEN = "8434751648:AAHxdICxD01RUkv0LeS_LRbZI1B-zOxd4mo"
bot = telebot.TeleBot(TOKEN)

user_data = {}
moderators = []
waiting_for_receipt = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    register_button = types.KeyboardButton("📝 Конкурс")
    setting_button = types.KeyboardButton("⚙ Настройки")
    markup.add(register_button, setting_button)
    bot.send_message(
        message.chat.id,
        "<b>Привет!</b>\n\nДля участия в конкурсе нажимай на кнопку <b>Конкурс</b>.\nЧтобы узнать что я еще умею нажми на кнопку <b>Настройки</b>",
        reply_markup=markup, 
        parse_mode='HTML'
    )

@bot.message_handler(func=lambda message: message.text == "📝 Конкурс")
def register(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        msg = bot.send_message(message.chat.id, "Введите ваше имя:")
        bot.register_next_step_handler(msg, process_name)
    else:
        bot.send_message(message.chat.id, "✅ Вы уже зарегистрированы!")

def validate_phone(phone):
    return phone.startswith('+') and phone[1:].isdigit() and 10 <= len(phone) <= 15

def process_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    user_data[user_id] = {
        "name": name, 
        "phone": None, 
        "chances": 0, 
        "receipt": None, 
        "approved_receipts": 0
    }
    msg = bot.send_message(message.chat.id, "📞 Введите ваш номер телефона (формат: +79123456789):")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    
    if not validate_phone(phone):
        msg = bot.send_message(message.chat.id, "❌ Некорректный номер телефона. Пожалуйста, введите ваш номер телефона заново:")
        bot.register_next_step_handler(msg, process_phone)
        return
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    setting_button = types.KeyboardButton("⚙ Настройки")
    markup.add(setting_button)
    user_data[user_id]['phone'] = phone
    bot.send_message(message.chat.id, "🎉 Вы зарегистрированы! Отправьте мне ваш чек.", reply_markup=markup)
    waiting_for_receipt[user_id] = True

def notify_moderators(user_id, receipt_file):
    for moderator_id in moderators:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        approve_button = types.KeyboardButton("✅ Одобрить")
        reject_button = types.KeyboardButton("❌ Отклонить")
        cancel_button = types.KeyboardButton("🔙 Отмена")
        markup.add(approve_button, reject_button, cancel_button)

        caption = f"📥 Пользователь {user_data[user_id]['name']} (ID: {user_id}) отправил чек на модерацию."
        bot.send_photo(moderator_id, receipt_file, caption=caption, reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def receive_receipt(message):
    user_id = message.from_user.id
    
    if user_id in waiting_for_receipt and waiting_for_receipt[user_id]:
        photo_id = message.photo[-1].file_id
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)

        receipt_file = io.BytesIO(downloaded_file)
        receipt_file.name = f"receipt_{user_id}.jpg" 

        user_data[user_id]['receipt'] = receipt_file 
        notify_moderators(user_id, receipt_file) 
        
        bot.send_message(message.chat.id, "✔️ Чек получен! Ожидайте модерации.")
        waiting_for_receipt[user_id] = False
    else:
        if user_id in waiting_for_receipt:
            if not waiting_for_receipt[user_id]:
                bot.send_message(message.chat.id, "⚠️ Вы уже отправили чек. Ожидайте ответа модератора.")
            else:
                bot.send_message(message.chat.id, "❌ Вы не находитесь в процессе отправки чека.")
        else:
            bot.send_message(message.chat.id, "❌ Вы не находитесь в процессе отправки чека. Пожалуйста, отправьте ваш чек.")

@bot.message_handler(func=lambda message: message.text in ["✅ Одобрить", "❌ Отклонить", "🔙 Отмена"])
def handle_moderation(message):
    moderator_id = message.from_user.id
    
    if moderator_id in moderators:
        try:
            caption = message.reply_to_message.caption
            user_id_str = caption.split("(ID: ")[1].split(")")[0]
            user_id = int(user_id_str)

            if message.text == "✅ Одобрить":
                user_data[user_id]['chances'] += 4
                user_data[user_id]['approved_receipts'] += 1
                bot.send_message(user_id, f"🎉 Ваш чек принят! У вас теперь {user_data[user_id]['chances']} шанса(ов) в конкурсе.")
                bot.send_message(moderator_id, f"✅ Чек пользователя {user_data[user_id]['name']} (ID: {user_id}) принят.")
                
                waiting_for_receipt[user_id] = True

            elif message.text == "❌ Отклонить":
                bot.send_message(user_id, "❌ Извините, ваш чек не принят.")
                bot.send_message(moderator_id, f"❌ Чек пользователя {user_data[user_id]['name']} (ID: {user_id}) отклонён.")

            elif message.text == "🔙 Отмена":
                bot.send_message(user_id, "❌ Вы отменили отправку чека.")
                bot.send_message(moderator_id, f"🔙 Пользователь {user_data[user_id]['name']} (ID: {user_id}) отменил отправку чека.")
                waiting_for_receipt[user_id] = True

        except Exception as e:
            bot.send_message(moderator_id, f"🚨 Произошла ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "📊 Таблица")
def export_users(message):
    if message.from_user.id in moderators:
        result = "📋 Список участников:\n"
        for user_id, data in user_data.items():
            result += f"👤 Имя: {data['name']}, 📞 Телефон: {data['phone']}, 🎟️ Шансы: {data['chances']}, ✅ Одобренные чеки: {data['approved_receipts']}\n"
        bot.send_message(message.chat.id, result)
    else:
        bot.send_message(message.chat.id, "🚫 У вас нет прав для этой команды.")

@bot.message_handler(func=lambda message: message.text == "🧾 Мои чеки")
def my_receipts(message):
    user_id = message.from_user.id
    if user_id in user_data:
        approved_count = user_data[user_id]['approved_receipts']
        bot.send_message(message.chat.id, f"🧾 Количество одобренных чеков: {approved_count}")
    else:
        bot.send_message(message.chat.id, "🚫 Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь с помощью команды Конкурс.")

@bot.message_handler(func=lambda message: message.text == "⚙ Настройки")
def menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    my_receipts_button = types.KeyboardButton("🧾 Мои чеки")
    markup.add(my_receipts_button)
    
    bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=markup)

@bot.message_handler(commands=['grant_moderator'])
def grant_moderator(message):
    moderator_id = message.from_user.id
    
    if moderator_id in moderators:
        try:
            msg = bot.send_message(message.chat.id, "Введите ID пользователя для выдачи модерки:")
            bot.register_next_step_handler(msg, process_grant_moderator)
        except Exception as e:
            bot.send_message(moderator_id, f"🚨 Произошла ошибка: {str(e)}")
    else:
        bot.send_message(message.chat.id, "🚫 У вас нет прав для этой команды.")

def process_grant_moderator(message):
    moderator_id = message.from_user.id
    user_id = message.text.strip()
    
    if user_id.isdigit():
        user_id = int(user_id)
        
        if user_id not in moderators:
            moderators.append(user_id)
            bot.send_message(moderator_id, f"✅ Пользователь с ID {user_id} теперь является модератором.")
            bot.send_message(user_id, "🎉 Вы были назначены модератором!")
        else:
            bot.send_message(moderator_id, "🚫 Этот пользователь уже является модератором.")
    else:
        bot.send_message(moderator_id, "❌ Введён некорректный ID. Пожалуйста, введите числовой ID пользователя.")

moderators.append(1121163791) 

try:
    bot.polling()
except KeyboardInterrupt:
    print("Бот остановлен.")

