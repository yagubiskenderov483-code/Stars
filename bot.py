import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "7511789367:AAGVIDu27Sb5ZwJUjQRiHOJ-CZinbRUFrDQ"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    webapp_url = "https://stars-zdgz.onrender.com"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url=webapp_url))]
    ])
    await message.answer("Нажми кнопку, чтобы открыть Mini App", reply_markup=keyboard)

@dp.message(F.web_app_data)
async def handle_webapp(message: Message):
    data = message.web_app_data.data
    await message.answer(f"✅ Получено: {data}")

async def main():
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
