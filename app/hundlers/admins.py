# ==========================================
# ФАЙЛ app/hundlers/admins.py
# ==========================================
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.request import (
    password_check, admin_info, change_password, get_admins_info, get_admin_info,
    admin_block, admin_unblock, unblock_all_admins, invites,
    get_operators_info, get_operator_info, delete_operator,
    get_operators_rating, get_operator_reviews, get_tariffs_popularity,
    add_faq_item, get_all_faqs, get_all_reviews, id_check
)
from app.keyboards.inline import (
    come_in_cabinet, admin_cabinet_keyboard, block_admin, blocked_admins,
    administrator_kb_active, administrator_kb_inactive, administrators_kb,
    operators_kb, operator_kb, back_to_operators_kb,
    admin_users_kb, back_to_admin_users_kb, cancel_fsm_kb
)
from app.states.states import ChangePassword, ConfimPassword, AddFaq
from app.utils.utils import is_strong_password, generate_invite_code

router = Router()


# ==========================================
# 1. КАБИНЕТ И УНИВЕРСАЛЬНАЯ СМЕНА ПАРОЛЯ (АДМИН + ОПЕРАТОР)
# ==========================================

# Примечание: Открывает главное меню личного кабинета администратора.
@router.callback_query(F.data == 'admin_cabinet')
async def admin_cabinet(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        'Добро пожаловать в личный кабинет администратора!',
        reply_markup=admin_cabinet_keyboard()
    )
    await callback.answer()


