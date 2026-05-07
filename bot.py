import logging
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Loglarni Render konsolida ko'rish uchun sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Tokenni Render Environment Variables'dan olamiz
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot muvaffaqiyatli ishga tushdi!")

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN topilmadi! Render Environment bo'limini tekshiring.")
        return

    # v20.8 uchun to'g'ri struktura
    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        
        logger.info("Bot polling rejimida ishga tushmoqda...")
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xato: {e}")

if __name__ == "__main__":
    main()
