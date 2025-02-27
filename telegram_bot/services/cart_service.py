# services/cart_service.py
from models.models import CartItem, Coffee
from storage.conversations_storage import get_conversation, save_conversation
from config.config import BOT_MIND_FILE
import json
import logging

logger = logging.getLogger(__name__)

async def get_user_cart(user_id: int) -> list[CartItem]:
    """Получает корзину пользователя из кэша."""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    return [CartItem(**item) for item in conversation.get("cart", [])]

async def add_to_cart(user_id: int, coffee_index: int, weight: str) -> None:
    """Добавляет товар в корзину и уменьшает количество для выбранного веса."""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    if "cart" not in conversation:
        conversation["cart"] = []

    # Загружаем данные о кофе из bot_mind.json
    with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        coffee_list = data.get("coffee_shop", [])
        if not 0 <= coffee_index < len(coffee_list):
            raise ValueError("Кофе с указанным индексом не найдено!")

    coffee = Coffee(**coffee_list[coffee_index])
    quantity_key = f"quantity_{weight}g"
    price_key = f"price_{weight}g"

    # Проверка наличия
    if getattr(coffee, quantity_key) <= 0 or getattr(coffee, price_key) is None:
        raise ValueError("Товар с таким весом отсутствует в наличии!")

    # Создаём объект CartItem
    cart_item = CartItem(
        coffee_index=coffee_index,
        name=coffee.name,
        weight=weight,
        price=getattr(coffee, price_key)
    )

    # Добавляем товар в корзину
    conversation["cart"].append(cart_item.__dict__)
    await save_conversation(user_id, conversation)

    # Уменьшаем количество в наличии
    coffee_list[coffee_index][quantity_key] -= 1
    with open(BOT_MIND_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Добавлен товар в корзину: {cart_item}, осталось {weight}г: {coffee_list[coffee_index][quantity_key]}")
    logger.info(f"Текущее состояние корзины в кэше: {conversation['cart']}")

async def clear_cart(user_id: int, restore_quantity: bool = False) -> None:
    """Очищает корзину пользователя, с опцией возврата остатков."""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    if "cart" not in conversation or not conversation["cart"]:
        return

    if restore_quantity:
        # Загружаем bot_mind.json и возвращаем остатки
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])

        for item in conversation["cart"]:
            cart_item = CartItem(**item)
            coffee = Coffee(**coffee_list[cart_item.coffee_index])
            quantity_key = f"quantity_{cart_item.weight}g"
            coffee_list[cart_item.coffee_index][quantity_key] += 1

        with open(BOT_MIND_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Остатки возвращены в bot_mind.json для пользователя {user_id}")

    # Очищаем корзину
    conversation["cart"] = []
    await save_conversation(user_id, conversation)

    logger.info(f"Корзина пользователя {user_id} очищена, restore_quantity={restore_quantity}")