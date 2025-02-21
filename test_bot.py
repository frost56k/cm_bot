import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7584113884:AAHJ9ZaZ2_m9_24Rwb3s9rRqEnKyAYpnobc"  # Вставьте токен напрямую для теста

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("coffeeshop"))
async def coffeeshop_handler(msg: types.Message):
    coffee_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Эспрессо", callback_data="espresso")],
        [InlineKeyboardButton(text="Капучино", callback_data="cappuccino")]
    ])
    await msg.answer("Выберите кофе:", reply_markup=coffee_keyboard)
    logger.info("Клавиатура отправлена")

async def main():
    logger.info("Запуск бота")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())