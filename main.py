import telebot
import os
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from telebot import types
import pytz
import random
from enum import Enum

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================== SETTINGS ==================
OWNER_ID = 8299633855
WHATSAPP_NUMBER = "601160879707"
PRICE_PER_BOTTLE = 95
DELIVERY_SEMENANJUNG = 8
DELIVERY_SABAH_SARAWAK = 18

BANK_INFO = """🏦 **Maybank**
Nama: Shafirul Ridhzuan
No Akaun: 162040050328

💸 **DuitNow / Touch n Go**: 131442809630"""

FLAVOURS = ["Grape Ice", "Strawberry", "Mango", "Blueberry", "Watermelon"]

MY_TZ = pytz.timezone('Asia/Kuala_Lumpur')

# ================== DATABASE ==================
DB_NAME = "orders.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            chat_id INTEGER,
            flavour TEXT,
            quantity INTEGER,
            subtotal REAL,
            delivery REAL,
            total REAL,
            name TEXT,
            phone TEXT,
            address TEXT,
            status TEXT,
            date TEXT,
            created_at TEXT,
            payment_proof TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_order_to_db(order):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO orders 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        order['order_id'], order['chat_id'], order['flavour'], order['quantity'],
        order['subtotal'], order['delivery'], order['total'], order['name'],
        order['phone'], order['address'], order['status'], order['date'],
        order['created_at'], order.get('payment_proof')
    ))
    conn.commit()
    conn.close()

def update_order_status_in_db(order_id, new_status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))
    conn.commit()
    conn.close()

def get_pending_orders():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT order_id, chat_id, created_at FROM orders WHERE status = 'Pending'")
    rows = cur.fetchall()
    conn.close()
    return rows

# ================== PRODUCT IMAGES ==================
PRODUCT_IMAGES = {f: None for f in FLAVOURS}

def load_product_photos():
    global PRODUCT_IMAGES
    try:
        if os.path.exists("product_photos.json"):
            with open("product_photos.json", "r", encoding="utf-8") as f:
                saved = json.load(f)
                PRODUCT_IMAGES.update(saved)
            print("✅ Gambar produk dimuat dari product_photos.json")
    except Exception as e:
        print(f"⚠️ Gagal load gambar: {e}")

def save_product_photo(flavour, file_id):
    PRODUCT_IMAGES[flavour] = file_id
    print(f"✅ Gambar untuk {flavour} disimpan.")
    try:
        with open("product_photos.json", "w", encoding="utf-8") as f:
            json.dump(PRODUCT_IMAGES, f, ensure_ascii=False, indent=2)
    except:
        pass

# States
class State(Enum):
    IDLE = 0
    CHOOSING_FLAVOUR = 1
    ENTER_QUANTITY = 2
    ENTER_NAME = 3
    ENTER_PHONE = 4
    ENTER_ADDRESS = 5
    CONFIRM_ORDER = 6
    WAITING_PAYMENT_PROOF = 7

user_data = {}
user_state = {}

# ================== HELPER FUNCTIONS ==================
def generate_order_id():
    now = datetime.now(MY_TZ)
    timestamp = now.strftime("%y%m%d")
    random_num = random.randint(1000, 9999)
    return f"RVS{timestamp}{random_num}"

def get_current_datetime_str():
    return datetime.now(MY_TZ).strftime("%d/%m/%Y %H:%M")

def get_delivery_fee(address):
    addr_lower = address.lower()
    if any(word in addr_lower for word in ["sabah", "sarawak", "kota kinabalu", "kuching", "labuan", "kk", "kch"]):
        return DELIVERY_SABAH_SARAWAK
    return DELIVERY_SEMENANJUNG

# ================== AUTO REMINDER & AUTO CANCEL ==================
def auto_payment_checker():
    while True:
        try:
            now = datetime.now(MY_TZ)
            pending_orders = get_pending_orders()

            for order_id, chat_id, created_at_str in pending_orders:
                try:
                    created_at = datetime.strptime(created_at_str, "%d/%m/%Y %H:%M").replace(tzinfo=MY_TZ)
                    elapsed = now - created_at

                    if elapsed >= timedelta(hours=24):
                        # Auto Cancel
                        update_order_status_in_db(order_id, "Cancelled")
                        bot.send_message(chat_id, f"❌ Order `{order_id}` telah **dibatalkan secara automatik** kerana tiada bayaran dalam 24 jam.")
                        print(f"Order {order_id} dibatalkan secara auto.")

                    elif elapsed >= timedelta(hours=12):
                        # Reminder
                        bot.send_message(chat_id, f"⏰ **Peringatan Bayaran**\n\nOrder `{order_id}` anda masih **Pending**.\nSila buat bayaran secepat mungkin sebelum dibatalkan dalam 24 jam dari masa order dibuat.")
                        print(f"Reminder dihantar untuk order {order_id}")

                except:
                    continue

        except Exception as e:
            print(f"Auto checker error: {e}")

        time.sleep(1800)  # Semak setiap 30 minit

