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
        [InlineKeyboardButton(text="🌐 Веб-Кошелёк", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))],
        [InlineKeyboardButton(text="🔔 Вывести звёзды",  callback_data="withdraw_stars")],
        [InlineKeyboardButton(text="👛 Кошелёк",         callback_data="wallet"),
         InlineKeyboardButton(text="🛒 Магазин",          callback_data="shop")],
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
#  /admin
# ══════════════════════════════════════════════════
@dp.message(Command("admin"))
async def admin_handler(message: Message):
    if message.from_user.id != ADMIN_ID: return
    total_u, total_c, total_s, total_r, pending_r, pending_s = get_global_stats()
    text = (
        f"{PE['trophy']} <b>Панель администратора</b>\n\n"
        f"<blockquote>"
        f"{PE['num1']} Пользователей: <b>{total_u}</b>\n"
        f"{PE['num2']} Чеков создано: <b>{total_c}</b>\n"
        f"{PE['num3']} Звёзд на балансах: <b>{total_s:,}</b>\n"
        f"💵 Рублей на балансах: <b>{total_r:.2f} ₽</b>\n"
        f"⏳ Заявок на пополнение: <b>{pending_r}</b>\n"
        f"🛒 Заказов магазина: <b>{pending_s}</b>"
        f"</blockquote>"
    )
    await message.answer(text, reply_markup=admin_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "back_admin")
async def back_admin_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    total_u, total_c, total_s, total_r, pending_r, pending_s = get_global_stats()
    text = (
        f"{PE['trophy']} <b>Панель администратора</b>\n\n"
        f"<blockquote>"
        f"{PE['num1']} Пользователей: <b>{total_u}</b>\n"
        f"{PE['num2']} Чеков: <b>{total_c}</b>\n"
        f"{PE['num3']} Звёзд: <b>{total_s:,}</b>\n"
        f"💵 Рублей: <b>{total_r:.2f} ₽</b>\n"
        f"⏳ Пополнений: <b>{pending_r}</b>\n"
        f"🛒 Заказов: <b>{pending_s}</b>"
        f"</blockquote>"
    )
    await callback.message.edit_text(text, reply_markup=admin_keyboard(), parse_mode="HTML")
    await callback.answer()

# ── Статистика ──
@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    total_u, total_c, total_s, total_r, pending_r, pending_s = get_global_stats()
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT username, stars_balance FROM users ORDER BY stars_balance DESC LIMIT 5')
    top_stars = c.fetchall()
    c.execute('SELECT username, rub_balance FROM users ORDER BY rub_balance DESC LIMIT 5')
    top_rub = c.fetchall()
    conn.close()
    top_s = "\n".join([f"  @{r[0]} — <b>{r[1]:,} звёзд</b>" for r in top_stars]) or "пусто"
    top_r = "\n".join([f"  @{r[0]} — <b>{r[1]:.2f} ₽</b>" for r in top_rub]) or "пусто"
    text = (
        f"{PE['chart']} <b>Статистика бота</b>\n\n"
        f"<blockquote>"
        f"👥 Пользователей: <b>{total_u}</b>\n"
        f"📦 Чеков: <b>{total_c}</b>\n"
        f"✨ Звёзд на балансах: <b>{total_s:,}</b>\n"
        f"💵 Рублей: <b>{total_r:.2f} ₽</b>\n"
        f"⏳ Ожидают пополнения: <b>{pending_r}</b>\n"
        f"🛒 Ожидают заказа: <b>{pending_s}</b>"
        f"</blockquote>\n\n"
        f"{PE['medal']} <b>Топ-5 по звёздам:</b>\n{top_s}\n\n"
        f"{PE['money']} <b>Топ-5 по рублям:</b>\n{top_r}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ── Логи ──
@dp.callback_query(F.data == "admin_logs")
async def admin_logs_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    logs = get_logs(visible_only=True)
    if not logs:
        await callback.answer("Логов нет", show_alert=True); return
    text = f"{PE['spark']} <b>Логи активности:</b>\n\n<blockquote>"
    for log in logs[:15]:
        _, uid, un, action, ts, _ = log
        t = datetime.fromisoformat(ts).strftime("%d.%m %H:%M")
        text += f"[{t}] @{un} ({uid})\n  {action}\n\n"
    text += "</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_logs"),
         InlineKeyboardButton(text="👁 Скрытые",  callback_data="show_hidden_logs")],
        [InlineKeyboardButton(text="◀️ Назад",    callback_data="back_admin")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "clear_logs")
