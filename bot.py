"""
Gulcha Taom - Telegram buyurtma boti
python-telegram-bot==20.7
"""

import logging
import os
import json
from datetime import datetime, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ==============================================================
# SOZLAMALAR
# ==============================================================

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "0000 0000 0000 0000")
DATA_FILE = "data.json"

# ==============================================================
# CONVERSATION STATES
# ==============================================================

(
    REG_NAME,
    REG_PHONE,
    REG_LOCATION,
    MENU_BROWSE,
    UPSELL,
    PAYMENT,
    CONFIRM,
    ADMIN_MENU_INPUT,
    ADMIN_BROADCAST,
    CHANGE_LOCATION,
) = range(10)

# ==============================================================
# GLOBAL MA'LUMOTLAR
# ==============================================================

users: dict = {}
menu: dict = {}
orders: dict = {}
order_counter: list = [0]
stats: dict = {
    "total_orders": 0,
    "total_revenue": 0,
    "daily": {},
    "weekly": {},
}

UPSELL_ITEMS = [
    {"name": "🥤 Cola", "price": 8000},
    {"name": "🍞 Non", "price": 3000},
    {"name": "🥗 Salat", "price": 12000},
]

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ==============================================================
# JSON SAQLASH / YUKLASH
# ==============================================================

def save_data() -> None:
    try:
        payload = {
            "users": {str(k): v for k, v in users.items()},
            "menu": menu,
            "orders": {str(k): v for k, v in orders.items()},
            "order_counter": order_counter[0],
            "stats": stats,
        }
        with open(DATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("save_data xatosi: %s", exc)

def load_data() -> None:
    global users, menu, orders, stats
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
            users = {int(k): v for k, v in payload.get("users", {}).items()}
            menu = payload.get("menu", {})
            orders = {int(k): v for k, v in payload.get("orders", {}).items()}
            order_counter[0] = payload.get("order_counter", 0)
            stats.update(payload.get("stats", {}))
            log.info("Yuklandi: %d mijoz, %d buyurtma", len(users), len(orders))
    except Exception as exc:
        log.error("load_data xatosi: %s", exc)

# ==============================================================
# YORDAMCHI FUNKSIYALAR
# ==============================================================

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def today_str() -> str:
    return datetime.now().strftime("%d.%m.%Y")

def week_key() -> str:
    now = datetime.now()
    return (now - timedelta(days=now.weekday())).strftime("%d.%m.%Y")

def gmap(lat, lon) -> str:
    return f"https://www.google.com/maps?q={lat},{lon}"

def item_price(item) -> int:
    if isinstance(item, dict):
        return int(item.get("price", 0))
    return int(item)

def item_photo(item):
    if isinstance(item, dict):
        return item.get("photo_id") or None
    return None

def admin_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📋 Menyu kiritish", "📦 Buyurtmalar"],
            ["📢 Xabar yuborish", "📊 Hisobot"],
            ["👥 Mijozlar bazasi"],
        ],
        resize_keyboard=True,
    )

def user_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🍽 Buyurtma berish"],
            ["📦 Buyurtmalarim", "👤 Profilim"],
            ["📍 Manzilni yangilash"],
        ],
        resize_keyboard=True,
    )

def main_kb(uid: int):
    return admin_keyboard() if is_admin(uid) else user_keyboard()

def order_admin_text(order: dict, user: dict) -> str:
    lines = "\n".join(
        f"  • {i['name']} x{i['qty']} — {i['qty'] * i['price']:,} so'm"
        for i in order["items"]
    )
    pay = "💵 Naqd" if order["payment"] == "cash" else "💳 Karta"
    statuses = {
        "new": "🆕 Yangi",
        "cooking": "👨‍🍳 Tayyorlanmoqda",
        "delivering": "🚚 Yetkazilmoqda",
        "delivered": "✅ Yetkazildi",
        "cancelled": "❌ Bekor",
    }
    status = statuses.get(order.get("status", "new"), "🆕 Yangi")
    lat, lon = user.get("lat"), user.get("lon")
    if lat and lon:
        loc = f"📍 [{user.get('address', 'Manzil')}]({gmap(lat, lon)})"
    else:
        loc = f"📍 {user.get('address', 'Noma`lum')}"
    return (
        f"🔔 *Buyurtma #{order['id']}*\n\n"
        f"👤 {user.get('name', '?')}\n"
        f"📞 {user.get('phone', '?')}\n"
        f"{loc}\n\n"
        f"🍽 *Tarkib:*\n{lines}\n\n"
        f"💰 *Jami: {order['total']:,} so'm*\n"
        f"{pay}\n"
        f"📌 {status}\n"
        f"🕐 {order['time']}"
    )

def cart_total(cart: dict) -> int:
    total = 0
    for name, qty in cart.items():
        if name in menu:
            total += qty * item_price(menu[name])
    return total

def cart_lines(cart: dict) -> str:
    rows = []
    for name, qty in cart.items():
        if name in menu and qty > 0:
            p = item_price(menu[name])
            rows.append(f"  • {name} x{qty} — {qty * p:,} so'm")
    return "\n".join(rows)

# ==============================================================
# /start
# ==============================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_admin(uid):
        await update.message.reply_text(
            "👋 Salom, Admin! 🎛\n\nBoshqaruv paneliga xush kelibsiz.",
            reply_markup=admin_keyboard(),
        )
        return ConversationHandler.END

    if uid in users:
        if menu:
            mlines = "\n".join(
                f"  • {n} — {item_price(v):,} so'm" for n, v in menu.items()
            )
            msg = f"📋 *Bugungi menyu:*\n{mlines}"
        else:
            msg = "⏳ Bugungi menyu hali tayyor emas."
        await update.message.reply_text(
            f"👋 Qaytib keldingiz, *{users[uid]['name']}*!\n\n{msg}",
            reply_markup=user_keyboard(),
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 *Gulcha Taom* botiga xush kelibsiz! 🍽\n\n"
        "Toshkentdagi eng mazali tushliklar eshigingizgacha!\n\n"
        "Ro'yxatdan o'tish uchun *ism va familiyangizni* kiriting:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return REG_NAME

# ==============================================================
# RO'YXATDAN O'TISH
# ==============================================================

async def reg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["reg_name"] = update.message.text.strip()
    kb = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
    await update.message.reply_text(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
    )
    return REG_PHONE

async def reg_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = update.message.text.strip()
    ctx.user_data["reg_phone"] = phone

    kb = [[KeyboardButton("📍 Lokatsiyamni yuborish", request_location=True)]]
    await update.message.reply_text(
        "📍 Ofis yoki yetkazib berish manzilingizni yuboring:\n"
        "_(kuryer to'g'ri manzilni topadi)_",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown",
    )
    return REG_LOCATION

async def reg_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        address = f"{lat:.5f}, {lon:.5f}"
    else:
        lat, lon = None, None
        address = update.message.text.strip()

    users[uid] = {
        "name": ctx.user_data["reg_name"],
        "phone": ctx.user_data["reg_phone"],
        "address": address,
        "lat": lat,
        "lon": lon,
        "joined": today_str(),
        "orders": [],
        "total_spent": 0,
        "order_count": 0,
        "favorite_items": {},
        "vip": False,
        "last_order": None,
    }
    save_data()

    map_url = f"\n🗺 [Xaritada ko'rish]({gmap(lat, lon)})" if lat and lon else ""
    await update.message.reply_text(
        f"✅ *Ro'yxatdan o'tdingiz!*\n\n"
        f"👤 {users[uid]['name']}\n"
        f"📞 {users[uid]['phone']}\n"
        f"📍 {address}{map_url}\n\n"
        f"Buyurtma berishingiz mumkin! 🎉",
        parse_mode="Markdown",
        reply_markup=user_keyboard(),
    )
    return ConversationHandler.END

# ==============================================================
# MANZIL YANGILASH
# ==============================================================

async def change_loc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        await update.message.reply_text("Avval /start bosing.")
        return ConversationHandler.END
    kb = [[KeyboardButton("📍 Yangi lokatsiyamni yuborish", request_location=True)]]
    await update.message.reply_text(
        "📍 Yangi manzilni yuboring:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
    )
    return CHANGE_LOCATION

async def change_loc_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        address = f"{lat:.5f}, {lon:.5f}"
    else:
        lat, lon = None, None
        address = update.message.text.strip()

    users[uid]["address"] = address
    users[uid]["lat"] = lat
    users[uid]["lon"] = lon
    save_data()

    map_url = f" — [Xaritada]({gmap(lat, lon)})" if lat and lon else ""
    await update.message.reply_text(
        f"✅ Manzil yangilandi!\n📍 {address}{map_url}",
        reply_markup=user_keyboard(),
        parse_mode="Markdown",
    )
    return ConversationHandler.END

# ==============================================================
# BUYURTMA — MENYU KO'RISH
# ==============================================================

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in users:
        await update.message.reply_text("Avval /start bosing va ro'yxatdan o'ting.")
        return ConversationHandler.END
    if not menu:
        await update.message.reply_text("⏳ Bugungi menyu hali tayyor emas.")
        return ConversationHandler.END

    ctx.user_data["cart"] = {}
    ctx.user_data["menu_keys"] = list(menu.keys())
    ctx.user_data["menu_idx"] = 0
    return await send_menu_card(update, ctx, from_callback=False)

def build_menu_keyboard(name: str, qty: int, cart: dict, idx: int, total_items: int) -> InlineKeyboardMarkup:
    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data="m_prev"))
    nav.append(InlineKeyboardButton(f"{idx + 1} / {total_items}", callback_data="m_noop"))
    if idx < total_items - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data="m_next"))

    qty_row = [
        InlineKeyboardButton("➖", callback_data="m_minus"),
        InlineKeyboardButton(f"  {qty} ta  ", callback_data="m_noop"),
        InlineKeyboardButton("➕", callback_data="m_plus"),
    ]

    rows = [nav, qty_row]
    if cart:
        total = cart_total(cart)
        rows.append([
            InlineKeyboardButton(
                f"✅ Buyurtma berish — {total:,} so'm",
                callback_data="m_checkout",
            )
        ])
    return InlineKeyboardMarkup(rows)

async def send_menu_card(update: Update, ctx: ContextTypes.DEFAULT_TYPE, from_callback: bool = True) -> int:
    cart: dict = ctx.user_data.get("cart", {})
    keys: list = ctx.user_data.get("menu_keys", [])
    idx: int = ctx.user_data.get("menu_idx", 0)

    if not keys or idx >= len(keys):
        return MENU_BROWSE

    name = keys[idx]
    m_item = menu[name]
    price = item_price(m_item)
    photo = item_photo(m_item)
    qty = cart.get(name, 0)

    cart_info = f"\n\n🛒 *Savatcha:*\n{cart_lines(cart)}\n💰 Jami: {cart_total(cart):,} so'm" if cart else ""
    caption = f"🍽 *{name}*\n💰 Narxi: {price:,} so'm{cart_info}"
    kb = build_menu_keyboard(name, qty, cart, idx, len(keys))

    if from_callback:
        query = update.callback_query
        try:
            if photo:
                await query.message.delete()
                await ctx.bot.send_photo(chat_id=query.message.chat_id, photo=photo, caption=caption, reply_markup=kb, parse_mode="Markdown")
            else:
                await query.edit_message_text(caption, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass
    else:
        if photo:
            await update.message.reply_photo(photo=photo, caption=caption, reply_markup=kb, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, reply_markup=kb, parse_mode="Markdown")
    return MENU_BROWSE

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    cart = ctx.user_data.get("cart", {})
    keys = ctx.user_data.get("menu_keys", [])
    idx = ctx.user_data.get("menu_idx", 0)

    if data == "m_next" and idx < len(keys) - 1:
        ctx.user_data["menu_idx"] += 1
    elif data == "m_prev" and idx > 0:
        ctx.user_data["menu_idx"] -= 1
    elif data == "m_plus":
        name = keys[idx]
        cart[name] = cart.get(name, 0) + 1
    elif data == "m_minus":
        name = keys[idx]
        if cart.get(name, 0) > 0:
            cart[name] -= 1
            if cart[name] == 0: del cart[name]
    elif data == "m_checkout":
        return await upsell_start(update, ctx)

    return await send_menu_card(update, ctx, from_callback=True)

# ==============================================================
# UPSELL
# ==============================================================

async def upsell_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["upsell_idx"] = 0
    return await send_upsell(update, ctx)

async def send_upsell(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    idx = ctx.user_data.get("upsell_idx", 0)
    if idx >= len(UPSELL_ITEMS):
        return await payment_start(update, ctx)

    item = UPSELL_ITEMS[idx]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Ha, qo'shaman ({item['price']:,} so'm)", callback_data="up_yes")],
        [InlineKeyboardButton("❌ Yo'q, kerak emas", callback_data="up_no")],
    ])
    text = f"🎁 *Qo'shimcha taklif:*\n\n{item['name']} — {item['price']:,} so'm\n\nQo'shasizmi?"
    query = update.callback_query
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return UPSELL

