import os
import sys
import re
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Tuple

# Загрузка переменных окружения
load_dotenv('.env')

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API-ключ OpenRouter не найден")
print(api_key)  # Для проверки

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)

def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для Markdown V2"""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(escape_chars) + r"])", r"\\\1", text)

# Загрузка системного сообщения
def load_bot_mind(filename: str = "bot_mind.json") -> str:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        logging.error(f"Ошибка при загрузке системного сообщения: {e}")
        return ""

# Функции для загрузки и сохранения переписки
def load_conversations():
    if os.path.exists('conversations.json'):
        try:
            with open('conversations.json', 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            # Если файл пуст или повреждён, возвращаем пустой словарь
            return {}
    else:
        return {}

def save_conversations(conversations):
    with open('conversations.json', 'w', encoding='utf-8') as file:
        json.dump(conversations, file, ensure_ascii=False, indent=4)

# Инициализация OpenAI
def initialize_openai() -> Tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")  # Убедитесь, что переменная окружения правильно задана
    if not api_key:
        raise ValueError("API-ключ OpenRouter не найден")
    
    system_content = load_bot_mind()
    if not system_content:
        raise ValueError("Системное сообщение не загружено")
    
    return api_key, system_content

# Инициализация клиента
api_key, system_content = initialize_openai()

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.message.from_user.first_name
    welcome_text = (
        f"Привет, {user_name}! Я — Кофе Мастер, ваш виртуальный помощник по ремонту кофемашин. 🛠️\n\n"
        f"Наш чат-бот проходит тестирование. Если увидите ошибки, пишите: coffeemasterbel@gmail.com\n\n"
        "📍 Где нас найти:\n"
        "🔹 Instagram: [@coffee1master](https://www.instagram.com/coffee1master/)\n"
        "🔹 TikTok: [@coffee1master](https://www.tiktok.com/@coffee1master)\n"
        "🔹 YouTube: [@Coffee1master](https://www.youtube.com/@Coffee1master)\n\n"
        "/start - Перезапуск бота"
    )
    await update.message.reply_text(welcome_text, disable_web_page_preview=True)

# Обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = str(user.id)
    username = user.username or "NoUsername"
    first_name = user.first_name
    last_name = user.last_name or ""
    user_message = update.message.text
    timestamp = datetime.now().isoformat()

    logging.info(f"Получено сообщение от {username} ({user_id}): {user_message}")

    # Загрузка текущих переписок
    conversations = load_conversations()

    # Инициализация истории для нового пользователя
    if user_id not in conversations:
        conversations[user_id] = {
            "user_info": {
                "username": username,
                "first_name": first_name,
                "last_name": last_name
            },
            "messages": []
        }

    # Сохранение сообщения пользователя
    conversations[user_id]["messages"].append({
        "role": "user",
        "message": user_message,
        "timestamp": timestamp
    })

    save_conversations(conversations)

    if not api_key or not system_content:
        await update.message.reply_text("Ошибка системы. Попробуйте позже.")
        return

    loading_message = await update.message.reply_text("⏳ Мастер думает...")

    # Извлечение истории переписки
    user_conversation = conversations[user_id]["messages"]

    # Преобразование истории в формат для API
    conversation_history = []
    for msg in user_conversation:
        role = msg["role"]
        if role == "bot":
            role = "assistant"  # Меняем 'bot' на 'assistant'
        conversation_history.append({
            "role": role,
            "content": msg["message"]
        })

    # Добавление системного сообщения в начало
    conversation_history.insert(0, {"role": "system", "content": system_content})

    # Ограничение длины истории
    max_history_length = 20  # Настрой это значение по необходимости
    if len(conversation_history) > max_history_length:
        conversation_history = [conversation_history[0]] + conversation_history[-(max_history_length - 1):]

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates",
                "X-Title": "Coffee Master Bot"
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat:free",
                "messages": conversation_history,
                "temperature": 0.5,
                "max_tokens": 700
            })
        )

        response_json = response.json()
        print(response_json)
        if response_json.get('choices'):
            response_text = response_json['choices'][0]['message']['content']
        else:
            response_text = "Не удалось получить ответ."
        logging.info(f"Ответ от API: {response_text}")

    except Exception as api_error:
        logging.error(f"Ошибка API: {api_error}")
        response_text = "Ошибка обработки запроса. Попробуйте позже."

    await loading_message.delete()
    response_escaped = escape_markdown_v2(response_text)
    await update.message.reply_text(response_escaped, parse_mode="MarkdownV2")

    # Сохранение ответа бота
    timestamp = datetime.now().isoformat()
    conversations[user_id]["messages"].append({
        "role": "assistant",
        "message": response_text,
        "timestamp": timestamp
    })

    save_conversations(conversations)

# Основная функция
def main() -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logging.error("Токен Telegram не найден в переменных окружения.")
        return

    application = Application.builder().token(bot_token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
