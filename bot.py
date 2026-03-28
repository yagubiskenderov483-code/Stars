import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN   = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"
ADMIN_ID    = 174415647
SBP_PHONE   = "89041751408"
SBP_BANK    = "ВТБ — Александр Ф."
TON_ADDRESS = "UQDGN5pfjPxorFyjN2xha84bapuADDtPcRofNDJ4dK2YXxZd"
CRYPTO_BOT  = "https://t.me/send?start=IVbfPL7Tk4XA"

# Курс звёзд в магазине (ниже рыночного)
SHOP_STAR_PRICE_RUB = 1.1   # рублей за 1 звезду
SHOP_MIN_STARS      = 50

bot     = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp      = Dispatcher(storage=storage)

# ══════════════════════════════════════════════════
#  PREMIUM ANIMATED EMOJI  (только в тексте!)
# ══════════════════════════════════════════════════
def e(doc_id: str) -> str:
    return f"<tg-emoji emoji-id='{doc_id}'>⭐</tg-emoji>"

PE = {
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
    "num4":       e("5794002218729162934"),
    "store":      e("4988289890769699938"),
}

# ══════════════════════════════════════════════════
#  БД
# ══════════════════════════════════════════════════
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
    c.execute('''CREATE TABLE IF NOT EXISTS shop_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        stars INTEGER,
        target_username TEXT,
        amount_rub REAL,
        status TEXT DEFAULT 'pending',
        created_date TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

# ══════════════════════════════════════════════════
#  FSM
# ══════════════════════════════════════════════════
class CheckStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_photo  = State()

class WithdrawStates(StatesGroup):
    waiting_for_username = State()

class RefillStates(StatesGroup):
    waiting_for_amount = State()

class ShopStates(StatesGroup):
    waiting_for_stars    = State()
    waiting_for_username = State()

class AdminStates(StatesGroup):
    broadcast_text   = State()
    give_stars_id    = State()
    give_stars_count = State()
    give_rub_id      = State()
    give_rub_amount  = State()
    ban_user_id      = State()

# ══════════════════════════════════════════════════
#  DB UTILS
# ══════════════════════════════════════════════════
def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id,username,first_name,registration_date) VALUES (?,?,?,?)',
              (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    u = c.fetchone(); conn.close(); return u

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    rows = c.fetchall(); conn.close()
    return [r[0] for r in rows]

def update_stars(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET stars_balance=stars_balance+? WHERE user_id=?', (amount, user_id))
    conn.commit(); conn.close()

def update_rub(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET rub_balance=rub_balance+? WHERE user_id=?', (amount, user_id))
    conn.commit(); conn.close()

def can_create_check(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT registration_date, neptun_team FROM users WHERE user_id=?', (user_id,))
    r = c.fetchone(); conn.close()
    if not r: return False
    if r[1] == 1: return True
    return (datetime.now() - datetime.fromisoformat(r[0])).days >= 21

def add_log(user_id, username, action):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (user_id,username,action,timestamp) VALUES (?,?,?,?)',
              (user_id, username, action, datetime.now().isoformat()))
    conn.commit(); conn.close()

def get_logs(visible_only=True):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    q = 'SELECT * FROM logs WHERE visible=1 ORDER BY timestamp DESC LIMIT 50' if visible_only \
        else 'SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50'
    c.execute(q); logs = c.fetchall(); conn.close(); return logs

def hide_all_logs():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE logs SET visible=0')
    conn.commit(); conn.close()

def save_refill(user_id, username, amount, method):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO refill_requests (user_id,username,amount,method,created_date) VALUES (?,?,?,?,?)',
              (user_id, username, amount, method, datetime.now().isoformat()))
    rid = c.lastrowid; conn.commit(); conn.close(); return rid

def save_shop_order(user_id, username, stars, target, amount_rub):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO shop_orders (user_id,username,stars,target_username,amount_rub,created_date) VALUES (?,?,?,?,?,?)',
              (user_id, username, stars, target, amount_rub, datetime.now().isoformat()))
    oid = c.lastrowid; conn.commit(); conn.close(); return oid

def get_global_stats():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users'); total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM checks'); total_checks = c.fetchone()[0]
    c.execute('SELECT SUM(stars_balance) FROM users'); total_stars = c.fetchone()[0] or 0
    c.execute('SELECT SUM(rub_balance) FROM users'); total_rub = c.fetchone()[0] or 0.0
    c.execute("SELECT COUNT(*) FROM refill_requests WHERE status='pending'"); pending_r = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM shop_orders WHERE status='pending'"); pending_s = c.fetchone()[0]
    conn.close()
    return total_users, total_checks, total_stars, total_rub, pending_r, pending_s

# ══════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{PE['num1']} Веб-Кошелёк", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))],
        [InlineKeyboardButton(text=f"{PE['num2']} Вывести звёзды",  callback_data="withdraw_stars")],
        [InlineKeyboardButton(text=f"{PE['num3']} Кошелёк",         callback_data="wallet"),
         InlineKeyboardButton(text=f"{PE['num4']} Магазин",          callback_data="shop")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="refill")],
        [InlineKeyboardButton(text="👑 Создать чек",      callback_data="create_check")],
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика",      callback_data="admin_stats")],
        [InlineKeyboardButton(text="📋 Логи",            callback_data="admin_logs"),
         InlineKeyboardButton(text="🗑 Очистить логи",   callback_data="clear_logs")],
        [InlineKeyboardButton(text="⭐ Выдать звёзды",   callback_data="admin_give_stars"),
         InlineKeyboardButton(text="💰 Выдать рубли",    callback_data="admin_give_rub")],
        [InlineKeyboardButton(text="📢 Рассылка",        callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🚫 Забанить юзера",  callback_data="admin_ban")],
        [InlineKeyboardButton(text="📦 Заявки пополнений", callback_data="admin_requests")],
        [InlineKeyboardButton(text="🛒 Заказы магазина", callback_data="admin_shop_orders")],
        [InlineKeyboardButton(text="👥 Пользователи",    callback_data="admin_users")],
    ])

# ══════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════
@dp.message(CommandStart())
async def start_handler(message: Message):
    uid  = message.from_user.id
    un   = message.from_user.username or "unknown"
    name = message.from_user.first_name or "User"
    add_user(uid, un, name)
    add_log(uid, un, "Запустил бота /start")

    text = (
        f"{PE['welcome']} <b>Добро пожаловать, {name}!</b>\n\n"
        f"<blockquote>"
        f"Этот бот — один из самых быстрых и надёжных сервисов по покупке и передаче Telegram Stars.\n\n"
        f"Мы работаем с тысячами клиентов и уже помогли купить миллионы звёзд по всему миру. "
        f"Здесь нет лишних шагов — просто выбираешь нужное количество, оплачиваешь и получаешь звёзды на аккаунт в течение нескольких минут.\n\n"
        f"Принимаем оплату через СБП, TON, CryptoBot. "
        f"Работаем без выходных, заявки обрабатываются круглосуточно.\n\n"
        f"Также доступен вывод звёзд через официальную платформу Fragment — "
        f"просто укажи юзернейм и пройди быструю авторизацию."
        f"</blockquote>\n\n"
        f"{PE['stats']} <b>Куплено через бота:</b>\n"
        f"{PE['stars_deal']} <b>7 357 760 звёзд</b>  (~$110 366)\n\n"
        f"{PE['shield']} <i>Безопасно · Быстро · Надёжно</i>"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="HTML")

# ══════════════════════════════════════════════════
#  СЕКРЕТНАЯ КОМАНДА
# ══════════════════════════════════════════════════
@dp.message(Command("neptunteam"))
async def neptun_handler(message: Message):
    uid = message.from_user.id
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET neptun_team=1 WHERE user_id=?', (uid,))
    conn.commit(); conn.close()
    add_log(uid, message.from_user.username or "?", "Активировал секретный доступ")
    await message.answer(f"{PE['shield']} <b>Доступ открыт.</b>", parse_mode="HTML")

# ══════════════════════════════════════════════════
#  КОШЕЛЁК
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "wallet")
async def wallet_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    user = get_user(uid)
    stars = user[4] if user else 0
    rub = user[5] if user else 0.0
    add_log(uid, callback.from_user.username or "?", "Просмотрел кошелёк")
    
    text = (
        f"{PE['wallet']} <b>Ваш кошелёк</b>\n\n"
        f"<blockquote>"
        f"{PE['star']} Звёзды: <b>{stars:,}</b>\n"
        f"{PE['money']} Рубли: <b>{rub:.2f} ₽</b>"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ══════════════════════════════════════════════════
#  МАГАЗИН (ИСПРАВЛЕНО - ПРОВЕРКА БАЛАНСА)
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "shop")
async def shop_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    user = get_user(uid)
    rub_balance = user[5] if user else 0.0
    add_log(uid, callback.from_user.username or "?", "Открыл магазин")
    
    text = (
        f"{PE['store']} <b>Магазин звёзд</b>\n\n"
        f"<blockquote>"
        f"Здесь вы можете купить звёзды по выгодному курсу и отправить их любому пользователю Telegram.\n\n"
        f"💰 Ваш баланс: <b>{rub_balance:.2f} ₽</b>\n"
        f"💫 Курс: <b>1 звезда = {SHOP_STAR_PRICE_RUB} ₽</b>\n"
        f"📦 Минимум: <b>{SHOP_MIN_STARS} звёзд</b>\n\n"
        f"Звёзды будут отправлены указанному пользователю автоматически после обработки заказа."
        f"</blockquote>\n\n"
        f"<i>Введите количество звёзд для покупки:</i>"
    )
    await state.set_state(ShopStates.waiting_for_stars)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(ShopStates.waiting_for_stars)
async def shop_stars_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    user = get_user(uid)
    rub_balance = user[5] if user else 0.0
    
    try:
        stars = int(message.text.strip())
        if stars < SHOP_MIN_STARS:
            await message.answer(
                f"{PE['warning']} <b>Минимальное количество: {SHOP_MIN_STARS} звёзд</b>",
                parse_mode="HTML"
            )
            return
        
        total_cost = stars * SHOP_STAR_PRICE_RUB
        
        # ПРОВЕРКА БАЛАНСА
        if rub_balance < total_cost:
            await message.answer(
                f"{PE['warning']} <b>Недостаточно средств!</b>\n\n"
                f"<blockquote>"
                f"Стоимость: <b>{total_cost:.2f} ₽</b>\n"
                f"Ваш баланс: <b>{rub_balance:.2f} ₽</b>\n"
                f"Не хватает: <b>{(total_cost - rub_balance):.2f} ₽</b>"
                f"</blockquote>\n\n"
                f"<i>Пополните баланс и попробуйте снова.</i>",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        await state.update_data(stars=stars, total_cost=total_cost)
        await state.set_state(ShopStates.waiting_for_username)
        await message.answer(
            f"{PE['target']} <b>Покупка звёзд</b>\n\n"
            f"<blockquote>"
            f"Количество: <b>{stars:,} звёзд</b>\n"
            f"Стоимость: <b>{total_cost:.2f} ₽</b>"
            f"</blockquote>\n\n"
            f"<i>Введите @username получателя (с @):</i>",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(f"{PE['warning']} <b>Введите число!</b>", parse_mode="HTML")

@dp.message(ShopStates.waiting_for_username)
async def shop_username_input(message: Message, state: FSMContext):
    uid = message.from_user.id
    un = message.from_user.username or "unknown"
    target = message.text.strip()
    
    if not target.startswith("@"):
        await message.answer(f"{PE['warning']} <b>Username должен начинаться с @</b>", parse_mode="HTML")
        return
    
    data = await state.get_data()
    stars = data['stars']
    total_cost = data['total_cost']
    
    # Списываем рубли
    update_rub(uid, -total_cost)
    
    # Сохраняем заказ
    oid = save_shop_order(uid, un, stars, target, total_cost)
    add_log(uid, un, f"Заказал {stars} звёзд для {target} за {total_cost:.2f}₽")
    
    # Уведомляем админа
    try:
        await bot.send_message(
            ADMIN_ID,
            f"{PE['store']} <b>Новый заказ магазина!</b>\n\n"
            f"<blockquote>"
            f"ID заказа: <b>#{oid}</b>\n"
            f"От: @{un} ({uid})\n"
            f"Звёзды: <b>{stars:,}</b>\n"
            f"Получатель: <b>{target}</b>\n"
            f"Сумма: <b>{total_cost:.2f} ₽</b>"
            f"</blockquote>",
            parse_mode="HTML"
        )
    except:
        pass
    
    await message.answer(
        f"{PE['check']} <b>Заказ принят!</b>\n\n"
        f"<blockquote>"
        f"ID заказа: <b>#{oid}</b>\n"
        f"Звёзды: <b>{stars:,}</b>\n"
        f"Получатель: <b>{target}</b>\n"
        f"Списано: <b>{total_cost:.2f} ₽</b>"
        f"</blockquote>\n\n"
        f"{PE['clock']} <i>Обработка займёт несколько минут.</i>",
        parse_mode="HTML"
    )
    await state.clear()

# ══════════════════════════════════════════════════
#  ВЫВОД ЗВЁЗД
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "withdraw_stars")
async def withdraw_cb(callback: CallbackQuery):
    uid = callback.from_user.id
    add_log(uid, callback.from_user.username or "?", "Попытка вывести звёзды")
    
    text = (
        f"{PE['warning']} <b>Вывод звёзд</b>\n\n"
        f"<blockquote>"
        f"Для вывода звёзд необходим аккаунт на <b>Fragment</b> от Telegram.\n\n"
        f"Без регистрации на Fragment вывод невозможен.\n\n"
        f"Зарегистрируйтесь по кнопке ниже, затем возвращайтесь для вывода."
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Регистрация Fragment", url="https://stars-zdgz.onrender.com")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ══════════════════════════════════════════════════
#  ПОПОЛНЕНИЕ
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "refill")
async def refill_cb(callback: CallbackQuery):
    text = (
        f"{PE[
