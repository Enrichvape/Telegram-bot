import telebot
import os
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

user_data = {}

# START
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📦 Order", "💨 Flavour", "📞 Contact")

    bot.send_message(message.chat.id, "Welcome ke Rich Vape Shop 🔥", reply_markup=markup)

# MENU HANDLER
@bot.message_handler(func=lambda m: True)
def handle(message):
    chat_id = message.chat.id

    if message.text == "📦 Order":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Grape Ice", "Strawberry", "Mango", "⬅️ Back")

        bot.send_message(chat_id, "Pilih flavour:", reply_markup=markup)

    elif message.text in ["Grape Ice", "Strawberry", "Mango"]:
        user_data[chat_id] = {"flavour": message.text}

        bot.send_message(chat_id, f"Kau pilih {message.text}\nMasukkan nama:")

        bot.register_next_step_handler(message, get_name)

    elif message.text == "💨 Flavour":
        bot.send_message(chat_id, "Available:\n- Grape Ice\n- Strawberry\n- Mango")

    elif message.text == "📞 Contact":
        bot.send_message(chat_id, "Contact: 011-60879707")

    elif message.text == "⬅️ Back":
        start(message)

# STEP 1: NAME
def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text

    bot.send_message(chat_id, "Masukkan alamat:")
    bot.register_next_step_handler(message, get_address)

# STEP 2: ADDRESS
def get_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text

    data = user_data[chat_id]

    order_text = f"""
🔥 ORDER BARU 🔥
Nama: {data['name']}
Flavour: {data['flavour']}
Alamat: {data['address']}
"""

    # 👉 GANTI DENGAN USER ID TELEGRAM KAU
    OWNER_ID = 8299633855

    bot.send_message(OWNER_ID, order_text)
    bot.send_message(chat_id, "Order berjaya dihantar 🔥")
bot.send_message(OWNER_ID, "TEST SAMPAI TAK")

bot.infinity_polling()
