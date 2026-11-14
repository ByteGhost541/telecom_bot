# ==========================================
# ФАЙЛ app/hundlers/operator.py
# ==========================================
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.request import (
    set_operator_work_status, get_operator_info,
    get_operator_reviews, get_subscribers_for_operator,
    get_next_waiter, get_client_card_text, end_active_chat_in_db
)
from app.keyboards.inline import (
    operator_cabinet_kb, operator_wait_kb, finish_chat_kb, rate_operator_kb
)
from app.hundlers.filters import ActiveChatFilter

router = Router()


# ==========================================
# 1. СМЕНА ОПЕРАТОРА И РАБОТА С ОЧЕРЕДЬЮ
# ==========================================

# Примечание: Выводит оператора на смену (is_working = True) и показывает текущее число клиентов в очереди.
@router.callback_query(F.data == 'start_work')
async def operator_start_work(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    await set_operator_work_status(telegram_id=user_id, is_working=True, session=session)
    _, waiters = await get_subscribers_for_operator(session)

    await callback.message.edit_text(
        f'🟢 <b>Вы на линии и готовы принимать обращения!</b>\n'
        f'⏳ Клиентов в очереди ожидания сейчас: <b>{len(waiters)}</b>\n\n'
        'Нажмите «💬 Следующий чат», чтобы подключить клиента из очереди, или ожидайте нового обращения.',
        reply_markup=operator_wait_kb(),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Обновляет информацию о количестве ожидающих клиентов на рабочей панели оператора.
@router.callback_query(F.data == 'refresh_queue')
async def operator_refresh_queue(callback: CallbackQuery, session: AsyncSession):
    _, waiters = await get_subscribers_for_operator(session)
    await callback.answer(f'Клиентов в очереди: {len(waiters)}', show_alert=False)
    text = (
        f'🟢 <b>Рабочая панель оператора</b>\n'
        f'⏳ Клиентов в очереди ожидания: <b>{len(waiters)}</b>\n\n'
        'Нажмите «💬 Следующий чат», чтобы взять клиента в работу.'
    )
    try:
        await callback.message.edit_text(text, reply_markup=operator_wait_kb(), parse_mode='HTML')
    except Exception:
        pass


# Примечание: Подключает к оператору первого клиента из очереди ожидания Waiter и уведомляет обе стороны.
@router.callback_query(F.data == 'next_chat')
async def operator_take_next_chat(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    operator_id = callback.from_user.id
    operator = await get_operator_info(operator_id, session)

    if not operator or not operator.is_working:
        await callback.answer('Сначала начните рабочую смену!', show_alert=True)
        return

    if operator.current_client_id is not None:
        card = await get_client_card_text(operator.current_client_id, session)
        await callback.message.edit_text(
            f'⚠️ У вас уже есть активный диалог!\n\n{card}\n\nНапишите сообщение клиенту или завершите текущий чат:',
            reply_markup=finish_chat_kb(),
            parse_mode='HTML'
        )
        await callback.answer()
        return

    client_id = await get_next_waiter(operator_id, session)
    if client_id is None:
        await callback.answer('Очередь ожидания сейчас пуста! Новые клиенты подключатся автоматически.', show_alert=True)
        return

    card = await get_client_card_text(client_id, session)

    # Уведомляем оператора и выдаем карточку клиента
    await callback.message.edit_text(
        f'🔗 <b>Клиент из очереди подключен к чату!</b>\n\n{card}\n\n'
        '✍️ <i>Все ваши сообщения ниже будут пересылаться клиенту:</i>',
        reply_markup=finish_chat_kb(),
        parse_mode='HTML'
    )

    # Уведомляем самого клиента о подключении оператора
    try:
        await bot.send_message(
            chat_id=client_id,
            text=(
                f'🎧 <b>К вам подключился оператор {operator.name}!</b>\n'
                f'ℹ️ <i>{operator.description}</i> (Рейтинг: ⭐ {operator.rating})\n\n'
                'Напишите ваш вопрос в этот чат:'
            ),
            reply_markup=finish_chat_kb(),
            parse_mode='HTML'
        )
    except Exception:
        pass

    await callback.answer()


# Примечание: Завершает смену оператора (is_working = False), проверяя отсутствие незавершенного диалога.
@router.callback_query(F.data == 'finish_work')
async def operator_finish_work(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    operator = await get_operator_info(user_id, session)

    if operator and operator.current_client_id is not None:
        await callback.answer('⚠️ Сначала завершите активный чат с клиентом!', show_alert=True)
        return

    updated_op = await set_operator_work_status(telegram_id=user_id, is_working=False, session=session)
    hours = updated_op.hours if updated_op else 0
    await callback.message.edit_text(
        f'🔴 <b>Рабочий день завершен.</b> Вы сняты с линии.\n'
        f'⏱ Всего отработано смен/часов: <b>{hours}</b>',
        reply_markup=operator_cabinet_kb(is_continuing=False),
        parse_mode='HTML'
    )
    await callback.answer()


# ==========================================
# 2. КАБИНЕТ, СТАТИСТИКА, ОТЗЫВЫ И СПИСОК АБОНЕНТОВ
# ==========================================

# Примечание: Возвращает оператора в главное меню личного кабинета.
@router.callback_query(F.data == 'op_cabinet')
async def back_to_operator_cabinet(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    user_id = callback.from_user.id
    operator = await get_operator_info(op_id=user_id, session=session)
    is_continuing = operator.is_working if operator else False
    await callback.message.edit_text(
        '🎧 Личный кабинет оператора:',
        reply_markup=operator_cabinet_kb(is_continuing=is_continuing)
    )
    await callback.answer()


# Примечание: Показывает личную карточку и статистику самого оператора.
@router.callback_query(F.data == 'op_my_stats')
async def operator_my_stats(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    operator = await get_operator_info(op_id=user_id, session=session)
    if not operator:
        await callback.answer('Профиль оператора не найден.', show_alert=True)
        return

    status = '🟢 На смене' if operator.is_working else '🔴 Не на смене'
    exp_date = operator.experience.strftime('%d.%m.%Y') if operator.experience else 'Неизвестно'
    text = (
        f'📊 <b>Ваша статистика и анкета</b>\n\n'
        f'👤 Имя: <b>{operator.name}</b>\n'
        f'📞 Телефон: <code>{operator.phone_number}</code>\n'
        f'📝 О себе: <i>{operator.description}</i>\n'
        f'⭐ Ваш рейтинг: <b>{operator.rating} / 5.0</b>\n'
        f'💬 Завершенных чатов: <b>{operator.count}</b>\n'
        f'⏱ Отработано смен/часов: <b>{operator.hours}</b>\n'
        f'📅 В команде с: <b>{exp_date}</b>\n'
        f'📡 Текущий статус: {status}'
    )
    await callback.message.edit_text(
        text,
        reply_markup=operator_cabinet_kb(is_continuing=operator.is_working),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Загружает из БД все отзывы, адресованные текущему оператору, и отображает их.
@router.callback_query(F.data == 'reviews')
async def operator_own_reviews(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    reviews = await get_operator_reviews(operator_telegram_id=user_id, session=session)
    operator = await get_operator_info(op_id=user_id, session=session)
    is_continuing = operator.is_working if operator else False

    if not reviews:
        text = '📝 На вас пока не оставили ни одного отзыва.'
    else:
        lines = [f'📝 <b>Отзывы клиентов о вашей работе (⭐ {operator.rating if operator else 5.0}):</b>\n']
        for rev in reviews[:15]:
            lines.append(f'⭐ Оценка: <b>{rev.rating}/5</b>\n💬 Отзыв: {rev.review}\n')
        text = '\n'.join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=operator_cabinet_kb(is_continuing=is_continuing),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Показывает оператору список ожидающих клиентов в очереди и список абонентов.
@router.callback_query(F.data == 'users_info_op')
async def operator_users_info(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    subscribers, waiters = await get_subscribers_for_operator(session)
    operator = await get_operator_info(op_id=user_id, session=session)
    is_continuing = operator.is_working if operator else False

    lines = [
        '👥 <b>Сводка по абонентам и очереди:</b>',
        f'• Всего зарегистрировано абонентов: <b>{len(subscribers)}</b>',
        f'• Клиентов в очереди ожидания: <b>{len(waiters)}</b>\n'
    ]
    if waiters:
        lines.append('⏳ <b>Сейчас ожидают в очереди:</b>')
        for idx, w in enumerate(waiters[:10], start=1):
            lines.append(f'{idx}. {w.name} (ID: <code>{w.telegram_id}</code>)')
        lines.append('')

    lines.append('📋 <b>Список абонентов:</b>')
    for sub in subscribers[:15]:
        status = '❄️ Заморожен' if sub.freeze else '✅ Активен'
        lines.append(f'👤 <b>{sub.name}</b> (<code>{sub.phone_number}</code>) — {sub.balance} сом [{status}]')

    await callback.message.edit_text(
        '\n'.join(lines),
        reply_markup=operator_cabinet_kb(is_continuing=is_continuing),
        parse_mode='HTML'
    )
    await callback.answer()


# ==========================================
# 3. ЖИВОЙ ЧАТ (ПЕРЕСЫЛКА СООБЩЕНИЙ И ЗАВЕРШЕНИЕ ЧАТА)
# ==========================================

# Примечание: Завершает активный диалог по нажатию кнопки end_chat (от оператора или от клиента) и отправляет клиенту анкету оценки оператора.
@router.callback_query(F.data == 'end_chat')
async def end_live_chat_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    await state.clear()
    chat_data = await end_active_chat_in_db(callback.from_user.id, session)

    if not chat_data:
        await callback.answer('Активный диалог уже завершен.', show_alert=True)
        return

    op_id = chat_data['operator_id']
    op_name = chat_data['operator_name']
    client_id = chat_data['client_id']
    who_ended = 'оператором' if callback.from_user.id == op_id else 'клиентом'

    # 1. Уведомляем оператора и возвращаем его на смену
    op_text = f'✅ <b>Диалог с клиентом завершен ({who_ended}).</b>\nВы снова свободны для новых обращений.'
    if callback.from_user.id == op_id:
        await callback.message.edit_text(op_text, reply_markup=operator_wait_kb(), parse_mode='HTML')
    else:
        try:
            await bot.send_message(chat_id=op_id, text=op_text, reply_markup=operator_wait_kb(), parse_mode='HTML')
        except Exception:
            pass

    # 2. Уведомляем клиента и сразу предлагаем оценить этого оператора (1-5 звезд)
    client_text = (
        f'🛑 <b>Диалог с оператором {op_name} завершен ({who_ended}).</b>\n\n'
        f'Пожалуйста, оцените работу оператора <b>{op_name}</b> от 1 до 5 звезд:'
    )
    if callback.from_user.id == client_id:
        await callback.message.edit_text(
            client_text,
            reply_markup=rate_operator_kb(op_id),
            parse_mode='HTML'
        )
    else:
        try:
            await bot.send_message(
                chat_id=client_id,
                text=client_text,
                reply_markup=rate_operator_kb(op_id),
                parse_mode='HTML'
            )
        except Exception:
            pass

    await callback.answer('Диалог завершен.')


# Примечание: Перехватывает любые сообщения (текст, медиа, файлы) участников активного чата и пересылает их собеседнику.
@router.message(StateFilter('*'), ActiveChatFilter())
async def relay_live_chat_messages(message: Message, chat_info: dict, bot: Bot):
    sender_role = chat_info['sender_role']
    partner_id = chat_info['partner_id']
    operator = chat_info['operator']

    header = (
        f'🎧 <b>Оператор {operator.name}:</b>'
        if sender_role == 'operator'
        else f'👤 <b>Клиент ({message.from_user.first_name or "Абонент"}):</b>'
    )

    try:
        if message.text:
            await bot.send_message(
                chat_id=partner_id,
                text=f'{header}\n{message.text}',
                reply_markup=finish_chat_kb(),
                parse_mode='HTML'
            )
        else:
            await bot.send_message(chat_id=partner_id, text=header, parse_mode='HTML')
            await message.copy_to(chat_id=partner_id, reply_markup=finish_chat_kb())
    except Exception:
        await message.answer('⚠️ Не удалось доставить сообщение собеседнику.')