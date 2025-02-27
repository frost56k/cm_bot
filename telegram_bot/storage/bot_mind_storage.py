# storage/bot_mind_storage.py
import json
import logging
from config import BOT_MIND_FILE
from typing import List, Dict

logger = logging.getLogger(__name__)

def load_bot_mind() -> Dict[str, Any]:
    """Загружает все поля из bot_mind.json."""
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        logger.warning(f"Файл {BOT_MIND_FILE} не найден, возвращается пустой словарь")
        return {"coffee_shop": []}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в {BOT_MIND_FILE}: {e}")
        return {"coffee_shop": []}
    except Exception as e:
        logger.error(f"Ошибка при загрузке bot_mind: {e}")
        return {"coffee_shop": []}

def save_bot_mind(data: Dict[str, Any]):
    """Сохраняет данные в bot_mind.json."""
    try:
        with open(BOT_MIND_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {BOT_MIND_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в {BOT_MIND_FILE}: {e}")

def get_coffee_list() -> List[Dict]:
    """Получает список кофе из bot_mind.json."""
    data = load_bot_mind()
    return data.get("coffee_shop", [])