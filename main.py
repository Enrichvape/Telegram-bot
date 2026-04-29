import telebot
import os
from telebot import types
from enum import Enum

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ================== SETTING ==================
OWNER_ID = 8299633855
WHATSAPP_NUMBER = "601160879707"   # Tukar ikut nombor WhatsApp kamu
PRICE = 95

# States untuk conversation
class UserState(Enum):
    IDLE = 0
    CHOOSING_FLAVOUR = 1
    ENTERING_NAME = 2
    ENTERING_PHONE = 3
    ENTERING_ADDRESS = 4
    CONFIRMING_ORDER = 5

user_data = {}
user_state = {}

# ================== KEYBOARDS ==================
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📦 Lai Order", "💨 Usha Lu Flavour")
    markup.add("📞 Contact Admin")
    return markup

def flavour_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Grape Ice", "Strawberry")
    markup.add("Mango", "⬅️ Kembali")
    return markup

def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Batal Order")
    return markup

# ================== START ==================
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    user_state[chat_id] = UserState.IDLE
    
    bot.send_message(
        chat_id, 
        "👋 Selamat datang ke **enRich Vape Shop** 🔥\n\n"
        "Gerenti Murah And Pati Padu Teruokkk",
        reply_markup=main_keyboard(),
        parse_mode="Markdown"
    )

# ================== MAIN MENU HANDLER ==================
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    # Reset state jika tekan Back atau Batal
    if text in ["⬅️ Kembali", "❌ Batal Order"]:
        user_data[chat_id] = {}
        user_state[chat_id] = UserState.IDLE
        start(message)
        return

    if text == "📦 Lai Order":
        user_state[chat_id] = UserState.CHOOSING_FLAVOUR
        bot.send_message(chat_id, "Pilih flavour yang anda mahu:", reply_markup=flavour_keyboard())

    elif text == "💨 Usha Lu Flavour":
        bot.send_message(
            chat_id,
            f"🔥 **FLAVOUR PATI** 🔥\n\n"
            f"• Grape Ice\n"
            f"• Strawberry\n"
            f"• Mango\n\n"
            f"💰 Harga: RM{PRICE} sebotol\n"
            f"✅ Pati sedap & tahan lama",
            parse_mode="Markdown"
        )

    elif text == "📞 Contact Admin":
        wa_link = f"https://wa.me/01160879707"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💬 Hubungi WhatsApp", url=wa_link))
        
        bot.send_message(chat_id, "Klik butang di bawah untuk hubungi admin:", reply_markup=markup)

    # Flavour selection
    elif text in ["Grape Ice", "Strawberry", "Mango"]:
        if user_state.get(chat_id) == UserState.CHOOSING_FLAVOUR:
            user_data[chat_id] = {"flavour": text}
            user_state[chat_id] = UserState.ENTERING_NAME
            
            bot.send_message(
                chat_id, 
                f"Anda pilih: **{text}**\n\n"
                "Sila masukkan **nama penuh** anda:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )

    # ================== ORDER STEPS ==================
    elif user_state.get(chat_id) == UserState.ENTERING_NAME:
        user_data[chat_id]["name"] = text
        user_state[chat_id] = UserState.ENTERING_PHONE
        bot.send_message(chat_id, "Masukkan **nombor telefon** anda (contoh: 60123456789):", 
                        parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == UserState.ENTERING_PHONE:
        # Simple validation
        phone = text.replace(" ", "").replace("-", "")
        if not phone.startswith("60") or len(phone) < 10:
            bot.send_message(chat_id, "❌ Nombor telefon tidak sah.\n\nSila masukkan nombor yang betul (contoh: 60123456789)")
            return
        
        user_data[chat_id]["phone"] = phone
        user_state[chat_id] = UserState.ENTERING_ADDRESS
        bot.send_message(chat_id, "Masukkan **alamat penghantaran** lengkap:", 
                        reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == UserState.ENTERING_ADDRESS:
        user_data[chat_id]["address"] = text
        user_state[chat_id] = UserState.CONFIRMING_ORDER
        
        data = user_data[chat_id]
        
        confirmation_text = f"""
🔥 **KOMPOM ORDER** 🔥

Nama          : {data['name']}
Flavour       : {data['flavour']}
Harga         : RM{PRICE}
No. Telefon   : {data['phone']}
Alamat        : {data['address']}

Betul ke order ni? 
Balas *YA* untuk hantar order.
        """
        
        bot.send_message(chat_id, confirmation_text.strip(), parse_mode="Markdown", reply_markup=cancel_keyboard())

    elif user_state.get(chat_id) == UserState.CONFIRMING_ORDER:
        if text.upper() in ["YA", "YES", "OK", "HANTAR"]:
            data = user_data[chat_id]
            
            order_text = f"""
🔥 **ORDER BARU DITERIMA** 🔥

📌 Nama       : {data['name']}
📌 Flavour    : {data['flavour']}
💰 Harga      : RM{PRICE}
📱 Telefon    : {data['phone']}
📍 Alamat     : {data['address']}
⏰ Masa       : {message.date}

Dari: @{message.from_user.username if message.from_user.username else message.from_user.id}
            """
            
            bot.send_message(OWNER_ID, order_text)
            
            bot.send_message(
                chat_id, 
                "✅ *Order anda berjaya dihantar!* 🔥\n\n"
                "Admin akan hubungi anda sebentar lagi.",
                parse_mode="Markdown"
            )
            
            # Reset
            user_data[chat_id] = {}
            user_state[chat_id] = UserState.IDLE
            bot.send_message(chat_id, "Terima kasih kerana order di Rich Vape Shop! 🙏", reply_markup=main_keyboard())
        else:
            bot.send_message(chat_id, "Sila balas *YA* jika betul, atau tekan *❌ Batal Order* jika nak batalkan.")

# ================== RUN BOT ==================
print("Rich Vape Bot is running...")
bot.infinity_polling()
