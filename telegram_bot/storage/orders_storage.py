# storage/orders_storage.py
import json
import aiofiles
import logging
from config import PENDING_ORDERS_FILE, ORDER_NUMBER_FILE, ORDER_HISTORY_FILE

logger = logging.getLogger(__name__)

async def generate_order_number() -> str:
    try:
        async with aiofiles.open(ORDER_NUMBER_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content) if content else {"last_order_number": 0}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"last_order_number": 0}

    new_order_number = data["last_order_number"] + 1
    async with aiofiles.open(ORDER_NUMBER_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps({"last_order_number": new_order_number}, ensure_ascii=False, indent=2))

    formatted_number = f"{new_order_number:06d}"
    logger.info(f"Сгенерирован новый номер заказа: {formatted_number}")
    return formatted_number

async def save_pending_order(order: dict):
    """Сохраняет заказ в pending_orders.json."""
    try:
        async with aiofiles.open(PENDING_ORDERS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            pending_orders = json.loads(content) if content else {"orders": []}
    except FileNotFoundError:
        pending_orders = {"orders": []}

    pending_orders["orders"].append(order)
    try:
        async with aiofiles.open(PENDING_ORDERS_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(pending_orders, ensure_ascii=False, indent=2))
        logger.info(f"Заказ №{order['order_number']} сохранён в pending_orders.json")
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа в pending_orders.json: {e}")

async def load_pending_orders() -> dict:
    """Загружает все ожидающие заказы из pending_orders.json."""
    try:
        async with aiofiles.open(PENDING_ORDERS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content) if content else {"orders": []}
    except FileNotFoundError:
        return {"orders": []}
    except Exception as e:
        logger.error(f"Ошибка при загрузке pending_orders: {e}")
        return {"orders": []}

async def load_order_history() -> dict:
    """Загружает историю заказов из order_history.json."""
    try:
        async with aiofiles.open(ORDER_HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content) if content else {"orders": []}
    except FileNotFoundError:
        return {"orders": []}
    except Exception as e:
        logger.error(f"Ошибка при загрузке order_history: {e}")
        return {"orders": []}

async def remove_pending_order(order_number: str) -> bool:
    """Удаляет заказ из pending_orders.json по номеру."""
    pending_orders = await load_pending_orders()
    initial_length = len(pending_orders["orders"])
    pending_orders["orders"] = [order for order in pending_orders["orders"] if order["order_number"] != order_number]
    
    if len(pending_orders["orders"]) < initial_length:
        try:
            async with aiofiles.open(PENDING_ORDERS_FILE, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(pending_orders, ensure_ascii=False, indent=2))
            logger.info(f"Заказ №{order_number} удалён из pending_orders.json")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении заказа из pending_orders.json: {e}")
            return False
    return False

async def save_order_to_history(order: dict):
    """Сохраняет заказ в order_history.json."""
    history = await load_order_history()
    history["orders"].append(order)
    try:
        async with aiofiles.open(ORDER_HISTORY_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(history, ensure_ascii=False, indent=2))
        logger.info(f"Заказ №{order['order_number']} добавлен в order_history.json")
    except Exception as e:
        logger.error(f"Ошибка при сохранении заказа в order_history.json: {e}")