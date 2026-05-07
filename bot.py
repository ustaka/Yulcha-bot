import logging
import os
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# --- SOZLAMALAR ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DATA_FILE = "data.json"

# --- STATES ---
NAME, PHONE, LOCATION = range(3)

# --- LOGGING ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- FUNKSIYALAR ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {"users": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    
    if user_id == str(ADMIN_ID):
        await update.message.reply_text("Salom Admin! Bot ishga tushdi.")
        return ConversationHandler.END
        
    if user_id in data["users"]:
        name = data["users"][user_id]["name"]
        await update.message.reply_text(f"Xush kelibsiz, {name}!", reply_markup=ReplyKeyboardMarkup([["🍽 Buyurtma berish"]], resize_keyboard=True))
        return ConversationHandler.END
        
    await update.message.reply_text("Ismingizni kiriting:")
    return NAME

async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text
    await update.message.reply_text("Telefon raqamingizni yuboring:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]], resize_keyboard=True))
    return PHONE

async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    ctx.user_data["phone"] = contact.phone_number if contact else update.message.text
    await update.message.reply_text("Manzilingizni (Location) yuboring:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📍 Joylashuvni yuborish", request_location=True)]], resize_keyboard=True))
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
    
    await update.message.reply_text("Ro'yxatdan o'tdingiz!", reply_markup=ReplyKeyboardMarkup([["🍽 Buyurtma berish"]], resize_keyboard=True))
    return ConversationHandler.END

# --- MAIN ---
def main():
    if not TOKEN:
        print("XATO: BOT_TOKEN topilmadi!")
        return

    # Skrinshotingizdagi 'Updater' xatosini oldini olish uchun Application ishlatamiz
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, get_phone)],
            LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT, get_location)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    print("Bot yoqildi...")
    app.run_polling()

if __name__ == "__main__":
    main()
