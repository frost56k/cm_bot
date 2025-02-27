import asyncio
import logging
from aiogram import Bot, Dispatcher
from config.config import BOT_TOKEN
from storage.conversations_storage import load_conversations_to_cache
from utils.utils import periodic_save
from handlers.user_handlers import router as user_router
from handlers.coffee_handlers import router as coffee_router
from handlers.order_handlers import router as order_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Инициализация бота
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Подключаем роутеры
        dp.include_router(user_router)
        dp.include_router(coffee_router)
        dp.include_router(order_router)

        # Загружаем кэш
        await load_conversations_to_cache()

        # Запускаем периодическое сохранение
        asyncio.create_task(periodic_save())

        # Запускаем бота
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в main: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())