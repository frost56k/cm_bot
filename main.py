import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from openai import OpenAI
from dotenv import load_dotenv
import time
import aiofiles

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CONVERSATIONS_FILE = "conversations.json"
BOT_MIND_FILE = "bot_mind.json"

if not os.path.exists(CONVERSATIONS_FILE):
    with open(CONVERSATIONS_FILE, 'w') as f:
        json.dump({}, f)

# Инициализация бота и OpenAI
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Глобальный кэш
conversations_cache = {}

def load_bot_mind() -> str:
    """Загрузка всех полей из bot_mind.json"""
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error loading bot mind: {e}")
        return ""

async def load_conversations_to_cache():
    """Загружает данные из файла в кэш"""
    global conversations_cache
    try:
        async with aiofiles.open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            conversations_cache = json.loads(content) if content else {}
        logger.info("Кэш загружен из файла")
    except Exception as e:
        logger.error(f"Ошибка при загрузке кэша: {e}")
        conversations_cache = {}

async def save_conversations_from_cache():
    """Сохраняет кэш в файл"""
    try:
        async with aiofiles.open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(conversations_cache, indent=4, ensure_ascii=False))
        logger.info("Кэш сохранен в файл")
    except Exception as e:
        logger.error(f"Ошибка при сохранении кэша: {e}")

async def periodic_save():
    """Периодически сохраняет кэш через некоторое время"""
    while True:
        await asyncio.sleep(300)  # сохранение 
        await save_conversations_from_cache()

async def get_conversation(user_id: int) -> Dict[str, Any]:
    """Получает историю чата из кэша"""
    return conversations_cache.get(str(user_id), {})

async def save_conversation(user_id: int, data: Dict[str, Any]):
    """Сохраняет данные в кэш"""
    conversations_cache[str(user_id)] = data

async def update_chat_history(user_id: int, message: str, role: str = "user"):
    """Обновляет историю чата"""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": []}
    conversation["messages"].append({
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    if len(conversation["messages"]) > 20:
        conversation["messages"] = conversation["messages"][-20:]
    await save_conversation(user_id, conversation)
    logger.info(f"Обновлена история для пользователя {user_id}: {conversation}")

async def on_shutdown(dp: Dispatcher):
    """Сохраняет кэш при завершении работы бота"""
    await save_conversations_from_cache()
    logger.info("Бот остановлен, кэш сохранен")

dp.shutdown.register(on_shutdown)

@dp.message(Command("start"))
async def start_handler(msg: Message):
    """Обработчик команды /start"""
    user = msg.from_user
    conversation = await get_conversation(user.id) or {"user_info": {}, "messages": []}
    
    if not conversation.get("user_info"):
        conversation["user_info"] = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        await save_conversation(user.id, conversation)
        logger.info(f"Сохранена информация о пользователе: {conversation['user_info']}")
    
    welcome_text = (
        f"Привет, {user.full_name}! Я — Кофе Мастер, ваш виртуальный помощник по ремонту кофемашин. 🛠️\n\n"
        "Наш чат-бот проходит тестирование. Если увидите ошибки, пишите: coffeemasterbel@gmail.com"
    )
    await msg.answer(welcome_text)

async def send_typing_indicator(chat_id):
    """Отправляет индикатор набора сообщения"""
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(10)

@dp.message(F.text)
async def message_handler(msg: Message):
    """Обработчик текстовых сообщений"""
    user_id = msg.from_user.id
    user = msg.from_user
    user_message = msg.text
    start_time = time.time()

    logger.info(f"Начало обработки сообщения: {start_time}")
    logger.info(f"Пользователь {user_id} написал: {user_message}")
    
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": []}
    
    if not conversation.get("user_info"):
        conversation["user_info"] = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        await save_conversation(user_id, conversation)
        logger.info(f"Сохранена информация о пользователе: {conversation['user_info']}")
    
    await bot.send_chat_action(msg.chat.id, "typing")
    await update_chat_history(user_id, user_message)
    logger.info(f"История обновлена: {time.time() - start_time} сек")

    messages = conversation.get("messages", [])
    system_prompt = load_bot_mind()
    messages_for_ai = [{"role": "system", "content": system_prompt}] + [
        {"role": m["role"], "content": m["message"]} for m in messages[-20:]
    ]
    
    logger.info(f"Запрос к ИИ с системным промптом: {messages_for_ai}")
    
    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=messages_for_ai,
            extra_headers={
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Coffee Master Bot"
            }
        )
        ai_response = completion.choices[0].message.content
        logger.info(f"ИИ ответил: {ai_response}")
        
        await update_chat_history(user_id, ai_response, "assistant")
        await msg.answer(ai_response)
        logger.info(f"Ответ отправлен: {time.time() - start_time} сек")
    except Exception as e:
        logger.error(f"API Error: {e}")
        await msg.answer("⚠️ Произошла ошибка. Попробуйте позже.")

async def main():
    """Главная функция для запуска бота"""
    await load_conversations_to_cache()  # Загружаем кэш
    asyncio.create_task(periodic_save())  # Запускаем периодическое сохранение
    logger.info("Запуск бота")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())