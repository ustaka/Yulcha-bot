“””
Gulcha Taom - Telegram buyurtma boti
python-telegram-bot==20.7
“””

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

TOKEN = os.getenv(“BOT_TOKEN”, “”)
ADMIN_ID = int(os.getenv(“ADMIN_ID”, “0”))
CARD_NUMBER = os.getenv(“CARD_NUMBER”, “0000 0000 0000 0000”)
DATA_FILE = “data.json”

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

# GLOBAL MA’LUMOTLAR

# ==============================================================

# users[user_id] = {name, phone, address, lat, lon, joined,

# orders[], total_spent, order_count,

# favorite_items{}, vip, last_order}

users: dict = {}

# menu[name] = {price: int, photo_id: str|None}

menu: dict = {}

# orders[order_id] = {id, user_id, items[], payment,

# total, time, status, rated, rating}

orders: dict = {}

order_counter: list = [0]

stats: dict = {
“total_orders”: 0,
“total_revenue”: 0,
“daily”: {},
“weekly”: {},
}

UPSELL_ITEMS = [
{“name”: “🥤 Cola”, “price”: 8000},
{“name”: “🍞 Non”, “price”: 3000},
{“name”: “🥗 Salat”, “price”: 12000},
]

logging.basicConfig(
format=”%(asctime)s [%(levelname)s] %(message)s”,
level=logging.INFO,
)
log = logging.getLogger(**name**)

# ==============================================================

# JSON SAQLASH / YUKLASH

# ==============================================================

def save_data() -> None:
try:
payload = {
“users”: {str(k): v for k, v in users.items()},
“menu”: menu,
“orders”: {str(k): v for k, v in orders.items()},
“order_counter”: order_counter[0],
“stats”: stats,
}
with open(DATA_FILE, “w”, encoding=“utf-8”) as fh:
json.dump(payload, fh, ensure_ascii=False, indent=2)
except Exception as exc:
log.error(“save_data xatosi: %s”, exc)

def load_data() -> None:
global users, menu, orders, stats
if not os.path.exists(DATA_FILE):
return
try:
with open(DATA_FILE, “r”, encoding=“utf-8”) as fh:
payload = json.load(fh)
users = {int(k): v for k, v in payload.get(“users”, {}).items()}
menu = payload.get(“menu”, {})
orders = {int(k): v for k, v in payload.get(“orders”, {}).items()}
order_counter[0] = payload.get(“order_counter”, 0)
stats.update(payload.get(“stats”, {}))
log.info(“Yuklandi: %d mijoz, %d buyurtma”, len(users), len(orders))
except Exception as exc:
log.error(“load_data xatosi: %s”, exc)

# ==============================================================

# YORDAMCHI FUNKSIYALAR

# ==============================================================

def is_admin(uid: int) -> bool:
return uid == ADMIN_ID

def today_str() -> str:
return datetime.now().strftime(”%d.%m.%Y”)

def week_key() -> str:
now = datetime.now()
return (now - timedelta(days=now.weekday())).strftime(”%d.%m.%Y”)

def gmap(lat, lon) -> str:
return f”https://maps.google.com/?q={lat},{lon}”

def item_price(item) -> int:
if isinstance(item, dict):
return int(item.get(“price”, 0))
return int(item)

def item_photo(item):
if isinstance(item, dict):
return item.get(“photo_id”) or None
return None

def admin_keyboard():
return ReplyKeyboardMarkup(
[
[“📋 Menyu kiritish”, “📦 Buyurtmalar”],
[“📢 Xabar yuborish”, “📊 Hisobot”],
[“👥 Mijozlar bazasi”],
],
resize_keyboard=True,
)

def user_keyboard():
return ReplyKeyboardMarkup(
[
[“🍽 Buyurtma berish”],
[“📦 Buyurtmalarim”, “👤 Profilim”],
[“📍 Manzilni yangilash”],
],
resize_keyboard=True,
)

def main_kb(uid: int):
return admin_keyboard() if is_admin(uid) else user_keyboard()

