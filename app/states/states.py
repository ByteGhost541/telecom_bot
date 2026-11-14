# ==========================================
# ФАЙЛ app/states/states.py
# ==========================================
from aiogram.fsm.state import State, StatesGroup


class ChatModes(StatesGroup):
    operator = State()
    chatbot = State()
    wait_queue = State()


class ChangePassword(StatesGroup):
    old_password = State()
    new_password = State()
    confirm_password = State()


class ConfimPassword(StatesGroup):
    confim_password_for_block = State()
    confim_password_for_unblock = State()


class UpdateProfile(StatesGroup):
    new_phone = State()
    new_name = State()
    new_operator_desc = State()


class AddFaq(StatesGroup):
    question = State()
    answer = State()


class LeaveReview(StatesGroup):
    review_text = State()