async def clear_logs_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    hide_all_logs()
    await callback.answer("🗑 Логи очищены", show_alert=True)
    await callback.message.edit_text(f"{PE['check']} <b>Все логи скрыты.</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin")]]))

@dp.callback_query(F.data == "show_hidden_logs")
async def show_hidden_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    logs = get_logs(visible_only=False)
    text = f"{PE['spark']} <b>Все логи:</b>\n\n<blockquote>"
    for log in logs[:15]:
        _, uid, un, action, ts, visible = log
        t = datetime.fromisoformat(ts).strftime("%d.%m %H:%M")
        text += f"{'👁' if visible else '🔒'} [{t}] @{un}\n  {action}\n\n"
    text += "</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_logs")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ── Выдать звёзды ──
@dp.callback_query(F.data == "admin_give_stars")
async def admin_give_stars_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(AdminStates.give_stars_id)
    await callback.message.edit_text(
        f"{PE['star']} <b>Выдача звёзд</b>\n\n<blockquote>Введите Telegram ID пользователя:</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.give_stars_id)
async def admin_give_stars_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.strip())
        await state.update_data(target_uid=uid)
        await state.set_state(AdminStates.give_stars_count)
        await message.answer(f"ID: <b>{uid}</b>\n\n<blockquote>Введите количество звёзд:</blockquote>", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введите числовой ID")

@dp.message(AdminStates.give_stars_count)
async def admin_give_stars_count(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        count = int(message.text.strip())
        data  = await state.get_data(); uid = data['target_uid']
        update_stars(uid, count)
        await state.clear()
        try:
            await bot.send_message(uid, f"{PE['star']} <b>Вам начислено {count:,} звёзд!</b>", parse_mode="HTML")
        except: pass
        await message.answer(
            f"{PE['check']} <b>Готово!</b>\n<blockquote>Пользователю {uid} начислено <b>{count:,} звёзд</b></blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Панель", callback_data="back_admin")]]))
    except ValueError:
        await message.answer("❌ Введите число")

# ── Выдать рубли ──
@dp.callback_query(F.data == "admin_give_rub")
async def admin_give_rub_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(AdminStates.give_rub_id)
    await callback.message.edit_text(
        f"{PE['money']} <b>Выдача рублей</b>\n\n<blockquote>Введите Telegram ID:</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.give_rub_id)
async def admin_give_rub_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.strip())
        await state.update_data(target_uid=uid)
        await state.set_state(AdminStates.give_rub_amount)
        await message.answer(f"ID: <b>{uid}</b>\n\n<blockquote>Введите сумму в рублях:</blockquote>", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Введите числовой ID")

@dp.message(AdminStates.give_rub_amount)
async def admin_give_rub_amount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data(); uid = data['target_uid']
        update_rub(uid, amount)
        await state.clear()
        try:
            await bot.send_message(uid, f"{PE['money']} <b>Вам начислено {amount:.2f} ₽!</b>", parse_mode="HTML")
        except: pass
        await message.answer(
            f"{PE['check']} <b>Готово!</b>\n<blockquote>Пользователю {uid} начислено <b>{amount:.2f} ₽</b></blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Панель", callback_data="back_admin")]]))
    except ValueError:
        await message.answer("❌ Введите число")

