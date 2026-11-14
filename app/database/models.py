# ==========================================
# ФАЙЛ app/database/models.py
# ==========================================
from datetime import datetime
from sqlalchemy import BigInteger, String, Numeric, ForeignKey, DateTime, Float, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.sql import func

from config import DB_URL

engine = create_async_engine(url=DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Tariff(Base):
    __tablename__ = 'tariffs'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    monthly_price: Mapped[float] = mapped_column(Numeric(10, 2))
    gb_limit: Mapped[int] = mapped_column()
    minutes_limit: Mapped[int] = mapped_column()


class Subscriber(Base):
    __tablename__ = 'subscribers'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    phone_number: Mapped[str] = mapped_column(String(20))
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=500.00)
    tariff_id: Mapped[int] = mapped_column(ForeignKey('tariffs.id'), default=1)
    freeze: Mapped[bool] = mapped_column(default=False)
    time_with_me: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Operators(Base):
    __tablename__ = 'operators'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(40), default='Operator1234')
    description: Mapped[str] = mapped_column(String(200), default='Оператор клиентской поддержки')
    is_working: Mapped[bool] = mapped_column(default=False)
    is_free: Mapped[bool] = mapped_column(default=True)
    hours: Mapped[int] = mapped_column(default=0)
    work_seconds: Mapped[int] = mapped_column(default=0)
    count: Mapped[int] = mapped_column(default=0)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.00)
    shift_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    current_client_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)


class Waiter(Base):
    __tablename__ = 'waiters'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(50))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Admins(Base):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    phone_number: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(50))
    password: Mapped[str] = mapped_column(String(40), default='Admin1234')
    is_active: Mapped[bool] = mapped_column(default=True)


class Invites(Base):
    __tablename__ = 'invites_for_admins'

    id: Mapped[int] = mapped_column(primary_key=True)
    invite_code: Mapped[str] = mapped_column(String(8), unique=True)
    used: Mapped[bool] = mapped_column(default=False)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, default=None, nullable=True)
    role: Mapped[str] = mapped_column(String(20))


class Reviews(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    rating: Mapped[int] = mapped_column(Numeric(2, 0))
    review: Mapped[str] = mapped_column(String(1000))


class Faq(Base):
    __tablename__ = 'faqs'

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(String(300))
    answer: Mapped[str] = mapped_column(String(1000))


# Примечание: Создает все таблицы в БД, проверяет наличие новых колонок и добавляет стартовые тарифы и FAQ, если база пустая.
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE operators ADD COLUMN IF NOT EXISTS work_seconds INTEGER DEFAULT 0"))
        except Exception:
            pass

    async with async_session() as session:
        existing_tariffs = await session.execute(select(Tariff))
        if existing_tariffs.scalars().first() is None:
            session.add_all([
                Tariff(name='Старт 15 ГБ', monthly_price=250.00, gb_limit=15, minutes_limit=100),
                Tariff(name='Оптима 40 ГБ', monthly_price=450.00, gb_limit=40, minutes_limit=300),
                Tariff(name='Безлимит PRO', monthly_price=750.00, gb_limit=999, minutes_limit=1000),
            ])
            await session.commit()

        existing_faqs = await session.execute(select(Faq))
        if existing_faqs.scalars().first() is None:
            session.add_all([
                Faq(
                    question='Как сменить свой тариф?',
                    answer='Перейдите в «Личный кабинет» -> «🔄 Сменить тариф», выберите нужный план и подтвердите подключение.'
                ),
                Faq(
                    question='Для чего нужна заморозка баланса?',
                    answer='Заморозка временно приостанавливает списания и операции по счету на время вашего отъезда.'
                ),
            ])
            await session.commit()
