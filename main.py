import os
import sys
import re
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Tuple

# Загрузка переменных окружения
load_dotenv('.env')
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

# Инициализация OpenAI
def initialize_openai() -> Tuple[OpenAI, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API-ключ OpenAI не найден в переменных окружения.")
    
    system_content = load_bot_mind()
    if not system_content:
        raise ValueError("Системное сообщение не загружено.")
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1/",
        api_key=api_key
    )
    return client, system_content

# Инициализация клиента
client, system_content = initialize_openai()

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
    user_message = update.message.text
    logging.info(f"Получено сообщение: {user_message}")

    if not client or not system_content:
        await update.message.reply_text("Ошибка системы. Попробуйте позже.")
        return

    loading_message = await update.message.reply_text("⏳ Мастер думает...")

    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5,
            max_tokens=700
        )

        response = completion.choices[0].message.content if completion.choices else "Не удалось получить ответ."
        logging.info(f"Ответ от API: {response}")

    except Exception as api_error:
        logging.error(f"Ошибка API: {api_error}")
        response = "Ошибка обработки запроса. Попробуйте позже."

    await loading_message.delete()
    response = escape_markdown_v2(response)
    await update.message.reply_text(response, parse_mode="MarkdownV2")


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