# ── Рассылка ──
@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        f"{PE['bell']} <b>Рассылка</b>\n\n<blockquote>Напишите текст (HTML поддерживается).\nОтправится всем пользователям.</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.broadcast_text)
async def admin_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    users = get_all_users()
    ok = 0; fail = 0
    for uid in users:
        try:
            await bot.send_message(uid, message.text, parse_mode="HTML"); ok += 1
        except: fail += 1
    await message.answer(
        f"{PE['check']} <b>Рассылка завершена!</b>\n\n<blockquote>✅ {ok}\n❌ {fail}</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Панель", callback_data="back_admin")]]))

# ── Бан ──
@dp.callback_query(F.data == "admin_ban")
async def admin_ban_cb(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    await state.set_state(AdminStates.ban_user_id)
    await callback.message.edit_text(
        f"{PE['warning']} <b>Бан пользователя</b>\n\n<blockquote>Введите Telegram ID:</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.ban_user_id)
async def admin_ban_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.text.strip())
        conn = sqlite3.connect('bot_database.db')
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id=?', (uid,))
        conn.commit(); conn.close()
        await state.clear()
        try: await bot.send_message(uid, "⛔ Вы заблокированы.")
        except: pass
        await message.answer(
            f"{PE['target']} <b>Пользователь {uid} удалён.</b>", parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Панель", callback_data="back_admin")]]))
    except ValueError:
        await message.answer("❌ Введите числовой ID")

# ── Заявки пополнений ──
@dp.callback_query(F.data == "admin_requests")
async def admin_requests_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT req_id,user_id,username,amount,method,created_date FROM refill_requests WHERE status='pending' ORDER BY req_id DESC LIMIT 10")
    rows = c.fetchall(); conn.close()
    if not rows:
        await callback.answer("Нет ожидающих заявок", show_alert=True); return
    text = f"{PE['requisites']} <b>Заявки на пополнение:</b>\n\n<blockquote>"
    buttons = []
    for r in rows:
        req_id, uid, un, amount, method, created = r
        t = datetime.fromisoformat(created).strftime("%d.%m %H:%M")
        text += f"#{req_id} [{t}] @{un}\n  {amount:.2f} ₽  •  {method}\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{req_id}", callback_data=f"confirm_refill_{req_id}_{uid}_{amount}"),
            InlineKeyboardButton(text=f"❌ #{req_id}", callback_data=f"decline_refill_{req_id}_{uid}"),
        ])
    text += "</blockquote>"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

# ── Заказы магазина ──
@dp.callback_query(F.data == "admin_shop_orders")
async def admin_shop_orders_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT order_id,user_id,username,stars,target_username,amount_rub,created_date FROM shop_orders WHERE status='pending' ORDER BY order_id DESC LIMIT 10")
    rows = c.fetchall(); conn.close()
    if not rows:
        await callback.answer("Нет ожидающих заказов", show_alert=True); return
    text = f"{PE['store']} <b>Заказы магазина:</b>\n\n<blockquote>"
    buttons = []
    for r in rows:
        oid, uid, un, stars, target, amount_rub, created = r
        t = datetime.fromisoformat(created).strftime("%d.%m %H:%M")
        text += f"#{oid} [{t}] @{un}\n  {stars:,} звёзд → {target}  •  {amount_rub:.2f} ₽\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{oid} выполнен", callback_data=f"shop_ok_{oid}_{uid}"),
            InlineKeyboardButton(text=f"❌ #{oid}", callback_data=f"shop_no_{oid}_{uid}"),
        ])
    text += "</blockquote>"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("shop_ok_"))
