import logging
import os
import json
from datetime import datetime, timedelta

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters, ContextTypes
)

# ==============================================================
# SOZLAMALAR
# ==============================================================
TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
DATA_FILE = "data.json"

# STATES
(REG_NAME, REG_PHONE, REG_LOCATION, MENU_BROWSE, UPSELL, PAYMENT, CONFIRM, 
 ADMIN_MENU_INPUT, ADMIN_BROADCAST, CHANGE_LOCATION) = range(10)

# MA'LUMOTLAR
users, menu, orders = {}, {}, {}
order_counter = [0]
stats = {"total_orders": 0, "total_revenue": 0, "daily": {}, "weekly": {}}

UPSELL_ITEMS = [
    {"name": "🥤 Cola", "price": 8000},
    {"name": "🍞 Non", "price": 3000},
    {"name": "🥗 Salat", "price": 12000},
]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ==============================================================
# MA'LUMOTLAR BILAN ISHLASH
# ==============================================================
def save_data():
    try:
        payload = {
            "users": {str(k): v for k, v in users.items()}, 
            "menu": menu, 
            "orders": {str(k): v for k, v in orders.items()}, 
            "order_counter": order_counter[0], 
            "stats": stats
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e: log.error(f"Saqlashda xato: {e}")

def load_data():
    global users, menu, orders, stats
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                p = json.load(f)
                users = {int(k): v for k, v in p.get("users", {}).items()}
                menu = p.get("menu", {})
                orders = {int(k): v for k, v in p.get("orders", {}).items()}
                order_counter[0] = p.get("order_counter", 0)
                stats.update(p.get("stats", {}))
        except Exception as e: log.error(f"Yuklashda xato: {e}")

# ==============================================================
# YORDAMCHI FUNKSIYALAR
# ==============================================================
def is_admin(uid): return uid == ADMIN_ID
def admin_kb(): return ReplyKeyboardMarkup([["📋 Menyu kiritish", "📦 Buyurtmalar"], ["📢 Xabar yuborish", "📊 Hisobot"]], resize_keyboard=True)
def user_kb(): return ReplyKeyboardMarkup([["🍽 Buyurtma berish"], ["📦 Buyurtmalarim", "👤 Profilim"]], resize_keyboard=True)

# ==============================================================
# ASOSIY LOGIKA
# ==============================================================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    load_data()
    if is_admin(uid):
        await update.message.reply_text("Salom, Admin!", reply_markup=admin_kb())
        return ConversationHandler.END
    if uid in users:
        await update.message.reply_text(f"Xush kelibsiz, {users[uid]['name']}!", reply_markup=user_kb())
        return ConversationHandler.END
    await update.message.reply_text("Gulcha Taom botiga xush kelibsiz! Ismingizni kiriting:")
    return REG_NAME

# ... (Bu yerda ro'yxatdan o'tish, menyu va to'lov funksiyalari davom etadi)

def main():
    load_data()
    if not TOKEN:
        log.error("BOT_TOKEN topilmadi!")
        return

    # Render xatosini oldini olish uchun Application ishlatamiz
    app = Application.builder().token(TOKEN).build()

    # Handlerlar
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
            # Boshqa statelar...
        },
        fallbacks=[CommandHandler("cancel", start)],
    )

    app.add_handler(conv)
    
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    # Render uchun pooling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
