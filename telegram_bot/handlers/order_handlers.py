from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from services.order_service import create_pickup_order, create_europochta_order, issue_order
from services.cart_service import get_user_cart, clear_cart
from utils.utils import format_cart
from states.states import OrderStates

router = Router()

class OrderStatesGroup(StatesGroup):
    waiting_for_comment = State()
    waiting_for_recipient_name = State()
    waiting_for_post_office_number = State()

@router.callback_query(F.data == "checkout")
async def checkout_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)
    
    if not cart:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text="Ваша корзина пуста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")]
            ])
        )
        await callback.message.delete()
        await callback.answer()
        return
    
    total = sum(float(item["price"].replace(" руб.", "")) for item in cart)  # Изменено с item.price на item["price"]
    checkout_text = (
        f"*Оформление заказа.*\n"
        f"\n"
        f"{format_cart(cart)}\n"
        f"Выберите способ оплаты:\n"
        f"Самовывоз. Оплата при получении наличными или картой\n"
        f"Европочта. Оплата при получении в отделении почты наличными или картой"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Самовывоз", callback_data="pickup_cash"),
            InlineKeyboardButton(text="Европочта", callback_data="europochta_send")
        ],
        [
            InlineKeyboardButton(text="Назад к корзине", callback_data="view_cart")
        ]
    ])
    
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=checkout_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "pickup_cash")
async def pickup_cash_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)
    
    if not cart:
        await callback.bot.send_message(callback.message.chat.id, "Ваша корзина пуста!")
        await callback.message.delete()
        await callback.answer()
        return
    
    total = sum(float(item["price"].replace(" руб.", "")) for item in cart)  # Изменено с item.price на item["price"]
    order_text = (
        f"🛒 *Ваш заказ:*\n"
        f"{format_cart(cart)}\n"
        f"Способ оплаты: Самовывоз (оплата при получении)\n"
        f"Сумма к оплате: {total:.2f} руб.\n\n"
        f"‼️ Пожалуйста, добавьте комментарий к заказу (например, удобное время самовывоза) "
        f"или напишите 'нет', если комментарий не нужен:"
    )
    
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=order_text,
        parse_mode="Markdown"
    )
    
    await state.update_data(cart=cart, total=total, user_id=user_id)
    await state.set_state(OrderStatesGroup.waiting_for_comment)
    await callback.message.delete()
    await callback.answer()

@router.message(OrderStatesGroup.waiting_for_comment)
async def process_order_comment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    comment = message.text.strip()
    
    data = await state.get_data()
    cart = data["cart"]
    total = data["total"]
    
    order_number = await create_pickup_order(user_id, message.bot, comment, cart, total)
    await state.clear()

@router.callback_query(F.data == "europochta_send")
async def europochta_send_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart = await get_user_cart(user_id)
    
    if not cart:
        await callback.bot.send_message(
            chat_id=callback.message.chat.id,
            text="Ваша корзина пуста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад к каталогу", callback_data="coffee_catalog")]
            ])
        )
        await callback.message.delete()
        await callback.answer()
        return
    
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text="Введите имя и фамилию получателя:"
    )
    await state.set_state(OrderStatesGroup.waiting_for_recipient_name)
    await callback.message.delete()
    await callback.answer()

@router.message(OrderStatesGroup.waiting_for_recipient_name)
async def process_recipient_name(message: Message, state: FSMContext):
    recipient_name = message.text.strip()
    await state.update_data(recipient_name=recipient_name)
    await message.answer("Введите адрес получателя и номер отделения почты (например, 'ул. Ленина 10, отделение 123'):")
    await state.set_state(OrderStatesGroup.waiting_for_post_office_number)

@router.message(OrderStatesGroup.waiting_for_post_office_number)
async def process_post_office_number(message: Message, state: FSMContext):
    user_input = message.text.strip()
    data = await state.get_data()
    recipient_name = data["recipient_name"]
    user_id = message.from_user.id
    cart = await get_user_cart(user_id)
    total = sum(float(item["price"].replace(" руб.", "")) for item in cart)  # Изменено с item.price на item["price"]
    
    try:
        address, post_office_number = [part.strip() for part in user_input.split(",", 1)]
        if not address or not post_office_number:
            raise ValueError("Пожалуйста, укажите и адрес, и номер отделения, разделённые запятой.")
    except ValueError as e:
        await message.answer(str(e) if str(e) else "Пожалуйста, введите адрес и номер отделения в формате 'адрес, номер отделения'.")
        return
    
    order_number = await create_europochta_order(user_id, message.bot, recipient_name, address, post_office_number, cart, total)
    await state.clear()

@router.callback_query(F.data.startswith("issue_order_"))
async def confirm_issue_order(callback: CallbackQuery):
    order_number = callback.data.split("_")[2]
    confirm_text = f"Вы уверены, что хотите подтвердить выдачу заказа №{order_number}?"
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_issue_{order_number}")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_issue")]
    ])
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=confirm_text,
        reply_markup=confirm_keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_issue_"))
async def issue_order_confirmed(callback: CallbackQuery):
    order_number = callback.data.split("_")[2]
    await issue_order(order_number, callback.bot)
    await callback.answer()

@router.callback_query(F.data == "cancel_issue")
async def cancel_issue(callback: CallbackQuery):
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Выдача заказа отменена."
    )
    await callback.answer()