import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- 1. SOZLAMALAR (Render'dan o'qiydi) ---
TOKEN = os.getenv("BOT_TOKEN")
# Admin ID ni o'qishda xatolik bo'lmasligi uchun default 0 qo'yamiz
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"

# --- 2. HOLATLAR ---
NAME, PHONE, LOCATION = range(3)

# --- 3. LOGGING ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- 4. MA'LUMOTLARNI BOSHQARISH ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {"users": {}}
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

# --- 5. BOT FUNKSIYALARI ---
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    
    if user_id == str(ADMIN_ID):
        await update.message.reply_text("Salom Admin! Tizim tayyor.", reply_markup=ReplyKeyboardMarkup([["📦 Buyurtmalar"]], resize_keyboard=True))
        return ConversationHandler.END
        
    if user_id in data["users"]:
        name = data["users"][user_id]["name"]
        await update.message.reply_text(f"Xush kelibsiz, {name}!", reply_markup=ReplyKeyboardMarkup([["🍽 Menu"]], resize_keyboard=True))
        return ConversationHandler.END
        
    await update.message.reply_text("Salom! Ro'yxatdan o'tish uchun ismingizni kiriting:")
    return NAME

async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text("Telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📞 Yuborish", request_contact=True)]], resize_keyboard=True))
    return PHONE

async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        ctx.user_data["phone"] = update.message.contact.phone_number
    else:
        ctx.user_data["phone"] = update.message.text
    await update.message.reply_text("Manzilingizni yuboring:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📍 Lokatsiya", request_location=True)]], resize_keyboard=True))
    return LOCATION

async def get_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    loc = update.message.location
    data["users"][user_id] = {
        "name": ctx.user_data["name"],
        "phone": ctx.user_data["phone"],
        "lat": loc.latitude if loc else None,
        "lon": loc.longitude if loc else None
    }
    save_data(data)
    await update.message.reply_text("Ro'yxatdan o'tdingiz!", reply_markup=ReplyKeyboardMarkup([["🍽 Menu"]], resize_keyboard=True))
    return ConversationHandler.END

# --- 6. ASOSIY QISM ---
def main():
    if not TOKEN:
        print("XATO: BOT_TOKEN o'zgaruvchisi topilmadi!")
        return

    # Updater xatosini oldini olish uchun Application ishlatamiz
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
            LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT, get_location)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    
    # Render uchun pooling ishga tushadi
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
