# ==========================================
# ФАЙЛ app/hundlers/starts.py
# ==========================================
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.reply import get_contact_keyboard
from app.keyboards.inline import (
    log_in_as, admin_cabinet_keyboard, operator_cabinet_kb,
    user_cabinet_kb, help_kb, profile_update_kb, cancel_fsm_kb
)
from app.database.request import (
    id_check, admin_is_active, password_check, get_operator_info,
    get_subscriber_info, admin_info, update_phone_number,
    update_profile_name, update_operator_description
)
from app.hundlers.filters import RoleFilter
from app.states.states import UpdateProfile

router = Router()


# Примечание: Обрабатывает команду /start, проверяет роль пользователя в БД и открывает регистрацию или выбор входа.
@router.message(Command('start'))
async def start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    status = await id_check(user_id, session)

    if status is None:
        await message.answer(
            'Добро пожаловать! Пожалуйста, поделитесь номером телефона для регистрации:',
            reply_markup=get_contact_keyboard()
        )
    elif status == 'user':
        await message.answer('Добро пожаловать в личный кабинет!', reply_markup=user_cabinet_kb())
    elif status in ('admin', 'operator'):
        await message.answer('Добро пожаловать! Выберите режим входа:', reply_markup=log_in_as(status))


# Примечание: Позволяет сотруднику (админу/оператору) зайти в обычный кабинет абонента или зарегистрироваться по контакту.
@router.callback_query(F.data == 'log_in_as_user')
async def log_in_as_user(callback: CallbackQuery, session: AsyncSession):
    sub = await get_subscriber_info(callback.from_user.id, session)
    if sub:
        await callback.message.edit_text('Ваш личный кабинет абонента:', reply_markup=user_cabinet_kb())
    else:
        await callback.message.delete()
        await callback.message.answer(
            'Пожалуйста, поделитесь номером телефона:',
            reply_markup=get_contact_keyboard()
        )
    await callback.answer()