def order_admin_text(order: dict, user: dict) -> str:
lines = “\n”.join(
f”  • {i[‘name’]} x{i[‘qty’]} — {i[‘qty’] * i[‘price’]:,} so’m”
for i in order[“items”]
)
pay = “💵 Naqd” if order[“payment”] == “cash” else “💳 Karta”
statuses = {
“new”: “🆕 Yangi”,
“cooking”: “👨‍🍳 Tayyorlanmoqda”,
“delivering”: “🚚 Yetkazilmoqda”,
“delivered”: “✅ Yetkazildi”,
“cancelled”: “❌ Bekor”,
}
status = statuses.get(order.get(“status”, “new”), “🆕 Yangi”)
lat, lon = user.get(“lat”), user.get(“lon”)
if lat and lon:
loc = f”📍 [{user.get(‘address’, ‘Manzil’)}]({gmap(lat, lon)})”
else:
loc = f”📍 {user.get(‘address’, ‘Noma`lum’)}”
return (
f”🔔 *Buyurtma #{order[‘id’]}*\n\n”
f”👤 {user.get(‘name’, ‘?’)}\n”
f”📞 {user.get(‘phone’, ‘?’)}\n”
f”{loc}\n\n”
f”🍽 *Tarkib:*\n{lines}\n\n”
f”💰 *Jami: {order[‘total’]:,} so’m*\n”
f”{pay}\n”
f”📌 {status}\n”
f”🕐 {order[‘time’]}”
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
rows.append(f”  • {name} x{qty} — {qty * p:,} so’m”)
return “\n”.join(rows)

# ==============================================================

# /start

# ==============================================================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id

```
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
```

# ==============================================================

# RO’YXATDAN O’TISH

# ==============================================================

async def reg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data[“reg_name”] = update.message.text.strip()
kb = [[KeyboardButton(“📱 Telefon raqamni yuborish”, request_contact=True)]]
await update.message.reply_text(
“📱 Telefon raqamingizni yuboring:”,
reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
)
return REG_PHONE

async def reg_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if update.message.contact:
phone = update.message.contact.phone_number
if not phone.startswith(”+”):
phone = “+” + phone
else:
phone = update.message.text.strip()
ctx.user_data[“reg_phone”] = phone

```
kb = [[KeyboardButton("📍 Lokatsiyamni yuborish", request_location=True)]]
await update.message.reply_text(
    "📍 Ofis yoki yetkazib berish manzilingizni yuboring:\n"
    "_(kuryer to'g'ri manzilni topadi)_",
    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
    parse_mode="Markdown",
)
return REG_LOCATION
```

async def reg_location(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if update.message.location:
lat = update.message.location.latitude
lon = update.message.location.longitude
address = f”{lat:.5f}, {lon:.5f}”
else:
lat, lon = None, None
address = update.message.text.strip()

```
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
```

# ==============================================================

# MANZIL YANGILASH

# ==============================================================

async def change_loc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return ConversationHandler.END
kb = [[KeyboardButton(“📍 Yangi lokatsiyamni yuborish”, request_location=True)]]
await update.message.reply_text(
“📍 Yangi manzilni yuboring:”,
reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
)
return CHANGE_LOCATION

async def change_loc_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if update.message.location:
lat = update.message.location.latitude
lon = update.message.location.longitude
address = f”{lat:.5f}, {lon:.5f}”
else:
lat, lon = None, None
address = update.message.text.strip()

```
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
```

# ==============================================================

# BUYURTMA — MENYU KO’RISH

# ==============================================================

async def order_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing va ro’yxatdan o’ting.”)
return ConversationHandler.END
if not menu:
await update.message.reply_text(“⏳ Bugungi menyu hali tayyor emas.”)
return ConversationHandler.END

```
ctx.user_data["cart"] = {}
ctx.user_data["menu_keys"] = list(menu.keys())
ctx.user_data["menu_idx"] = 0
return await send_menu_card(update, ctx, from_callback=False)
```

def build_menu_keyboard(name: str, qty: int, cart: dict, idx: int, total_items: int) -> InlineKeyboardMarkup:
# Navigatsiya qatori
nav = []
if idx > 0:
nav.append(InlineKeyboardButton(“◀️”, callback_data=“m_prev”))
nav.append(InlineKeyboardButton(f”{idx + 1} / {total_items}”, callback_data=“m_noop”))
if idx < total_items - 1:
nav.append(InlineKeyboardButton(“▶️”, callback_data=“m_next”))

```
# Miqdor qatori
qty_row = [
    InlineKeyboardButton("➖", callback_data=f"m_minus"),
    InlineKeyboardButton(f"  {qty} ta  ", callback_data="m_noop"),
    InlineKeyboardButton("➕", callback_data=f"m_plus"),
]

rows = [nav, qty_row]

# Buyurtma berish tugmasi
if cart:
    total = cart_total(cart)
    rows.append([
        InlineKeyboardButton(
            f"✅ Buyurtma berish — {total:,} so'm",
            callback_data="m_checkout",
        )
    ])

return InlineKeyboardMarkup(rows)
```

async def send_menu_card(
update: Update,
ctx: ContextTypes.DEFAULT_TYPE,
from_callback: bool = True,
) -> int:
cart: dict = ctx.user_data.get(“cart”, {})
keys: list = ctx.user_data.get(“menu_keys”, [])
idx: int = ctx.user_data.get(“menu_idx”, 0)

```
if not keys or idx >= len(keys):
    return MENU_BROWSE

name = keys[idx]
if name not in menu:
    return MENU_BROWSE

m_item = menu[name]
price = item_price(m_item)
photo = item_photo(m_item)
qty = cart.get(name, 0)

# Savatcha ma'lumoti
if cart:
    cl = cart_lines(cart)
    total = cart_total(cart)
    cart_info = f"\n\n🛒 *Savatcha:*\n{cl}\n💰 Jami: {total:,} so'm"
else:
    cart_info = ""

caption = (
    f"🍽 *{name}*\n"
    f"💰 Narxi: {price:,} so'm"
    f"{cart_info}"
)

kb = build_menu_keyboard(name, qty, cart, idx, len(keys))

if from_callback:
    query = update.callback_query
    if photo:
        # Rasm bor — yangi xabar yuboramiz
        try:
            await query.message.delete()
        except Exception:
            pass
        await ctx.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=caption,
            reply_markup=kb,
            parse_mode="Markdown",
        )
    else:
        # Rasm yo'q — mavjud xabarni edit qilamiz
        try:
            await query.edit_message_text(
                caption,
                reply_markup=kb,
                parse_mode="Markdown",
            )
        except Exception:
            await ctx.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption,
                reply_markup=kb,
                parse_mode="Markdown",
            )
