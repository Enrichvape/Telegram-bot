import telebot
import os
import json
import sqlite3
import threading
import time
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

BANK_INFO = """🏦 Maybank
Nama: Shafirul Ridhzuan
No Akaun: 162040050328

💸 DuitNow / TNG: 131442809630"""

FLAVOURS = ["Grape Ice", "Strawberry", "Mango", "Blueberry", "Watermelon"]
MY_TZ = pytz.timezone('Asia/Kuala_Lumpur')

# ================== DATABASE ==================
conn = sqlite3.connect("orders.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    chat_id INTEGER,
    flavour TEXT,
    quantity INTEGER,
    total INTEGER,
    name TEXT,
    phone TEXT,
    address TEXT,
    status TEXT,
    date TEXT
)
""")
conn.commit()

# ================== STATES ==================
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

# ================== HELPER ==================
def generate_order_id():
    now = datetime.now(MY_TZ)
    return f"RVS{now.strftime('%y%m%d')}{random.randint(1000,9999)}"

def get_current_datetime_str():
    return datetime.now(MY_TZ).strftime("%d/%m/%Y %H:%M")

def get_delivery_fee(address):
    if any(x in address.lower() for x in ["sabah","sarawak","kk","kuching"]):
        return DELIVERY_SABAH_SARAWAK
    return DELIVERY_SEMENANJUNG

# ================== AUTO SYSTEM ==================
def payment_reminder(chat_id, order_id):
    time.sleep(3600)
    cursor.execute("SELECT status FROM orders WHERE order_id=?", (order_id,))
    r = cursor.fetchone()
    if r and r[0] == "Pending":
        bot.send_message(chat_id, f"⏰ Reminder: Order `{order_id}` belum dibayar.", parse_mode="Markdown")

def auto_cancel_order(chat_id, order_id):
    time.sleep(86400)
    cursor.execute("SELECT status FROM orders WHERE order_id=?", (order_id,))
    r = cursor.fetchone()
    if r and r[0] == "Pending":
        cursor.execute("UPDATE orders SET status='Cancelled' WHERE order_id=?", (order_id,))
        conn.commit()
        bot.send_message(chat_id, f"❌ Order `{order_id}` auto cancel.")
        bot.send_message(OWNER_ID, f"⚠️ {order_id} auto cancel")

def resume_pending_orders():
    cursor.execute("SELECT order_id, chat_id FROM orders WHERE status='Pending'")
    for oid, cid in cursor.fetchall():
        threading.Thread(target=payment_reminder, args=(cid, oid)).start()
        threading.Thread(target=auto_cancel_order, args=(cid, oid)).start()

# ================== KEYBOARD ==================
def main_kb():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.add("📦 Buat Order", "📋 Order Saya")
    m.add("💨 Flavour", "📞 Admin")
    return m

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(m):
    user_state[m.chat.id] = State.IDLE
    bot.send_message(m.chat.id, "🔥 Welcome Rich Vape Shop", reply_markup=main_kb())

# ================== MAIN ==================
@bot.message_handler(func=lambda m: True)
def main(m):
    cid = m.chat.id
    text = m.text

    if text == "📦 Buat Order":
        user_state[cid] = State.CHOOSING_FLAVOUR
        bot.send_message(cid, "Pilih flavour:\n" + "\n".join(FLAVOURS))

    elif text in FLAVOURS:
        user_data[cid] = {"flavour": text}
        user_state[cid] = State.ENTER_QUANTITY
        bot.send_message(cid, "Berapa botol? (1-10)")

    elif text.isdigit() and user_state.get(cid) == State.ENTER_QUANTITY:
        user_data[cid]["qty"] = int(text)
        user_data[cid]["price"] = int(text) * PRICE_PER_BOTTLE
        user_state[cid] = State.ENTER_NAME
        bot.send_message(cid, "Nama:")

    elif user_state.get(cid) == State.ENTER_NAME:
        user_data[cid]["name"] = text
        user_state[cid] = State.ENTER_PHONE
        bot.send_message(cid, "Phone:")

    elif user_state.get(cid) == State.ENTER_PHONE:
        user_data[cid]["phone"] = text
        user_state[cid] = State.ENTER_ADDRESS
        bot.send_message(cid, "Alamat:")

    elif user_state.get(cid) == State.ENTER_ADDRESS:
        user_data[cid]["address"] = text
        create_order(cid)

    elif text == "📋 Order Saya":
        show_orders(cid)

# ================== ORDER ==================
def create_order(cid):
    d = user_data[cid]
    delivery = get_delivery_fee(d["address"])
    total = d["price"] + delivery
    oid = generate_order_id()

    cursor.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)", (
        oid, cid, d["flavour"], d["qty"], total,
        d["name"], d["phone"], d["address"], "Pending", get_current_datetime_str()
    ))
    conn.commit()

    bot.send_message(cid, f"✅ Order `{oid}`\nTotal: RM{total}\n\n{BANK_INFO}", parse_mode="Markdown")
    bot.send_message(OWNER_ID, f"🛒 {oid} | RM{total}")

    threading.Thread(target=payment_reminder, args=(cid, oid)).start()
    threading.Thread(target=auto_cancel_order, args=(cid, oid)).start()

# ================== VIEW ==================
def show_orders(cid):
    cursor.execute("SELECT * FROM orders WHERE chat_id=?", (cid,))
    data = cursor.fetchall()

    if not data:
        bot.send_message(cid, "Tiada order")
        return

    text = "📋 Order:\n\n"
    for o in data:
        text += f"{o[0]} | {o[2]} x{o[3]} | {o[8]} | RM{o[4]}\n"

    bot.send_message(cid, text)

# ================== RUN ==================
if __name__ == "__main__":
    resume_pending_orders()
    print("🚀 BOT RUNNING")
    bot.infinity_polling()