# ================== KEYBOARDS ==================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Buat Order Baru", "📋 Order Saya")
    markup.add("💨 Lihat Flavour", "📞 Hubungi Admin")
    return markup

def flavour_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for i in range(0, len(FLAVOURS), 2):
        markup.add(*FLAVOURS[i:i+2])
    markup.add("🖼️ Lihat Semua Gambar Produk")
    markup.add("⬅️ Kembali ke Menu")
    return markup

def quantity_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for i in range(1, 7):
        markup.add(str(i))
    markup.add("⬅️ Kembali")
    return markup

def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Batal Order")
    return markup

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(message):
    reset_user(message.chat.id)
    welcome_text = f"""
🔥 *SELAMAT DATANG KE RICH VAPE SHOP* 🔥

Kami menjual **e-liquid premium** dengan harga terbaik!

Pilih menu di bawah untuk mula:
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=main_keyboard())

# ================== ADMIN COMMANDS ==================
@bot.message_handler(commands=['admin', 'orders', 'pending', 'stats', 'broadcast', 'update', 'myorders', 'setphoto'])
def admin_commands(message):
    if message.chat.id != OWNER_ID:
        bot.send_message(message.chat.id, "⛔ Anda tiada akses admin.")
        return

    cmd = message.text.split()[0].lower().replace('/', '')

    if cmd in ['orders', 'pending']:
        show_all_orders(message.chat.id, pending_only=(cmd == 'pending'))
    elif cmd == 'stats':
        show_stats(message.chat.id)
    elif cmd == 'broadcast':
        # ... (kekal sama seperti sebelum ini)
        pass
    elif cmd == 'update':
        # ... (kekal sama)
        pass
    elif cmd == 'setphoto':
        try:
            flavour = message.text.split(maxsplit=1)[1]
            if flavour not in FLAVOURS:
                bot.send_message(OWNER_ID, f"❌ Flavour tidak sah!\nFlavour yang ada: {', '.join(FLAVOURS)}")
                return
            bot.send_message(OWNER_ID, f"✅ Sila hantar **gambar** untuk flavour **{flavour}** sekarang.")
            user_data[OWNER_ID] = {"setting_photo_for": flavour}
        except:
            bot.send_message(OWNER_ID, "Cara guna:\n`/setphoto Nama Flavour`\nContoh: `/setphoto Grape Ice`")

# ================== HANDLE PHOTO ==================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id

    if chat_id == OWNER_ID and user_data.get(OWNER_ID, {}).get("setting_photo_for"):
        flavour = user_data[OWNER_ID]["setting_photo_for"]
        file_id = message.photo[-1].file_id
        save_product_photo(flavour, file_id)
        bot.send_message(chat_id, f"✅ Gambar untuk **{flavour}** berjaya disimpan!", parse_mode="Markdown")
        user_data[OWNER_ID].pop("setting_photo_for", None)
        return

    elif user_state.get(chat_id) == State.WAITING_PAYMENT_PROOF:
        handle_payment_proof(message)

# ================== MAIN HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip() if message.text else ""

    if text == "❌ Batal Order":
        reset_user(chat_id)
        bot.send_message(chat_id, "✅ Order telah dibatalkan.", reply_markup=main_keyboard())
        return

    if text == "⬅️ Kembali ke Menu":
        reset_user(chat_id)
        start(message)
        return

    if text == "📦 Buat Order Baru":
        user_state[chat_id] = State.CHOOSING_FLAVOUR
        bot.send_message(chat_id, "💨 *Pilih Flavour Vape anda:*", parse_mode="Markdown", reply_markup=flavour_keyboard())

    elif text == "📋 Order Saya":
        show_user_orders(chat_id)

    elif text == "💨 Lihat Flavour":
        flavours_text = "💨 **FLAVOUR TERSEDIA**\n\n" + "\n".join([f"• {f}" for f in FLAVOURS]) + f"\n\n💰 Harga: *RM{PRICE_PER_BOTTLE}* setiap botol"
        bot.send_message(chat_id, flavours_text, parse_mode="Markdown")

    elif text == "📞 Hubungi Admin":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 Chat WhatsApp Admin", url=f"https://wa.me/{WHATSAPP_NUMBER}"))
        bot.send_message(chat_id, "Hubungi admin terus:", reply_markup=markup)

    # Pilih Flavour
    elif text in FLAVOURS and user_state.get(chat_id) == State.CHOOSING_FLAVOUR:
        user_data[chat_id] = {"flavour": text, "chat_id": chat_id}
        user_state[chat_id] = State.ENTER_QUANTITY
        flavour = text
        file_id = PRODUCT_IMAGES.get(flavour)
        caption = f"✅ Anda pilih: **{flavour}**\n\nBerapa botol yang anda mahu? (1-10)"

        if file_id:
            try:
                bot.send_photo(chat_id, file_id, caption=caption, parse_mode="Markdown", reply_markup=quantity_keyboard())
            except:
                bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=quantity_keyboard())
        else:
            bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=quantity_keyboard())

    elif text == "🖼️ Lihat Semua Gambar Produk" and user_state.get(chat_id) == State.CHOOSING_FLAVOUR:
        sent = False
        for flavour in FLAVOURS:
            file_id = PRODUCT_IMAGES.get(flavour)
            if file_id:
                try:
                    bot.send_photo(chat_id, file_id, caption=f"**{flavour}**", parse_mode="Markdown")
                    sent = True
                except:
                    pass
        if not sent:
            bot.send_message(chat_id, "⚠️ Belum ada gambar produk yang dimuat naik.")

    # Quantity, Name, Phone, Address, Confirmation, Create Order (sama seperti sebelum ini)
    # ... (Saya ringkaskan untuk ruang, tapi anda boleh copy dari kod lama anda)

    # Untuk lengkapkan, sila gantikan bahagian create_order dengan yang di bawah:

    elif user_state.get(chat_id) == State.CONFIRM_ORDER and text.upper() in ["YA", "YES", "OK", "HANTAR", "CONFIRM"]:
        create_order(message)

    elif user_state.get(chat_id) == State.WAITING_PAYMENT_PROOF:
        bot.send_message(chat_id, "📸 Sila hantar gambar bukti bayaran anda.")

    else:
        bot.send_message(chat_id, "Gunakan butang di bawah atau ikut arahan.", reply_markup=main_keyboard())

# ================== CONFIRMATION & CREATE ORDER ==================
def show_confirmation(chat_id):
    # ... (sama seperti kod lama anda)
    pass   # Gantikan dengan kod confirmation lama anda

def create_order(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    delivery = get_delivery_fee(data["address"])
    subtotal = data["price"]
    total = subtotal + delivery
    order_id = generate_order_id()

    order = {
        "order_id": order_id,
        "chat_id": chat_id,
        "flavour": data['flavour'],
        "quantity": data['quantity'],
        "subtotal": subtotal,
        "delivery": delivery,
        "total": total,
        "name": data['name'],
        "phone": data['phone'],
        "address": data['address'],
        "status": "Pending",
        "date": get_current_datetime_str(),
        "created_at": get_current_datetime_str(),
        "payment_proof": None
    }

    save_order_to_db(order)

    # Hantar ke Admin
    admin_text = f"""
