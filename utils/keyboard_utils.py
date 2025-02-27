# utils/keyboard_utils.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_coffee_catalog_keyboard(coffee_list):
    keyboard = []
    for coffee in coffee_list:
        total_quantity = coffee["quantity_250g"] + coffee["quantity_1000g"]
        keyboard.append([
            InlineKeyboardButton(
                text=f"{coffee['name']} (в наличии: {total_quantity})",
                callback_data=f"coffee_{coffee_list.index(coffee)}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="Назад", callback_data="back_to_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_coffee_detail_keyboard(coffee_index):
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