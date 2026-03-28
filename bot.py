import logging
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== НАСТРОЙКИ ====================
# Проверка обязательных переменных окружения
def get_env_var(key, default=None, required=False):
    """Безопасное получение переменных окружения"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"❌ ОШИБКА: Переменная окружения '{key}' не установлена!")
    return value

TOKEN        = '7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ'
BOT_NAME = "Dark Stars || Buy Stars
BOT_USERNAME = @DarkStudiox_bot
ADMIN_IDS    = 174415647
SUPPORT_USERNAME = @hostelman

CARD_NUMBER    = get_env_var("CARD_NUMBER", "2200702051809809")
CARD_PHONE     = get_env_var("CARD_PHONE", "+79242143705")
CRYPTO_ADDRESS = get_env_var("CRYPTO_ADDRESS", "UQBWGb7EHQBMjFujxu0uUef33aaOuKM_xj_s_XaEz5tdS3Gi")

STARS_PRICE_RUB = float(get_env_var("STARS_PRICE_RUB", "1.3"))
RATES = {
    "rub": 1.0,
    "usd": float(get_env_var("RATE_USD", "90.0")),
    "ton": float(get_env_var("RATE_TON", "115.0"))
}

# ==================== ХРАНИЛИЩЕ ====================
user_balances     = {}
user_referrals    = {}
referral_earnings = {}
pending_payments  = {}
pending_ton_orders = {}
pending_withdrawals = {}
all_users         = set()
banner_file_id    = None

# Промокоды: { "КОД": {"discount": 20, "uses_left": 10, "total_uses": 10, "activated_by": set()} }
promo_codes = {}

user_state = {}
user_temp  = {}

# ==================== УТИЛИТЫ ====================
def get_balance(uid): return user_balances.get(uid, 0.0)
def add_balance(uid, amt): user_balances[uid] = get_balance(uid) + amt
def is_admin(uid): return uid in ADMIN_IDS

def set_state(uid, state, **kw):
    user_state[uid] = state
    user_temp.setdefault(uid, {}).update(kw)

def clear_state(uid):
    user_state.pop(uid, None)
    user_temp.pop(uid, None)

def gtemp(uid, key, default=None):
    return user_temp.get(uid, {}).get(key, default)

async def notify_admins(context, text, kb=None):
    for aid in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=aid, text=text,
                parse_mode="Markdown", reply_markup=kb)
        except Exception as e:
            logger.error(f"notify_admins {aid}: {e}")

async def sdel(msg):
    try: await msg.delete()
    except: pass

async def send_with_banner(chat_id, context, text, kb):
    if banner_file_id:
        await context.bot.send_photo(chat_id, photo=banner_file_id,
            caption=text, parse_mode="Markdown", reply_markup=kb)
    else:
        await context.bot.send_message(chat_id, text=text,
            parse_mode="Markdown", reply_markup=kb)

def back_btn(target="main_menu", label="◀️ Назад"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=target)]])

def rub_requisites():
    return (
        f"💳 *Реквизиты для оплаты:*\n\n"
        f"Номер карты:\n`{CARD_NUMBER}`\n\n"
        f"Номер телефона:\n`{CARD_PHONE}`\n\n"
        f"Банк: *Тбанк*"
    )

# ==================== ГЛАВНОЕ МЕНЮ ====================
async def show_main_menu(chat_id, uid, context, extra=""):
    balance = get_balance(uid)
    text = (
        f"🏠 *{BOT_NAME}*\n\n"
        f"📈 Курсы:\n• 1 ⭐ = *{STARS_PRICE_RUB}₽*\n• 1 💎 TON = *{RATES['ton']:.0f}₽*\n\n"
        f"💰 Ваш баланс: *{balance:.2f}₽*\n\n"
        + (f"{extra}\n" if extra else "") +
        "Выберите действие:"
    )
    rows = [
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data="buy_stars"),
         InlineKeyboardButton("💎 Купить TON",    callback_data="buy_ton")],
        [InlineKeyboardButton("🎟 Промокод",      callback_data="promo"),
         InlineKeyboardButton("💸 Вывод",         callback_data="withdraw")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton("ℹ️ Информация",    callback_data="info"),
         InlineKeyboardButton("🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    ]
    if is_admin(uid):
        rows.append([InlineKeyboardButton("🔧 Админ-панель", callback_data="admin_panel")])
    await send_with_banner(chat_id, context, text, InlineKeyboardMarkup(rows))

# ==================== /start ====================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    clear_state(user.id)
    if context.args and context.args[0].startswith("ref_"):
        try:
            rid = int(context.args[0].split("_")[1])
            if rid != user.id and user.id not in user_referrals:
                user_referrals[user.id] = rid
        except: pass
    text = (
        f"✨ *Добро пожаловать в {BOT_NAME}!*\n\n"
        f"Привет, {user.first_name}! 👋\n\n"
        f"📈 Курсы:\n• 1 ⭐ = *{STARS_PRICE_RUB}₽*\n• 1 💎 TON = *{RATES['ton']:.0f}₽*\n\n"
        f"💰 Баланс: *{get_balance(user.id):.2f}₽*\n\nВыберите действие:"
    )
    rows = [
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data="buy_stars"),
         InlineKeyboardButton("💎 Купить TON",    callback_data="buy_ton")],
        [InlineKeyboardButton("🎟 Промокод",      callback_data="promo"),
         InlineKeyboardButton("💸 Вывод",         callback_data="withdraw")],
        [InlineKeyboardButton("👥 Реферальная система", callback_data="referral")],
        [InlineKeyboardButton("ℹ️ Информация",    callback_data="info"),
         InlineKeyboardButton("🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
    ]
    if is_admin(user.id):
        rows.append([InlineKeyboardButton("🔧 Админ-панель", callback_data="admin_panel")])
    await send_with_banner(update.effective_chat.id, context, text, InlineKeyboardMarkup(rows))

async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; all_users.add(uid); clear_state(uid)
    await sdel(q.message)
    await show_main_menu(q.message.chat_id, uid, context)

# ==================== ПРОМОКОД ====================
async def cb_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; clear_state(uid)
    set_state(uid, "promo_enter")
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        "🎟 *Промокод*\n\nВведите промокод:",
        back_btn("main_menu"))

# ==================== ПОКУПКА ЗВЁЗД ====================
async def cb_buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    # Сохраняем скидку если была активирована
    discount = gtemp(uid, "promo_discount", 0)
    clear_state(uid)
    set_state(uid, "stars_count", promo_discount=discount)
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        "⭐ *Покупка звёзд*\n\nВведите количество звёзд:\n_(минимум 50)_",
        back_btn("main_menu"))

async def cb_buy_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    btype = q.data.replace("buy_type_", "")
    stars = gtemp(uid, "stars_count")
    discount = gtemp(uid, "promo_discount", 0)
    rub = stars * STARS_PRICE_RUB * (1 - discount / 100)
    disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
    if btype == "self":
        uname = f"@{q.from_user.username}" if q.from_user.username else f"ID:{uid}"
        set_state(uid, "stars_currency", buy_type="self", stars_count=stars,
                  target_username=uname, promo_discount=discount)
        await sdel(q.message)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Рубли (₽)",   callback_data="scurrency_rub"),
             InlineKeyboardButton("💵 Доллары ($)", callback_data="scurrency_usd")],
            [InlineKeyboardButton("💎 TON",          callback_data="scurrency_ton")],
            [InlineKeyboardButton("◀️ Назад",        callback_data="buy_stars")],
        ])
        await send_with_banner(q.message.chat_id, context,
            f"💳 *Выберите валюту:*\n\n⭐ Звёзды: *{stars}*\n🙋 Получатель: *{uname}* (вы){disc_str}\n\n"
            f"• ₽ {rub:.2f}₽\n• $ {rub/RATES['usd']:.2f}$\n• TON {rub/RATES['ton']:.4f}", kb)
    else:
        set_state(uid, "stars_username", buy_type="anon", stars_count=stars, promo_discount=discount)
        await sdel(q.message)
        await send_with_banner(q.message.chat_id, context,
            "🥷 *Анонимная покупка*\n\nВведите *@юзернейм* получателя:\n_(он не узнает, кто купил)_",
            back_btn("buy_stars"))

async def cb_stars_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    cur = q.data.replace("scurrency_", "")
    stars    = gtemp(uid, "stars_count")
    username = gtemp(uid, "target_username")
    btype    = gtemp(uid, "buy_type", "anon")
    discount = gtemp(uid, "promo_discount", 0)
    rub = stars * STARS_PRICE_RUB * (1 - discount / 100)
    fmt = {"rub": f"{rub:.2f}₽", "usd": f"{rub/RATES['usd']:.2f}$", "ton": f"{rub/RATES['ton']:.4f} TON"}
    amounts = {"rub": rub, "usd": rub/RATES["usd"], "ton": rub/RATES["ton"]}
    set_state(uid, "stars_awaiting_payment", stars_count=stars, target_username=username,
              currency=cur, buy_type=btype, amount=amounts[cur], promo_discount=discount)
    req = rub_requisites() if cur == "rub" else f"💎 *Крипто-адрес (TON/USDT):*\n\n`{CRYPTO_ADDRESS}`"
    tlabel = "🙋 Себе" if btype == "self" else "🥷 Анонимно"
    disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data="paid_stars")],
        [InlineKeyboardButton("◀️ Назад",     callback_data="buy_stars")],
    ])
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        f"📋 *Детали заказа:*\n\n⭐ Звёзды: *{stars}*\n"
        f"👤 Получатель: *{username}*\n🏷 Тип: *{tlabel}*{disc_str}\n"
        f"💰 К оплате: *{fmt[cur]}*\n\n{req}\n\nПосле оплаты нажмите кнопку:", kb)

async def cb_paid_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid  = q.from_user.id; user = q.from_user
    stars    = gtemp(uid, "stars_count", "?")
    username = gtemp(uid, "target_username", "?")
    cur      = gtemp(uid, "currency", "rub")
    amount   = gtemp(uid, "amount", 0)
    btype    = gtemp(uid, "buy_type", "anon")
    discount = gtemp(uid, "promo_discount", 0)
    sym      = {"rub": "₽", "usd": "$", "ton": " TON"}.get(cur, "₽")
    tlabel   = "🙋 Себе" if btype == "self" else "🥷 Анонимно"
    oid = f"stpay{uid}{int(time.time())}"
    pending_payments[oid] = {
        "user_id": uid, "user_name": user.full_name,
        "username_tg": f"@{user.username}" if user.username else f"ID:{uid}",
        "stars": stars, "target": username, "currency": cur,
        "amount": amount, "symbol": sym, "buy_type": btype, "discount": discount,
    }
    disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Оплата пришла",  callback_data=f"stok_{oid}")],
        [InlineKeyboardButton("❌ Не пришла",      callback_data=f"stno_{oid}")],
    ])
    await notify_admins(context,
        f"🔔 *Новая оплата за звёзды!*\n\n"
        f"👤 {user.full_name} ({'@'+user.username if user.username else 'ID:'+str(uid)})\n"
        f"⭐ Звёзд: *{stars}*\n📨 Получатель: *{username}*\n"
        f"🏷 Тип: *{tlabel}*{disc_str}\n💰 Сумма: *{amount}{sym}*\n💳 Валюта: *{cur.upper()}*",
        admin_kb)
    clear_state(uid)
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        "⏳ *Заявка отправлена!*\n\nАдминистратор проверит оплату.\nЗвёзды придут после подтверждения.\n\n⏱ До 15 минут",
        back_btn("main_menu", "🏠 Главное меню"))

async def cb_admin_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer()
    if q.data.startswith("stok_"):
        action = "confirm"; oid = q.data[5:]
    else:
        action = "decline"; oid = q.data[5:]
    p = pending_payments.get(oid)
    if not p: await q.edit_message_text("⚠️ Заявка не найдена"); return
    uid = p["user_id"]
    if action == "confirm":
        if uid in user_referrals:
            rid = user_referrals[uid]
            bonus = float(p["stars"]) * STARS_PRICE_RUB * 0.03
            add_balance(rid, bonus)
            referral_earnings[rid] = referral_earnings.get(rid, 0) + bonus
            try: await context.bot.send_message(rid,
                f"🎉 *Реферальный бонус!*\nНачислено: *+{bonus:.2f}₽*", parse_mode="Markdown")
            except: pass
        await context.bot.send_message(uid,
            f"✅ *Оплата подтверждена!*\n\n⭐ *{p['stars']} звёзд* отправлены на {p['target']}.\nСпасибо! 🙏",
            parse_mode="Markdown")
        await q.edit_message_text(f"✅ Подтверждено!\n{p['username_tg']} | {p['stars']}⭐ → {p['target']}")
    else:
        await context.bot.send_message(uid, "❌ *Оплата не найдена.*\nОбратитесь в поддержку.", parse_mode="Markdown")
        await q.edit_message_text(f"❌ Отклонено!\n{p['username_tg']}")
    del pending_payments[oid]

# ==================== ПОКУПКА TON ====================
async def cb_buy_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    discount = gtemp(uid, "promo_discount", 0)
    clear_state(uid)
    set_state(uid, "ton_amount", promo_discount=discount)
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        f"💎 *Покупка TON*\n\nКурс: *1 TON = {RATES['ton']:.0f}₽*\n\nВведите количество TON:\n_(например: 5 или 10.5)_",
        back_btn("main_menu"))

async def cb_ton_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    ptype = q.data.replace("tonpay_", "")
    amount   = gtemp(uid, "ton_amount")
    addr     = gtemp(uid, "ton_address")
    discount = gtemp(uid, "promo_discount", 0)
    rub_cost = amount * RATES["ton"] * (1 - discount / 100)
    usd_cost = rub_cost / RATES["usd"]
    pay_amount = rub_cost if ptype == "rub" else usd_cost
    set_state(uid, "ton_awaiting_payment", ton_amount=amount, ton_address=addr,
              ton_pay_type=ptype, ton_pay_amount=pay_amount, promo_discount=discount)
    disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
    if ptype == "rub":
        pay_str = f"*{rub_cost:.2f}₽*"
        req = rub_requisites()
    else:
        pay_str = f"*{usd_cost:.2f} USDT*"
        req = f"💎 *Крипто-адрес:*\n\n`{CRYPTO_ADDRESS}`"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data="paid_ton")],
        [InlineKeyboardButton("◀️ Назад",     callback_data="buy_ton")],
    ])
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        f"📋 *Детали покупки TON:*\n\n💎 Количество: *{amount} TON*\n"
        f"📬 Адрес:\n`{addr}`{disc_str}\n💰 К оплате: {pay_str}\n\n{req}\n\nПосле оплаты нажмите кнопку:", kb)

async def cb_paid_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; user = q.from_user
    amount     = gtemp(uid, "ton_amount", 0)
    addr       = gtemp(uid, "ton_address", "?")
    ptype      = gtemp(uid, "ton_pay_type", "rub")
    pay_amount = gtemp(uid, "ton_pay_amount", 0)
    discount   = gtemp(uid, "promo_discount", 0)
    sym        = "₽" if ptype == "rub" else " USDT"
    oid = f"tonpay{uid}{int(time.time())}"
    pending_ton_orders[oid] = {
        "user_id": uid, "user_name": user.full_name,
        "username_tg": f"@{user.username}" if user.username else f"ID:{uid}",
        "ton_amount": amount, "address": addr, "pay_amount": pay_amount,
        "symbol": sym, "discount": discount,
    }
    disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Оплата пришла", callback_data=f"tonok_{oid}")],
        [InlineKeyboardButton("❌ Не пришла",     callback_data=f"tonno_{oid}")],
    ])
    await notify_admins(context,
        f"🔔 *Новая покупка TON!*\n\n"
        f"👤 {user.full_name} ({'@'+user.username if user.username else 'ID:'+str(uid)})\n"
        f"💎 TON: *{amount}*\n📬 Адрес: `{addr}`{disc_str}\n💰 Сумма: *{pay_amount}{sym}*",
        admin_kb)
    clear_state(uid)
    await sdel(q.message)
    await send_with_banner(q.message.chat_id, context,
        "⏳ *Заявка на TON отправлена!*\n\nАдминистратор проверит оплату.\nTON придут после подтверждения.\n\n⏱ До 30 минут",
        back_btn("main_menu", "🏠 Главное меню"))

async def cb_admin_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer()
    if q.data.startswith("tonok_"):
        action = "confirm"; oid = q.data[6:]
    else:
        action = "decline"; oid = q.data[6:]
    o = pending_ton_orders.get(oid)
    if not o: await q.edit_message_text("⚠️ Заявка не найдена"); return
    uid = o["user_id"]
    if action == "confirm":
        if uid in user_referrals:
            rid = user_referrals[uid]
            bonus = float(o["ton_amount"]) * RATES["ton"] * 0.03
            add_balance(rid, bonus)
            referral_earnings[rid] = referral_earnings.get(rid, 0) + bonus
            try: await context.bot.send_message(rid,
                f"🎉 *Реф. бонус!*\nНачислено: *+{bonus:.2f}₽*", parse_mode="Markdown")
            except: pass
        await context.bot.send_message(uid,
            f"✅ *Покупка TON подтверждена!*\n\n💎 *{o['ton_amount']} TON* отправлены на:\n`{o['address']}`\n\nСпасибо! 🙏",
            parse_mode="Markdown")
        await q.edit_message_text(f"✅ TON отправлен!\n{o['username_tg']} | {o['ton_amount']} TON")
    else:
        await context.bot.send_message(uid, "❌ *Оплата TON не найдена.*\nОбратитесь в поддержку.", parse_mode="Markdown")
        await q.edit_message_text(f"❌ TON отклонён!\n{o['username_tg']}")
    del pending_ton_orders[oid]

# ==================== ВЫВОД ====================
async def cb_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; clear_state(uid); await sdel(q.message)
    balance = get_balance(uid)
    if balance < 100:
        return await send_with_banner(q.message.chat_id, context,
            f"❌ *Недостаточно средств*\n\nБаланс: *{balance:.2f}₽*\nМинимум: *100₽*",
            back_btn("main_menu"))
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Рублями (₽)",   callback_data="wdcur_rub")],
        [InlineKeyboardButton("💵 Долларами ($)", callback_data="wdcur_usd")],
        [InlineKeyboardButton("💎 TON",            callback_data="wdcur_ton")],
        [InlineKeyboardButton("◀️ Назад",          callback_data="main_menu")],
    ])
    await send_with_banner(q.message.chat_id, context,
        f"💸 *Вывод средств*\n\nБаланс: *{balance:.2f}₽*\nМинимум: 100₽\n\nВыберите валюту:", kb)

async def cb_withdraw_cur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    cur = q.data.replace("wdcur_", "")
    set_state(uid, "withdraw_amount", withdraw_currency=cur)
    syms = {"rub": "₽", "usd": "$", "ton": "TON"}
    await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        f"💸 Введите сумму вывода в *{syms[cur]}*:",
        parse_mode="Markdown", reply_markup=back_btn("withdraw", "◀️ Отмена"))

async def cb_admin_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer()
    if q.data.startswith("wdok_"):
        action = "confirm"; wid = q.data[5:]
    else:
        action = "decline"; wid = q.data[5:]
    w = pending_withdrawals.get(wid)
    if not w: await q.edit_message_text("⚠️ Заявка не найдена"); return
    uid = w["user_id"]
    if action == "confirm":
        add_balance(uid, -w["amount_rub"])
        await context.bot.send_message(uid,
            f"✅ *Вывод выполнен!*\n\n*{w['amount']}{w['symbol']}* отправлено на ваши реквизиты.\nОстаток: *{get_balance(uid):.2f}₽*",
            parse_mode="Markdown")
        await q.edit_message_text(f"✅ Выплачено!\n{w['username_tg']} {w['amount']}{w['symbol']}")
    else:
        await context.bot.send_message(uid, "❌ *Вывод отклонён.*\nОбратитесь в поддержку.", parse_mode="Markdown")
        await q.edit_message_text(f"❌ Отклонено!\n{w['username_tg']}")
    del pending_withdrawals[wid]

# ==================== РЕФЕРАЛЬНАЯ СИСТЕМА ====================
async def cb_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; await sdel(q.message)
    bu = BOT_USERNAME.lstrip("@")
    ref_link  = f"https://t.me/{bu}?start=ref_{uid}"
    ref_count = sum(1 for v in user_referrals.values() if v == uid)
    earned    = referral_earnings.get(uid, 0)
    await send_with_banner(q.message.chat_id, context,
        f"👥 *Реферальная система*\n\n💡 Зарабатывайте *3%* с покупок рефералов!\n"
        f"_(работает для ⭐ и 💎 TON)_\n\n🔗 Ваша ссылка:\n`{ref_link}`\n\n"
        f"📊 Статистика:\n• Приглашено: *{ref_count}*\n• Заработано: *{earned:.2f}₽*\n"
        f"• Баланс: *{get_balance(uid):.2f}₽*\n\n_По своей ссылке перейти нельзя_",
        back_btn("main_menu"))

# ==================== ИНФОРМАЦИЯ ====================
async def cb_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); await sdel(q.message)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")],
    ])
    await send_with_banner(q.message.chat_id, context,
        f"ℹ️ *О сервисе {BOT_NAME}*\n\n"
        "━━━━━━━━━━━━━━━━━━\n🏆 *КТО МЫ*\n\n"
        f"{BOT_NAME} — надёжный сервис покупки Telegram Stars и TON. "
        "Ручная проверка каждой транзакции, честные условия, быстрая обработка.\n\n"
        "━━━━━━━━━━━━━━━━━━\n⚡ *СКОРОСТЬ*\n\n"
        "• Подтверждение оплаты ⭐: 5–30 мин\n"
        "• Покупка TON: до 30 мин\n"
        "• Вывод средств: до 24 ч\n"
        "• Ответ поддержки: до 2 ч\n\n"
        "━━━━━━━━━━━━━━━━━━\n💎 *ГАРАНТИИ*\n\n"
        "✅ Только реальные Stars и TON\n"
        "✅ Если не пришло — возврат\n"
        "✅ Приём ₽, $, TON\n"
        "✅ Реферальная программа 3%\n"
        "✅ Вывод на карту или крипто\n\n"
        "━━━━━━━━━━━━━━━━━━\n📊 *ТАРИФЫ*\n\n"
        f"• 1 ⭐ = *{STARS_PRICE_RUB}₽*\n"
        f"• 1 TON = *{RATES['ton']:.0f}₽*\n"
        f"• Мин. покупка ⭐: 50 шт\n"
        f"• Мин. вывод: 100₽\n"
        f"• Реф. бонус: 3%\n\n"
        f"━━━━━━━━━━━━━━━━━━\n📞 *ПОДДЕРЖКА*\n\n"
        f"👉 {SUPPORT_USERNAME}", kb)

# ==================== АДМИН-ПАНЕЛЬ ====================
def admin_text():
    return (
        f"🔧 *Админ-панель {BOT_NAME}*\n\n"
        f"👥 Пользователей: *{len(all_users)}*\n"
        f"💰 Суммарный баланс: *{sum(user_balances.values()):.2f}₽*\n"
        f"⏳ Ожидают оплаты ⭐: *{len(pending_payments)}*\n"
        f"⏳ Ожидают оплаты 💎: *{len(pending_ton_orders)}*\n"
        f"⏳ Ожидают вывода: *{len(pending_withdrawals)}*\n\n"
        f"🎟 Промокодов: *{len(promo_codes)}*\n"
        f"🖼️ Баннер: *{'есть ✅' if banner_file_id else 'нет ❌'}*\n"
        f"⭐ Курс: *1 ⭐ = {STARS_PRICE_RUB}₽*\n"
        f"💎 Курс: *1 TON = {RATES['ton']:.0f}₽*"
    )

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Установить баннер", callback_data="admin_set_banner"),
         InlineKeyboardButton("🗑️ Удалить баннер",   callback_data="admin_del_banner")],
        [InlineKeyboardButton("📢 Рассылка",          callback_data="admin_broadcast")],
        [InlineKeyboardButton("⭐ Курс звёзд",        callback_data="admin_edit_price"),
         InlineKeyboardButton("💎 Курс TON",          callback_data="admin_edit_ton")],
        [InlineKeyboardButton("👤 Изменить баланс",   callback_data="admin_edit_balance")],
        [InlineKeyboardButton("✉️ Написать юзеру",    callback_data="admin_msg_user")],
        [InlineKeyboardButton("🎟 Промокоды",         callback_data="admin_promos")],
        [InlineKeyboardButton("📊 Статистика",        callback_data="admin_stats")],
        [InlineKeyboardButton("◀️ Главное меню",      callback_data="main_menu")],
    ])

async def cb_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); clear_state(q.from_user.id); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id, admin_text(),
        parse_mode="Markdown", reply_markup=admin_kb())

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    clear_state(update.effective_user.id)
    await context.bot.send_message(update.effective_chat.id, admin_text(),
        parse_mode="Markdown", reply_markup=admin_kb())

async def cb_admin_set_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_set_banner"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "🖼️ *Установка баннера*\n\nОтправьте фото:", parse_mode="Markdown",
        reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_del_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global banner_file_id
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); banner_file_id = None; await sdel(q.message)
    await context.bot.send_message(q.message.chat_id, "🗑️ *Баннер удалён.*",
        parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))

async def cb_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_broadcast"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "📢 *Рассылка*\n\nОтправьте сообщение или фото с подписью:", parse_mode="Markdown",
        reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_edit_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_edit_price"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        f"⭐ *Изменение курса звёзд*\n\nТекущий: *1 ⭐ = {STARS_PRICE_RUB}₽*\n\nВведите новый курс:",
        parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_edit_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_edit_ton"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        f"💎 *Изменение курса TON*\n\nТекущий: *1 TON = {RATES['ton']:.0f}₽*\n\nВведите новый курс:",
        parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_edit_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_balance_uid"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "👤 *Изменение баланса*\n\nВведите Telegram ID пользователя:", parse_mode="Markdown",
        reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_msg_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_msg_uid"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "✉️ *Написать пользователю*\n\nВведите Telegram ID:", parse_mode="Markdown",
        reply_markup=back_btn("admin_panel", "◀️ Отмена"))

async def cb_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); await sdel(q.message)
    top = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:5]
    top_str = "\n".join([f"  `{u}`: {b:.2f}₽" for u, b in top]) or "  нет данных"
    await context.bot.send_message(q.message.chat_id,
        f"📊 *Статистика*\n\n👥 Пользователей: *{len(all_users)}*\n"
        f"💰 Суммарный баланс: *{sum(user_balances.values()):.2f}₽*\n"
        f"⏳ Ожидают ⭐: *{len(pending_payments)}*\n"
        f"⏳ Ожидают 💎: *{len(pending_ton_orders)}*\n"
        f"⏳ Ожидают вывода: *{len(pending_withdrawals)}*\n\n"
        f"🏆 Топ-5 балансов:\n{top_str}",
        parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))

# ==================== АДМИН — ПРОМОКОДЫ ====================
async def cb_admin_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); await sdel(q.message)
    if promo_codes:
        lines = []
        for code, data in promo_codes.items():
            lines.append(
                f"• `{code}` — скидка *{data['discount']}%*, "
                f"осталось: *{data['uses_left']}/{data['total_uses']}*"
            )
        promo_list = "\n".join(lines)
    else:
        promo_list = "_Промокодов пока нет_"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать промокод", callback_data="admin_promo_create")],
        [InlineKeyboardButton("🗑 Удалить промокод",  callback_data="admin_promo_delete")],
        [InlineKeyboardButton("◀️ В панель",          callback_data="admin_panel")],
    ])
    await context.bot.send_message(q.message.chat_id,
        f"🎟 *Промокоды*\n\n{promo_list}",
        parse_mode="Markdown", reply_markup=kb)

async def cb_admin_promo_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_promo_code"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "🎟 *Создание промокода*\n\nШаг 1/3: Введите *название* промокода:\n_(латиница и цифры, например: SALE20)_",
        parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ Отмена"))

async def cb_admin_promo_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): await q.answer("❌ Нет доступа", show_alert=True); return
    await q.answer(); set_state(q.from_user.id, "admin_promo_delete"); await sdel(q.message)
    await context.bot.send_message(q.message.chat_id,
        "🗑 *Удаление промокода*\n\nВведите название промокода для удаления:",
        parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ Отмена"))

# ==================== ОБРАБОТЧИК ТЕКСТА И ФОТО ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STARS_PRICE_RUB, banner_file_id
    msg   = update.message
    uid   = msg.from_user.id
    text  = (msg.text or "").strip()
    photo = msg.photo
    all_users.add(uid)
    state = user_state.get(uid)
    if not state:
        return

    # --- Промокод: ввод пользователем ---
    if state == "promo_enter":
        code = text.upper().strip()
        if code not in promo_codes:
            return await msg.reply_text("❌ Промокод не найден. Попробуйте ещё раз:",
                reply_markup=back_btn("main_menu"))
        promo = promo_codes[code]
        if promo["uses_left"] <= 0:
            return await msg.reply_text("❌ Этот промокод уже исчерпан.",
                reply_markup=back_btn("main_menu"))
        if uid in promo["activated_by"]:
            return await msg.reply_text("❌ Вы уже использовали этот промокод.",
                reply_markup=back_btn("main_menu"))
        promo["activated_by"].add(uid)
        promo["uses_left"] -= 1
        clear_state(uid)
        set_state(uid, "promo_active", promo_discount=promo["discount"])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ Купить звёзды", callback_data="buy_stars"),
             InlineKeyboardButton("💎 Купить TON",    callback_data="buy_ton")],
            [InlineKeyboardButton("🏠 Главное меню",  callback_data="main_menu")],
        ])
        await msg.reply_text(
            f"✅ *Промокод активирован!*\n\n🎟 Скидка *{promo['discount']}%* применена к следующей покупке.\n\nВыберите что купить:",
            parse_mode="Markdown", reply_markup=kb)

    # --- Звёзды: количество ---
    elif state == "stars_count":
        try:
            count = int(text)
            if count < 50:
                return await msg.reply_text("❌ Минимум — 50 звёзд. Введите снова:")
            discount = gtemp(uid, "promo_discount", 0)
            set_state(uid, "stars_buy_type", stars_count=count, promo_discount=discount)
            rub = count * STARS_PRICE_RUB * (1 - discount / 100)
            disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🙋 Купить себе",     callback_data="buy_type_self"),
                 InlineKeyboardButton("🥷 Купить анонимно", callback_data="buy_type_anon")],
                [InlineKeyboardButton("◀️ Назад", callback_data="buy_stars")],
            ])
            await msg.reply_text(
                f"⭐ *Звёзд: {count}*\n💰 Стоимость: *{rub:.2f}₽*{disc_str}\n\nТип покупки:",
                parse_mode="Markdown", reply_markup=kb)
        except ValueError:
            await msg.reply_text("❌ Введите число:")

    # --- Звёзды: юзернейм ---
    elif state == "stars_username":
        username = text if text.startswith("@") else "@" + text
        stars    = gtemp(uid, "stars_count")
        discount = gtemp(uid, "promo_discount", 0)
        rub = stars * STARS_PRICE_RUB * (1 - discount / 100)
        set_state(uid, "stars_currency", stars_count=stars, target_username=username,
                  buy_type="anon", promo_discount=discount)
        disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Рубли (₽)",   callback_data="scurrency_rub"),
             InlineKeyboardButton("💵 Доллары ($)", callback_data="scurrency_usd")],
            [InlineKeyboardButton("💎 TON",          callback_data="scurrency_ton")],
            [InlineKeyboardButton("◀️ Назад",        callback_data="buy_stars")],
        ])
        await msg.reply_text(
            f"💳 *Выберите валюту:*\n\n⭐ *{stars}*\n🥷 Получатель: *{username}*{disc_str}\n\n"
            f"• ₽ {rub:.2f}₽\n• $ {rub/RATES['usd']:.2f}$\n• TON {rub/RATES['ton']:.4f}",
            parse_mode="Markdown", reply_markup=kb)

    # --- TON: количество ---
    elif state == "ton_amount":
        try:
            amount = float(text.replace(",", "."))
            if amount <= 0: raise ValueError
            discount = gtemp(uid, "promo_discount", 0)
            rub = amount * RATES["ton"] * (1 - discount / 100)
            set_state(uid, "ton_address", ton_amount=amount, promo_discount=discount)
            disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
            await msg.reply_text(
                f"💎 *TON: {amount}*\n\nСтоимость: *{rub:.2f}₽* / *{rub/RATES['usd']:.2f}$*{disc_str}\n\n"
                f"Введите ваш *TON-адрес* для получения:",
                parse_mode="Markdown", reply_markup=back_btn("buy_ton"))
        except ValueError:
            await msg.reply_text("❌ Введите число (например: 5 или 10.5):")

    # --- TON: адрес ---
    elif state == "ton_address":
        amount   = gtemp(uid, "ton_amount")
        discount = gtemp(uid, "promo_discount", 0)
        rub = amount * RATES["ton"] * (1 - discount / 100)
        set_state(uid, "ton_pay_type", ton_amount=amount, ton_address=text, promo_discount=discount)
        disc_str = f"\n🎟 Скидка: *{discount}%*" if discount else ""
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Рублями (₽)", callback_data="tonpay_rub"),
             InlineKeyboardButton("💵 USDT",           callback_data="tonpay_usdt")],
            [InlineKeyboardButton("◀️ Назад", callback_data="buy_ton")],
        ])
        await msg.reply_text(
            f"💎 *Детали покупки:*\n\n📦 *{amount} TON*\n📬 Адрес:\n`{text}`{disc_str}\n\n"
            f"Стоимость: *{rub:.2f}₽* / *{rub/RATES['usd']:.2f} USDT*\n\nВыберите валюту оплаты:",
            parse_mode="Markdown", reply_markup=kb)

    # --- Вывод: сумма ---
    elif state == "withdraw_amount":
        try:
            amount = float(text.replace(",", "."))
            cur = gtemp(uid, "withdraw_currency", "rub")
            amount_rub = amount * RATES.get(cur, 1)
            balance = get_balance(uid)
            sym = {"rub": "₽", "usd": "$", "ton": "TON"}[cur]
            if amount_rub > balance:
                return await msg.reply_text(
                    f"❌ Недостаточно средств!\nБаланс: {balance:.2f}₽, нужно: {amount_rub:.2f}₽\nВведите меньше:")
            set_state(uid, "withdraw_details", withdraw_amount=amount,
                      withdraw_amount_rub=amount_rub, withdraw_currency=cur)
            await msg.reply_text(
                f"💸 Введите реквизиты для вывода *{amount}{sym}*:\n_(карта / адрес кошелька)_",
                parse_mode="Markdown", reply_markup=back_btn("withdraw", "◀️ Отмена"))
        except ValueError:
            await msg.reply_text("❌ Введите сумму:")

    # --- Вывод: реквизиты ---
    elif state == "withdraw_details":
        amount     = gtemp(uid, "withdraw_amount")
        amount_rub = gtemp(uid, "withdraw_amount_rub")
        cur        = gtemp(uid, "withdraw_currency", "rub")
        sym        = {"rub": "₽", "usd": "$", "ton": " TON"}[cur]
        user       = msg.from_user
        wid = f"wd{uid}{int(time.time())}"
        pending_withdrawals[wid] = {
            "user_id": uid, "user_name": user.full_name,
            "username_tg": f"@{user.username}" if user.username else f"ID:{uid}",
            "amount": amount, "amount_rub": amount_rub,
            "currency": cur, "symbol": sym, "details": text,
        }
        admin_kb2 = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Выплатить",  callback_data=f"wdok_{wid}")],
            [InlineKeyboardButton("❌ Отклонить", callback_data=f"wdno_{wid}")],
        ])
        await notify_admins(context,
            f"🔔 *Заявка на вывод!*\n\n"
            f"👤 {user.full_name} ({'@'+user.username if user.username else 'ID:'+str(uid)})\n"
            f"💰 Сумма: *{amount}{sym}*\n💵 В рублях: *{amount_rub:.2f}₽*\n"
            f"📋 Реквизиты:\n`{text}`",
            admin_kb2)
        clear_state(uid)
        await msg.reply_text(
            "⏳ *Заявка на вывод отправлена!*\n\nАдмин обработает в течение 24 часов.",
            parse_mode="Markdown", reply_markup=back_btn("main_menu", "🏠 Главное меню"))

    # --- Админ: баннер ---
    elif state == "admin_set_banner":
        if photo:
            banner_file_id = photo[-1].file_id
            clear_state(uid)
            await msg.reply_text("✅ *Баннер установлен!*", parse_mode="Markdown",
                reply_markup=back_btn("admin_panel", "◀️ В панель"))
        else:
            await msg.reply_text("❌ Отправьте фото (не файл):")

    # --- Админ: рассылка ---
    elif state == "admin_broadcast":
        ok, fail = 0, 0
        for tuid in list(all_users):
            try:
                if photo:
                    await context.bot.send_photo(tuid, photo=photo[-1].file_id,
                        caption=msg.caption or "", parse_mode="Markdown")
                else:
                    await context.bot.send_message(tuid, text=text, parse_mode="Markdown")
                ok += 1
            except: fail += 1
        clear_state(uid)
        await msg.reply_text(f"📢 *Рассылка завершена!*\n\n✅ {ok}\n❌ {fail}",
            parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))

    # --- Админ: курс звёзд ---
    elif state == "admin_edit_price":
        try:
            p = float(text.replace(",", "."))
            if p <= 0: raise ValueError
            STARS_PRICE_RUB = p; clear_state(uid)
            await msg.reply_text(f"✅ Новый курс: *1 ⭐ = {STARS_PRICE_RUB}₽*",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))
        except ValueError:
            await msg.reply_text("❌ Введите число:")

    # --- Админ: курс TON ---
    elif state == "admin_edit_ton":
        try:
            p = float(text.replace(",", "."))
            if p <= 0: raise ValueError
            RATES["ton"] = p; clear_state(uid)
            await msg.reply_text(f"✅ Новый курс: *1 TON = {RATES['ton']:.0f}₽*",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))
        except ValueError:
            await msg.reply_text("❌ Введите число:")

    # --- Админ: баланс — ID ---
    elif state == "admin_balance_uid":
        try:
            tuid = int(text)
            set_state(uid, "admin_balance_amount", admin_target_uid=tuid)
            await msg.reply_text(
                f"👤 ID *{tuid}*\nБаланс: *{get_balance(tuid):.2f}₽*\n\n"
                f"Введите:\n• `+100` — добавить\n• `-50` — вычесть\n• `500` — установить",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ Отмена"))
        except ValueError:
            await msg.reply_text("❌ Введите числовой ID:")

    # --- Админ: баланс — сумма ---
    elif state == "admin_balance_amount":
        tuid = gtemp(uid, "admin_target_uid")
        try:
            if text.startswith("+"): amt = float(text[1:]); add_balance(tuid, amt); act = f"+{amt:.2f}₽"
            elif text.startswith("-"): amt = float(text[1:]); add_balance(tuid, -amt); act = f"-{amt:.2f}₽"
            else: amt = float(text); user_balances[tuid] = amt; act = f"= {amt:.2f}₽"
            try: await context.bot.send_message(tuid,
                f"💰 *Ваш баланс изменён!*\nНовый: *{get_balance(tuid):.2f}₽*", parse_mode="Markdown")
            except: pass
            clear_state(uid)
            await msg.reply_text(f"✅ Баланс {tuid}: {act}\nИтого: *{get_balance(tuid):.2f}₽*",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))
        except ValueError:
            await msg.reply_text("❌ Формат: +100, -50 или 500")

    # --- Админ: написать юзеру — ID ---
    elif state == "admin_msg_uid":
        try:
            tuid = int(text)
            set_state(uid, "admin_msg_text", admin_msg_uid=tuid)
            await msg.reply_text(f"✉️ Введите сообщение для *{tuid}*:",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ Отмена"))
        except ValueError:
            await msg.reply_text("❌ Введите числовой ID:")

    # --- Админ: написать юзеру — текст ---
    elif state == "admin_msg_text":
        tuid = gtemp(uid, "admin_msg_uid")
        try:
            await context.bot.send_message(tuid,
                f"📩 *Сообщение от администратора:*\n\n{text}", parse_mode="Markdown")
            clear_state(uid)
            await msg.reply_text(f"✅ Отправлено пользователю *{tuid}*",
                parse_mode="Markdown", reply_markup=back_btn("admin_panel", "◀️ В панель"))
        except Exception as e:
            await msg.reply_text(f"❌ Ошибка: {e}")

    # --- Админ: промокод — название ---
    elif state == "admin_promo_code":
        code = text.upper().strip()
        if not code.replace("_", "").isalnum():
            return await msg.reply_text("❌ Только латиница, цифры и _. Введите снова:")
        set_state(uid, "admin_promo_discount", promo_new_code=code)
        await msg.reply_text(
            f"🎟 Промокод: *{code}*\n\nШаг 2/3: Введите *скидку в %*:\n_(например: 10 — это 10%)_",
            parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ Отмена"))

    # --- Админ: промокод — скидка ---
    elif state == "admin_promo_discount":
        try:
            discount = int(text)
            if discount <= 0 or discount > 100: raise ValueError
            code = gtemp(uid, "promo_new_code")
            set_state(uid, "admin_promo_uses", promo_new_code=code, promo_new_discount=discount)
            await msg.reply_text(
                f"🎟 Промокод: *{code}*\n💰 Скидка: *{discount}%*\n\nШаг 3/3: Введите *количество активаций*:\n_(например: 10)_",
                parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ Отмена"))
        except ValueError:
            await msg.reply_text("❌ Введите число от 1 до 100:")

    # --- Админ: промокод — количество активаций ---
    elif state == "admin_promo_uses":
        try:
            uses = int(text)
            if uses <= 0: raise ValueError
            code     = gtemp(uid, "promo_new_code")
            discount = gtemp(uid, "promo_new_discount")
            promo_codes[code] = {
                "discount": discount,
                "uses_left": uses,
                "total_uses": uses,
                "activated_by": set(),
            }
            clear_state(uid)
            await msg.reply_text(
                f"✅ *Промокод создан!*\n\n🎟 Код: `{code}`\n💰 Скидка: *{discount}%*\n🔢 Активаций: *{uses}*",
                parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ К промокодам"))
        except ValueError:
            await msg.reply_text("❌ Введите целое число больше 0:")

    # --- Админ: удалить промокод ---
    elif state == "admin_promo_delete":
        code = text.upper().strip()
        if code in promo_codes:
            del promo_codes[code]
            clear_state(uid)
            await msg.reply_text(f"✅ Промокод `{code}` удалён.",
                parse_mode="Markdown", reply_markup=back_btn("admin_promos", "◀️ К промокодам"))
        else:
            await msg.reply_text(f"❌ Промокод `{code}` не найден. Попробуйте ещё раз:",
                parse_mode="Markdown")

# ==================== КОМАНДЫ ====================
async def setup_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start",       "🏠 Главное меню"),
        BotCommand("buy",         "⭐ Купить звёзды"),
        BotCommand("buyton",      "💎 Купить TON"),
        BotCommand("balance",     "💰 Мой баланс"),
        BotCommand("withdraw",    "💸 Вывести средства"),
        BotCommand("referral",    "👥 Реферальная программа"),
        BotCommand("info",        "ℹ️ Информация"),
        BotCommand("support",     "🆘 Поддержка"),
        BotCommand("admin",       "🔧 Панель администратора"),
        BotCommand("setcommands", "🔄 Обновить меню команд"),
    ])
    logger.info("✅ Команды зарегистрированы")

async def cmd_setcommands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await setup_commands(context.application)
    await update.message.reply_text("✅ *Команды обновлены!*", parse_mode="Markdown")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; all_users.add(uid); clear_state(uid); set_state(uid, "stars_count")
    await update.message.reply_text("⭐ *Покупка звёзд*\n\nВведите количество:\n_(минимум 50)_",
        parse_mode="Markdown", reply_markup=back_btn("main_menu"))

async def cmd_buyton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; all_users.add(uid); clear_state(uid); set_state(uid, "ton_amount")
    await update.message.reply_text(
        f"💎 *Покупка TON*\n\nКурс: *1 TON = {RATES['ton']:.0f}₽*\n\nВведите количество:",
        parse_mode="Markdown", reply_markup=back_btn("main_menu"))

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; all_users.add(uid)
    await update.message.reply_text(f"💰 *Ваш баланс: {get_balance(uid):.2f}₽*",
        parse_mode="Markdown", reply_markup=back_btn("main_menu", "🏠 Главное меню"))

async def cmd_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; all_users.add(uid)
    bu = BOT_USERNAME.lstrip("@")
    ref_link  = f"https://t.me/{bu}?start=ref_{uid}"
    ref_count = sum(1 for v in user_referrals.values() if v == uid)
    earned    = referral_earnings.get(uid, 0)
    await update.message.reply_text(
        f"👥 *Реферальная система*\n\n🔗 Ваша ссылка:\n`{ref_link}`\n\n"
        f"• Приглашено: *{ref_count}*\n• Заработано: *{earned:.2f}₽*",
        parse_mode="Markdown", reply_markup=back_btn("main_menu", "🏠 Главное меню"))

async def cmd_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆘 *Поддержка*\n\n👉 {SUPPORT_USERNAME}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Написать", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]))

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ *{BOT_NAME}*\n\n⭐ 1 ⭐ = {STARS_PRICE_RUB}₽\n💎 1 TON = {RATES['ton']:.0f}₽\n📞 {SUPPORT_USERNAME}",
        parse_mode="Markdown", reply_markup=back_btn("main_menu", "🏠 Главное меню"))

async def cmd_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; all_users.add(uid); clear_state(uid)
    balance = get_balance(uid)
    if balance < 100:
        return await update.message.reply_text(
            f"❌ Недостаточно средств!\nБаланс: *{balance:.2f}₽*, минимум 100₽", parse_mode="Markdown")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Рублями (₽)", callback_data="wdcur_rub")],
        [InlineKeyboardButton("💵 Долларами ($)", callback_data="wdcur_usd")],
        [InlineKeyboardButton("💎 TON", callback_data="wdcur_ton")],
        [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")],
    ])
    await update.message.reply_text(
        f"💸 *Вывод средств*\n\nБаланс: *{balance:.2f}₽*\n\nВыберите валюту:",
        parse_mode="Markdown", reply_markup=kb)

# ==================== MAIN ====================
def main():
    app = Application.builder().token(TOKEN).post_init(setup_commands).build()

    # Команды
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("admin",       cmd_admin))
    app.add_handler(CommandHandler("setcommands", cmd_setcommands))
    app.add_handler(CommandHandler("buy",         cmd_buy))
    app.add_handler(CommandHandler("buyton",      cmd_buyton))
    app.add_handler(CommandHandler("balance",     cmd_balance))
    app.add_handler(CommandHandler("referral",    cmd_referral))
    app.add_handler(CommandHandler("withdraw",    cmd_withdraw))
    app.add_handler(CommandHandler("support",     cmd_support))
    app.add_handler(CommandHandler("info",        cmd_info))

    # ---- Callbacks ----

    # Главное меню
    app.add_handler(CallbackQueryHandler(cb_main_menu,            pattern="^main_menu$"))

    # Промокод
    app.add_handler(CallbackQueryHandler(cb_promo,                pattern="^promo$"))

    # Звёзды
    app.add_handler(CallbackQueryHandler(cb_buy_stars,            pattern="^buy_stars$"))
    app.add_handler(CallbackQueryHandler(cb_buy_type,             pattern="^buy_type_(self|anon)$"))
    app.add_handler(CallbackQueryHandler(cb_stars_currency,       pattern="^scurrency_(rub|usd|ton)$"))
    app.add_handler(CallbackQueryHandler(cb_paid_stars,           pattern="^paid_stars$"))
    app.add_handler(CallbackQueryHandler(cb_admin_payment,        pattern="^st(ok|no)_"))

    # TON
    app.add_handler(CallbackQueryHandler(cb_buy_ton,              pattern="^buy_ton$"))
    app.add_handler(CallbackQueryHandler(cb_ton_pay,              pattern="^tonpay_(rub|usdt)$"))
    app.add_handler(CallbackQueryHandler(cb_paid_ton,             pattern="^paid_ton$"))
    app.add_handler(CallbackQueryHandler(cb_admin_ton,            pattern="^ton(ok|no)_"))

    # Вывод
    app.add_handler(CallbackQueryHandler(cb_withdraw,             pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(cb_withdraw_cur,         pattern="^wdcur_(rub|usd|ton)$"))
    app.add_handler(CallbackQueryHandler(cb_admin_withdrawal,     pattern="^wd(ok|no)_"))

    # Прочее
    app.add_handler(CallbackQueryHandler(cb_referral,             pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(cb_info,                 pattern="^info$"))
    app.add_handler(CallbackQueryHandler(cb_admin_panel,          pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(cb_admin_set_banner,     pattern="^admin_set_banner$"))
    app.add_handler(CallbackQueryHandler(cb_admin_del_banner,     pattern="^admin_del_banner$"))
    app.add_handler(CallbackQueryHandler(cb_admin_broadcast,      pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(cb_admin_edit_price,     pattern="^admin_edit_price$"))
    app.add_handler(CallbackQueryHandler(cb_admin_edit_ton,       pattern="^admin_edit_ton$"))
    app.add_handler(CallbackQueryHandler(cb_admin_edit_balance,   pattern="^admin_edit_balance$"))
    app.add_handler(CallbackQueryHandler(cb_admin_msg_user,       pattern="^admin_msg_user$"))
    app.add_handler(CallbackQueryHandler(cb_admin_stats,          pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(cb_admin_promos,         pattern="^admin_promos$"))
    app.add_handler(CallbackQueryHandler(cb_admin_promo_create,   pattern="^admin_promo_create$"))
    app.add_handler(CallbackQueryHandler(cb_admin_promo_delete,   pattern="^admin_promo_delete$"))

    # Текст и фото
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    print(f"✅ {BOT_NAME} запущен!")
    print(f"🤖 {BOT_USERNAME}")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