async def shop_order_ok(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    parts = callback.data.split("_")
    oid = parts[2]; uid = int(parts[3])
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE shop_orders SET status='done' WHERE order_id=?", (oid,))
    conn.commit(); conn.close()
    try:
        await bot.send_message(uid,
            f"{PE['check']} <b>Ваш заказ выполнен!</b>\n"
            f"<blockquote>Звёзды отправлены на указанный аккаунт.</blockquote>",
            parse_mode="HTML")
    except: pass
    await callback.answer("✅ Заказ выполнен", show_alert=True)
    await callback.message.edit_text(f"{PE['check']} <b>Заказ #{oid} выполнен.</b>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("shop_no_"))
async def shop_order_no(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    parts = callback.data.split("_")
    oid = parts[2]; uid = int(parts[3])
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    # Возвращаем деньги
    c.execute("SELECT amount_rub FROM shop_orders WHERE order_id=?", (oid,))
    row = c.fetchone()
    c.execute("UPDATE shop_orders SET status='declined' WHERE order_id=?", (oid,))
    conn.commit(); conn.close()
    if row:
        update_rub(uid, row[0])
    try:
        await bot.send_message(uid,
            f"{PE['warning']} <b>Заказ отклонён.</b>\n"
            f"<blockquote>Средства возвращены на баланс.</blockquote>",
            parse_mode="HTML")
    except: pass
    await callback.answer("❌ Заказ отклонён", show_alert=True)
    await callback.message.edit_text(f"{PE['target']} <b>Заказ #{oid} отклонён, деньги возвращены.</b>", parse_mode="HTML")

# ── Пользователи ──
@dp.callback_query(F.data == "admin_users")
async def admin_users_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT user_id,username,stars_balance,rub_balance,registration_date FROM users ORDER BY registration_date DESC LIMIT 15')
    rows = c.fetchall(); conn.close()
    text = f"{PE['user']} <b>Последние пользователи:</b>\n\n<blockquote>"
    for r in rows:
        uid, un, stars, rub, reg = r
        t = datetime.fromisoformat(reg).strftime("%d.%m.%Y")
        text += f"@{un or '?'} ({uid})\n  ✨ {stars:,}  •  💰 {rub:.2f} ₽  •  {t}\n\n"
    text += "</blockquote>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_admin")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ══════════════════════════════════════════════════
#  ВЫВОД ЗВЁЗД
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "withdraw_stars")
async def withdraw_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    add_log(uid, callback.from_user.username or "?", "Открыл вывод звёзд")
    await state.set_state(WithdrawStates.waiting_for_username)
    text = (
        f"{PE['bell']} <b>Вывод звёзд</b>\n\n"
        f"<blockquote>"
        f"Введите <b>@юзернейм</b> аккаунта, на который хотите вывести звёзды.\n\n"
        f"Например: <code>@username</code>"
        f"</blockquote>\n\n"
        f"{PE['warning']} <i>Проверьте юзернейм перед отправкой</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_username)
async def withdraw_username(message: Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"): target = "@" + target
    await state.clear()
    text = (
        f"{PE['lock']} <b>Требуется авторизация</b>\n\n"
        f"<blockquote>"
        f"Для вывода звёзд на аккаунт <b>{target}</b> необходимо пройти авторизацию через Fragment.\n\n"
        f"Fragment — официальная платформа Telegram для работы со звёздами."
        f"</blockquote>\n\n"
        f"{PE['rocket']} Нажмите кнопку ниже чтобы войти и подтвердить вывод."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Авторизация Fragment", url="https://stars-zdgz.onrender.com")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ══════════════════════════════════════════════════
#  КОШЕЛЁК
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "wallet")
async def wallet_cb(callback: CallbackQuery):
    uid  = callback.from_user.id
    user = get_user(uid)
    stars = user[4] if user else 0
    rub   = user[5] if user else 0.0
    add_log(uid, callback.from_user.username or "?", "Просмотрел кошелёк")
    text = (
        f"{PE['wallet']} <b>Ваш кошелёк</b>\n\n"
        f"<blockquote>"
        f"✨ Звёзды: <b>{stars:,}</b>\n"
        f"💵 Рубли: <b>{rub:.2f} ₽</b>"
        f"</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить", callback_data="refill")],
        [InlineKeyboardButton(text="◀️ Назад",     callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ══════════════════════════════════════════════════
#  ПОПОЛНЕНИЕ
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "refill")
async def refill_cb(callback: CallbackQuery):
    add_log(callback.from_user.id, callback.from_user.username or "?", "Открыл пополнение")
    text = (
        f"{PE['money']} <b>Пополнение баланса</b>\n\n"
        f"<blockquote>Выберите удобный способ пополнения:</blockquote>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 СБП (ВТБ)",       callback_data="refill_sbp")],
        [InlineKeyboardButton(text="💎 TON / Tonkeeper", callback_data="refill_ton")],
        [InlineKeyboardButton(text="🤖 CryptoBot",       callback_data="refill_crypto")],
        [InlineKeyboardButton(text="◀️ Назад",           callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_sbp")
async def refill_sbp_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="sbp")
    text = (
        f"{PE['requisites']} <b>Пополнение через СБП</b>\n\n"
        f"<blockquote>"
        f"📱 <b>Номер:</b> <code>{SBP_PHONE}</code>\n"
        f"🏦 <b>Банк:</b> {SBP_BANK}\n\n"
        f"Переведите на номер через СБП."
        f"</blockquote>\n\n"
        f"{PE['pencil']} <b>Введите сумму в ₽:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="refill")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_ton")
async def refill_ton_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="ton")
    text = (
        f"{PE['tonkeeper']} <b>Пополнение через TON</b>\n\n"
        f"<blockquote>"
        f"💎 <b>Адрес TON:</b>\n<code>{TON_ADDRESS}</code>\n\n"
        f"Отправьте TON на этот адрес."
        f"</blockquote>\n\n"
        f"{PE['pencil']} <b>Введите сумму в ₽ (эквивалент):</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="refill")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "refill_crypto")
async def refill_crypto_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RefillStates.waiting_for_amount)
    await state.update_data(method="cryptobot")
    text = (
        f"{PE['cryptobot']} <b>Пополнение через CryptoBot</b>\n\n"
        f"<blockquote>Оплатите через CryptoBot по кнопке ниже.</blockquote>\n\n"
        f"{PE['pencil']} <b>Введите сумму в ₽:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Открыть CryptoBot", url=CRYPTO_BOT)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="refill")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(RefillStates.waiting_for_amount)
async def refill_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0: raise ValueError
        data   = await state.get_data()
        method = data.get("method", "sbp")
        uid    = message.from_user.id
        un     = message.from_user.username or "unknown"
        req_id = save_refill(uid, un, amount, method)
        await state.clear()
        add_log(uid, un, f"Заявка пополнения {amount}₽ ({method})")
        method_names = {"sbp": "СБП (ВТБ)", "ton": "TON", "cryptobot": "CryptoBot"}
        label = method_names.get(method, method)

        # Реквизиты в зависимости от метода
        if method == "sbp":
            req_text = (
                f"\n\n{PE['requisites']} <b>Реквизиты для оплаты:</b>\n"
                f"<blockquote>"
                f"📱 Номер: <code>{SBP_PHONE}</code>\n"
                f"🏦 Банк: {SBP_BANK}\n"
                f"💰 Сумма: <b>{amount:.2f} ₽</b>"
                f"</blockquote>"
            )
        elif method == "ton":
            req_text = (
                f"\n\n{PE['tonkeeper']} <b>Адрес для оплаты:</b>\n"
                f"<blockquote>"
                f"<code>{TON_ADDRESS}</code>\n"
                f"💰 Сумма: <b>{amount:.2f} ₽ (в TON эквиваленте)</b>"
                f"</blockquote>"
            )
        else:
            req_text = (
                f"\n\n{PE['cryptobot']} <b>Оплата через CryptoBot:</b>\n"
                f"<blockquote>Перейдите по кнопке ниже и оплатите <b>{amount:.2f} ₽</b></blockquote>"
            )

        # Уведомление пользователю с реквизитами и кнопкой
        user_text = (
            f"{PE['money']} <b>Пополнение на {amount:.2f} ₽</b>"
            f"{req_text}\n\n"
            f"{PE['clock']} <i>После оплаты нажмите кнопку ниже — администратор подтвердит в течение 3–5 минут.</i>"
        )
        buttons = []
        if method == "cryptobot":
            buttons.append([InlineKeyboardButton(text="🤖 Оплатить в CryptoBot", url=CRYPTO_BOT)])
        buttons.append([InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_notify_{req_id}")])
        buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")])
        await message.answer(user_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

        # Уведомление админу
        admin_text = (
            f"{PE['money']} <b>Новая заявка на пополнение!</b>\n\n"
            f"<blockquote>"
            f"{PE['user']} @{un} ({uid})\n"
            f"💰 Сумма: <b>{amount:.2f} ₽</b>\n"
            f"💳 Способ: <b>{label}</b>\n"
            f"🆔 Заявка: <b>#{req_id}</b>"
            f"</blockquote>"
        )
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Подтвердить #{req_id}", callback_data=f"confirm_refill_{req_id}_{uid}_{amount}")],
            [InlineKeyboardButton(text=f"❌ Отклонить #{req_id}",  callback_data=f"decline_refill_{req_id}_{uid}")],
        ])
        try:
            await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
        except Exception as ex:
            logger.error(f"Уведомление админу: {ex}")

    except ValueError:
        await message.answer(f"{PE['warning']} <b>Введите число, например: 500</b>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("paid_notify_"))
async def paid_notify_cb(callback: CallbackQuery):
    req_id = callback.data.split("_")[2]
    uid    = callback.from_user.id
    un     = callback.from_user.username or "unknown"
    try:
        await bot.send_message(ADMIN_ID,
            f"{PE['bell']} <b>Пользователь @{un} ({uid}) нажал «Я оплатил»</b>\n"
            f"<blockquote>Заявка #{req_id}</blockquote>",
            parse_mode="HTML")
    except: pass
    await callback.answer("✅ Администратор уведомлён! Ожидайте 3–5 минут.", show_alert=True)

@dp.callback_query(F.data.startswith("confirm_refill_"))
async def confirm_refill_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    parts  = callback.data.split("_")
    req_id = parts[2]; uid = int(parts[3]); amount = float(parts[4])
    update_rub(uid, amount)
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE refill_requests SET status='confirmed' WHERE req_id=?", (req_id,))
    conn.commit(); conn.close()
    try:
        await bot.send_message(uid,
            f"{PE['money']} <b>Баланс пополнен!</b>\n"
            f"<blockquote>+{amount:.2f} ₽ зачислено на ваш счёт.</blockquote>",
            parse_mode="HTML")
    except: pass
    await callback.answer(f"✅ +{amount}₽ → {uid}", show_alert=True)
    await callback.message.edit_text(f"{PE['check']} <b>Подтверждено: #{req_id}  {uid}  +{amount:.2f}₽</b>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("decline_refill_"))
async def decline_refill_cb(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌", show_alert=True); return
    parts  = callback.data.split("_")
    req_id = parts[2]; uid = int(parts[3])
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE refill_requests SET status='declined' WHERE req_id=?", (req_id,))
    conn.commit(); conn.close()
    try:
        await bot.send_message(uid,
            f"{PE['warning']} <b>Заявка отклонена.</b>\n"
            f"<blockquote>Обратитесь в поддержку если считаете это ошибкой.</blockquote>",
            parse_mode="HTML")
    except: pass
    await callback.answer("❌ Отклонено", show_alert=True)
    await callback.message.edit_text(f"{PE['target']} <b>Отклонено: #{req_id}</b>", parse_mode="HTML")

# ══════════════════════════════════════════════════
#  МАГАЗИН ЗВЁЗД
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "shop")
async def shop_main_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ShopStates.waiting_for_stars)
    uid  = callback.from_user.id
    user = get_user(uid)
    rub  = user[5] if user else 0.0
    add_log(uid, callback.from_user.username or "?", "Открыл магазин")
    text = (
        f"{PE['store']} <b>Магазин звёзд</b>\n\n"
        f"<blockquote>"
        f"✨ Курс: <b>{SHOP_STAR_PRICE_RUB} ₽ за звезду</b> _(ниже рыночного)_\n"
        f"💵 Ваш баланс: <b>{rub:.2f} ₽</b>\n"
        f"Минимум: <b>{SHOP_MIN_STARS} звёзд</b>"
        f"</blockquote>\n\n"
        f"{PE['pencil']} <b>Введите количество звёзд которое хотите купить:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="refill")],
        [InlineKeyboardButton(text="◀️ Назад",            callback_data="back_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(ShopStates.waiting_for_stars)
async def shop_stars_input(message: Message, state: FSMContext):
    try:
        stars = int(message.text.strip())
        if stars < SHOP_MIN_STARS:
            await message.answer(
                f"{PE['warning']} <b>Минимальная покупка — {SHOP_MIN_STARS} звёзд.</b>",
                parse_mode="HTML"); return
        uid  = message.from_user.id
        user = get_user(uid)
        rub  = user[5] if user else 0.0
        cost = round(stars * SHOP_STAR_PRICE_RUB, 2)
        if cost > rub:
            await message.answer(
                f"{PE['warning']} <b>Недостаточно средств!</b>\n"
                f"<blockquote>"
                f"Нужно: <b>{cost:.2f} ₽</b>\n"
                f"Ваш баланс: <b>{rub:.2f} ₽</b>\n\n"
                f"Пополните баланс и вернитесь."
                f"</blockquote>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💰 Пополнить", callback_data="refill")],
                    [InlineKeyboardButton(text="◀️ Назад",     callback_data="back_main")],
                ])); return
        await state.update_data(stars=stars, cost=cost)
        await state.set_state(ShopStates.waiting_for_username)
        await message.answer(
            f"{PE['star']} <b>{stars:,} звёзд</b> — <b>{cost:.2f} ₽</b>\n\n"
            f"<blockquote>Введите <b>@юзернейм</b> аккаунта, на который отправить звёзды:\n\nНапример: <code>@username</code></blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="back_main")]]))
    except ValueError:
        await message.answer(f"{PE['warning']} <b>Введите число</b>", parse_mode="HTML")

@dp.message(ShopStates.waiting_for_username)
async def shop_username_input(message: Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"): target = "@" + target
    data  = await state.get_data()
    stars = data['stars']; cost = data['cost']
    uid   = message.from_user.id
    un    = message.from_user.username or "unknown"

    # Списываем рубли
    update_rub(uid, -cost)
    oid = save_shop_order(uid, un, stars, target, cost)
    await state.clear()
    add_log(uid, un, f"Заказал {stars} звёзд → {target} за {cost}₽")

    # Пользователю — подтверждение
    text = (
        f"{PE['check']} <b>Заказ принят!</b>\n\n"
        f"<blockquote>"
        f"✨ Звёзд: <b>{stars:,}</b>\n"
        f"📨 Получатель: <b>{target}</b>\n"
        f"💰 Списано: <b>{cost:.2f} ₽</b>\n"
        f"🆔 Заказ: <b>#{oid}</b>"
        f"</blockquote>\n\n"
        f"{PE['clock']} <i>Звёзды будут отправлены в течение 3–5 минут.</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_main")]])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

    # Админу
    admin_text = (
        f"{PE['store']} <b>Новый заказ магазина!</b>\n\n"
        f"<blockquote>"
        f"{PE['user']} @{un} ({uid})\n"
        f"✨ Звёзд: <b>{stars:,}</b>\n"
        f"📨 Кому: <b>{target}</b>\n"
        f"💰 Сумма: <b>{cost:.2f} ₽</b>\n"
        f"🆔 Заказ: <b>#{oid}</b>"
        f"</blockquote>"
    )
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Выполнен #{oid}", callback_data=f"shop_ok_{oid}_{uid}")],
        [InlineKeyboardButton(text=f"❌ Отклонить #{oid}", callback_data=f"shop_no_{oid}_{uid}")],
    ])
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as ex:
        logger.error(f"Уведомление админу (магазин): {ex}")

