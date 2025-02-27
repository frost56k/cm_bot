# states/states.py
from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_recipient_name = State()
    waiting_for_post_office_number = State()