# Примечание: Запрашивает ввод команды /password у администратора или оператора.
@router.callback_query(F.data.startswith('log_in_as_'))
async def log_in_as_not_user(callback: CallbackQuery):
    await callback.message.edit_text(
        '🔐 Введите свой пароль командой в формате:\n<code>/password ВашПароль</code>',
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Проверяет пароль через БД, определяет роль (admin или operator) и открывает соответствующий кабинет.
@router.message(Command('password'), RoleFilter(['admin', 'operator']))
async def check_password(message: Message, command: CommandObject, session: AsyncSession):
    user_password = command.args
    user_id = message.from_user.id

    if user_password is None:
        await message.answer(
            '⚠️ Вы не ввели сам пароль. Пример:\n<code>/password Admin1234</code>',
            parse_mode='HTML'
        )
        return

    role = await id_check(user_id, session)

    if role == 'admin':
        is_active = await admin_is_active(telegram_id=user_id, role='admin', session=session)
        if not is_active:
            await message.answer(
                '🚫 Ваш аккаунт администратора заблокирован. Вы вошли как обычный пользователь.',
                reply_markup=user_cabinet_kb()
            )
            return

        check = await password_check(telegram_id=user_id, role='admin', password=user_password, session=session)
        if check:
            await message.answer(
                '✅ Вы ввели верный пароль! Добро пожаловать в панель администратора:',
                reply_markup=admin_cabinet_keyboard()
            )
            return
        await message.answer('❌ Вы ввели неверный пароль! Попробуйте ещё раз.')

    elif role == 'operator':
        check = await password_check(telegram_id=user_id, role='operator', password=user_password, session=session)
        if check:
            operator = await get_operator_info(user_id, session)
            is_continuing = operator.is_working if operator else False
            await message.answer(
                '✅ Вы ввели верный пароль! Добро пожаловать в кабинет оператора:',
                reply_markup=operator_cabinet_kb(is_continuing=is_continuing)
            )
            return
        await message.answer('❌ Вы ввели неверный пароль! Попробуйте ещё раз.')


# ==========================================
# ОБНОВЛЕНИЕ ПРОФИЛЯ (ТЕЛЕФОН / ИМЯ / ОПИСАНИЕ ОПЕРАТОРА)
# ==========================================

# Примечание: Отображает текущие данные профиля (админа, оператора или пользователя) и кнопки их изменения.
@router.callback_query(F.data.startswith('update_profile_'))
async def open_profile_update_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    target = callback.data.split('_')[-1]  # admin, operator, user
    user_id = callback.from_user.id

    if target == 'admin':
        profile = await admin_info(user_id, session)
        back_cb = 'admin_cabinet'
        role_label = 'Администратор'
        extra_line = ''
    elif target == 'operator':
        profile = await get_operator_info(user_id, session)
        back_cb = 'op_cabinet'
        role_label = 'Оператор'
        extra_line = f'📝 О себе: <i>{profile.description}</i>\n' if profile else ''
    else:
        profile = await get_subscriber_info(user_id, session)
        back_cb = 'cabinet'
        role_label = 'Абонент'
        extra_line = ''

    await state.update_data(profile_role=target, back_cb=back_cb)

    name = profile.name if profile else callback.from_user.first_name
    phone = profile.phone_number if profile else 'Не указан'

    text = (
        f'📱 <b>Профиль ({role_label})</b>\n\n'
        f'👤 Имя: <b>{name}</b>\n'
        f'📞 Телефон: <code>{phone}</code>\n'
        f'{extra_line}\n'
        'Выберите, какие данные вы хотите обновить:'
    )
    await callback.message.edit_text(
        text,
        reply_markup=profile_update_kb(back_cb, is_operator=(target == 'operator')),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Запускает состояние FSM UpdateProfile.new_phone для ввода нового номера телефона.
@router.callback_query(F.data == 'edit_phone')
async def start_edit_phone(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    back_cb = data.get('back_cb', 'cabinet')
    await state.set_state(UpdateProfile.new_phone)
    await callback.message.edit_text(
        '📞 Введите новый номер телефона (например, <code>+996700123456</code>):',
        reply_markup=cancel_fsm_kb(back_cb),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Валидирует и сохраняет новый номер телефона в БД для выбранной роли.
@router.message(UpdateProfile.new_phone)
async def process_new_phone(message: Message, state: FSMContext, session: AsyncSession):
    digits = ''.join(filter(str.isdigit, message.text or ''))
    if len(digits) < 9 or len(digits) > 15:
        await message.answer('⚠️ Некорректный формат номера! Введите номер от 9 до 15 цифр:')
        return

    data = await state.get_data()
    role = data.get('profile_role', 'user')
    back_cb = data.get('back_cb', 'cabinet')

    await update_phone_number(message.from_user.id, role, message.text.strip(), session)
    await state.clear()

    if back_cb == 'admin_cabinet':
        kb = admin_cabinet_keyboard()
    elif back_cb == 'op_cabinet':
        op = await get_operator_info(message.from_user.id, session)
        kb = operator_cabinet_kb(is_continuing=op.is_working if op else False)
    else:
        kb = user_cabinet_kb()

    await message.answer(
        f'✅ Номер телефона успешно обновлен на <code>{message.text.strip()}</code>!',
        reply_markup=kb,
        parse_mode='HTML'
    )


# Примечание: Запускает состояние FSM UpdateProfile.new_name для смены имени.
@router.callback_query(F.data == 'edit_name')
async def start_edit_name(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    back_cb = data.get('back_cb', 'cabinet')
    await state.set_state(UpdateProfile.new_name)
    await callback.message.edit_text(
        '✏️ Введите новое имя (до 50 символов):',
        reply_markup=cancel_fsm_kb(back_cb)
    )
    await callback.answer()


# Примечание: Сохраняет новое имя в БД и возвращает пользователя в соответствующий кабинет.
@router.message(UpdateProfile.new_name)
async def process_new_name(message: Message, state: FSMContext, session: AsyncSession):
    new_name = (message.text or '').strip()
    if not new_name or len(new_name) > 50:
        await message.answer('⚠️ Имя не должно быть пустым или длиннее 50 символов. Попробуйте снова:')
        return

    data = await state.get_data()
    role = data.get('profile_role', 'user')
    back_cb = data.get('back_cb', 'cabinet')

    await update_profile_name(message.from_user.id, role, new_name, session)
    await state.clear()

    if back_cb == 'admin_cabinet':
        kb = admin_cabinet_keyboard()
    elif back_cb == 'op_cabinet':
        op = await get_operator_info(message.from_user.id, session)
        kb = operator_cabinet_kb(is_continuing=op.is_working if op else False)
    else:
        kb = user_cabinet_kb()

    await message.answer(f'✅ Ваше имя успешно изменено на <b>{new_name}</b>!', reply_markup=kb, parse_mode='HTML')


# Примечание: Запускает состояние FSM UpdateProfile.new_operator_desc для изменения описания оператора.
@router.callback_query(F.data == 'edit_op_desc')
async def start_edit_op_desc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UpdateProfile.new_operator_desc)
    await callback.message.edit_text(
        '📝 Введите новое описание вашего профиля оператора (до 200 символов, его увидят клиенты при подключении):',
        reply_markup=cancel_fsm_kb('op_cabinet')
    )
    await callback.answer()


# Примечание: Сохраняет новое описание оператора в БД и возвращает в кабинет оператора.
@router.message(UpdateProfile.new_operator_desc)
async def process_edit_op_desc(message: Message, state: FSMContext, session: AsyncSession):
    new_desc = (message.text or '').strip()
    if not new_desc or len(new_desc) > 200:
        await message.answer('⚠️ Описание должно содержать от 1 до 200 символов. Попробуйте ещё раз:')
        return

    await update_operator_description(message.from_user.id, new_desc, session)
    await state.clear()
    op = await get_operator_info(message.from_user.id, session)
    await message.answer(
        f'✅ Описание профиля обновлено:\n<i>{new_desc}</i>',
        reply_markup=operator_cabinet_kb(is_continuing=op.is_working if op else False),
        parse_mode='HTML'
    )


# Примечание: Универсальный обработчик кнопки отмены любого активного состояния FSM.
@router.callback_query(F.data.startswith('cancel_fsm_'))
async def cancel_any_fsm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    target = callback.data.replace('cancel_fsm_', '')
    await state.clear()

    if target == 'admin_cabinet':
        kb = admin_cabinet_keyboard()
    elif target == 'op_cabinet':
        op = await get_operator_info(callback.from_user.id, session)
        kb = operator_cabinet_kb(is_continuing=op.is_working if op else False)
    elif target == 'help':
        kb = help_kb()
    else:
        kb = user_cabinet_kb()

    await callback.message.edit_text('❌ Действие отменено.', reply_markup=kb)
    await callback.answer()