else:
    # Yangi xabar
    if photo:
        await update.message.reply_photo(
            photo=photo,
            caption=caption,
            reply_markup=kb,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=kb,
            parse_mode="Markdown",
        )

return MENU_BROWSE
```

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
query = update.callback_query
await query.answer()

```
data = query.data
cart: dict = ctx.user_data.get("cart", {})
keys: list = ctx.user_data.get("menu_keys", [])
idx: int = ctx.user_data.get("menu_idx", 0)

if data == "m_noop":
    return MENU_BROWSE

if data == "m_next":
    if idx < len(keys) - 1:
        ctx.user_data["menu_idx"] = idx + 1
    return await send_menu_card(update, ctx, from_callback=True)

if data == "m_prev":
    if idx > 0:
        ctx.user_data["menu_idx"] = idx - 1
    return await send_menu_card(update, ctx, from_callback=True)

if data == "m_plus":
    name = keys[idx]
    cart[name] = cart.get(name, 0) + 1
    ctx.user_data["cart"] = cart
    return await send_menu_card(update, ctx, from_callback=True)

if data == "m_minus":
    name = keys[idx]
    if cart.get(name, 0) > 0:
        cart[name] -= 1
        if cart[name] == 0:
            del cart[name]
    ctx.user_data["cart"] = cart
    return await send_menu_card(update, ctx, from_callback=True)

if data == "m_checkout":
    if not cart:
        await query.answer("Savatcha bo'sh!", show_alert=True)
        return MENU_BROWSE
    return await upsell_start(update, ctx)

return MENU_BROWSE
```

# ==============================================================

# UPSELL

# ==============================================================

async def upsell_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
ctx.user_data[“upsell_idx”] = 0
return await send_upsell(update, ctx)

async def send_upsell(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
idx = ctx.user_data.get(“upsell_idx”, 0)
if idx >= len(UPSELL_ITEMS):
return await payment_start(update, ctx)

```
item = UPSELL_ITEMS[idx]
kb = InlineKeyboardMarkup([
    [InlineKeyboardButton(
        f"✅ Ha, qo'shaman ({item['price']:,} so'm)",
        callback_data="up_yes",
    )],
    [InlineKeyboardButton("❌ Yo'q, kerak emas", callback_data="up_no")],
])
text = (
    f"🎁 *Qo'shimcha taklif:*\n\n"
    f"{item['name']} — {item['price']:,} so'm\n\n"
    f"Qo'shasizmi?"
)
query = update.callback_query
try:
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
except Exception:
    await ctx.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=kb,
        parse_mode="Markdown",
    )
return UPSELL
```

async def upsell_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
query = update.callback_query
await query.answer()

```
idx = ctx.user_data.get("upsell_idx", 0)
item = UPSELL_ITEMS[idx]

if query.data == "up_yes":
    cart: dict = ctx.user_data.get("cart", {})
    cart[item["name"]] = cart.get(item["name"], 0) + 1
    ctx.user_data["cart"] = cart
    if item["name"] not in menu:
        menu[item["name"]] = {"price": item["price"], "photo_id": None}

ctx.user_data["upsell_idx"] = idx + 1
return await send_upsell(update, ctx)
```

# ==============================================================

# TO’LOV

# ==============================================================

async def payment_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
cart: dict = ctx.user_data.get(“cart”, {})
total = cart_total(cart)
items = [
{“name”: n, “qty”: q, “price”: item_price(menu[n]) if n in menu else 0}
for n, q in cart.items()
if q > 0
]
ctx.user_data[“order_items”] = items
ctx.user_data[“order_total”] = total

```
cl = "\n".join(
    f"  • {i['name']} x{i['qty']} — {i['qty'] * i['price']:,} so'm"
    for i in items
)
kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("💵 Naqd (yetkazganda)", callback_data="pay_cash")],
    [InlineKeyboardButton("💳 Karta orqali", callback_data="pay_card")],
])
text = (
    f"📦 *Buyurtmangiz:*\n{cl}\n\n"
    f"💰 *Jami: {total:,} so'm*\n\n"
    f"To'lov usulini tanlang:"
)
query = update.callback_query
try:
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
except Exception:
    await ctx.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=kb,
        parse_mode="Markdown",
    )
return PAYMENT
```

async def payment_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
query = update.callback_query
await query.answer()

```
payment = "cash" if query.data == "pay_cash" else "card"
ctx.user_data["payment"] = payment

items = ctx.user_data["order_items"]
total = ctx.user_data["order_total"]
cl = "\n".join(
    f"  • {i['name']} x{i['qty']} — {i['qty'] * i['price']:,} so'm"
    for i in items
)
if payment == "cash":
    pay_text = "💵 Naqd (yetkazganda)"
else:
    pay_text = f"💳 Karta: *{CARD_NUMBER}*"

kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Tasdiqlash", callback_data="cf_yes")],
    [InlineKeyboardButton("✏️ O'zgartirish", callback_data="cf_no")],
])
text = (
    f"📦 *Buyurtmangiz:*\n{cl}\n\n"
    f"💰 *Jami: {total:,} so'm*\n"
    f"To'lov: {pay_text}\n\n"
    f"Tasdiqlaysizmi?"
)
try:
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
except Exception:
    await ctx.bot.send_message(
        chat_id=query.message.chat_id,
        text=text,
        reply_markup=kb,
        parse_mode="Markdown",
    )
return CONFIRM
```

async def confirm_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
query = update.callback_query
await query.answer()

```
if query.data == "cf_no":
    # Menyuga qaytish
    ctx.user_data["cart"] = {
        i["name"]: i["qty"]
        for i in ctx.user_data.get("order_items", [])
    }
    ctx.user_data["menu_idx"] = 0
    return await send_menu_card(update, ctx, from_callback=True)

# Buyurtmani saqlash
uid = update.effective_user.id
user = users[uid]
items = ctx.user_data["order_items"]
payment = ctx.user_data["payment"]
total = ctx.user_data["order_total"]

order_counter[0] += 1
oid = order_counter[0]
now = datetime.now().strftime("%d.%m.%Y %H:%M")

order = {
    "id": oid,
    "user_id": uid,
    "items": items,
    "payment": payment,
    "total": total,
    "time": now,
    "status": "new",
    "rated": False,
    "rating": 0,
}
orders[oid] = order

# CRM
users[uid].setdefault("orders", []).append(oid)
users[uid]["total_spent"] = users[uid].get("total_spent", 0) + total
users[uid]["order_count"] = users[uid].get("order_count", 0) + 1
users[uid]["last_order"] = now
fav = users[uid].setdefault("favorite_items", {})
for it in items:
    fav[it["name"]] = fav.get(it["name"], 0) + it["qty"]
if users[uid]["order_count"] >= 5 or users[uid]["total_spent"] >= 500_000:
    users[uid]["vip"] = True

# Statistika
td = today_str()
wk = week_key()
stats["total_orders"] += 1
stats["total_revenue"] += total
stats["daily"][td] = stats["daily"].get(td, 0) + 1
stats["weekly"][wk] = stats["weekly"].get(wk, 0) + 1
save_data()

# Mijozga xabar
if payment == "cash":
    pay_info = "💵 Naqd — yetkazganda to'laysiz"
else:
    pay_info = f"💳 Karta: {CARD_NUMBER}\nO'tkazma qiling va tasdiqlang"

try:
    await query.edit_message_text(
        f"✅ *Buyurtmangiz qabul qilindi!*\n\n"
        f"📦 Buyurtma #{oid}\n"
        f"💰 Jami: {total:,} so'm\n"
        f"{pay_info}\n\n"
        f"🚚 Tez orada yetkazib boramiz!",
        parse_mode="Markdown",
    )
except Exception:
    await ctx.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            f"✅ *Buyurtmangiz qabul qilindi!*\n\n"
            f"📦 Buyurtma #{oid}\n"
            f"💰 Jami: {total:,} so'm\n"
            f"{pay_info}\n\n"
            f"🚚 Tez orada yetkazib boramiz!"
        ),
        parse_mode="Markdown",
    )

# Adminga xabar
if ADMIN_ID:
    try:
        lat, lon = user.get("lat"), user.get("lon")
        if lat and lon:
            await ctx.bot.send_location(
                chat_id=ADMIN_ID, latitude=lat, longitude=lon
            )
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍🍳 Tayyorlanmoqda", callback_data=f"st_{oid}_cooking")],
            [InlineKeyboardButton("🚚 Yetkazilmoqda", callback_data=f"st_{oid}_delivering")],
            [InlineKeyboardButton("✅ Yetkazildi", callback_data=f"st_{oid}_delivered")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"st_{oid}_cancelled")],
        ])
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=order_admin_text(order, user),
            reply_markup=admin_kb,
            parse_mode="Markdown",
        )
    except Exception as exc:
        log.error("Admin xabari yuborilmadi: %s", exc)

return ConversationHandler.END
```

# ==============================================================

# ADMIN — BUYURTMA HOLATI

# ==============================================================

async def status_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
if not is_admin(update.effective_user.id):
    return

_, oid_str, new_status = query.data.split("_", 2)
oid = int(oid_str)

if oid not in orders:
    await query.answer("Buyurtma topilmadi!", show_alert=True)
    return

orders[oid]["status"] = new_status
save_data()

user = users.get(orders[oid]["user_id"], {})
try:
    await query.edit_message_text(
        order_admin_text(orders[oid], user),
        parse_mode="Markdown",
    )
except Exception:
    pass

uid = orders[oid]["user_id"]
msgs = {
    "cooking": f"👨‍🍳 *Buyurtma #{oid}* tayyorlanmoqda!",
    "delivering": f"🚚 *Buyurtma #{oid}* yo'lda!",
    "cancelled": f"❌ *Buyurtma #{oid}* bekor qilindi. Kechirasiz!",
}
if new_status == "delivered":
    rate_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("1⭐", callback_data=f"rate_{oid}_1"),
        InlineKeyboardButton("2⭐", callback_data=f"rate_{oid}_2"),
        InlineKeyboardButton("3⭐", callback_data=f"rate_{oid}_3"),
        InlineKeyboardButton("4⭐", callback_data=f"rate_{oid}_4"),
        InlineKeyboardButton("5⭐", callback_data=f"rate_{oid}_5"),
    ]])
    try:
        await ctx.bot.send_message(
            uid,
            f"✅ *Buyurtma #{oid}* yetkazildi!\n\nIltimos, taomni baholang 👇",
            reply_markup=rate_kb,
            parse_mode="Markdown",
        )
    except Exception:
        pass
elif new_status in msgs:
    try:
        await ctx.bot.send_message(uid, msgs[new_status], parse_mode="Markdown")
    except Exception:
        pass
```

# ==============================================================

# BAHOLASH

# ==============================================================

async def rate_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
_, oid_str, rating_str = query.data.split("_")
oid = int(oid_str)
rating = int(rating_str)

if oid in orders and not orders[oid].get("rated"):
    orders[oid]["rating"] = rating
    orders[oid]["rated"] = True
    save_data()

stars = "⭐" * rating
try:
    await query.edit_message_text(f"Rahmat! {stars}\nBahoingiz qabul qilindi! 🙏")
except Exception:
    pass

if ADMIN_ID:
    try:
        u = users.get(orders[oid]["user_id"], {})
        await ctx.bot.send_message(
            ADMIN_ID,
            f"⭐ #{oid} — {u.get('name','?')} — {stars} ({rating}/5)",
        )
    except Exception:
        pass
```

# ==============================================================

# MENING BUYURTMALARIM

# ==============================================================

async def my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return

```
oids = users[uid].get("orders", [])
if not oids:
    await update.message.reply_text("Siz hali buyurtma bermagansiz.")
    return

status_icon = {
    "new": "🆕", "cooking": "👨‍🍳",
    "delivering": "🚚", "delivered": "✅", "cancelled": "❌",
}
text = "📦 *Oxirgi buyurtmalaringiz:*\n\n"
for oid in reversed(oids[-5:]):
    if oid in orders:
        o = orders[oid]
        items_str = ", ".join(f"{i['name']} x{i['qty']}" for i in o["items"])
        st = status_icon.get(o.get("status", "new"), "🆕")
        rating_str = f" {'⭐' * o['rating']}" if o.get("rated") else ""
        text += (
            f"{st} *#{oid}* | {o['time']}\n"
            f"{items_str}\n"
            f"💰 {o['total']:,} so'm{rating_str}\n\n"
        )
await update.message.reply_text(text, parse_mode="Markdown")
```

# ==============================================================

# PROFIL

# ==============================================================

async def my_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
if uid not in users:
await update.message.reply_text(“Avval /start bosing.”)
return
u = users[uid]
fav_items = u.get(“favorite_items”, {})
fav = max(fav_items, key=fav_items.get) if fav_items else “-”
vip = “👑 VIP mijoz” if u.get(“vip”) else “Oddiy mijoz”
lat, lon = u.get(“lat”), u.get(“lon”)
map_url = f”\n🗺 [Xaritada ko’rish]({gmap(lat, lon)})” if lat and lon else “”

```
await update.message.reply_text(
    f"👤 *Profilingiz:*\n\n"
    f"Ism: {u['name']}\n"
    f"Telefon: {u['phone']}\n"
    f"Manzil: {u.get('address', '?')}{map_url}\n"
    f"Ro'yxat: {u.get('joined', '?')}\n\n"
    f"📊 *Statistika:*\n"
    f"Buyurtmalar: {u.get('order_count', 0)} ta\n"
    f"Jami xarid: {u.get('total_spent', 0):,} so'm\n"
    f"Sevimli taom: {fav}\n"
    f"Status: {vip}",
    parse_mode="Markdown",
)
```

# ==============================================================

# ADMIN — MENYU KIRITISH

# ==============================================================

async def admin_menu_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return ConversationHandler.END
menu.clear()
ctx.user_data[“menu_active”] = True
await update.message.reply_text(
“📋 *Bugungi menyuni kiriting*\n\n”
“Har bir taom uchun:\n”
“• *Rasmsiz:* `Taom nomi - narx`\n”
“• *Rasmli:* Rasmni yuboring, caption da: `Taom nomi - narx`\n\n”
“Masalan: `Osh - 25000`\n\n”
“Tugagach /done yuboring.”,
parse_mode=“Markdown”,
)
return ADMIN_MENU_INPUT

async def admin_menu_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not ctx.user_data.get(“menu_active”):
return ConversationHandler.END
raw = update.message.text.strip()
if “ - “ not in raw:
await update.message.reply_text(
“❌ Format noto’g’ri.\nMasalan: `Osh - 25000`”, parse_mode=“Markdown”
)
return ADMIN_MENU_INPUT
name, price_str = raw.split(” - “, 1)
name = name.strip()
price_str = price_str.strip().replace(”,”, “”).replace(” “, “”)
if not price_str.isdigit():
await update.message.reply_text(“❌ Narx faqat raqam bo’lishi kerak.”)
return ADMIN_MENU_INPUT
price = int(price_str)
menu[name] = {“price”: price, “photo_id”: None}
await update.message.reply_text(
f”✅ *{name}* — {price:,} so’m qo’shildi.”, parse_mode=“Markdown”
)
return ADMIN_MENU_INPUT

async def admin_menu_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not ctx.user_data.get(“menu_active”):
return ConversationHandler.END
caption = (update.message.caption or “”).strip()
if “ - “ not in caption:
await update.message.reply_text(
“❌ Caption formatı: `Taom nomi - narx`”, parse_mode=“Markdown”
)
return ADMIN_MENU_INPUT
name, price_str = caption.split(” - “, 1)
name = name.strip()
price_str = price_str.strip().replace(”,”, “”).replace(” “, “”)
if not price_str.isdigit():
await update.message.reply_text(“❌ Narx faqat raqam bo’lishi kerak.”)
return ADMIN_MENU_INPUT
price = int(price_str)
photo_id = update.message.photo[-1].file_id
menu[name] = {“price”: price, “photo_id”: photo_id}
await update.message.reply_text(
f”✅ 🖼 *{name}* — {price:,} so’m (rasmli) qo’shildi.”, parse_mode=“Markdown”
)
return ADMIN_MENU_INPUT

async def admin_menu_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data[“menu_active”] = False
if not menu:
await update.message.reply_text(“Hech narsa kiritilmadi.”)
return ConversationHandler.END
save_data()
lines = []
for n, v in menu.items():
icon = “🖼” if isinstance(v, dict) and v.get(“photo_id”) else “📝”
lines.append(f”  {icon} {n} — {item_price(v):,} so’m”)
await update.message.reply_text(
f”✅ *Menyu saqlandi ({len(menu)} ta taom):*\n\n” + “\n”.join(lines),
parse_mode=“Markdown”,
)
return ConversationHandler.END

# ==============================================================

# ADMIN — BUYURTMALAR

# ==============================================================

async def admin_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return
td = today_str()
today_orders = [o for o in orders.values() if o[“time”].startswith(td)]
if not today_orders:
await update.message.reply_text(“Bugun hali buyurtma yo’q.”)
return
revenue = sum(o[“total”] for o in today_orders)
status_icon = {
“new”: “🆕”, “cooking”: “👨‍🍳”,
“delivering”: “🚚”, “delivered”: “✅”, “cancelled”: “❌”,
}
text = f”📦 *Bugungi buyurtmalar ({len(today_orders)} ta):*\n\n”
for o in today_orders:
u = users.get(o[“user_id”], {})
items_str = “, “.join(f”{i[‘name’]} x{i[‘qty’]}” for i in o[“items”])
st = status_icon.get(o.get(“status”, “new”), “🆕”)
pay = “Naqd” if o[“payment”] == “cash” else “Karta”
text += f”{st} *#{o[‘id’]}* | {u.get(‘name’,’?’)} | {items_str} | {o[‘total’]:,} so’m | {pay}\n”
text += f”\n💰 *Jami: {revenue:,} so’m*”
await update.message.reply_text(text, parse_mode=“Markdown”)

# ==============================================================

# ADMIN — MIJOZLAR BAZASI

# ==============================================================

async def admin_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return
if not users:
await update.message.reply_text(“Hali mijoz yo’q.”)
return

```
td = today_str()
vip_count = sum(1 for u in users.values() if u.get("vip"))
active = len({o["user_id"] for o in orders.values() if o["time"].startswith(td)})

text = (
    f"👥 *Mijozlar bazasi*\n\n"
    f"Jami: {len(users)} ta\n"
    f"👑 VIP: {vip_count} ta\n"
    f"Bugun faol: {active} ta\n\n"
    f"{'─' * 25}\n\n"
)
for uid, u in users.items():
    icon = "👑 " if u.get("vip") else ""
    lat, lon = u.get("lat"), u.get("lon")
    map_link = f" [🗺]({gmap(lat, lon)})" if lat and lon else ""
    last = u.get("last_order") or u.get("joined", "?")
    text += (
        f"{icon}*{u['name']}*\n"
        f"📞 {u['phone']}{map_link}\n"
        f"📦 {u.get('order_count', 0)} buyurtma | 💰 {u.get('total_spent', 0):,} so'm\n"
        f"🕐 Oxirgi: {last}\n\n"
    )
    if len(text) > 3500:
        await update.message.reply_text(text, parse_mode="Markdown")
        text = ""
if text:
    await update.message.reply_text(text, parse_mode="Markdown")
```

# ==============================================================

# ADMIN — XABAR YUBORISH

# ==============================================================

async def admin_broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return ConversationHandler.END
await update.message.reply_text(
f”📢 Barcha *{len(users)}* ta mijozga xabar yozing:\n(/cancel — bekor qilish)”,
parse_mode=“Markdown”,
)
return ADMIN_BROADCAST

async def admin_broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
text = update.message.text
sent = failed = 0
for uid in users:
try:
await ctx.bot.send_message(uid, text)
sent += 1
except Exception:
failed += 1
await update.message.reply_text(
f”✅ Xabar yuborildi!\n📤 Yuborildi: {sent}\n❌ Yuborilmadi: {failed}”
)
return ConversationHandler.END

# ==============================================================

# ADMIN — HISOBOT

# ==============================================================

async def admin_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
if not is_admin(update.effective_user.id):
return
td = today_str()
today_orders = [o for o in orders.values() if o[“time”].startswith(td)]
today_rev = sum(o[“total”] for o in today_orders)

```
wk = week_key()
week_count = stats["weekly"].get(wk, 0)

rated = [o for o in orders.values() if o.get("rated")]
avg_rating = sum(o["rating"] for o in rated) / len(rated) if rated else 0

best_day = max(stats["daily"], key=stats["daily"].get) if stats["daily"] else "-"
best_count = stats["daily"].get(best_day, 0)
avg_check = stats["total_revenue"] // stats["total_orders"] if stats["total_orders"] else 0
vip_count = sum(1 for u in users.values() if u.get("vip"))

item_counts: dict = {}
for o in orders.values():
    for i in o["items"]:
        item_counts[i["name"]] = item_counts.get(i["name"], 0) + i["qty"]
top = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:3]
top_text = "\n".join(f"  {i+1}. {n} — {c} ta" for i, (n, c) in enumerate(top)) or "  -"

await update.message.reply_text(
    f"📊 *To'liq hisobot*\n\n"
    f"📅 *Bugun ({td}):*\n"
    f"  Buyurtmalar: {len(today_orders)} ta\n"
    f"  Tushum: {today_rev:,} so'm\n\n"
    f"📆 *Bu hafta:* {week_count} ta\n\n"
    f"📈 *Jami:*\n"
    f"  Buyurtmalar: {stats['total_orders']} ta\n"
    f"  Tushum: {stats['total_revenue']:,} so'm\n"
    f"  O'rtacha chek: {avg_check:,} so'm\n"
    f"  Mijozlar: {len(users)} ta\n"
    f"  👑 VIP: {vip_count} ta\n"
    f"  ⭐ O'rtacha baho: {avg_rating:.1f}/5\n"
    f"  🏆 Eng faol kun: {best_day} ({best_count} ta)\n\n"
    f"🍽 *Top mahsulotlar:*\n{top_text}",
    parse_mode="Markdown",
)
```

# ==============================================================

# CANCEL

# ==============================================================

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
ctx.user_data.clear()
await update.message.reply_text(
“❌ Bekor qilindi.”,
reply_markup=main_kb(update.effective_user.id),
)
return ConversationHandler.END

# ==============================================================

# MAIN

# ==============================================================

def main():
load_data()

```
if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!\n"
        "Render > Environment > BOT_TOKEN = <token>"
    )

app = Application.builder().token(TOKEN).build()

# --- Ro'yxatdan o'tish ---
reg_conv = ConversationHandler(
    entry_points=[CommandHandler("start", cmd_start)],
    states={
        REG_NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
        REG_PHONE:    [
            MessageHandler(filters.CONTACT, reg_phone),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
        ],
        REG_LOCATION: [
            MessageHandler(filters.LOCATION, reg_location),
            MessageHandler(filters.TEXT & ~filters.COMMAND, reg_location),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# --- Buyurtma ---
order_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^🍽 Buyurtma berish$"), order_start)
    ],
    states={
        MENU_BROWSE: [CallbackQueryHandler(menu_callback)],
        UPSELL:      [CallbackQueryHandler(upsell_callback, pattern="^up_")],
        PAYMENT:     [CallbackQueryHandler(payment_callback, pattern="^pay_")],
        CONFIRM:     [CallbackQueryHandler(confirm_callback, pattern="^cf_")],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Menyu kiritish (admin) ---
menu_conv = ConversationHandler(
    entry_points=[
        CommandHandler("menyu", admin_menu_start),
        MessageHandler(filters.Regex("^📋 Menyu kiritish$"), admin_menu_start),
    ],
    states={
        ADMIN_MENU_INPUT: [
            MessageHandler(filters.PHOTO, admin_menu_photo),
            CommandHandler("done", admin_menu_done),
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_text),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Broadcast ---
broadcast_conv = ConversationHandler(
    entry_points=[
        CommandHandler("xabar", admin_broadcast_start),
        MessageHandler(filters.Regex("^📢 Xabar yuborish$"), admin_broadcast_start),
    ],
    states={
        ADMIN_BROADCAST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Manzil yangilash ---
loc_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex("^📍 Manzilni yangilash$"), change_loc_start)
    ],
    states={
        CHANGE_LOCATION: [
            MessageHandler(filters.LOCATION, change_loc_save),
            MessageHandler(filters.TEXT & ~filters.COMMAND, change_loc_save),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Handlerlarni qo'shish
app.add_handler(reg_conv)
app.add_handler(order_conv)
app.add_handler(menu_conv)
app.add_handler(broadcast_conv)
app.add_handler(loc_conv)

# Global callback handlerlar
app.add_handler(CallbackQueryHandler(status_callback, pattern=r"^st_\d+_\w+$"))
app.add_handler(CallbackQueryHandler(rate_callback, pattern=r"^rate_\d+_\d+$"))

# Admin tugma handlerlar
app.add_handler(MessageHandler(filters.Regex("^📦 Buyurtmalar$"), admin_orders))
app.add_handler(MessageHandler(filters.Regex("^📊 Hisobot$"), admin_report))
app.add_handler(MessageHandler(filters.Regex("^👥 Mijozlar bazasi$"), admin_users))

# Foydalanuvchi tugma handlerlar
app.add_handler(MessageHandler(filters.Regex("^📦 Buyurtmalarim$"), my_orders))
app.add_handler(MessageHandler(filters.Regex("^👤 Profilim$"), my_profile))

print("✅ Gulcha Taom Bot ishga tushdi!")
app.run_polling(drop_pending_updates=True)
```

if **name** == “**main**”:
main()
