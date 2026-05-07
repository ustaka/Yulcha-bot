import logging
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Loglarni aniq ko'rish uchun
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ishga tushdi!")

def main():
    if not TOKEN:
        print("XATO: BOT_TOKEN topilmadi!")
        return

    # BU YERDA UPDATER YO'Q! Faqat Application.
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("=== BOT ISHLASHGA TAYYOR ===")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
