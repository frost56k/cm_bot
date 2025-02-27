from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from services.cart_service import get_user_cart, add_to_cart
from utils.keyboard_utils import get_coffee_catalog_keyboard, get_coffee_detail_keyboard
import json
import logging

logger = logging.getLogger(__name__)
router = Router() 

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
    
