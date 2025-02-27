# storage/conversations_storage.py
import json
import aiofiles
import logging
from config.config import CONVERSATIONS_FILE  # Укажи полный путь
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
conversations_cache: Dict[str, Any] = {}

async def load_conversations_to_cache():
    """Загружает данные из файла в кэш."""
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
    """Сохраняет кэш в файл."""
    try:
        async with aiofiles.open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(conversations_cache, indent=4, ensure_ascii=False))
        logger.info("Кэш сохранен в файл")
    except Exception as e:
        logger.error(f"Ошибка при сохранении кэша: {e}")

async def get_conversation(user_id: int) -> Dict[str, Any]:
    """Получает историю чата из кэша."""
    return conversations_cache.get(str(user_id), {"user_info": {}, "messages": [], "cart": []})

async def save_conversation(user_id: int, data: Dict[str, Any]):
    """Сохраняет данные в кэш."""
    conversations_cache[str(user_id)] = data
    logger.info(f"Данные сохранены в кэш для пользователя {user_id}")

async def update_chat_history(user_id: int, message: str, role: str = "user"):
    """Обновляет историю чата."""
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

async def get_user_cart(user_id: int) -> list:
    """
    Возвращает корзину пользователя по его ID.
    """
    conversation = await get_conversation(user_id)
    return conversation.get("cart", [])

async def clear_cart(user_id: int, restore_quantity: bool = False) -> None:
    """
    Очищает корзину пользователя.
    Если restore_quantity=True, восстанавливает количество товаров на складе.
    """
    conversation = await get_conversation(user_id)
    if "cart" in conversation:
        if restore_quantity:
            # Логика восстановления количества товаров (если требуется)
            pass
        conversation["cart"] = []  # Очищаем корзину
        await save_conversation(user_id, conversation)
        logger.info(f"Корзина пользователя {user_id} очищена")