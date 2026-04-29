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
PRICE_PER_BOTTLE = 95
DELIVERY_SEMENANJUNG = 8
DELIVERY_SABAH_SARAWAK = 18

BANK_INFO = """Maybank
Nama: Shafirul Ridhzuan
No Akaun: 162040050328
Atau DuitNow / Touch n Go: 131442809630"""

FLAVOURS = ["Grape Ice", "Strawberry", "Mango", "Blueberry", "Watermelon"]

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
user_orders = {}   # Semua order

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
    reset_user(message.chat.id)
    bot.send_message(
        message.chat.id,
        "🔥 *Selamat datang ke Rich Vape Shop!* 🔥\n\n"
        "Pilih menu di bawah:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ================== ADMIN COMMANDS ==================
@bot.message_handler(commands=['myorders', 'orders', 'stats', 'broadcast', 'update'])
def admin_commands(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "Anda tiada akses.")
        return

    cmd = message.text.split()[0].lower()

    if cmd in ['/myorders', '/orders']:
        show_all_orders(message.chat.id, pending_only=(cmd == '/orders'))

    elif cmd == '/stats':
        total = sum(len(orders) for orders in user_orders.values())
        pending = sum(1 for orders in user_orders.values() for o in orders if o['status'] == "Pending")
        bot.send_message(OWNER_ID, f"📊 Statistik\n\nTotal Order: {total}\nPending: {pending}")

    elif cmd == '/broadcast':
        try:
            text = message.text.split(maxsplit=1)[1]
            sent = 0
            for chat_id in user_orders.keys():
                try:
                    bot.send_message(chat_id, f"📢 Pengumuman dari Admin:\n\n{text}")
                    sent += 1
                except:
                    pass
            bot.send_message(OWNER_ID, f"Broadcast berjaya dihantar kepada {sent} user.")
        except:
            bot.send_message(OWNER_ID, "Cara guna: `/broadcast Teks promo anda di sini`")

    elif cmd == '/update':
        try:
            _, order_id, new_status = message.text.split(maxsplit=2)
            updated = False
            for orders in user_orders.values():
                for order in orders:
                    if order['order_id'] == order_id:
                        old = order['status']
                        order['status'] = new_status.capitalize()
                        bot.send_message(OWNER_ID, f"✅ Order {order_id} diubah: {old} → {order['status']}")
                        try:
                            bot.send_message(order['chat_id'], f"🔄 Status order **#{order_id}** telah dikemaskini ke **{order['status']}**")
                        except:
                            pass
                        updated = True
                        break
            if not updated:
                bot.send_message(OWNER_ID, "Order ID tidak dijumpai.")
        except:
            bot.send_message(OWNER_ID, "Cara guna:\n`/update RVS1741234567 Paid`")

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

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

    elif text == "📋 Order Saya":
        show_user_orders(chat_id)

    elif text == "💨 Flavour":
        bot.send_message(chat_id, f"🔥 **Flavour Tersedia**\n\n" + "\n".join([f"• {f}" for f in FLAVOURS]) + f"\n\n💰 RM{PRICE_PER_BOTTLE} / botol", parse_mode="Markdown")

    elif text == "📞 Contact":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 WhatsApp Admin", url=f"https://wa.me/{WHATSAPP_NUMBER}"))
        bot.send_message(chat_id, "Hubungi admin:", reply_markup=markup)

    # Pilih Flavour
    elif text in FLAVOURS and user_state.get(chat_id) == State.CHOOSING_FLAVOUR:
        user_data[chat_id] = {"flavour": text, "price": PRICE_PER_BOTTLE, "chat_id": chat_id}
        user_state[chat_id] = State.ENTER_NAME
        bot.send_message(chat_id, f"Anda pilih: **{text}**\n\nMasukkan **Nama Penuh**:", parse_mode="Markdown", reply_markup=cancel_keyboard())

    # Order flow
    elif user_state.get(chat_id) == State.ENTER_NAME:
        user_data[chat_id]["name"] = text
        user_state[chat_id] = State.ENTER_PHONE
        bot.send_message(chat_id, "Masukkan **No. Telefon** (contoh: 60123456789):", parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_PHONE:
        phone = text.replace(" ", "").replace("-", "")
        if len(phone) < 10 or not phone.startswith("60"):
            bot.send_message(chat_id, "❌ Nombor telefon tidak sah. Sila masukkan semula.")
            return
        user_data[chat_id]["phone"] = phone
        user_state[chat_id] = State.ENTER_ADDRESS
        bot.send_message(chat_id, "Masukkan **Alamat Penghantaran** lengkap (sebut negeri kalau Sabah/Sarawak):", reply_markup=cancel_keyboard())

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
            bot.send_message(chat_id, "Sila hantar **gambar** bukti bayaran.")

    else:
        bot.send_message(chat_id, "Gunakan butang menu atau ikut arahan di atas.")

# ================== HELPER FUNCTIONS ==================
def get_delivery_fee(address):
    addr_lower = address.lower()
    if any(word in addr_lower for word in ["sabah", "sarawak", "kota kinabalu", "kuching", "labuan"]):
        return DELIVERY_SABAH_SARAWAK
    return DELIVERY_SEMENANJUNG

def show_confirmation(chat_id):
    data = user_data[chat_id]
    delivery = get_delivery_fee(data["address"])
    total = data["price"] + delivery

    text = f"""
🔥 **KONFIRMASI ORDER**

Flavour     : {data['flavour']}
Harga Barang: RM{data['price']}
Delivery    : RM{delivery} ({'Sabah/Sarawak' if delivery > 10 else 'Semenanjung'})
**Total     : RM{total}**

Nama        : {data['name']}
Telefon     : {data['phone']}
Alamat      : {data['address']}

Balas *YA* jika betul.
"""
    bot.send_message(chat_id, text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())

def create_order(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    delivery = get_delivery_fee(data["address"])
    total = data["price"] + delivery
    order_id = f"RVS{int(datetime.now().timestamp())}"

    order = {
        "order_id": order_id,
        "flavour": data['flavour'],
        "price": data['price'],
        "delivery": delivery,
        "total": total,
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
    bot.send_message(OWNER_ID, f"""
🔥 **ORDER BARU** #{order_id}

Nama     : {data['name']}
Flavour  : {data['flavour']}
Total    : RM{total} (incl. delivery RM{delivery})
Telefon  : {data['phone']}
Alamat   : {data['address']}
Tarikh   : {order['date']}
""")

    # Reply ke customer
    bot.send_message(
        chat_id,
        f"✅ *Order #{order_id} berjaya dihantar!*\n\n"
        f"**Jumlah yang perlu dibayar: RM{total}**\n\n"
        f"Sila bayar ke:\n{BANK_INFO}\n\n"
        f"Selepas bayar, hantar gambar bukti bayaran di sini.",
        parse_mode="Markdown"
    )

    user_state[chat_id] = State.WAITING_PAYMENT_PROOF

def handle_payment_proof(message):
    chat_id = message.chat.id
    latest_order = user_orders[chat_id][-1] if user_orders.get(chat_id) else None
    order_id = latest_order['order_id'] if latest_order else "Unknown"

    bot.forward_message(OWNER_ID, chat_id, message.message_id)
    bot.send_message(OWNER_ID, f"💰 Bukti bayaran diterima untuk Order #{order_id}")

    bot.send_message(chat_id, "✅ Bukti bayaran telah dihantar kepada admin.\nAdmin akan semak dan update status secepat mungkin. Terima kasih! 🔥")

    reset_user(chat_id)
    bot.send_message(chat_id, "Kembali ke menu utama:", reply_markup=main_keyboard())

def show_user_orders(chat_id):
    if not user_orders.get(chat_id):
        bot.send_message(chat_id, "Anda belum ada order lagi.")
        return

    text = "📋 **Order Saya**\n\n"
    for order in user_orders[chat_id]:
        text += f"🔖 `{order['order_id']}` — {order['flavour']}\n"
        text += f"Status : **{order['status']}**\n"
        text += f"Total  : RM{order['total']}\n"
        text += f"Tarikh : {order['date']}\n\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

def show_all_orders(chat_id, pending_only=False):
    if not user_orders:
        bot.send_message(chat_id, "Tiada order lagi.")
        return
    text = "📋 **Semua Order**\n\n" if not pending_only else "📋 **Order Pending**\n\n"
    for cid, orders in user_orders.items():
        for o in orders:
            if pending_only and o['status'] != "Pending":
                continue
            text += f"`{o['order_id']}` | {o['flavour']} | {o['status']} | RM{o['total']}\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

def reset_user(chat_id):
    user_data[chat_id] = {}
    user_state[chat_id] = State.IDLE

# ================== RUN BOT ==================
print("🚀 Rich Vape Shop Bot (dengan Delivery Fee & Admin Panel) sedang berjalan...")
bot.infinity_polling()
