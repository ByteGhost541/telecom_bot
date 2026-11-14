# ==========================================
# ФАЙЛ app/keyboards/reply.py
# ==========================================
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# Примечание: Создает нижнюю Reply-клавиатуру для отправки контакта пользователя при регистрации.
def get_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Отправить контакт', request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard