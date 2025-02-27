# config/config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

CONVERSATIONS_FILE = "conversations.json"
BOT_MIND_FILE = "bot_mind.json"
ORDER_NUMBER_FILE = "order_number.json"
PENDING_ORDERS_FILE = "pending_orders.json"
ORDER_HISTORY_FILE = "order_history.json"

ADMIN_ID = 222467350