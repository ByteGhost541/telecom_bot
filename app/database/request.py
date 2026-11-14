# ==========================================
# ФАЙЛ app/database/request.py
# ==========================================
from datetime import datetime
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Tariff, Subscriber, Operators, Waiter, Invites, Admins, Reviews, Faq
)


# ==========================================
# 1. РЕГИСТРАЦИЯ, АВТОРИЗАЦИЯ И ИНВАЙТЫ
# ==========================================

# Примечание: Создает первого (главного) администратора при запуске бота по его telegram_id.
async def set_first_admin(admin_id: int, session: AsyncSession):
    query = select(Admins).where(Admins.telegram_id == admin_id)
    result = await session.execute(query)
    admin = result.scalar()

    if not admin:
        new_admin = Admins(
            telegram_id=admin_id,
            phone_number='Не указан',
            name='Создатель'
        )
        session.add(new_admin)
        await session.commit()
        print(f"✅ Главный администратор с Telegram ID {admin_id} успешно создан!")


# Примечание: Регистрирует нового абонента в БД по telegram_id с начальным балансом 500 сом и базовым тарифом.
async def add_subscriber(telegram_id: int, name: str, phone_number: str, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
    result = await session.execute(query)

    if result.scalar() is None:
        new_sub = Subscriber(
            telegram_id=telegram_id,
            name=name,
            phone_number=phone_number,
            balance=500.00,
            tariff_id=1
        )
        session.add(new_sub)
        await session.commit()
        return True
    return False


# Примечание: Определяет роль пользователя строго по его telegram_id (проверяет таблицы Admins, Operators, Subscriber).
async def id_check(telegram_id: int, session: AsyncSession):
    query1 = select(Admins).where(Admins.telegram_id == telegram_id)
    admin = await session.execute(query1)
    if admin.scalar() is not None:
        return 'admin'

    query2 = select(Operators).where(Operators.telegram_id == telegram_id)
    operator = await session.execute(query2)
    if operator.scalar() is not None:
        return 'operator'

    query3 = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
    subscriber = await session.execute(query3)
    if subscriber.scalar() is not None:
        return 'user'

    return None


# Примечание: Проверяет соответствие введенного пароля для роли admin или operator по telegram_id.
async def password_check(telegram_id: int, role: str, password: str, session: AsyncSession):
    if role == 'admin':
        query = select(Admins).where(Admins.telegram_id == telegram_id)
        result = await session.execute(query)
        admin = result.scalar()
        return bool(admin and admin.password == password)
    elif role == 'operator':
        query = select(Operators).where(Operators.telegram_id == telegram_id)
        result = await session.execute(query)
        operator = result.scalar()
        return bool(operator and operator.password == password)
    return False


# Примечание: Проверяет активность аккаунта администратора (флаг is_active) по telegram_id.
async def admin_is_active(telegram_id: int, role: str = 'admin', session: AsyncSession = None):
    if role == 'admin':
        query = select(Admins).where(Admins.telegram_id == telegram_id)
        result = await session.execute(query)
        admin = result.scalar()
        return admin.is_active if admin else False
    return True


# Примечание: Сохраняет новый сгенерированный инвайт-код для указанной роли (admin или operator) в БД.
async def invites(invite_code: str, role: str, session: AsyncSession):
    query = select(Invites).where(Invites.invite_code == invite_code)
    result = await session.execute(query)

    if result.scalar() is None:
        new_invite = Invites(
            invite_code=invite_code,
            role=role
        )
        session.add(new_invite)
        await session.commit()
        return True
    return False


# Примечание: Активирует инвайт-код и создает запись в таблице Admins или Operators с привязкой к telegram_id пользователя.
async def invites_use(invite_code: str, role: str | None, user_id: int, session: AsyncSession):
    query1 = select(Invites).where(Invites.invite_code == invite_code)
    result1 = await session.execute(query1)
    invite = result1.scalar()

    if not invite:
        return (False, '❌ Неверный инвайт-код!', None)
    if invite.used:
        return (False, '❌ Этот инвайт-код уже был использован!', None)

    query2 = select(Subscriber).where(Subscriber.telegram_id == user_id)
    result2 = await session.execute(query2)
    subscriber = result2.scalar()

    if not subscriber:
        return (False, '⚠️ Сначала зарегистрируйтесь как пользователь через /start (отправьте контакт).', None)

    user_name = subscriber.name
    phone_number = subscriber.phone_number
    target_role = invite.role if invite.role else role

    if target_role == 'admin':
        query = select(Admins).where(Admins.telegram_id == user_id)
        result = await session.execute(query)
        admin = result.scalar()

        if not admin:
            new_admin = Admins(
                telegram_id=user_id,
                phone_number=phone_number,
                name=user_name
            )
            session.add(new_admin)
            invite.used = True
            invite.admin_id = user_id
            await session.commit()
            return (True, '✅ Вы успешно зарегистрировались в качестве администратора! (Стандартный пароль: Admin1234)', 'admin')
        return (True, 'ℹ️ Вы уже зарегистрированы в качестве администратора.', 'admin')

    elif target_role == 'operator':
        query = select(Operators).where(Operators.telegram_id == user_id)
        result = await session.execute(query)
        operator = result.scalar()

        if not operator:
            new_operator = Operators(
                telegram_id=user_id,
                phone_number=phone_number,
                name=user_name,
                description='Оператор клиентской поддержки'
            )
            session.add(new_operator)
            invite.used = True
            invite.admin_id = user_id
            await session.commit()
            return (True, '✅ Вы успешно зарегистрировались в качестве оператора! (Стандартный пароль: Operator1234)', 'operator')
        return (True, 'ℹ️ Вы уже зарегистрированы в качестве оператора.', 'operator')

    return (False, '❌ Неизвестная роль инвайт-кода.', None)


# ==========================================
# 2. УПРАВЛЕНИЕ ПРОФИЛЕМ И ПАРОЛЯМИ
# ==========================================

# Примечание: Обновляет пароль в БД для администратора или оператора по telegram_id.
async def change_password(telegram_id: int, role: str, new_password: str, session: AsyncSession):
    if role == 'admin':
        query = select(Admins).where(Admins.telegram_id == telegram_id)
        result = await session.execute(query)
        admin = result.scalar()
        if admin:
            admin.password = new_password
            await session.commit()
    elif role == 'operator':
        query = select(Operators).where(Operators.telegram_id == telegram_id)
        result = await session.execute(query)
        operator = result.scalar()
        if operator:
            operator.password = new_password
            await session.commit()


# Примечание: Обновляет номер телефона сотрудника (админа/оператора) и абонента по его telegram_id.
async def update_phone_number(telegram_id: int, role: str, new_phone: str, session: AsyncSession):
    if role == 'admin':
        res = await session.execute(select(Admins).where(Admins.telegram_id == telegram_id))
        admin = res.scalar()
        if admin:
            admin.phone_number = new_phone
    elif role == 'operator':
        res = await session.execute(select(Operators).where(Operators.telegram_id == telegram_id))
        operator = res.scalar()
        if operator:
            operator.phone_number = new_phone

    sub_res = await session.execute(select(Subscriber).where(Subscriber.telegram_id == telegram_id))
    sub = sub_res.scalar()
    if sub:
        sub.phone_number = new_phone

    await session.commit()


# Примечание: Обновляет имя пользователя/админа/оператора во всех связанных таблицах по telegram_id.
async def update_profile_name(telegram_id: int, role: str, new_name: str, session: AsyncSession):
    if role == 'admin':
        res = await session.execute(select(Admins).where(Admins.telegram_id == telegram_id))
        admin = res.scalar()
        if admin:
            admin.name = new_name
    elif role == 'operator':
        res = await session.execute(select(Operators).where(Operators.telegram_id == telegram_id))
        operator = res.scalar()
        if operator:
            operator.name = new_name

    sub_res = await session.execute(select(Subscriber).where(Subscriber.telegram_id == telegram_id))
    sub = sub_res.scalar()
    if sub:
        sub.name = new_name

    await session.commit()


# Примечание: Обновляет описание (о себе) оператора в таблице Operators по его telegram_id.
async def update_operator_description(telegram_id: int, new_desc: str, session: AsyncSession):
    res = await session.execute(select(Operators).where(Operators.telegram_id == telegram_id))
    operator = res.scalar()
    if operator:
        operator.description = new_desc
        await session.commit()


# ==========================================
# 3. УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ (ПО TELEGRAM_ID)
# ==========================================

# Примечание: Получает профиль администратора по его telegram_id.
async def admin_info(telegram_id: int, session: AsyncSession):
    query = select(Admins).where(Admins.telegram_id == telegram_id)
    result = await session.execute(query)
    return result.scalar()


# Примечание: Возвращает список всех администраторов из БД.
async def get_admins_info(session: AsyncSession):
    query = select(Admins)
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Находит администратора строго по его telegram_id.
async def get_admin_info(admin_id: int, session: AsyncSession):
    query = select(Admins).where(Admins.telegram_id == admin_id)
    result = await session.execute(query)
    return result.scalar()


# Примечание: Блокирует администратора (устанавливает is_active = False) по его telegram_id.
async def admin_block(block_id: int, session: AsyncSession):
    query = select(Admins).where(Admins.telegram_id == block_id)
    result = await session.execute(query)
    admin = result.scalar()
    if admin:
        admin.is_active = False
        await session.commit()


# Примечание: Разблокирует администратора (устанавливает is_active = True) по его telegram_id.
async def admin_unblock(block_id: int, session: AsyncSession):
    query = select(Admins).where(Admins.telegram_id == block_id)
    result = await session.execute(query)
    admin = result.scalar()
    if admin:
        admin.is_active = True
        await session.commit()


# Примечание: Разблокирует сразу всех заблокированных администраторов в БД.
async def unblock_all_admins(session: AsyncSession):
    await session.execute(update(Admins).where(Admins.is_active == False).values(is_active=True))
    await session.commit()


# ==========================================
# 4. ОПЕРАТОРЫ, ОЧЕРЕДЬ И ЖИВОЙ ЧАТ
# ==========================================

# Примечание: Возвращает список всех операторов из таблицы Operators.
async def get_operators_info(session: AsyncSession):
    query = select(Operators)
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Получает объект оператора строго по его telegram_id.
async def get_operator_info(op_id: int, session: AsyncSession):
    query = select(Operators).where(Operators.telegram_id == op_id)
    result = await session.execute(query)
    return result.scalar()


# Примечание: Снимает пользователя с роли оператора (удаляет запись из Operators) по его telegram_id.
async def delete_operator(op_id: int, session: AsyncSession):
    query = select(Operators).where(Operators.telegram_id == op_id)
    result = await session.execute(query)
    operator = result.scalar()
    if operator:
        await session.delete(operator)
        await session.commit()
        return True
    return False


# Примечание: Возвращает список операторов, отсортированный по рейтингу и числу обслуженных клиентов.
async def get_operators_rating(session: AsyncSession):
    query = select(Operators).order_by(Operators.rating.desc(), Operators.count.desc())
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Переключает статус рабочей смены оператора (is_working), накапливает точное время сессий в секундах и округляет часы (hours) после каждого завершения смены.
async def set_operator_work_status(telegram_id: int, is_working: bool, session: AsyncSession):
    query = select(Operators).where(Operators.telegram_id == telegram_id)
    result = await session.execute(query)
    operator = result.scalar()
    if operator:
        now = datetime.now()
        if is_working:
            # Фиксируем старт сессии только если оператор еще не был на смене
            if not operator.is_working or operator.shift_start is None:
                operator.shift_start = now
            operator.is_working = True
            if operator.current_client_id is None:
                operator.is_free = True
        else:
            # При завершении смены считаем длительность сессии и прибавляем к общему времени
            if operator.is_working and operator.shift_start is not None:
                session_seconds = max(0, int((now - operator.shift_start).total_seconds()))
                operator.work_seconds = (operator.work_seconds or 0) + session_seconds
                # Математическое округление общего накопленного времени до целых часов
                operator.hours = round(operator.work_seconds / 3600)

            operator.is_working = False
            operator.is_free = False
            operator.shift_start = None

        await session.commit()
        return operator
    return None


# Примечание: Возвращает список всех работающих в данный момент операторов (для уведомлений о новых клиентах).
async def get_working_operators(session: AsyncSession):
    query = select(Operators).where(Operators.is_working == True)
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Возвращает список всех абонентов и список ожидающих в очереди для панели оператора.
async def get_subscribers_for_operator(session: AsyncSession):
    sub_res = await session.execute(select(Subscriber))
    subscribers = sub_res.scalars().all()

    wait_res = await session.execute(select(Waiter).order_by(Waiter.joined_at))
    waiters = wait_res.scalars().all()

    return subscribers, waiters


# Примечание: Находит свободного оператора на смене и сразу связывает его с клиентом (current_client_id = user_id).
async def get_and_occupy_free_operator(user_id: int, session: AsyncSession):
    # Сначала удаляем пользователя из очереди ожидания, если он там был
    await session.execute(delete(Waiter).where(Waiter.telegram_id == user_id))

    query = select(Operators).where(
        Operators.is_free == True,
        Operators.is_working == True,
        Operators.current_client_id.is_(None)
    ).order_by(Operators.count.asc())
    result = await session.execute(query)
    operator = result.scalars().first()
    if operator:
        operator.is_free = False
        operator.current_client_id = user_id
        await session.commit()
        return operator
    return None


# Примечание: Помещает абонента в очередь ожидания оператора (таблица Waiter) и возвращает его позицию в очереди.
async def waiting(user_id: int, user_name: str, session: AsyncSession) -> int:
    query = select(Waiter).where(Waiter.telegram_id == user_id)
    waiter = await session.execute(query)
    if waiter.scalar() is None:
        new_waiter = Waiter(
            telegram_id=user_id,
            name=user_name
        )
        session.add(new_waiter)
        await session.commit()

    count_res = await session.execute(select(func.count(Waiter.id)))
    return count_res.scalar() or 1


# Примечание: Удаляет клиента из очереди ожидания Waiter по его желанию.
async def leave_wait_queue(user_id: int, session: AsyncSession):
    await session.execute(delete(Waiter).where(Waiter.telegram_id == user_id))
    await session.commit()


# Примечание: Берет следующего клиента из очереди ожидания и привязывает его к оператору (current_client_id).
async def get_next_waiter(operator_id: int, session: AsyncSession):
    query1 = select(Operators).where(Operators.telegram_id == operator_id)
    result1 = await session.execute(query1)
    operator = result1.scalar()

    if not operator:
        return None

    if operator.current_client_id is not None:
        return operator.current_client_id

    query2 = select(Waiter).order_by(Waiter.joined_at.asc())
    result2 = await session.execute(query2)
    user = result2.scalars().first()

    if user is None:
        operator.is_free = True
        await session.commit()
        return None

    user_id = user.telegram_id
    operator.is_free = False
    operator.current_client_id = user_id
    await session.delete(user)
    await session.commit()
    return user_id


# Примечание: Проверяет, состоит ли пользователь (оператор или клиент) в активном диалоге, и возвращает данные диалога.
async def get_active_chat_info(telegram_id: int, session: AsyncSession):
    # Проверяем, является ли отправитель оператором в активном чате
    op_res = await session.execute(
        select(Operators).where(
            Operators.telegram_id == telegram_id,
            Operators.current_client_id.is_not(None)
        )
    )
    operator = op_res.scalar()
    if operator:
        return {
            'sender_role': 'operator',
            'partner_id': operator.current_client_id,
            'operator': operator
        }

    # Проверяем, является ли отправитель клиентом в активном чате с оператором
    client_op_res = await session.execute(
        select(Operators).where(Operators.current_client_id == telegram_id)
    )
    client_operator = client_op_res.scalar()
    if client_operator:
        return {
            'sender_role': 'client',
            'partner_id': client_operator.telegram_id,
            'operator': client_operator
        }

    return None


# Примечание: Завершает активный чат (по инициативе оператора или клиента), освобождает оператора и увеличивает счетчик диалогов.
async def end_active_chat_in_db(telegram_id: int, session: AsyncSession):
    query = select(Operators).where(
        (Operators.telegram_id == telegram_id) | (Operators.current_client_id == telegram_id)
    )
    result = await session.execute(query)
    operator = result.scalar()

    if not operator or operator.current_client_id is None:
        return None

    client_id = operator.current_client_id
    op_tg_id = operator.telegram_id
    op_name = operator.name

    operator.current_client_id = None
    operator.is_free = True if operator.is_working else False
    operator.count += 1
    await session.commit()

    return {
        'operator_id': op_tg_id,
        'operator_name': op_name,
        'client_id': client_id
    }


# Примечание: Формирует подробную карточку клиента (имя, телефон, баланс, тариф, статус) для оператора при старте чата.
async def get_client_card_text(client_tg_id: int, session: AsyncSession) -> str:
    sub_res = await session.execute(select(Subscriber).where(Subscriber.telegram_id == client_tg_id))
    sub = sub_res.scalar()
    if not sub:
        return f"👤 <b>Клиент ID:</b> <code>{client_tg_id}</code> (не зарегистрирован в таблице абонентов)"

    tariff_res = await session.execute(select(Tariff).where(Tariff.id == sub.tariff_id))
    tariff = tariff_res.scalar()
    tariff_name = f"{tariff.name} ({tariff.monthly_price} сом)" if tariff else "Не выбран"
    freeze_str = "❄️ Заморожен" if sub.freeze else "✅ Активен"

    return (
        f"📋 <b>Карточка подключенного клиента:</b>\n"
        f"👤 Имя: <b>{sub.name}</b>\n"
        f"📞 Телефон: <code>{sub.phone_number}</code>\n"
        f"💰 Баланс: <b>{sub.balance} сом</b> ({freeze_str})\n"
        f"📦 Тариф: <b>{tariff_name}</b>"
    )


# ==========================================
# 5. БАЛАНС, ТАРИФЫ И АБОНЕНТЫ
# ==========================================

# Примечание: Возвращает полную информацию об абоненте по его telegram_id.
async def get_subscriber_info(telegram_id: int, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
    result = await session.execute(query)
    return result.scalar()


# Примечание: Возвращает текущий баланс абонента по его telegram_id.
async def get_user_balance(telegram_id: int, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == telegram_id)
    result = await session.execute(query)
    sub = result.scalar()
    return sub.balance if sub else 0.00


# Примечание: Возвращает список всех доступных тарифов (id и название тарифа).
async def get_all_tariffs(session: AsyncSession):
    query = select(Tariff.id, Tariff.name)
    result = await session.execute(query)
    return result.all()


# Примечание: Возвращает подробную информацию о конкретном тарифе по его id.
async def get_tarif_info(tarif_id: int, session: AsyncSession):
    query = select(Tariff).where(Tariff.id == tarif_id)
    result = await session.execute(query)
    return result.scalar()


# Примечание: Проверяет, заморожен ли счет абонента по его telegram_id.
async def freeze_check(user_id: int, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == user_id)
    user_profile = await session.execute(query)
    sub = user_profile.scalar()
    return sub.freeze if sub else False


# Примечание: Замораживает счет абонента (freeze = True) по его telegram_id.
async def freezeTrue(user_id: int, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == user_id)
    result = await session.execute(query)
    user_profile = result.scalar()
    if user_profile:
        user_profile.freeze = True
        await session.commit()


# Примечание: Размораживает счет абонента (freeze = False) по его telegram_id.
async def freezeFalse(user_id: int, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == user_id)
    result = await session.execute(query)
    user_profile = result.scalar()
    if user_profile:
        user_profile.freeze = False
        await session.commit()


# Примечание: Меняет тариф абонента по его telegram_id и списывает абонентскую плату.
async def change_tariff(user_id: int, new_tarif_id: int, session: AsyncSession):
    query1 = select(Subscriber).where(Subscriber.telegram_id == user_id)
    query2 = select(Tariff).where(Tariff.id == new_tarif_id)
    result1 = await session.execute(query1)
    result2 = await session.execute(query2)
    subscriber = result1.scalar()
    tariff = result2.scalar()

    if subscriber is None or tariff is None:
        return (False, '❌ Пользователь или тариф не найден.')
    if subscriber.freeze:
        return (False, '❄️ Ваш счёт заморожен. Разморозьте его для смены тарифа.')
    if subscriber.balance < tariff.monthly_price:
        return (False, f'❌ Недостаточно средств на балансе (нужно {tariff.monthly_price} сом). Пополните счёт!')
    if subscriber.tariff_id == new_tarif_id:
        return (False, 'ℹ️ Вы уже подключены к данному тарифу.')

    subscriber.tariff_id = new_tarif_id
    subscriber.balance -= tariff.monthly_price
    await session.commit()
    return (True, f'✅ Вы успешно сменили тариф на «{tariff.name}»!')


# Примечание: Пополняет баланс абонента по его telegram_id на указанную сумму.
async def top_up(user_id: int, amount: int | float, session: AsyncSession):
    query = select(Subscriber).where(Subscriber.telegram_id == user_id)
    result = await session.execute(query)
    subscriber = result.scalar()
    if subscriber:
        subscriber.balance += amount
        await session.commit()


# Примечание: Возвращает статистику популярности тарифов по количеству подключенных абонентов.
async def get_tariffs_popularity(session: AsyncSession):
    query = (
        select(Tariff.name, Tariff.monthly_price, func.count(Subscriber.id).label('sub_count'))
        .outerjoin(Subscriber, Tariff.id == Subscriber.tariff_id)
        .group_by(Tariff.id)
        .order_by(func.count(Subscriber.id).desc())
    )
    result = await session.execute(query)
    return result.all()


# ==========================================
# 6. ОТЗЫВЫ НА ОПЕРАТОРОВ, FAQ И КОНТЕКСТ ДЛЯ ИИ
# ==========================================

# Примечание: Получает отзывы на конкретного оператора строго по его telegram_id.
async def get_operator_reviews(operator_telegram_id: int, session: AsyncSession):
    query = select(Reviews).where(Reviews.operator_id == operator_telegram_id).order_by(Reviews.id.desc())
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Получает список всех отзывов от пользователей из таблицы Reviews.
async def get_all_reviews(session: AsyncSession):
    query = select(Reviews).order_by(Reviews.id.desc())
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Сохраняет отзыв на конкретного оператора и автоматически пересчитывает средний рейтинг этого оператора в таблице Operators.
async def add_review(user_id: int, rating: int, review_text: str, session: AsyncSession, operator_id: int):
    new_review = Reviews(
        operator_id=operator_id,
        user_id=user_id,
        rating=rating,
        review=review_text
    )
    session.add(new_review)
    await session.flush()

    # Пересчитываем среднюю оценку оператора по всем его отзывам
    avg_res = await session.execute(
        select(func.avg(Reviews.rating)).where(Reviews.operator_id == operator_id)
    )
    avg_rating = avg_res.scalar()

    op_res = await session.execute(select(Operators).where(Operators.telegram_id == operator_id))
    operator = op_res.scalar()
    if operator and avg_rating is not None:
        operator.rating = round(float(avg_rating), 2)

    await session.commit()


# Примечание: Добавляет новый вопрос и ответ в таблицу частых вопросов (Faq).
async def add_faq_item(question: str, answer: str, session: AsyncSession):
    faq = Faq(question=question, answer=answer)
    session.add(faq)
    await session.commit()


# Примечание: Возвращает все частые вопросы и ответы из таблицы Faq.
async def get_all_faqs(session: AsyncSession):
    query = select(Faq)
    result = await session.execute(query)
    return result.scalars().all()


# Примечание: Собирает актуальные данные о тарифах, FAQ и профиле абонента из БД для контекста ИИ-помощника.
async def build_ai_context(user_id: int, session: AsyncSession) -> str:
    sub = await get_subscriber_info(user_id, session)
    tariffs_res = await session.execute(select(Tariff))
    tariffs = tariffs_res.scalars().all()
    faqs = await get_all_faqs(session)

    lines = ["--- ДОСТУПНЫЕ ТАРИФЫ ---"]
    for t in tariffs:
        lines.append(f"• Тариф «{t.name}»: {t.monthly_price} сом/мес, {t.gb_limit} ГБ интернета, {t.minutes_limit} минут.")

    lines.append("\n--- ЧАСТЫЕ ВОПРОСЫ (FAQ) ---")
    for f in faqs:
        lines.append(f"В: {f.question}\nО: {f.answer}")

    if sub:
        user_tariff = next((t.name for t in tariffs if t.id == sub.tariff_id), "Неизвестен")
        freeze_status = "Заморожен" if sub.freeze else "Активен"
        lines.append(
            f"\n--- ДАННЫЕ ТЕКУЩЕГО АБОНЕНТА ---\n"
            f"Имя: {sub.name}, Баланс: {sub.balance} сом, Текущий тариф: {user_tariff}, Статус счёта: {freeze_status}."
        )
    return "\n".join(lines)