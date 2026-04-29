import telebot
import os
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

user_data = {}

# 👉 SETTING
OWNER_ID = 8299633855
WHATSAPP_NUMBER = "601160879707"
PRICE = 95

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

        image_url = "https://imgur.com/a/QqYVm0N"

        markup = types.InlineKeyboardMarkup()
        wa_link = f"https://wa.me/01160879707"
        markup.add(types.InlineKeyboardButton("📱 WhatsApp", url=wa_link))

        bot.send_photo(
            chat_id,
            image_url,
            caption=f"""
🔥 {message.text} (Flavour Pati)
💰 Harga: RM95
⭐ Sedap & padu

Masukkan nama:
""",
            reply_markup=markup
        )

        bot.register_next_step_handler(message, get_name)

    elif message.text == "💨 Flavour":
        bot.send_message(chat_id, f"""
🔥 FLAVOUR PATI 🔥
- Grape Ice
- Strawberry
- Mango

💰 RM95 sebotol
""")

    elif message.text == "📞 Contact":
        wa_link = f"https://wa.me/{WHATSAPP_NUMBER}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📱 WhatsApp", url=wa_link))

        bot.send_message(chat_id, "Klik bawah untuk contact 🔥", reply_markup=markup)

    elif message.text == "⬅️ Back":
        start(message)

# STEP 1
def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text

    bot.send_message(chat_id, "Masukkan alamat:")
    bot.register_next_step_handler(message, get_address)

# STEP 2
def get_address(message):
    chat_id = message.chat.id
    user_data[chat_id]["address"] = message.text

    data = user_data[chat_id]

    order_text = f"""
🔥 ORDER BARU 🔥
Nama: {data['name']}
Flavour: {data['flavour']}
Harga: RM{PRICE}
Alamat: {data['address']}
"""

    bot.send_message(OWNER_ID, order_text)
    bot.send_message(chat_id, "Order berjaya dihantar 🔥")

bot.infinity_polling()
