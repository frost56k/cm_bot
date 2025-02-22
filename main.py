import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from openai import OpenAI
from dotenv import load_dotenv
import time
import aiofiles
from aiogram.types import BotCommand

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CONVERSATIONS_FILE = "conversations.json"
BOT_MIND_FILE = "bot_mind.json"

if not os.path.exists(CONVERSATIONS_FILE):
    with open(CONVERSATIONS_FILE, 'w') as f:
        json.dump({}, f)

# Инициализация бота и OpenAI
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Глобальный кэш
conversations_cache = {}

def load_bot_mind() -> str:
    """Загрузка всех полей из bot_mind.json"""
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error loading bot mind: {e}")
        return ""  

async def load_conversations_to_cache():
    """Загружает данные из файла в кэш"""
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
    """Сохраняет кэш в файл"""
    try:
        async with aiofiles.open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(conversations_cache, indent=4, ensure_ascii=False))
        logger.info("Кэш сохранен в файл")
    except Exception as e:
        logger.error(f"Ошибка при сохранении кэша: {e}")

async def periodic_save():
    """Периодически сохраняет кэш через некоторое время"""
    while True:
        await asyncio.sleep(30)  # Уменьшаем до 30 секунд
        await save_conversations_from_cache()
        logger.info("Периодическое сохранение кэша выполнено")

async def get_conversation(user_id: int) -> Dict[str, Any]:
    """Получает историю чата из кэша"""
    return conversations_cache.get(str(user_id), {})

async def save_conversation(user_id: int, data: Dict[str, Any]):
    """Сохраняет данные в кэш"""
    conversations_cache[str(user_id)] = data
    logger.info(f"Данные сохранены в кэш для пользователя {user_id}")

async def update_chat_history(user_id: int, message: str, role: str = "user"):
    """Обновляет историю чата"""
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

async def on_shutdown(dp: Dispatcher):
    """Сохраняет кэш при завершении работы бота"""
    await save_conversations_from_cache()
    logger.info("Бот остановлен, кэш сохранен")

async def get_user_cart(user_id: int) -> list:
    """Получает корзину пользователя из кэша"""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    return conversation.get("cart", [])

async def add_to_cart(user_id: int, coffee_index: int, weight: str):
    """Добавляет товар в корзину"""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    if "cart" not in conversation:
        conversation["cart"] = []
    
    with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        coffee_list = data.get("coffee_shop", [])
        coffee = coffee_list[coffee_index]
    
    cart_item = {
        "coffee_index": coffee_index,
        "name": coffee["name"],
        "weight": weight,
        "price": coffee[f"price_{weight}g"]
    }
    conversation["cart"].append(cart_item)
    await save_conversation(user_id, conversation)
    logger.info(f"Добавлен товар в корзину пользователя {user_id}: {cart_item}")
    logger.info(f"Текущее состояние корзины в кэше: {conversation['cart']}")

async def clear_cart(user_id: int):
    """Очищает корзину пользователя"""
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": [], "cart": []}
    conversation["cart"] = []
    await save_conversation(user_id, conversation)
    logger.info(f"Корзина пользователя {user_id} очищена")

def format_cart(cart: list) -> str:
    """Форматирует содержимое корзины для отображения"""
    if not cart:
        return "Ваша корзина пуста."
    
    total = 0
    cart_text = "🛒 *Ваша корзина:*\n\n"
    for item in cart:
        cart_text += f"- {item['name']} ({item['weight']}г) - {item['price']}\n"
        total += float(item['price'].replace(" руб.", ""))
    cart_text += f"\n*Итого:* {total:.2f} руб."
    return cart_text

dp.shutdown.register(on_shutdown)

@dp.message(Command("start"))
async def start_handler(msg: Message):
    """Обработчик команды /start без загрузки данных"""
    user = msg.from_user
    welcome_text = (
        f"Привет, {user.full_name}! Я — Кофе Мастер, ваш виртуальный помощник по ремонту кофемашин. 🛠️\n\n"
        f"Наш чат-бот проходит тестирование. Если увидите ошибки, пишите: coffeemasterbel@gmail.com\n"
        f"Используйте /coffeeshop, чтобы посмотреть каталог кофе."
    )
    await msg.answer(welcome_text)
    if str(user.id) not in conversations_cache:
        conversations_cache[str(user.id)] = {
            "user_info": {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name
            },
            "messages": []
        }
    logger.info(f"Пользователь {user.id} начал работу с ботом")

async def send_typing_indicator(chat_id):
    """Отправляет индикатор набора сообщения"""
    while True:
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(10)

def get_coffee_catalog_keyboard(coffee_list):
    """Создаёт клавиатуру с каталогом кофе"""
    keyboard = []
    for coffee in coffee_list:
        keyboard.append([
            InlineKeyboardButton(
                text=coffee["name"],
                callback_data=f"coffee_{coffee_list.index(coffee)}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="back_to_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_coffee_detail_keyboard(coffee_index):
    """Создаёт клавиатуру для конкретного кофе с кнопками выбора веса и корзиной"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="250г", callback_data=f"weight_{coffee_index}_250"),
            InlineKeyboardButton(text="1000г", callback_data=f"weight_{coffee_index}_1000")
        ],
        [
            InlineKeyboardButton(text="Моя корзина", callback_data="view_cart"),
            InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")
        ]
    ])
    return keyboard

@dp.callback_query(lambda c: c.data.startswith("coffee_") and c.data.split("_")[1].isdigit())
async def process_coffee_selection(callback: CallbackQuery):
    """Обработчик выбора конкретного кофе"""
    coffee_index = int(callback.data.split("_")[1])
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
        
        if coffee_index >= len(coffee_list):
            await callback.answer("Кофе не найден!")
            return
            
        coffee = coffee_list[coffee_index]
        coffee_info = (
            f"☕ *{coffee['name']}*\n\n"
            f"{coffee['description']}\n\n"
            f"Цена:\n"
            f"250г - {coffee['price_250g']}\n"
            f"1000г - {coffee['price_1000g']}"
        )
        
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=coffee["image_url"],
            caption=coffee_info,
            parse_mode="Markdown",
            reply_markup=get_coffee_detail_keyboard(coffee_index)
        )
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при показе кофе: {e}")
        await callback.answer("Произошла ошибка!")
        await bot.send_message(callback.message.chat.id, "Произошла ошибка при показе кофе.")

@dp.callback_query(lambda c: c.data.startswith("weight_"))
async def process_weight_selection(callback: CallbackQuery):
    """Обработчик выбора веса кофе"""
    try:
        parts = callback.data.split("_")
        coffee_index = int(parts[1])
        weight = parts[2]
        user_id = callback.from_user.id
        
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
        
        if coffee_index >= len(coffee_list):
            await callback.answer("Кофе не найден!")
            return
            
        coffee = coffee_list[coffee_index]
        price_key = f"price_{weight}g"
        price = coffee[price_key]
        
        confirmation = (
            f"Вы выбрали:\n"
            f"*{coffee['name']}* ({weight}г) - {price}"
        )
        
        confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
       [
        InlineKeyboardButton(text="Подтверждаю", callback_data=f"add_to_cart_{coffee_index}_{weight}"),
        InlineKeyboardButton(text="Отмена", callback_data=f"back_to_details_{coffee_index}")
       ]
    ])
        
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=confirmation,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard
        )
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при выборе веса: {e}")
        await callback.answer("Произошла ошибка!")
        await bot.send_message(callback.message.chat.id, "Ошибка при выборе веса.")

@dp.callback_query(lambda c: c.data.startswith("back_to_details_") and len(c.data.split("_")) > 3 and c.data.split("_")[3].isdigit())
async def back_to_coffee_details(callback: CallbackQuery):
    """Возврат к деталям кофе"""
    logger.info(f"Вызван back_to_coffee_details с callback_data: {callback.data}")
    try:
        parts = callback.data.split("_")
        coffee_index = int(parts[3])  # Индекс в parts[3], а не parts[2]
        logger.info(f"Возврат к деталям кофе с индексом: {coffee_index}")
        
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Файл {BOT_MIND_FILE} успешно открыт")
            coffee_list = data.get("coffee_shop", [])
        
        logger.info(f"Загружен coffee_list длиной: {len(coffee_list)}")
        
        if coffee_index >= len(coffee_list):
            logger.warning(f"Кофе с индексом {coffee_index} не найден в списке длиной {len(coffee_list)}")
            await callback.answer("Кофе не найден!")
            return
            
        coffee = coffee_list[coffee_index]
        logger.info(f"Выбран кофе: {coffee['name']}")
        
        coffee_info = (
            f"☕ *{coffee['name']}*\n\n"
            f"{coffee['description']}\n\n"
            f"Цена:\n"
            f"250г - {coffee['price_250g']}\n"
            f"1000г - {coffee['price_1000g']}"
        )
        
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=coffee["image_url"],
            caption=coffee_info,
            parse_mode="Markdown",
            reply_markup=get_coffee_detail_keyboard(coffee_index)
        )
        logger.info(f"Сообщение с деталями отправлено пользователю")
        
        await callback.message.delete()
        await callback.answer()
        logger.info(f"Предыдущее сообщение удалено, callback обработан")
        
    except FileNotFoundError as e:
        logger.error(f"Файл {BOT_MIND_FILE} не найден: {e}")
        await callback.answer("Ошибка: файл данных не найден!")
        await bot.send_message(callback.message.chat.id, f"Ошибка: файл данных ({BOT_MIND_FILE}) не найден!")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в {BOT_MIND_FILE}: {e}")
        await callback.answer("Ошибка: некорректный формат данных!")
        await bot.send_message(callback.message.chat.id, f"Ошибка: некорректный формат данных в файле {BOT_MIND_FILE}!")
    except Exception as e:
        logger.error(f"Необработанная ошибка при возврате к деталям: {e}")
        await callback.answer(f"Ошибка: {str(e)}")
        await bot.send_message(callback.message.chat.id, f"Ошибка при возврате к деталям: {str(e)}")        

@dp.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    """Обработчик добавления товара в корзину"""
    logger.info(f"Вызван add_to_cart_handler с callback_data: {callback.data}")
    try:
        parts = callback.data.split("_")
        if len(parts) < 5 or not parts[3].isdigit():  # Проверяем parts[3] как индекс
            logger.warning(f"Некорректный callback_data: {callback.data}")
            await callback.answer("Ошибка: неверный формат данных!")
            return
            
        coffee_index = int(parts[3])  # Индекс в parts[3]
        weight = parts[4]             # Вес в parts[4]
        user_id = callback.from_user.id
        
        logger.info(f"Параметры: coffee_index={coffee_index}, weight={weight}, user_id={user_id}")
        
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Файл {BOT_MIND_FILE} успешно открыт")
            coffee_list = data.get("coffee_shop", [])
        
        logger.info(f"Загружен coffee_list длиной: {len(coffee_list)}")
        
        if coffee_index >= len(coffee_list):
            logger.warning(f"Кофе с индексом {coffee_index} не найден в списке длиной {len(coffee_list)}")
            await callback.answer("Кофе не найден!")
            return
            
        coffee = coffee_list[coffee_index]
        logger.info(f"Выбран кофе: {coffee['name']}")
        
        # Добавляем в корзину
        await add_to_cart(user_id, coffee_index, weight)
        logger.info(f"Товар добавлен в корзину: {coffee['name']} ({weight}г)")
        
        # Немедленно сохраняем в файл
        await save_conversations_from_cache()
        logger.info(f"Данные немедленно сохранены в {CONVERSATIONS_FILE}")
        
        # Отправляем сообщение пользователю
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"*{coffee['name']}* ({weight}г) добавлено в корзину!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В корзину", callback_data="view_cart")],
                [InlineKeyboardButton(text="Продолжить покупку", callback_data=f"back_to_details_{coffee_index}")]
            ])
        )
        logger.info(f"Сообщение успешно отправлено пользователю")
        
        await callback.message.delete()
        await callback.answer()
        logger.info(f"Предыдущее сообщение удалено, callback обработан")
        
    except FileNotFoundError as e:
        logger.error(f"Файл {BOT_MIND_FILE} не найден: {e}")
        await callback.answer("Ошибка: файл данных не найден!")
        await bot.send_message(callback.message.chat.id, f"Ошибка: файл данных ({BOT_MIND_FILE}) не найден!")
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в {BOT_MIND_FILE}: {e}")
        await callback.answer("Ошибка: некорректный формат данных!")
        await bot.send_message(callback.message.chat.id, f"Ошибка: некорректный формат данных в файле {BOT_MIND_FILE}!")
    except Exception as e:
        logger.error(f"Необработанная ошибка при добавлении в корзину: {e}")
        await callback.answer(f"Ошибка: {str(e)}")
        await bot.send_message(callback.message.chat.id, f"Ошибка при добавлении в корзину: {str(e)}")

@dp.callback_query(
    lambda c: c.data.startswith("add_to_cart_") 
    and len(c.data.split("_")) >= 4  # Минимум 4 части: ["add", "to", "cart", "0", "250"]
    and c.data.split("_")[2].isdigit()  # Индекс кофе находится в части [2]
)
async def add_to_cart_handler(callback: CallbackQuery):
    try:
        coffee_index = int(callback.data.split("_")[3])  # Изменили [2] на [3]
        logger.info(f"Возврат к деталям кофе с индексом: {coffee_index}")
        
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
        
        if coffee_index >= len(coffee_list):
            await callback.answer("Кофе не найден!")
            return
            
        coffee = coffee_list[coffee_index]
        coffee_info = (
            f"☕ *{coffee['name']}*\n\n"
            f"{coffee['description']}\n\n"
            f"Цена:\n"
            f"250г - {coffee['price_250g']}\n"
            f"1000г - {coffee['price_1000g']}"
        )
        
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=coffee["image_url"],
            caption=coffee_info,
            parse_mode="Markdown",
            reply_markup=get_coffee_detail_keyboard(coffee_index)
        )
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при возврате к деталям: {e}")
        await callback.answer("Ошибка!")
        await bot.send_message(callback.message.chat.id, "Произошла ошибка при возврате к деталям.")

@dp.callback_query(F.data == "view_cart")
async def view_cart(callback: CallbackQuery):
    """Показывает содержимое корзины"""
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)
    
    cart_text = format_cart(cart)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart"),
            InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")
        ]
    ])
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=cart_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.message.delete()
    await callback.answer()

@dp.message(Command("cart"))
async def cart_handler(msg: Message):
    """Обработчик команды /cart"""
    user_id = msg.from_user.id
    cart = await get_user_cart(user_id)
    
    cart_text = format_cart(cart)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart"),
            InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")
        ]
    ])
    
    await msg.answer(
        text=cart_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    """Очищает корзину"""
    user_id = callback.from_user.id
    await clear_cart(user_id)
    
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="Корзина очищена!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")]
        ])
    )
    await callback.message.delete()
    await callback.answer()

@dp.message(Command("coffeeshop"))
async def coffeeshop_handler(msg: Message):
    """Обработчик команды /coffeeshop с каталогом кофе"""
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
        
        if not coffee_list:
            await msg.answer("Кофейный каталог пуст!")
            return
        
        keyboard = get_coffee_catalog_keyboard(coffee_list)
        await msg.answer(
            "Добро пожаловать в кофейный магазин!\nВыберите кофе из каталога:",
            reply_markup=keyboard
        )
        logger.info(f"Пользователь {msg.from_user.id} открыл каталог кофе")
    except Exception as e:
        logger.error(f"Ошибка при загрузке каталога кофе: {e}")
        await msg.answer("Произошла ошибка при загрузке каталога. Попробуйте позже.")

@dp.callback_query(F.data == "coffee_catalog")
async def back_to_catalog(callback: CallbackQuery):
    """Возврат к каталогу кофе"""
    try:
        with open(BOT_MIND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
        
        keyboard = get_coffee_catalog_keyboard(coffee_list)
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Выберите кофе из каталога:",
            reply_markup=keyboard
        )
        await callback.message.delete()
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при возврате к каталогу: {e}")
        await callback.answer("Ошибка при загрузке каталога!")
        await bot.send_message(callback.message.chat.id, "Ошибка при загрузке каталога!")

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат к главному меню"""
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="Используйте /coffeeshop для просмотра каталога кофе"
    )
    await callback.message.delete()
    await callback.answer()

@dp.message(F.text)
async def message_handler(msg: Message):
    """Обработчик текстовых сообщений"""
    user_id = msg.from_user.id
    user = msg.from_user
    user_message = msg.text
    start_time = time.time()

    logger.info(f"Начало обработки сообщения: {start_time}")
    logger.info(f"Пользователь {user_id} написал: {user_message}")
    
    conversation = await get_conversation(user_id) or {"user_info": {}, "messages": []}
    
    if not conversation.get("user_info"):
        conversation["user_info"] = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        await save_conversation(user_id, conversation)
        logger.info(f"Сохранена информация о пользователе: {conversation['user_info']}")
    
    await bot.send_chat_action(msg.chat.id, "typing")
    await update_chat_history(user_id, user_message)
    logger.info(f"История обновлена: {time.time() - start_time} сек")

    messages = conversation.get("messages", [])
    system_prompt = load_bot_mind()
    messages_for_ai = [{"role": "system", "content": system_prompt}] + [
        {"role": m["role"], "content": m["message"]} for m in messages[-20:]
    ]
    
    logger.info(f"Запрос к ИИ с системным промптом: {messages_for_ai}")
    
    try:
        completion = client.chat.completions.create(
            model="deepseek/deepseek-chat:free",
            messages=messages_for_ai,
            extra_headers={
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Coffee Master Bot"
            }
        )
        ai_response = completion.choices[0].message.content
        logger.info(f"ИИ ответил: {ai_response}")
        
        await update_chat_history(user_id, ai_response, "assistant")
        await msg.answer(ai_response)
        logger.info(f"Ответ отправлен: {time.time() - start_time} сек")
    except Exception as e:
        logger.error(f"API Error: {e}")
        await msg.answer("⚠️ Произошла ошибка. Попробуйте позже.")

@dp.callback_query()
async def debug_callback(callback: CallbackQuery):
    """Логирует все callback-запросы для диагностики"""
    logger.info(f"Получен callback_data: {callback.data}")

async def main():
    """Главная функция для запуска бота"""
    await load_conversations_to_cache()
    asyncio.create_task(periodic_save())
    logger.info("Запуск бота")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())