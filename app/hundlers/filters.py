# ==========================================
# ФАЙЛ app/hundlers/filters.py
# ==========================================
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.request import id_check, get_active_chat_info


# Примечание: Фильтр проверки роли пользователя в БД (admin, operator, user).
class RoleFilter(BaseFilter):
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, event: Message | CallbackQuery, session: AsyncSession) -> bool:
        user_id = event.from_user.id
        status = await id_check(user_id, session)
        return status in self.allowed_roles


# Примечание: Фильтр активного живого чата между оператором и клиентом (игнорирует команды, начинающиеся с '/').
class ActiveChatFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool | dict:
        if message.text and message.text.startswith('/'):
            return False

        chat_info = await get_active_chat_info(message.from_user.id, session)
        if chat_info:
            return {"chat_info": chat_info}
        return False