async def upsell_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    idx = ctx.user_data.get("upsell_idx", 0)
    if query.data == "up_yes":
        item = UPSELL_ITEMS[idx]
        cart = ctx.user_data.get("cart", {})
        cart[item["name"]] = cart.get(item["name"], 0) + 1
        if item["name"] not in menu:
            menu[item["name"]] = {"price": item["price"], "photo_id": None}
    ctx.user_data["upsell_idx"] += 1
    return await send_upsell(update, ctx)

# ==============================================================
# TO'LOV
# ==============================================================

async def payment_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    cart = ctx.user_data.get("cart", {})
    items = [{"name": n, "qty": q, "price": item_price(menu[n])} for n, q in cart.items()]
    total = cart_total(cart)
    ctx.user_data["order_items"] = items
    ctx.user_data["order_total"] = total

    cl = "\n".join(f"  • {i['name']} x{i['qty']} — {i['qty'] * i['price']:,} so'm" for i in items)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Naqd (yetkazganda)", callback_data="pay_cash")],
        [InlineKeyboardButton("💳 Karta orqali", callback_data="pay_card")],
    ])
    text = f"📦 *Buyurtmangiz:*\n{cl}\n\n💰 *Jami: {total:,} so'm*\n\nTo'lov usulini tanlang:"
    await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return PAYMENT

async def payment_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    payment = "cash" if query.data == "pay_cash" else "card"
    ctx.user_data["payment"] = payment
    total = ctx.user_data["order_total"]
    cl = "\n".join(f"  • {i['name']} x{i['qty']} — {i['qty'] * i['price']:,} so'm" for i in ctx.user_data["order_items"])
    pay_text = "💵 Naqd" if payment == "cash" else f"💳 Karta: *{CARD_NUMBER}*"
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data="cf_yes")], [InlineKeyboardButton("✏️ O'zgartirish", callback_data="cf_no")]])
    text = f"📦 *Buyurtmangiz:*\n{cl}\n\n💰 *Jami: {total:,} so'm*\nTo'lov: {pay_text}\n\nTasdiqlaysizmi?"
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    return CONFIRM

async def confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "cf_no":
        ctx.user_data["menu_idx"] = 0
        return await send_menu_card(update, ctx)

    uid = update.effective_user.id
    order_counter[0] += 1
    oid = order_counter[0]
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    order = {
        "id": oid, "user_id": uid, "items": ctx.user_data["order_items"],
        "payment": ctx.user_data["payment"], "total": ctx.user_data["order_total"],
        "time": now, "status": "new", "rated": False, "rating": 0
    }
    orders[oid] = order
    users[uid].setdefault("orders", []).append(oid)
    save_data()

    await query.edit_message_text(f"✅ *Buyurtma #{oid} qabul qilindi!*\n💰 Jami: {order['total']:,} so'm\n🚚 Tez orada yetkazamiz!", parse_mode="Markdown")
    
    if ADMIN_ID:
        try:
            admin_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("👨‍🍳 Tayyorlanmoqda", callback_data=f"st_{oid}_cooking")],
                [InlineKeyboardButton("🚚 Yetkazilmoqda", callback_data=f"st_{oid}_delivering")],
                [InlineKeyboardButton("✅ Yetkazildi", callback_data=f"st_{oid}_delivered")]
            ])
            await ctx.bot.send_message(ADMIN_ID, order_admin_text(order, users[uid]), reply_markup=admin_kb, parse_mode="Markdown")
        except: pass
    return ConversationHandler.END

