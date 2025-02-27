# models/models.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Coffee:
    name: str
    description: str
    quantity_250g: int
    quantity_1000g: int
    image_url: str  # Перенёс поле выше, перед price_1000g
    price_250g: str
    price_1000g: Optional[str] = None

@dataclass
class CartItem:
    """Модель для элемента корзины пользователя."""
    coffee_index: int  # Индекс кофе в списке (для связи с bot_mind.json)
    name: str  # Название кофе
    weight: str  # Вес (например, "250" или "1000")
    price: str  # Цена в формате "X руб."

@dataclass
class Order:
    """Модель для представления заказа."""
    order_number: str
    user_id: int
    full_name: str
    cart: List[CartItem]  # Перенесено выше
    payment_method: str
    total: float
    issued: bool = False  # Поля с значениями по умолчанию идут в конце
    username: Optional[str] = None
    comment: Optional[str] = None
    recipient_name: Optional[str] = None
    address: Optional[str] = None
    post_office_number: Optional[str] = None
    issue_date: Optional[str] = None