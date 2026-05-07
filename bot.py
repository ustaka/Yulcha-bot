import logging
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# 1. LOGGING (Xatolarni ko'rish uchun)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. TOKEN (Render Environment Variables'dan olinadi)
TOKEN = os.getenv("BOT_TOKEN")

# 3. ASOSIY START BUYRUG'I
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Bu yerda hech qanday 'Updater' yoki 'dispatcher' ishlatilmaydi
    await update.message.reply_text(
        "Salom! Gulcha bot 20.8 versiyada muvaffaqiyatli ishga tushdi ✅",
        reply_markup=ReplyKeyboardMarkup([["🍽 Menu"]], resize_keyboard=True)
    )

# 4. ASOSIY ISHGA TUSHIRISH FUNKSIYASI
def main():
    if not TOKEN:
        print("XATO: Render sozlamalarida BOT_TOKEN topilmadi!")
        return

    # DIQQAT: v20.8 da faqat Application ishlatiladi
    app = Application.builder().token(TOKEN).build()
    
    # Buyruqlarni qo'shish
    app.add_handler(CommandHandler("start", start))
    
    # Botni yurgizish
    print("Bot pooling rejimida ishga tushmoqda...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
