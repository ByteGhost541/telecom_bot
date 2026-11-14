# ==========================================
# ФАЙЛ main.py
# ==========================================
import sys
import asyncio
import logging
from aiogram import Bot, Dispatcher

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from config import BOT_TOKEN
from app.database.models import init_db, async_session
from app.database.request import set_first_admin
from app.middlewares.db_mw import DataBaseSession
from app.hundlers.starts import router as starts_router
from app.hundlers.admins import router as admins_router
from app.hundlers.operator import router as operator_router
from app.hundlers.paiments import router as payments_router
from app.hundlers.user import router as user_router


# Примечание: Инициализирует БД, создает первого админа, регистрирует Middleware и запускает бота.
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()

    # Укажи здесь свой Telegram ID (например, 9294024026)
    async with async_session() as session:
        await set_first_admin(admin_id=9294024026, session=session)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.update.middleware(DataBaseSession(session_pool=async_session))

    dp.include_routers(
        starts_router,
        admins_router,
        operator_router,
        payments_router,
        user_router,
    )

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот остановлен.')