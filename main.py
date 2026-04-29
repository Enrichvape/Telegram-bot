import telebot
import os
from telebot import types
from datetime import datetime
from enum import Enum

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================== SETTINGS ==================
OWNER_ID = 8299633855
WHATSAPP_NUMBER = "601160879707"
PRICE = 95

# States
class State(Enum):
    IDLE = 0
    CHOOSING_FLAVOUR = 1
    ENTER_NAME = 2
    ENTER_PHONE = 3
    ENTER_ADDRESS = 4
    CONFIRM_ORDER = 5

user_data = {}      # Simpan data order sementara
user_state = {}     # Simpan state user
user_orders = {}    # Simpan senarai order setiap user (chat_id: list of orders)

FLAVOURS = ["Grape Ice", "Strawberry", "Mango", "Blueberry", "Watermelon"]  # Tambah flavour di sini

# ================== KEYBOARDS ==================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Buat Order", "📋 Order Saya")
    markup.add("💨 Flavour", "📞 Contact")
    return markup

def flavour_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for i in range(0, len(FLAVOURS), 2):
        row = FLAVOURS[i:i+2]
        markup.add(*row)
    markup.add("⬅️ Kembali")
    return markup

def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Batal")
    return markup

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    user_state[chat_id] = State.IDLE
    
    welcome_text = "🔥 *Selamat datang ke Rich Vape Shop!* 🔥\n\n" \
                   "Pilih menu di bawah untuk mula:"
    
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if text == "❌ Batal":
        reset_user(chat_id)
        bot.send_message(chat_id, "✅ Order dibatalkan.", reply_markup=main_keyboard())
        return

    if text == "⬅️ Kembali":
        reset_user(chat_id)
        start(message)
        return

    if text == "📦 Buat Order":
        user_state[chat_id] = State.CHOOSING_FLAVOUR
        bot.send_message(chat_id, "Pilih flavour:", reply_markup=flavour_keyboard())

    elif text == "💨 Flavour":
        flavours_list = "\n".join([f"• {f}" for f in FLAVOURS])
        bot.send_message(chat_id, f"🔥 **Flavour Tersedia**\n\n{flavours_list}\n\n💰 RM{PRICE} / botol", parse_mode="Markdown")

    elif text == "📞 Contact":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 WhatsApp Admin", url=f"https://wa.me/{WHATSAPP_NUMBER}"))
        bot.send_message(chat_id, "Hubungi admin terus:", reply_markup=markup)

    elif text == "📋 Order Saya":
        show_user_orders(chat_id)

    # Pilih Flavour
    elif text in FLAVOURS and user_state.get(chat_id) == State.CHOOSING_FLAVOUR:
        user_data[chat_id] = {"flavour": text, "price": PRICE}
        user_state[chat_id] = State.ENTER_NAME
        bot.send_message(chat_id, f"Anda pilih: **{text}**\n\nSila masukkan **Nama Penuh**:", 
                        parse_mode="Markdown", reply_markup=cancel_keyboard())

    # Step-by-step order
    elif user_state.get(chat_id) == State.ENTER_NAME:
        user_data[chat_id]["name"] = text
        user_state[chat_id] = State.ENTER_PHONE
        bot.send_message(chat_id, "Masukkan **No. Telefon** (contoh: 60123456789):", 
                        parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_PHONE:
        phone = text.replace(" ", "").replace("-", "")
        if len(phone) < 10 or not phone.startswith("60"):
            bot.send_message(chat_id, "❌ Nombor telefon tidak sah. Sila masukkan semula (contoh: 60123456789)")
            return
        user_data[chat_id]["phone"] = phone
        user_state[chat_id] = State.ENTER_ADDRESS
        bot.send_message(chat_id, "Masukkan **Alamat Penghantaran** lengkap:", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_ADDRESS:
        user_data[chat_id]["address"] = text
        user_state[chat_id] = State.CONFIRM_ORDER
        show_confirmation(chat_id)

    elif user_state.get(chat_id) == State.CONFIRM_ORDER and text.upper() in ["YA", "YES", "OK", "HANTAR"]:
        save_and_send_order(message)
    else:
        bot.send_message(chat_id, "Sila ikut arahan atau tekan butang menu.")

# ================== HELPER FUNCTIONS ==================
def show_confirmation(chat_id):
    data = user_data[chat_id]
    text = f"""
🔥 **KONFIRMASI ORDER** 🔥

Flavour   : {data['flavour']}
Harga     : RM{data['price']}
Nama      : {data['name']}
Telefon   : {data['phone']}
Alamat    : {data['address']}

Balas *YA* jika semua betul.
"""
    bot.send_message(chat_id, text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())

def save_and_send_order(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    
    order_id = f"RVS{int(datetime.now().timestamp())}"
    
    order_info = {
        "order_id": order_id,
        "flavour": data['flavour'],
        "price": data['price'],
        "name": data['name'],
        "phone": data['phone'],
        "address": data['address'],
        "status": "Pending",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    # Simpan order user
    if chat_id not in user_orders:
        user_orders[chat_id] = []
    user_orders[chat_id].append(order_info)

    # Hantar ke Owner
    admin_text = f"""
🔥 **ORDER BARU** #{order_id}

Nama     : {data['name']}
Flavour  : {data['flavour']}
Harga    : RM{data['price']}
Telefon  : {data['phone']}
Alamat   : {data['address']}
Tarikh   : {order_info['date']}
User ID  : {chat_id}
    """
    bot.send_message(OWNER_ID, admin_text)

    # Reply ke customer
    bot.send_message(chat_id, f"""
✅ *Order #{order_id} berjaya dihantar!*

Admin akan hubungi anda melalui telefon/whatsApp dalam masa terdekat.
Terima kasih kerana berbelanja di Rich Vape Shop 🔥
""", parse_mode="Markdown")

    reset_user(chat_id)
    bot.send_message(chat_id, "Kembali ke menu utama:", reply_markup=main_keyboard())

def show_user_orders(chat_id):
    if chat_id not in user_orders or not user_orders[chat_id]:
        bot.send_message(chat_id, "Anda belum ada sebarang order lagi.")
        return

    text = "📋 **Senarai Order Anda**\n\n"
    for order in user_orders[chat_id]:
        text += f"🔖 Order ID: `{order['order_id']}`\n"
        text += f"Flavour: {order['flavour']}\n"
        text += f"Status : {order['status']}\n"
        text += f"Tarikh : {order['date']}\n\n"

    bot.send_message(chat_id, text, parse_mode="Markdown")

def reset_user(chat_id):
    user_data[chat_id] = {}
    user_state[chat_id] = State.IDLE

# ================== RUN BOT ==================
print("🚀 Rich Vape Shop Bot is running...")
bot.infinity_polling()
