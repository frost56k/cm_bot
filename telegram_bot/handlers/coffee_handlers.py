from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.cart_service import get_user_cart, add_to_cart, clear_cart
from utils.keyboard_utils import get_coffee_catalog_keyboard, get_coffee_detail_keyboard
from utils.utils import format_cart
import json
import logging
import os

logger = logging.getLogger(__name__)
router = Router()

# Определяем путь к JSON файлу
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
JSON_PATH = os.path.join(PROJECT_ROOT, "bot_mind.json")

@router.message(Command("coffeeshop"))
async def coffeeshop_handler(msg: types.Message):
    with open("bot_mind.json", 'r', encoding='utf-8') as f:
        coffee_list = json.load(f).get("coffee_shop", [])
    await msg.answer(
        "Добро пожаловать в кофейный магазин!\nВыберите кофе из каталога:",
        reply_markup=get_coffee_catalog_keyboard(coffee_list)
    )
    logger.info(f"Пользователь {msg.from_user.id} открыл каталог кофе")

@router.callback_query(lambda c: c.data.startswith("coffee_") and c.data.split("_")[1].isdigit())
async def process_coffee_selection(callback: CallbackQuery):
    coffee_index = int(callback.data.split("_")[1])
    with open("bot_mind.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        coffee_list = data.get("coffee_shop", [])
    
    if coffee_index >= len(coffee_list):
        await callback.answer("Кофе не найден!")
        return
    
    coffee = coffee_list[coffee_index]
    coffee_info = (
        f"☕ *{coffee['name']}*\n\n"
        f"{coffee['description']}\n\n"
        f"Цена и наличие:\n"
        f"250г - {coffee['price_250g']} (в наличии: {coffee['quantity_250g']})\n"
        f"1000г - {coffee['price_1000g'] if coffee['price_1000g'] else 'нет в наличии'} "
        f"(в наличии: {coffee['quantity_1000g']})"
    )
    
    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=coffee["image_url"],
        caption=coffee_info,
        parse_mode="Markdown",
        reply_markup=get_coffee_detail_keyboard(coffee_index)
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("weight_"))
async def process_weight_selection(callback: CallbackQuery):
    parts = callback.data.split("_")
    coffee_index = int(parts[1])
    weight = parts[2]
    
    with open("bot_mind.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        coffee_list = data.get("coffee_shop", [])
    
    if coffee_index >= len(coffee_list):
        await callback.answer("Кофе не найден!")
        return
        
    coffee = coffee_list[coffee_index]
    price_key = f"price_{weight}g"
    price = coffee.get(price_key)
    
    if price is None:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text="Нет в наличии",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к кофе", callback_data=f"coffee_{coffee_index}")]
            ])
        )
        await callback.message.delete()
        await callback.answer()
        return
    
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
    
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=confirmation,
        parse_mode="Markdown",
        reply_markup=confirm_keyboard
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("back_to_details_") and len(c.data.split("_")) > 3 and c.data.split("_")[3].isdigit())
async def back_to_coffee_details(callback: CallbackQuery):
    parts = callback.data.split("_")
    coffee_index = int(parts[3])
    
    with open("bot_mind.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        coffee_list = data.get("coffee_shop", [])
    
    if coffee_index >= len(coffee_list):
        await callback.answer("Кофе не найден!")
        return
        
    coffee = coffee_list[coffee_index]
    coffee_info = (
        f"☕ *{coffee['name']}*\n\n"
        f"{coffee['description']}\n\n"
        f"Цена и наличие:\n"
        f"250г - {coffee['price_250g']} (в наличии: {coffee['quantity_250g']})\n"
        f"1000г - {coffee['price_1000g'] if coffee['price_1000g'] else 'нет в наличии'} "
        f"(в наличии: {coffee['quantity_1000g']})"
    )
    
    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=coffee["image_url"],
        caption=coffee_info,
        parse_mode="Markdown",
        reply_markup=get_coffee_detail_keyboard(coffee_index)
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    coffee_index = int(parts[3])
    weight = parts[4]
    user_id = callback.from_user.id
    
    try:
        await add_to_cart(user_id, coffee_index, weight)
        with open("bot_mind.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            coffee_list = data.get("coffee_shop", [])
            coffee = coffee_list[coffee_index]
            quantity_key = f"quantity_{weight}g"
        
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"*{coffee['name']}* ({weight}г) добавлено в корзину!\nОсталось: {coffee[quantity_key] - 1}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="В корзину", callback_data="view_cart")],
                [InlineKeyboardButton(text="Продолжить покупку", callback_data=f"back_to_details_{coffee_index}")]
            ])
        )
        await callback.message.delete()
        await callback.answer()
    except ValueError as e:
        await callback.bot.send_message(callback.message.chat.id, str(e))
        await callback.message.delete()
    except Exception as e:
        logger.error(f"Ошибка при добавлении в корзину: {e}")
        await callback.bot.send_message(callback.message.chat.id, "Ошибка при добавлении в корзину!")

# handlers/coffee_handlers.py (фрагмент view_cart)
@router.callback_query(F.data == "view_cart")
async def view_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)  # Теперь возвращает список словарей
    
    cart_text = format_cart(cart)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оформить покупку", callback_data="checkout"),
            InlineKeyboardButton(text="Очистить корзину", callback_data="clear_cart")
        ],
        [
            InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")
        ]
    ])
    
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=cart_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "coffee_catalog")
async def back_to_catalog(callback: CallbackQuery):
    with open("bot_mind.json", 'r', encoding='utf-8') as f:
        coffee_list = json.load(f).get("coffee_shop", [])
    
    await callback.message.delete()
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text="Выберите кофе из каталога:",
        reply_markup=get_coffee_catalog_keyboard(coffee_list)
    )
    await callback.answer()
    logger.info(f"Пользователь {callback.from_user.id} вернулся к каталогу")

@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)
    if not cart:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text="Корзина уже пуста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")]
            ])
        )
    else:
        await clear_cart(user_id, restore_quantity=True)
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text="Корзина очищена, товары возвращены в наличие!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")]
            ])
        )
    await callback.message.delete()
    await callback.answer()