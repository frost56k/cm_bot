# config/__init__.py
import os

# Пути к файлам в корне проекта
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # Поднимаемся на уровень выше (из config в корень)

PENDING_ORDERS_FILE = os.path.join(BASE_DIR, 'pending_orders.json')
ORDER_NUMBER_FILE = os.path.join(BASE_DIR, 'order_number.json')
ORDER_HISTORY_FILE = os.path.join(BASE_DIR, 'order_history.json')