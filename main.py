import telebot
import os
from telebot import types
from datetime import datetime
from enum import Enum

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================== SETTINGS ==================
OWNER_ID = 8299633855
WHATSAPP_NUMBER = "601160879707"   # Tukar ikut nombor anda
PRICE = 95
BANK_INFO = "Maybank\nNama: Shafirul Ridhzuan Bin Abd Halit\nNo Akaun: 162040050328\nAtau DuitNow ke 131442809630"

# States
class State(Enum):
    IDLE = 0
    CHOOSING_FLAVOUR = 1
    ENTER_NAME = 2
    ENTER_PHONE = 3
    ENTER_ADDRESS = 4
    CONFIRM_ORDER = 5
    WAITING_PAYMENT_PROOF = 6

user_data = {}
user_state = {}
user_orders = {}   # Simpan semua order setiap user

FLAVOURS = ["Grape Ice", "Strawberry", "Mango", "Blueberry", "Watermelon"]

# ================== KEYBOARDS ==================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Buat Order", "📋 Order Saya")
    markup.add("💨 Flavour", "📞 Contact")
    return markup

def flavour_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for i in range(0, len(FLAVOURS), 2):
        markup.add(*FLAVOURS[i:i+2])
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
    reset_user(chat_id)
    bot.send_message(
        chat_id,
        "🔥 *Selamat datang ke Rich Vape Shop!* 🔥\n\n"
        "Pilih menu di bawah untuk mula order.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ================== ADMIN COMMANDS ==================
@bot.message_handler(commands=['myorders'])
def admin_orders(message):
    if message.chat.id != OWNER_ID:
        return
    if not user_orders:
        bot.send_message(OWNER_ID, "Tiada order lagi.")
        return
    
    text = "📋 **Semua Order**\n\n"
    for chat_id, orders in user_orders.items():
        for order in orders:
            text += f"🔖 `{order['order_id']}` | {order['flavour']} | {order['status']}\n"
            text += f"Nama: {order['name']} | {order['phone']}\n\n"
    bot.send_message(OWNER_ID, text, parse_mode="Markdown")

@bot.message_handler(commands=['update'])
def update_status(message):
    if message.chat.id != OWNER_ID:
        return
    try:
        _, order_id, new_status = message.text.split(maxsplit=2)
        # Cari order dan update (simple search)
        for orders in user_orders.values():
            for order in orders:
                if order['order_id'] == order_id:
                    old_status = order['status']
                    order['status'] = new_status.capitalize()
                    bot.send_message(OWNER_ID, f"✅ Order {order_id} diubah dari {old_status} → {new_status}")
                    # Optional: Notify customer
                    try:
                        bot.send_message(order['chat_id'], f"🔄 Status order anda **#{order_id}** telah dikemaskini ke: **{new_status}**")
                    except:
                        pass
                    return
        bot.send_message(OWNER_ID, "Order ID tidak dijumpai.")
    except:
        bot.send_message(OWNER_ID, "Cara guna: `/update RVS123456789 Paid`")

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if text == "❌ Batal":
        reset_user(chat_id)
        bot.send_message(chat_id, "Order dibatalkan.", reply_markup=main_keyboard())
        return

    if text == "⬅️ Kembali":
        reset_user(chat_id)
        start(message)
        return

    if text == "📦 Buat Order":
        user_state[chat_id] = State.CHOOSING_FLAVOUR
        bot.send_message(chat_id, "Pilih flavour:", reply_markup=flavour_keyboard())

    elif text == "📋 Order Saya":
        show_user_orders(chat_id)

    elif text == "💨 Flavour":
        flavours_list = "\n".join([f"• {f}" for f in FLAVOURS])
        bot.send_message(chat_id, f"🔥 **Flavour Tersedia**\n\n{flavours_list}\n\n💰 RM{PRICE} / botol", parse_mode="Markdown")

    elif text == "📞 Contact":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 WhatsApp Admin", url=f"https://wa.me/{WHATSAPP_NUMBER}"))
        bot.send_message(chat_id, "Hubungi admin:", reply_markup=markup)

    # Pilih Flavour
    elif text in FLAVOURS and user_state.get(chat_id) == State.CHOOSING_FLAVOUR:
        user_data[chat_id] = {"flavour": text, "price": PRICE, "chat_id": chat_id}
        user_state[chat_id] = State.ENTER_NAME
        bot.send_message(chat_id, f"Anda pilih: **{text}**\n\nMasukkan **Nama Penuh**:", 
                        parse_mode="Markdown", reply_markup=cancel_keyboard())

    # Order Steps
    elif user_state.get(chat_id) == State.ENTER_NAME:
        user_data[chat_id]["name"] = text
        user_state[chat_id] = State.ENTER_PHONE
        bot.send_message(chat_id, "Masukkan **No. Telefon** (contoh: 60123456789):", parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_PHONE:
        phone = text.replace(" ", "").replace("-", "")
        if len(phone) < 10 or not phone.startswith("60"):
            bot.send_message(chat_id, "❌ Nombor tidak sah. Contoh: 60123456789")
            return
        user_data[chat_id]["phone"] = phone
        user_state[chat_id] = State.ENTER_ADDRESS
        bot.send_message(chat_id, "Masukkan **Alamat Penghantaran** lengkap:", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_ADDRESS:
        user_data[chat_id]["address"] = text
        user_state[chat_id] = State.CONFIRM_ORDER
        show_confirmation(chat_id)

    elif user_state.get(chat_id) == State.CONFIRM_ORDER and text.upper() in ["YA", "YES", "OK", "HANTAR"]:
        create_order(message)

    elif user_state.get(chat_id) == State.WAITING_PAYMENT_PROOF:
        if message.photo:
            handle_payment_proof(message)
        else:
            bot.send_message(chat_id, "Sila hantar gambar bukti bayaran.")

    else:
        bot.send_message(chat_id, "Sila gunakan butang menu atau ikut arahan.")

# ================== HELPER FUNCTIONS ==================
def show_confirmation(chat_id):
    data = user_data[chat_id]
    text = f"""
🔥 **KONFIRMASI ORDER**

Flavour : {data['flavour']}
Harga   : RM{data['price']}
Nama    : {data['name']}
Telefon : {data['phone']}
Alamat  : {data['address']}

Balas *YA* jika betul.
"""
    bot.send_message(chat_id, text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())

def create_order(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    order_id = f"RVS{int(datetime.now().timestamp())}"

    order = {
        "order_id": order_id,
        "flavour": data['flavour'],
        "price": data['price'],
        "name": data['name'],
        "phone": data['phone'],
        "address": data['address'],
        "status": "Pending",
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "chat_id": chat_id
    }

    if chat_id not in user_orders:
        user_orders[chat_id] = []
    user_orders[chat_id].append(order)

    # Hantar ke Admin
    admin_text = f"""
🔥 **ORDER BARU** #{order_id}

Nama     : {data['name']}
Flavour  : {data['flavour']}
Harga    : RM{data['price']}
Telefon  : {data['phone']}
Alamat   : {data['address']}
Tarikh   : {order['date']}
    """
    bot.send_message(OWNER_ID, admin_text)

    # Reply ke customer
    bot.send_message(
        chat_id,
        f"✅ *Order #{order_id} berjaya dihantar!*\n\n"
        f"Sila buat bayaran ke:\n{BANK_INFO}\n\n"
        f"Selepas bayar, hantar gambar bukti bayaran di sini.",
        parse_mode="Markdown"
    )

    user_state[chat_id] = State.WAITING_PAYMENT_PROOF

def handle_payment_proof(message):
    chat_id = message.chat.id
    order_id = user_orders[chat_id][-1]["order_id"] if user_orders.get(chat_id) else "Unknown"

    # Hantar gambar ke admin
    bot.forward_message(OWNER_ID, chat_id, message.message_id)
    bot.send_message(OWNER_ID, f"💰 Bukti bayaran untuk Order #{order_id} dari {chat_id}")

    bot.send_message(
        chat_id,
        "✅ Bukti bayaran anda telah dihantar kepada admin.\n"
        "Admin akan semak dan update status order anda secepat mungkin. Terima kasih! 🔥"
    )

    reset_user(chat_id)
    bot.send_message(chat_id, "Kembali ke menu utama:", reply_markup=main_keyboard())

def show_user_orders(chat_id):
    if chat_id not in user_orders or not user_orders[chat_id]:
        bot.send_message(chat_id, "Anda belum ada order lagi.")
        return

    text = "📋 **Order Saya**\n\n"
    for order in user_orders[chat_id]:
        text += f"🔖 Order ID: `{order['order_id']}`\n"
        text += f"Flavour : {order['flavour']}\n"
        text += f"Status  : **{order['status']}**\n"
        text += f"Tarikh  : {order['date']}\n\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

def reset_user(chat_id):
    user_data[chat_id] = {}
    user_state[chat_id] = State.IDLE

# ================== RUN ==================
print("🚀 Rich Vape Shop Bot dengan Bukti Bayaran & Status Order sedang berjalan...")
bot.infinity_polling()
