# handlers/user_handlers.py
from aiogram import Router, types, F
from aiogram.filters import Command
from services.ai_service import get_ai_response
from storage.conversations_storage import get_conversation, update_chat_history
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def start_handler(msg: types.Message):
    user = msg.from_user
    welcome_text = (
        f"Привет, {user.full_name}! Я — Кофе Мастер, ваш виртуальный помощник по ремонту кофемашин. 🛠️\n\n"
        f"Наш чат-бот проходит тестирование. Если увидите ошибки, пишите: coffeemasterbel@gmail.com\n"
        f"Используйте /coffeeshop, чтобы посмотреть каталог кофе."
    )
    await msg.answer(welcome_text)
    if str(user.id) not in (await get_conversation(user.id)):
        await update_chat_history(user.id, "", "user")  # Инициализация пустой истории
    logger.info(f"Пользователь {user.id} начал работу с ботом")

@router.message(F.text)
async def message_handler(msg: types.Message):
    user_id = msg.from_user.id
    user_message = msg.text
    await msg.bot.send_chat_action(msg.chat.id, "typing")
    await update_chat_history(user_id, user_message, "user")
    
    conversation = await get_conversation(user_id)
    messages = conversation.get("messages", [])
    ai_response = await get_ai_response([{"role": m["role"], "content": m["message"]} for m in messages[-20:]])
    await update_chat_history(user_id, ai_response, "assistant")
    await msg.answer(ai_response)
    logger.info(f"Ответ отправлен пользователю {user_id}")