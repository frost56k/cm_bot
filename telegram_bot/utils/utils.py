# utils/utils.py
import asyncio
from storage.conversations_storage import save_conversations_from_cache
import logging

logger = logging.getLogger(__name__)

async def periodic_save():
    while True:
        await asyncio.sleep(30)
        await save_conversations_from_cache()
        logger.info("Периодическое сохранение кэша выполнено")

def format_cart(cart: list) -> str:
    if not cart:
        return "Ваша корзина пуста."
    total = 0
    cart_text = "🛒 *Ваша корзина:*\n\n"
    for item in cart:
        cart_text += f"- {item['name']} ({item['weight']}г) - {item['price']}\n"
        total += float(item['price'].replace(" руб.", ""))
    cart_text += f"\n*Итого:* {total:.2f} руб."
    return cart_text