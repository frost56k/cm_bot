# services/order_service.py
import aiofiles
from models.models import Order, CartItem
from storage.orders_storage import generate_order_number, save_pending_order
from storage.conversations_storage import get_user_cart, clear_cart
from config.config import ADMIN_ID, PENDING_ORDERS_FILE
import json
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


logger = logging.getLogger(__name__)

async def create_pickup_order(user_id: int, bot: Bot, comment: str, cart: list[CartItem], total: float) -> str:
    order_number = await generate_order_number()
    order = Order(
        order_number=order_number,
        user_id=user_id,
        full_name="Имя пользователя",  # Замени на реальное имя из сообщения
        username=None,  # Замени на реальный username, если доступен
        cart=cart,
        payment_method="Самовывоз (оплата при получении)",
        total=total,
        comment=comment if comment.lower() != "нет" else "Без комментария",
        issued=False,
        issue_date=None
    )
    
    order_data = order.__dict__
    await save_pending_order(order_data)
    
    user_order_text = (
        f"✅ *Заказ №{order_number} оформлен!*\n"
        f"🛒 *Ваш заказ:*\n"
        f"{''.join(f'- {item.name} ({item.weight}г) - {item.price}\n' for item in cart)}\n"
        f"Способ оплаты: Самовывоз (оплата при получении)\n"
        f"Комментарий: {order.comment}\n"
        f"Заберите ваш заказ по адресу: город Минск ул. Неждановой д. 37 понедельник - пятница 9-17 часов\n"
        f"Оплата наличными или картой при получении."
    )
    
    await bot.send_message(
        chat_id=user_id,
        text=user_order_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вернуться в магазин", callback_data="back_to_shop_from_order")]
        ])
    )
    
    admin_text = (
        f"🔔 *Новый заказ №{order_number}!*\n"
        f"Пользователь: {order.full_name} (ID: {user_id}, @{order.username})\n"
        f"🛒 *Заказ:*\n"
        f"{''.join(f'- {item.name} ({item.weight}г) - {item.price}\n' for item in cart)}\n"
        f"Способ оплаты: Самовывоз (оплата при получении)\n"
        f"Сумма: {total:.2f} руб.\n"
        f"Комментарий: {order.comment}"
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выдать заказ", callback_data=f"issue_order_{order_number}")]
        ])
    )
    
    await clear_cart(user_id, restore_quantity=False)
    logger.info(f"Заказ №{order_number} создан и сохранён для пользователя {user_id}")
    return order_number

async def create_europochta_order(user_id: int, bot: Bot, recipient_name: str, address: str, post_office_number: str, cart: list[CartItem], total: float) -> str:
    order_number = await generate_order_number()
    order = Order(
        order_number=order_number,
        user_id=user_id,
        full_name="Имя пользователя",  # Замени на реальное имя из сообщения
        username=None,  # Замени на реальный username, если доступен
        cart=cart,
        payment_method="Европочта (оплата при получении)",
        total=total,
        recipient_name=recipient_name,
        address=address,
        post_office_number=post_office_number,
        issued=False,
        issue_date=None
    )
    
    order_data = order.__dict__
    await save_pending_order(order_data)
    
    order_text = (
        f"✅ *Заказ №{order_number} оформлен!*\n"
        f"🛒 *Ваш заказ:*\n"
        f"{''.join(f'- {item.name} ({item.weight}г) - {item.price}\n' for item in cart)}\n"
        f"Способ оплаты: Европочта (оплата при получении)\n"
        f"Получатель: {recipient_name}\n"
        f"Адрес: {address}\n"
        f"Номер отделения: {post_office_number}\n"
        f"Оплата при получении в отделении почты."
    )
    
    await bot.send_message(
        chat_id=user_id,
        text=order_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вернуться в магазин", callback_data="coffee_catalog")]
        ])
    )
    
    admin_text = (
        f"🔔 *Новый заказ №{order_number}!*\n"
        f"Пользователь: {order.full_name} (ID: {user_id}, @{order.username})\n"
        f"🛒 *Заказ:*\n"
        f"{''.join(f'- {item.name} ({item.weight}г) - {item.price}\n' for item in cart)}\n"
        f"Способ оплаты: Европочта (оплата при получении)\n"
        f"Получатель: {recipient_name}\n"
        f"Адрес: {address}\n"
        f"Номер отделения: {post_office_number}\n"
        f"Сумма: {total:.2f} руб."
    )
    
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выдать заказ", callback_data=f"issue_order_{order_number}")]
        ])
    )
    
    await clear_cart(user_id, restore_quantity=False)
    logger.info(f"Заказ №{order_number} создан и сохранён для пользователя {user_id}")
    return order_number

async def issue_order(order_number: str, bot: Bot) -> None:
    try:
        async with aiofiles.open(PENDING_ORDERS_FILE, 'r', encoding='utf-8') as f:
            content = await f.read()
            pending_orders = json.loads(content) if content else {"orders": []}
    except FileNotFoundError:
        logger.error(f"Файл {PENDING_ORDERS_FILE} не найден!")
        return

    order_data = next((order for order in pending_orders["orders"] if order["order_number"] == order_number), None)
    if not order_data:
        logger.error(f"Заказ №{order_number} не найден в ожидающих заказах!")
        return

    order_data["issued"] = True
    order_data["issue_date"] = datetime.now().isoformat()

    async with aiofiles.open("order_history.json", 'r', encoding='utf-8') as f:
        content = await f.read()
        history = json.loads(content) if content else {"orders": []}
    history["orders"].append(order_data)

    async with aiofiles.open("order_history.json", 'w', encoding='utf-8') as f:
        await f.write(json.dumps(history, ensure_ascii=False, indent=2))

    pending_orders["orders"] = [order for order in pending_orders["orders"] if order["order_number"] != order_number]
    async with aiofiles.open(PENDING_ORDERS_FILE, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(pending_orders, ensure_ascii=False, indent=2))

    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Заказ №{order_number} успешно выдан и записан в историю."
    )
    logger.info(f"Заказ №{order_number} выдан и перемещён в историю")