# ==============================================================
# ADMIN VA BOShQA FUNKSIYALAR
# ==============================================================

async def status_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, oid_str, new_status = query.data.split("_", 2)
    oid = int(oid_str)
    orders[oid]["status"] = new_status
    save_data()
    await query.edit_message_text(order_admin_text(orders[oid], users[orders[oid]["user_id"]]), parse_mode="Markdown")

async def rate_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, oid_str, rating = query.data.split("_")
    oid = int(oid_str)
    orders[oid]["rating"] = int(rating)
    orders[oid]["rated"] = True
    save_data()
    await query.edit_message_text("Rahmat! Bahoingiz qabul qilindi.")

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    oids = users.get(uid, {}).get("orders", [])
    if not oids:
        await update.message.reply_text("Sizda hali buyurtmalar yo'q.")
        return
    text = "📦 *Oxirgi buyurtmalaringiz:*\n\n"
    for oid in reversed(oids[-5:]):
        o = orders[oid]
        text += f"#{oid} | {o['time']} | {o['total']:,} so'm | {o['status']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def my_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = users[update.effective_user.id]
    await update.message.reply_text(f"👤 *Profil:*\nIsm: {u['name']}\nTel: {u['phone']}\nJami buyurtma: {u['order_count']}", parse_mode="Markdown")

async def admin_menu_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    menu.clear()
    ctx.user_data["menu_active"] = True
    await update.message.reply_text("📋 Menyu kiriting (Taom - Narx). Tugagach /done yuboring.")
    return ADMIN_MENU_INPUT

async def admin_menu_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        name, price = update.message.text.split("-")
        menu[name.strip()] = {"price": int(price.strip()), "photo_id": None}
        await update.message.reply_text(f"✅ {name.strip()} qo'shildi.")
    except:
        await update.message.reply_text("Xato format! (Masalan: Osh - 25000)")
    return ADMIN_MENU_INPUT

async def admin_menu_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    save_data()
    await update.message.reply_text("✅ Menyu saqlandi.")
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=main_kb(update.effective_user.id))
    return ConversationHandler.END

# ==============================================================
# MAIN
# ==============================================================

def main():
    load_data()
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()

    reg_conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE: [MessageHandler(filters.CONTACT | filters.TEXT, reg_phone)],
            REG_LOCATION: [MessageHandler(filters.LOCATION | filters.TEXT, reg_location)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    order_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🍽 Buyurtma berish$"), order_start)],
        states={
            MENU_BROWSE: [CallbackQueryHandler(menu_callback)],
            UPSELL: [CallbackQueryHandler(upsell_callback, pattern="^up_")],
            PAYMENT: [CallbackQueryHandler(payment_callback, pattern="^pay_")],
            CONFIRM: [CallbackQueryHandler(confirm_callback, pattern="^cf_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    menu_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Menyu kiritish$"), admin_menu_start)],
        states={ADMIN_MENU_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_text), CommandHandler("done", admin_menu_done)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(reg_conv)
    app.add_handler(order_conv)
    app.add_handler(menu_conv)
    app.add_handler(CallbackQueryHandler(status_callback, pattern=r"^st_"))
    app.add_handler(CallbackQueryHandler(rate_callback, pattern=r"^rate_"))
    app.add_handler(MessageHandler(filters.Regex("^📦 Buyurtmalarim$"), my_orders))
    app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), my_profile))

    print("✅ Gulcha Taom Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