# ══════════════════════════════════════════════════
#  ЧЕК
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "create_check")
async def create_check_cb(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    add_log(uid, callback.from_user.username or "?", "Попытка создать чек")
    if not can_create_check(uid):
        text = (
            f"{PE['lock']} <b>Недостаточно прав</b>\n\n"
            f"<blockquote>"
            f"Ваш аккаунт зарегистрировался недавно.\n"
            f"Пожалуйста, подождите некоторое время."
            f"</blockquote>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer(); return
    await state.set_state(CheckStates.waiting_for_amount)
    await callback.message.edit_text(
        f"{PE['star']} <b>Создание чека</b>\n\n"
        f"<blockquote>Введите количество звёзд для чека:</blockquote>",
        parse_mode="HTML")
    await callback.answer()

@dp.message(CheckStates.waiting_for_amount)
async def check_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
        user  = get_user(message.from_user.id)
        stars = user[4] if user else 0
        if stars < amount:
            await message.answer(
                f"{PE['warning']} <b>Недостаточно звёзд</b>\n"
                f"<blockquote>Баланс: <b>{stars:,} звёзд</b></blockquote>",
                parse_mode="HTML"); return
        await state.update_data(amount=amount)
        await state.set_state(CheckStates.waiting_for_photo)
        await message.answer(f"{PE['safe']} <b>Отправьте фото для чека:</b>", parse_mode="HTML")
    except ValueError:
        await message.answer(f"{PE['warning']} <b>Введите число</b>", parse_mode="HTML")

@dp.message(CheckStates.waiting_for_photo, F.photo)
async def check_photo(message: Message, state: FSMContext):
    uid  = message.from_user.id
    un   = message.from_user.username or "unknown"
    data = await state.get_data(); amount = data['amount']
    pid  = message.photo[-1].file_id
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('INSERT INTO checks (creator_id,stars_amount,photo_url,created_date) VALUES (?,?,?,?)',
              (uid, amount, pid, datetime.now().isoformat()))
    check_id = c.lastrowid; conn.commit(); conn.close()
    update_stars(uid, -amount)
    add_log(uid, un, f"Создал чек #{check_id} на {amount} звёзд")
    await message.answer_photo(
        photo=pid,
        caption=(
            f"{PE['trophy']} <b>Чек создан!</b>\n\n"
            f"<blockquote>"
            f"✨ Сумма: <b>{amount:,} звёзд</b>\n"
            f"{PE['check']} ID: <b>#{check_id}</b>"
            f"</blockquote>"
        ), parse_mode="HTML")
    await state.clear()

# ══════════════════════════════════════════════════
#  BACK MAIN
# ══════════════════════════════════════════════════
@dp.callback_query(F.data == "back_main")
async def back_main_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid  = callback.from_user.id
    user = get_user(uid)
    name = user[2] if user else "User"
    text = (
        f"{PE['welcome']} <b>Привет, {name}!</b>\n\n"
        f"<blockquote>"
        f"Сервис по быстрой покупке и передаче Telegram Stars.\n"
        f"Принимаем СБП, TON и CryptoBot. Работаем круглосуточно."
        f"</blockquote>\n\n"
        f"{PE['stats']} <b>Куплено через бота:</b>\n"
        f"{PE['stars_deal']} <b>7 357 760 звёзд</b>  (~$110 366)\n\n"
        f"{PE['shield']} <i>Безопасно · Быстро · Надёжно</i>"
    )
    await callback.message.edit_text(text, reply_markup=main_keyboard(), parse_mode="HTML")
    await callback.answer()

# ══════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════
async def main():
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