🛒 *ORDER BARU DITERIMA!*

**Order ID:** `{order_id}`
**Item:** {data['quantity']}x {data['flavour']}
**Total:** RM{total}
**Pembeli:** {data['name']}
    """
    bot.send_message(OWNER_ID, admin_text, parse_mode="Markdown")

    # Reply ke customer
    customer_text = f"""
✅ *Order #{order_id} berjaya dihantar!*

Jumlah yang perlu dibayar: *RM{total}*

Sila buat pembayaran ke:
{BANK_INFO}

Selepas bayar, hantar gambar bukti bayaran di sini.
    """
    bot.send_message(chat_id, customer_text, parse_mode="Markdown")

    user_state[chat_id] = State.WAITING_PAYMENT_PROOF

# ================== RESET USER ==================
def reset_user(chat_id):
    user_data[chat_id] = {}
    user_state[chat_id] = State.IDLE

# ================== RUN BOT ==================
if __name__ == "__main__":
    init_db()
    load_product_photos()
    
    # Jalankan auto reminder & cancel di background
    threading.Thread(target=auto_payment_checker, daemon=True).start()
    
    print("🚀 Rich Vape Shop Bot v2.3 (SQLite + Auto Reminder + Auto Cancel 24h) sedang berjalan...")
    bot.infinity_polling()