# Примечание: Запускает FSM смены пароля и сохраняет текущую роль сотрудника (admin или operator) в контекст FSM.
@router.callback_query(F.data == 'change_password')
async def change_staff_password(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    role = await id_check(callback.from_user.id, session) or 'admin'
    back_cb = 'admin_cabinet' if role == 'admin' else 'op_cabinet'

    await state.update_data(role=role)
    await state.set_state(ChangePassword.old_password)
    await callback.message.edit_text(
        '🔑 Введите, пожалуйста, свой старый пароль:',
        reply_markup=cancel_fsm_kb(back_cb)
    )
    await callback.answer()


# Примечание: Проверяет старый пароль в БД для роли из FSM и переводит на шаг ввода нового пароля.
@router.message(ChangePassword.old_password)
async def process_old_password(message: Message, state: FSMContext, session: AsyncSession):
    entered_old_password = message.text
    user_id = message.from_user.id
    data = await state.get_data()
    role = data.get('role', 'admin')

    check = await password_check(telegram_id=user_id, role=role, password=entered_old_password, session=session)
    if check:
        await message.answer('Введите, пожалуйста, свой новый пароль:')
        await state.set_state(ChangePassword.new_password)
    else:
        await message.answer('❌ Вы ввели неверный старый пароль! Попробуйте ещё раз:')


# Примечание: Проверяет надежность нового пароля через is_strong_password по имени и телефону сотрудника из БД.
@router.message(ChangePassword.new_password)
async def proccess_new_password(message: Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    new_password = message.text or ''
    data = await state.get_data()
    role = data.get('role', 'admin')

    if role == 'admin':
        staff = await admin_info(telegram_id=user_id, session=session)
    else:
        staff = await get_operator_info(op_id=user_id, session=session)

    check = is_strong_password(
        password=new_password,
        user_name=staff.name if staff else '',
        number=staff.phone_number if staff else ''
    )
    if check is True:
        await state.update_data(saved_new_password=new_password)
        await message.answer('Введите новый пароль ещё раз для подтверждения:')
        await state.set_state(ChangePassword.confirm_password)
        return
    await message.answer(f'⚠️ {check}')


# Примечание: Сверяет подтверждение нового пароля, обновляет его в БД (для админа или оператора) и завершает FSM.
@router.message(ChangePassword.confirm_password)
async def proccess_confirm_password(message: Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id
    password = message.text
    data = await state.get_data()
    new_password = data['saved_new_password']
    role = data.get('role', 'admin')

    if password == new_password:
        await change_password(telegram_id=user_id, new_password=new_password, role=role, session=session)
        await state.clear()
        await message.answer('🎉 Поздравляем! Вы успешно поменяли свой пароль.', reply_markup=come_in_cabinet(role))
        return

    await message.answer('❌ Пароли не совпадают! Придумайте новый пароль заново:')
    await state.set_state(ChangePassword.new_password)


# ==========================================
# 2. УПРАВЛЕНИЕ АДМИНИСТРАТОРАМИ
# ==========================================

# Примечание: Выводит список всех активных администраторов из БД.
@router.callback_query(F.data == 'admin_info')
async def admins_info_handler(callback: CallbackQuery, session: AsyncSession):
    admins = await get_admins_info(session=session)
    await callback.message.edit_text('🛡 Информация об администраторах:', reply_markup=administrators_kb(admins))
    await callback.answer()


# Примечание: Генерирует новый инвайт-код для роли admin, сохраняет в БД и отправляет его в сообщении.
@router.callback_query(F.data.in_({'admin+', 'admin_add_invite'}))
async def add_new_admin(callback: CallbackQuery, session: AsyncSession):
    invite_code = generate_invite_code()
    check = await invites(invite_code=invite_code, role='admin', session=session)
    if not check:
        await callback.answer('Такой invite-код уже есть, попробуйте ещё раз.', show_alert=True)
        return

    text = (
        '✅ <b>Инвайт-код для администратора успешно сгенерирован!</b>\n\n'
        f'Передайте эту команду новому сотруднику:\n<code>/admin {invite_code}</code>\n\n'
        'Он должен зарегистрироваться в боте и отправить эту команду.'
    )
    await callback.message.edit_text(text, reply_markup=block_admin(), parse_mode='HTML')
    await callback.answer()


# Примечание: Отображает карточку выбранного администратора по его telegram_id.
@router.callback_query(F.data.startswith('admin_id_'))
async def show_admin_card(callback: CallbackQuery, session: AsyncSession):
    admin_id = int(callback.data.split('_')[-1])
    admin = await get_admin_info(admin_id=admin_id, session=session)
    if not admin:
        await callback.answer('Администратор не найден.', show_alert=True)
        return

    status = '✅ Активен' if admin.is_active else '🚫 Заблокирован'
    text = (
        f'🛡 <b>Карточка администратора</b>\n\n'
        f'👤 Имя: {admin.name}\n'
        f'📞 Номер: {admin.phone_number}\n'
        f'📡 Статус: {status}'
    )
    if admin.is_active:
        await callback.message.edit_text(text, reply_markup=administrator_kb_active(admin=admin), parse_mode='HTML')
    else:
        await callback.message.edit_text(text, reply_markup=administrator_kb_inactive(admin=admin), parse_mode='HTML')
    await callback.answer()


# Примечание: Запрашивает пароль текущего администратора перед блокировкой выбранного админа.
@router.callback_query(F.data.startswith('admin-'))
async def start_delete_admin(callback: CallbackQuery, state: FSMContext):
    block_id = int(callback.data.split('-')[1])
    admin_id = callback.from_user.id
    await state.set_state(ConfimPassword.confim_password_for_block)
    await state.update_data(block_id=block_id, admin_id=admin_id)
    await callback.message.edit_text(
        '🔐 Подтвердите свой пароль перед блокировкой администратора:',
        reply_markup=cancel_fsm_kb('admin_cabinet')
    )
    await callback.answer()


# Примечание: Проверяет пароль и блокирует выбранного администратора в БД по telegram_id.
@router.message(ConfimPassword.confim_password_for_block)
async def confim_password_for_block(message: Message, state: FSMContext, session: AsyncSession):
    password = message.text
    data = await state.get_data()
    block_id = data['block_id']
    admin_id = data['admin_id']

    check = await password_check(telegram_id=admin_id, role='admin', password=password, session=session)
    if check:
        await admin_block(block_id=block_id, session=session)
        await state.clear()
        await message.answer('🚫 Вы успешно заблокировали администратора!', reply_markup=block_admin())
    else:
        await message.answer('❌ Вы ввели неправильный пароль! Попробуйте ещё раз:')


# Примечание: Выводит список заблокированных администраторов из БД.
@router.callback_query(F.data == 'blocked_admins')
async def blocked_admins_info(callback: CallbackQuery, session: AsyncSession):
    admins = await get_admins_info(session=session)
    await callback.message.edit_text(
        '🚫 Заблокированные администраторы:',
        reply_markup=blocked_admins(admins)
    )
    await callback.answer()


# Примечание: Разблокирует сразу всех заблокированных администраторов в БД по нажатию кнопки unblock_all.
@router.callback_query(F.data == 'unblock_all')
async def unblock_all_admins_handler(callback: CallbackQuery, session: AsyncSession):
    await unblock_all_admins(session)
    admins = await get_admins_info(session=session)
    await callback.message.edit_text(
        '🔓 Все администраторы успешно разблокированы!',
        reply_markup=administrators_kb(admins)
    )
    await callback.answer()


# Примечание: Запрашивает пароль перед разблокировкой конкретного администратора.
@router.callback_query(F.data.startswith('admin_unblock_'))
async def start_unblock_admin(callback: CallbackQuery, state: FSMContext):
    unblock_id = int(callback.data.split('_')[-1])
    admin_id = callback.from_user.id
    await state.set_state(ConfimPassword.confim_password_for_unblock)
    await state.update_data(block_id=unblock_id, admin_id=admin_id)
    await callback.message.edit_text(
        '🔐 Подтвердите свой пароль перед разблокировкой администратора:',
        reply_markup=cancel_fsm_kb('admin_cabinet')
    )
    await callback.answer()


# Примечание: Проверяет пароль и разблокирует выбранного администратора в БД по telegram_id.
@router.message(ConfimPassword.confim_password_for_unblock)
async def confim_password_for_unblock(message: Message, state: FSMContext, session: AsyncSession):
    password = message.text
    data = await state.get_data()
    block_id = data['block_id']
    admin_id = data['admin_id']

    check = await password_check(telegram_id=admin_id, role='admin', password=password, session=session)
    if check:
        await admin_unblock(block_id=block_id, session=session)
        await state.clear()
        await message.answer('🔓 Вы успешно разблокировали администратора!', reply_markup=block_admin())
    else:
        await message.answer('❌ Вы ввели неправильный пароль! Попробуйте ещё раз:')


# ==========================================
# 3. УПРАВЛЕНИЕ ОПЕРАТОРАМИ
# ==========================================

# Примечание: Выводит список всех операторов из БД с клавиатурой operators_kb.
@router.callback_query(F.data == 'operator_info')
async def show_operators_list(callback: CallbackQuery, session: AsyncSession):
    operators = await get_operators_info(session)
    await callback.message.edit_text('🎧 Список операторов:', reply_markup=operators_kb(operators))
    await callback.answer()


# Примечание: Генерирует инвайт-код для роли operator, сохраняет его в БД и выводит администратору.
@router.callback_query(F.data == 'operator+')
async def add_new_operator(callback: CallbackQuery, session: AsyncSession):
    invite_code = generate_invite_code()
    check = await invites(invite_code=invite_code, role='operator', session=session)
    if not check:
        await callback.answer('Ошибка генерации кода, попробуйте снова.', show_alert=True)
        return

    text = (
        '✅ <b>Инвайт-код для оператора успешно сгенерирован!</b>\n\n'
        f'Передайте эту команду новому оператору:\n<code>/admin {invite_code}</code>\n\n'
        'После отправки команды бот выдаст ему права оператора.'
    )
    await callback.message.edit_text(text, reply_markup=back_to_operators_kb(), parse_mode='HTML')
    await callback.answer()


# Примечание: Выводит подробную карточку выбранного оператора по его telegram_id.
@router.callback_query(F.data.startswith('op_id_'))
async def show_operator_card(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    op_tg_id = int(callback.data.split('_')[-1])
    operator = await get_operator_info(op_id=op_tg_id, session=session)
    if not operator:
        await callback.answer('Оператор не найден.', show_alert=True)
        return

    await state.update_data(selected_operator_tg_id=operator.telegram_id)
    work_status = '🟢 На смене' if operator.is_working else '🔴 Не в сети'
    free_status = 'Свободен' if operator.is_free else f'В чате с клиентом {operator.current_client_id}'

    text = (
        f'🎧 <b>Карточка оператора: {operator.name}</b>\n\n'
        f'🆔 Telegram ID: <code>{operator.telegram_id}</code>\n'
        f'📞 Телефон: <code>{operator.phone_number}</code>\n'
        f'📝 О себе: <i>{operator.description}</i>\n'
        f'⭐ Рейтинг: <b>{operator.rating}</b>\n'
        f'💬 Обслужено диалогов: <b>{operator.count}</b>\n'
        f'⏱ Отработано смен/часов: <b>{operator.hours}</b>\n'
        f'📡 Статус: {work_status} ({free_status})'
    )
    await callback.message.edit_text(text, reply_markup=operator_kb(operator), parse_mode='HTML')
    await callback.answer()


# Примечание: Снимает пользователя с роли оператора (удаляет из таблицы Operators) по его telegram_id.
@router.callback_query(F.data.startswith('operator-'))
async def remove_operator_handler(callback: CallbackQuery, session: AsyncSession):
    op_tg_id = int(callback.data.split('-')[1])
    await delete_operator(op_id=op_tg_id, session=session)
    operators = await get_operators_info(session)
    await callback.message.edit_text(
        '❌ Пользователь успешно снят с роли оператора.',
        reply_markup=operators_kb(operators)
    )
    await callback.answer()


# Примечание: Выводит рейтинг всех операторов, отсортированный по убыванию оценки и количества чатов.
@router.callback_query(F.data == 'operators_rating')
async def show_operators_rating(callback: CallbackQuery, session: AsyncSession):
    operators = await get_operators_rating(session)
    if not operators:
        text = 'В базе данных пока нет операторов.'
    else:
        lines = ['🏆 <b>Рейтинг операторов:</b>\n']
        for idx, op in enumerate(operators, start=1):
            lines.append(f'{idx}. <b>{op.name}</b> — ⭐ {op.rating} (чатов: {op.count}, часов: {op.hours})')
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_operators_kb(), parse_mode='HTML')
    await callback.answer()


# Примечание: Показывает все отзывы на конкретного оператора из таблицы Reviews по его telegram_id.
@router.callback_query(F.data.startswith('operator_review'))
async def show_operator_reviews_for_admin(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    parts = callback.data.split('_')
    if len(parts) >= 3 and parts[-1].isdigit():
        op_tg_id = int(parts[-1])
    else:
        data = await state.get_data()
        op_tg_id = data.get('selected_operator_tg_id', 0)

    operator = await get_operator_info(op_tg_id, session)
    reviews = await get_operator_reviews(operator_telegram_id=op_tg_id, session=session)

    op_name = operator.name if operator else f'ID {op_tg_id}'
    if not reviews:
        text = f'📝 На оператора <b>{op_name}</b> пока нет отзывов.'
    else:
        lines = [f'📝 <b>Отзывы на оператора {op_name} (⭐ {operator.rating if operator else "-"}):</b>\n']
        for rev in reviews:
            lines.append(f'👤 От абонента <code>{rev.user_id}</code> | ⭐ {rev.rating}/5\n💬 {rev.review}\n')
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_operators_kb(), parse_mode='HTML')
    await callback.answer()


# ==========================================
# 4. УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ, ТАРИФАМИ, FAQ И ОТЗЫВАМИ
# ==========================================

# Примечание: Открывает меню управления пользователями, тарифами и FAQ (admin_users_kb).
@router.callback_query(F.data == 'users_info_admin')
async def admin_users_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('👥 Раздел управления пользователями и контентом:', reply_markup=admin_users_kb())
    await callback.answer()


# Примечание: Выводит рейтинг популярности тарифов по числу абонентов из БД.
@router.callback_query(F.data == 'tariffs_info')
async def show_tariffs_popularity(callback: CallbackQuery, session: AsyncSession):
    stats = await get_tariffs_popularity(session)
    if not stats:
        text = 'Тарифы пока не созданы.'
    else:
        lines = ['📊 <b>Статистика и рейтинг тарифов:</b>\n']
        for idx, (name, price, count) in enumerate(stats, start=1):
            lines.append(f'{idx}. <b>{name}</b> ({price} сом/мес) — 👥 абонентов: <b>{count}</b>')
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_admin_users_kb(), parse_mode='HTML')
    await callback.answer()


# Примечание: Запускает FSM-состояние AddFaq.question для добавления нового частого вопроса.
@router.callback_query(F.data == 'add_faq')
async def start_add_faq(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddFaq.question)
    await callback.message.edit_text(
        '❓ Введите текст нового частого вопроса:',
        reply_markup=cancel_fsm_kb('admin_cabinet')
    )
    await callback.answer()


# Примечание: Сохраняет вопрос в FSM и запрашивает ответ на него (AddFaq.answer).
@router.message(AddFaq.question)
async def process_faq_question(message: Message, state: FSMContext):
    if not message.text:
        await message.answer('Пожалуйста, отправьте вопрос текстом:')
        return
    await state.update_data(question=message.text.strip())
    await state.set_state(AddFaq.answer)
    await message.answer('💬 Теперь введите ответ на этот вопрос:')


# Примечание: Сохраняет новый вопрос и ответ в таблицу Faq в БД и возвращает меню admin_users_kb.
@router.message(AddFaq.answer)
async def process_faq_answer(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text:
        await message.answer('Пожалуйста, отправьте ответ текстом:')
        return

    data = await state.get_data()
    question = data['question']
    answer = message.text.strip()

    await add_faq_item(question=question, answer=answer, session=session)
    await state.clear()
    await message.answer('✅ Новый частый вопрос успешно добавлен в базу!', reply_markup=admin_users_kb())


# Примечание: Выводит список всех частых вопросов из БД для просмотра администратором.
@router.callback_query(F.data == 'users_questions')
async def show_admin_faqs(callback: CallbackQuery, session: AsyncSession):
    faqs = await get_all_faqs(session)
    if not faqs:
        text = '❓ Список частых вопросов пока пуст.'
    else:
        lines = ['❓ <b>Список частых вопросов (FAQ):</b>\n']
        for idx, item in enumerate(faqs, start=1):
            lines.append(f'<b>{idx}. {item.question}</b>\nОтвет: {item.answer}\n')
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_admin_users_kb(), parse_mode='HTML')
    await callback.answer()


# Примечание: Выводит все отзывы пользователей на операторов из таблицы Reviews.
@router.callback_query(F.data == 'users_review')
async def show_all_user_reviews(callback: CallbackQuery, session: AsyncSession):
    reviews = await get_all_reviews(session)
    if not reviews:
        text = '🌟 Отзывов от пользователей пока нет.'
    else:
        lines = ['🌟 <b>Все отзывы пользователей на операторов:</b>\n']
        for rev in reviews:
            lines.append(
                f'👤 Клиент: <code>{rev.user_id}</code> ➡️ Оператор: <code>{rev.operator_id}</code>\n'
                f'⭐ Оценка: {rev.rating}/5 | 💬 {rev.review}\n'
            )
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=back_to_admin_users_kb(), parse_mode='HTML')
    await callback.answer()