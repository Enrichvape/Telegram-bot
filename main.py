import telebot
import os
import json
from telebot import types
from datetime import datetime
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

# Timezone Malaysia
MY_TZ = pytz.timezone('Asia/Kuala_Lumpur')

# ================== PRODUCT IMAGES (file_id) ==================
PRODUCT_IMAGES = {
    "Grape Ice": None,
    "Strawberry": None,
    "Mango": None,
    "Blueberry": None,
    "Watermelon": None,
}

# Load gambar dari JSON jika ada
def load_product_photos():
    global PRODUCT_IMAGES
    try:
        if os.path.exists("product_photos.json"):
            with open("product_photos.json", "r", encoding="utf-8") as f:
                saved_photos = json.load(f)
                PRODUCT_IMAGES.update(saved_photos)
            print("✅ Gambar produk dimuat dari product_photos.json")
    except Exception as e:
        print(f"⚠️ Gagal load product_photos.json: {e}")

def save_product_photo(flavour, file_id):
    """Simpan file_id gambar produk"""
    PRODUCT_IMAGES[flavour] = file_id
    print(f"✅ Gambar untuk {flavour} disimpan. file_id: {file_id}")
    
    try:
        with open("product_photos.json", "w", encoding="utf-8") as f:
            json.dump(PRODUCT_IMAGES, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Gagal simpan product_photos.json: {e}")

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
user_orders = {}   # {chat_id: [order1, order2, ...]}

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
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

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
        try:
            text = message.text.split(maxsplit=1)[1]
            sent = 0
            for chat_id in list(user_orders.keys()):
                try:
                    bot.send_message(chat_id, f"📢 *PENGUMUMAN DARI RICH VAPE*\n\n{text}", parse_mode="Markdown")
                    sent += 1
                except:
                    pass
            bot.send_message(OWNER_ID, f"✅ Broadcast berjaya dihantar kepada *{sent}* pengguna.", parse_mode="Markdown")
        except:
            bot.send_message(OWNER_ID, "Cara guna:\n`/broadcast Teks anda di sini`")

    elif cmd == 'update':
        try:
            _, order_id, new_status = message.text.split(maxsplit=2)
            update_order_status(order_id, new_status, message.chat.id)
        except:
            bot.send_message(OWNER_ID, 
                "Cara guna:\n`/update RVS1234567890 Paid`\n\nStatus: Paid, Shipped, Delivered, Cancelled")

    elif cmd == 'myorders':
        show_all_orders(message.chat.id)

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

# ================== HANDLE PHOTO (Admin Upload + Payment Proof) ==================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id

    # Admin sedang upload gambar produk
    if chat_id == OWNER_ID and user_data.get(OWNER_ID, {}).get("setting_photo_for"):
        flavour = user_data[OWNER_ID]["setting_photo_for"]
        file_id = message.photo[-1].file_id   # Ambil kualiti tertinggi
        
        save_product_photo(flavour, file_id)
        
        bot.send_message(chat_id, f"✅ Gambar untuk **{flavour}** berjaya disimpan!", parse_mode="Markdown")
        user_data[OWNER_ID].pop("setting_photo_for", None)
        return

    # Customer hantar bukti bayaran
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

    # === PILIH FLAVOUR + GAMBAR ===
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

    # Lihat Semua Gambar
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
            bot.send_message(chat_id, "⚠️ Belum ada gambar produk yang dimuat naik.\n\nAdmin boleh upload guna `/setphoto Nama Flavour`")

    # Quantity
    elif text.isdigit() and 1 <= int(text) <= 10 and user_state.get(chat_id) == State.ENTER_QUANTITY:
        qty = int(text)
        user_data[chat_id]["quantity"] = qty
        user_data[chat_id]["price"] = PRICE_PER_BOTTLE * qty
        user_state[chat_id] = State.ENTER_NAME
        bot.send_message(chat_id, f"✅ *{qty} botol* **{user_data[chat_id]['flavour']}**\n\nMasukkan **Nama Penuh** anda:", parse_mode="Markdown", reply_markup=cancel_keyboard())

    # Order Flow
    elif user_state.get(chat_id) == State.ENTER_NAME:
        user_data[chat_id]["name"] = text
        user_state[chat_id] = State.ENTER_PHONE
        bot.send_message(chat_id, "📱 Masukkan **No. Telefon** (contoh: 60123456789):", parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_PHONE:
        phone = text.replace(" ", "").replace("-", "").replace("+", "")
        if len(phone) < 10 or not phone.startswith("60"):
            bot.send_message(chat_id, "❌ Nombor telefon tidak sah. Sila masukkan semula (contoh: 60123456789)")
            return
        user_data[chat_id]["phone"] = phone
        user_state[chat_id] = State.ENTER_ADDRESS
        bot.send_message(chat_id, "📍 Masukkan **Alamat Penghantaran** lengkap\n(sebut negeri jika Sabah/Sarawak):", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == State.ENTER_ADDRESS:
        user_data[chat_id]["address"] = text
        user_state[chat_id] = State.CONFIRM_ORDER
        show_confirmation(chat_id)

    elif user_state.get(chat_id) == State.CONFIRM_ORDER and text.upper() in ["YA", "YES", "OK", "HANTAR", "CONFIRM"]:
        create_order(message)

    elif user_state.get(chat_id) == State.WAITING_PAYMENT_PROOF:
        bot.send_message(chat_id, "📸 Sila hantar *gambar bukti bayaran* anda.")

    else:
        bot.send_message(chat_id, "Gunakan butang di bawah atau ikut arahan.", reply_markup=main_keyboard())

# ================== CONFIRMATION & ORDER CREATION ==================
def show_confirmation(chat_id):
    data = user_data[chat_id]
    flavour = data['flavour']
    file_id = PRODUCT_IMAGES.get(flavour)

    delivery = get_delivery_fee(data["address"])
    subtotal = data["price"]
    total = subtotal + delivery

    text = f"""
✅ *KONFIRMASI ORDER*

**Item:**
{data['quantity']}x {flavour} 
Harga     : RM{subtotal}

**Penghantaran:**
RM{delivery} ({'Sabah/Sarawak' if delivery == 18 else 'Semenanjung Malaysia'})

**Jumlah Keseluruhan:** *RM{total}*

**Maklumat Pembeli:**
Nama   : {data['name']}
Telefon: {data['phone']}
Alamat : {data['address']}

Balas *YA* jika semua maklumat betul.
"""

    if file_id:
        try:
            bot.send_photo(chat_id, file_id, caption=text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())
            return
        except:
            pass

    bot.send_message(chat_id, text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())

def create_order(message):
    chat_id = message.chat.id
    data = user_data[chat_id]
    delivery = get_delivery_fee(data["address"])
    subtotal = data["price"]
    total = subtotal + delivery
    order_id = generate_order_id()

    order = {
        "order_id": order_id,
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
        "chat_id": chat_id,
        "payment_proof": None
    }

    if chat_id not in user_orders:
        user_orders[chat_id] = []
    user_orders[chat_id].append(order)

    # Hantar ke Admin
    admin_text = f"""
🛒 *ORDER BARU DITERIMA!*

**Order ID:** `{order_id}`
**Item:** {data['quantity']}x {data['flavour']}
**Total:** RM{total} (Delivery: RM{delivery})

**Pembeli:**
Nama   : {data['name']}
Telefon: {data['phone']}
Alamat : {data['address']}
Tarikh : {order['date']}
"""
    bot.send_message(OWNER_ID, admin_text, parse_mode="Markdown")

    # Reply ke customer
    customer_text = f"""
✅ *Order #{order_id} berjaya dihantar!*

Jumlah yang perlu dibayar: *RM{total}*

Sila buat pembayaran ke:
{BANK_INFO}

Selepas bayar, hantar **gambar bukti bayaran** di sini.
Admin akan semak secepat mungkin. Terima kasih! 🔥
"""
    bot.send_message(chat_id, customer_text, parse_mode="Markdown")

    user_state[chat_id] = State.WAITING_PAYMENT_PROOF

def handle_payment_proof(message):
    chat_id = message.chat.id
    latest_order = user_orders.get(chat_id, [{}])[-1]
    order_id = latest_order.get('order_id', "Unknown")

    bot.forward_message(OWNER_ID, chat_id, message.message_id)
    bot.send_message(OWNER_ID, f"💰 Bukti bayaran diterima untuk Order `{order_id}`")

    bot.send_message(chat_id, "✅ Bukti bayaran anda telah dihantar kepada admin.\n\nAdmin akan semak dan update status order anda secepat mungkin. Terima kasih! 🔥")

    reset_user(chat_id)
    bot.send_message(chat_id, "Kembali ke menu utama:", reply_markup=main_keyboard())

# ================== DISPLAY ORDERS ==================
def show_user_orders(chat_id):
    if not user_orders.get(chat_id):
        bot.send_message(chat_id, "Anda belum ada order lagi.")
        return

    text = "📋 **ORDER SAYA**\n\n"
    for order in user_orders[chat_id]:
        text += f"🔖 `{order['order_id']}` — {order['quantity']}x {order['flavour']}\n"
        text += f"Status : **{order['status']}**\n"
        text += f"Total  : RM{order['total']}\n"
        text += f"Tarikh : {order['date']}\n\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

def show_all_orders(chat_id, pending_only=False):
    if not user_orders:
        bot.send_message(chat_id, "Tiada order lagi.")
        return

    title = "📋 **SEMUA ORDER**" if not pending_only else "📋 **ORDER PENDING**"
    text = f"{title}\n\n"

    for cid, orders in user_orders.items():
        for o in orders:
            if pending_only and o['status'] != "Pending":
                continue
            text += f"`{o['order_id']}` | {o['quantity']}x {o['flavour']} | {o['status']} | RM{o['total']}\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

def update_order_status(order_id, new_status, admin_id):
    new_status = new_status.capitalize()
    for orders in user_orders.values():
        for order in orders:
            if order['order_id'] == order_id:
                old_status = order['status']
                order['status'] = new_status
                
                bot.send_message(admin_id, f"✅ Order `{order_id}` telah diubah:\n{old_status} → **{new_status}**")
                
                try:
                    bot.send_message(order['chat_id'], 
                        f"🔄 *Status order anda telah dikemaskini*\n\n"
                        f"Order `{order_id}`\n"
                        f"Status: **{new_status}**", parse_mode="Markdown")
                except:
                    pass
                return
    bot.send_message(admin_id, "❌ Order ID tidak dijumpai.")

def show_stats(chat_id):
    total_orders = sum(len(orders) for orders in user_orders.values())
    pending = sum(1 for orders in user_orders.values() for o in orders if o['status'] == "Pending")
    paid = sum(1 for orders in user_orders.values() for o in orders if o['status'] == "Paid")
    
    text = f"""
📊 **STATISTIK RICH VAPE SHOP**

Total Order     : {total_orders}
Pending         : {pending}
Sudah Dibayar   : {paid}
"""
    bot.send_message(chat_id, text, parse_mode="Markdown")

def reset_user(chat_id):
    if chat_id in user_data:
