# ==========================================
# ФАЙЛ app/hundlers/user.py
# ==========================================
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.request import (
    add_subscriber, get_user_balance, get_all_tariffs, get_tarif_info,
    change_tariff, freeze_check, get_and_occupy_free_operator,
    invites_use, get_all_faqs, add_review, waiting, leave_wait_queue,
    get_working_operators, get_client_card_text, get_operators_info,
    get_operator_info, build_ai_context, get_active_chat_info
)
from app.keyboards.inline import (
    user_cabinet_kb, balance_action_kb, get_tariffs_kb, agree_form_kb,
    help_kb, wait_operator_kb, admin_cabinet_keyboard, operator_cabinet_kb,
    finish_chat_kb, in_queue_kb, chatbot_active_kb,
    choose_operator_for_review_kb, rate_operator_kb, skip_review_text_kb
)
from app.states.states import ChatModes, LeaveReview
from app.utils.utils import ask_gemini_ai

router = Router()


# ==========================================
# 1. РЕГИСТРАЦИЯ, ИНВАЙТЫ (/admin), БАЛАНС И ТАРИФЫ
# ==========================================

# Примечание: Регистрирует пользователя по отправленному контакту в БД и открывает личный кабинет.
@router.message(F.contact)
async def register(message: Message, session: AsyncSession):
    number = message.contact.phone_number
    user_id = message.from_user.id
    name = message.from_user.first_name or 'Абонент'

    is_new = await add_subscriber(telegram_id=user_id, phone_number=number, session=session, name=name)

    if is_new:
        await message.answer(
            '🎉 Регистрация прошла успешно! Ваш стартовый баланс: 500 сом.',
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer('Вы успешно вошли в свой аккаунт!', reply_markup=ReplyKeyboardRemove())

    await message.answer('Ваш личный кабинет:', reply_markup=user_cabinet_kb())


# Примечание: Принимает инвайт-код из команды /admin, активирует его в БД и выдает кабинет админа или оператора.
@router.message(Command('admin'))
async def register_as_admin(message: Message, command: CommandObject, session: AsyncSession):
    invite_code = command.args
    if not invite_code:
        await message.answer(
            '⚠️ Укажите инвайт-код после команды.\nПример: <code>/admin КОД</code>',
            parse_mode='HTML'
        )
        return

    success, alert_text, assigned_role = await invites_use(
        invite_code=invite_code.strip(),
        role=None,
        user_id=message.from_user.id,
        session=session
    )

    if not success:
        await message.answer(alert_text)
        return

    if assigned_role == 'admin':
        await message.answer(alert_text, reply_markup=admin_cabinet_keyboard())
    elif assigned_role == 'operator':
        await message.answer(alert_text, reply_markup=operator_cabinet_kb())


# Примечание: Возвращает пользователя в главное меню личного кабинета.
@router.callback_query(F.data == 'cabinet')
async def my_cabinet(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('Ваш личный кабинет:', reply_markup=user_cabinet_kb())
    await callback.answer()


# Примечание: Запрашивает из БД баланс и статус заморозки счета абонента и отображает их.
@router.callback_query(F.data == 'balance')
async def my_balance(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    is_frozen = await freeze_check(user_id, session)
    balance = await get_user_balance(user_id, session)
    status_str = '\n❄️ <i>Ваш счёт сейчас заморожен</i>' if is_frozen else ''
    await callback.message.edit_text(
        f'💰 Ваш баланс: <b>{balance} сом</b>.{status_str}',
        reply_markup=balance_action_kb(is_frozen=is_frozen),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Загружает список всех тарифов из БД и выводит их в виде инлайн-кнопок.
@router.callback_query(F.data == 'tariffs')
async def get_tarif_list(callback: CallbackQuery, session: AsyncSession):
    tariffs = await get_all_tariffs(session)
    await callback.message.edit_text('📦 Доступные тарифы:', reply_markup=get_tariffs_kb(tariffs))
    await callback.answer()


# Примечание: Показывает подробное описание выбранного тарифа и предлагает сменить его.
@router.callback_query(F.data.startswith('tarif_'))
async def more_info(callback: CallbackQuery, session: AsyncSession):
    tarif_id = int(callback.data.split('_')[1])
    tarif_info = await get_tarif_info(tarif_id, session)
    text = (
        f'📦 <b>Название тарифа:</b> {tarif_info.name}\n'
        f'💵 <b>Стоимость (в месяц):</b> {tarif_info.monthly_price} сом\n'
        f'🌐 <b>Интернет:</b> {tarif_info.gb_limit} ГБ\n'
        f'📞 <b>Минуты:</b> {tarif_info.minutes_limit} мин.\n\n'
        'Хотите ли Вы сменить свой тариф на этот?'
    )
    await callback.message.edit_text(text, reply_markup=agree_form_kb(tarif_id), parse_mode='HTML')
    await callback.answer()


# Примечание: Выполняет смену тарифа абонента в БД со списанием абонентской платы.
@router.callback_query(F.data.startswith('yes_'))
async def get_agree(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    new_tarif_id = int(callback.data.split('_')[1])
    alert_bool, alert_text = await change_tariff(user_id, new_tarif_id, session)
    await callback.message.edit_text(alert_text, reply_markup=user_cabinet_kb())
    await callback.answer()


# ==========================================
# 2. РАЗДЕЛ ПОМОЩИ, СВЯЗЬ С ОПЕРАТОРОМ И ОЧЕРЕДЬ
# ==========================================

# Примечание: Открывает раздел помощи абонента.
@router.callback_query(F.data == 'help')
async def help_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text('🆘 Раздел помощи и поддержки:', reply_markup=help_kb())
    await callback.answer()


# Примечание: Выгружает список частых вопросов и ответов из таблицы Faq в БД.
@router.callback_query(F.data == 'questions')
async def faq_menu(callback: CallbackQuery, session: AsyncSession):
    faqs = await get_all_faqs(session)
    if not faqs:
        text = '📚 Список частых вопросов пока пуст.'
    else:
        lines = ['📚 <b>Частые вопросы (FAQ):</b>\n']
        for idx, item in enumerate(faqs, start=1):
            lines.append(f'<b>{idx}. {item.question}</b>\n💬 {item.answer}\n')
        text = '\n'.join(lines)

    await callback.message.edit_text(text, reply_markup=help_kb(), parse_mode='HTML')
    await callback.answer()


# Примечание: Ищет свободного оператора на смене и соединяет его с клиентом, либо предлагает встать в очередь.
@router.callback_query(F.data == 'operator')
async def call_operator(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    user_id = callback.from_user.id

    # Проверяем, не в активном ли чате уже пользователь
    existing_chat = await get_active_chat_info(user_id, session)
    if existing_chat:
        await callback.answer('Вы уже находитесь в активном чате с оператором!', show_alert=True)
        return

    operator = await get_and_occupy_free_operator(user_id, session)
    if operator is None:
        await callback.message.edit_text(
            '⏳ <b>На данный момент все операторы заняты или не на смене.</b>\n'
            'Вы можете встать в живую очередь ожидания или задать вопрос нашему ИИ-помощнику:',
            reply_markup=wait_operator_kb('help'),
            parse_mode='HTML'
        )
        await callback.answer()
        return

    await state.set_state(ChatModes.operator)
    card = await get_client_card_text(user_id, session)

    # Сообщаем клиенту о подключении оператора
    await callback.message.edit_text(
        f'🎧 <b>К вам подключился оператор {operator.name}!</b>\n'
        f'ℹ️ <i>{operator.description}</i> (Рейтинг: ⭐ {operator.rating})\n\n'
        'Напишите ваш вопрос следующим сообщением:',
        reply_markup=finish_chat_kb(),
        parse_mode='HTML'
    )

    # Мгновенно уведомляем оператора и присылаем карточку клиента
    try:
        await bot.send_message(
            chat_id=operator.telegram_id,
            text=(
                f'🔔 <b>К вам подключился новый клиент!</b>\n\n{card}\n\n'
                '✍️ <i>Отправьте сообщение в этот чат, чтобы ответить клиенту:</i>'
            ),
            reply_markup=finish_chat_kb(),
            parse_mode='HTML'
        )
    except Exception:
        pass

    await callback.answer()


# Примечание: Помещает клиента в очередь ожидания Waiter и уведомляет всех работающих операторов.
@router.callback_query(F.data == 'operator_wait')
async def put_user_in_wait_queue(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or 'Абонент'
    queue_pos = await waiting(user_id=user_id, user_name=user_name, session=session)
    await state.set_state(ChatModes.wait_queue)

    await callback.message.edit_text(
        f'⏳ <b>Вы добавлены в очередь ожидания!</b>\n'
        f'Ваша позиция в очереди: <b>#{queue_pos}</b>.\n\n'
        'Как только оператор освободится и возьмет чат, вам придет уведомление.',
        reply_markup=in_queue_kb(),
        parse_mode='HTML'
    )

    # Уведомляем работающих операторов о новом человеке в очереди
    working_ops = await get_working_operators(session)
    for op in working_ops:
        try:
            await bot.send_message(
                chat_id=op.telegram_id,
                text=f'🔔 Новый клиент <b>{user_name}</b> встал в очередь ожидания (всего в очереди: {queue_pos}).',
                parse_mode='HTML'
            )
        except Exception:
            pass

    await callback.answer()


# Примечание: Удаляет клиента из очереди ожидания Waiter по кнопке leave_queue.
@router.callback_query(F.data == 'leave_queue')
async def user_leave_queue(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await leave_wait_queue(callback.from_user.id, session)
    await state.clear()
    await callback.message.edit_text(
        '❌ Вы покинули очередь ожидания.',
        reply_markup=help_kb()
    )
    await callback.answer()


# ==========================================
# 3. ОБЩЕНИЕ С ИИ-ПОМОЩНИКОМ (GEMINI AI)
# ==========================================

# Примечание: Переключает пользователя в режим живого диалога с ИИ-ботом (ChatModes.chatbot).
@router.callback_query(F.data == 'chatbot')
async def start_chatbot(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatModes.chatbot)
    await callback.message.edit_text(
        '🤖 <b>ИИ-консультант подключен!</b>\n\n'
        'Я знаю всё о наших тарифах, правилах и вашем текущем балансе.\n'
        'Напишите ваш вопрос следующим сообщением:',
        reply_markup=chatbot_active_kb(),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Завершает диалог с ИИ-помощником и возвращает пользователя в меню помощи.
@router.callback_query(F.data == 'stop_chatbot')
async def stop_chatbot_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        '🛑 Диалог с ИИ-помощником завершен.',
        reply_markup=help_kb()
    )
    await callback.answer()


# Примечание: Обрабатывает вопросы пользователя в режиме ChatModes.chatbot, передавая контекст БД в Gemini AI.
@router.message(ChatModes.chatbot)
async def process_chatbot_message(message: Message, session: AsyncSession):
    if not message.text:
        await message.answer('🤖 Пожалуйста, напишите ваш вопрос текстом:', reply_markup=chatbot_active_kb())
        return

    wait_msg = await message.answer('🤖 <i>ИИ-помощник печатает ответ...</i>', parse_mode='HTML')
    db_context = await build_ai_context(message.from_user.id, session)
    ai_reply = await ask_gemini_ai(user_question=message.text, db_context=db_context)

    await wait_msg.edit_text(
        f'🤖 <b>ИИ-консультант:</b>\n\n{ai_reply}',
        reply_markup=chatbot_active_kb()
    )


# ==========================================
# 4. ОЦЕНКА И ОТЗЫВЫ НА КОНКРЕТНОГО ОПЕРАТОРА
# ==========================================

# Примечание: Позволяет выбрать оператора для отзыва вручную из раздела помощи.
@router.callback_query(F.data == 'leave_review')
async def leave_review_menu(callback: CallbackQuery, session: AsyncSession):
    operators = await get_operators_info(session)
    if not operators:
        await callback.answer('В системе пока нет зарегистрированных операторов.', show_alert=True)
        return

    await callback.message.edit_text(
        '📝 <b>Оставить отзыв оператору</b>\n\n'
        'Обычно бот автоматически предлагает оценить оператора сразу после завершения чата.\n'
        'Но вы также можете выбрать оператора из списка ниже:',
        reply_markup=choose_operator_for_review_kb(operators),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Открывает кнопки от 1 до 5 звезд для выбранного вручную оператора.
@router.callback_query(F.data.startswith('select_rev_op_'))
async def select_operator_for_review(callback: CallbackQuery, session: AsyncSession):
    op_tg_id = int(callback.data.split('_')[-1])
    operator = await get_operator_info(op_tg_id, session)
    op_name = operator.name if operator else 'Оператор'

    await callback.message.edit_text(
        f'⭐ Оцените работу оператора <b>{op_name}</b> от 1 до 5 звезд:',
        reply_markup=rate_operator_kb(op_tg_id),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Сохраняет выбранную оценку (1-5 звезд) для конкретного оператора и запрашивает текст отзыва.
@router.callback_query(F.data.startswith('rate_op_'))
async def rate_operator_stars(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_')
    op_tg_id = int(parts[2])
    rating = int(parts[3])

    await state.update_data(review_operator_id=op_tg_id, review_rating=rating)
    await state.set_state(LeaveReview.review_text)

    await callback.message.edit_text(
        f'⭐ Вы поставили оценку: <b>{rating}/5</b>.\n\n'
        '✍️ Напишите текстовый комментарий о работе оператора следующим сообщением '
        '(или нажмите кнопку ниже, чтобы отправить оценку без текста):',
        reply_markup=skip_review_text_kb(),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Сохраняет оценку оператора без текста (по кнопке «Отправить оценку без текста»), пересчитывает рейтинг и уведомляет оператора.
@router.callback_query(LeaveReview.review_text, F.data == 'skip_review_text')
async def skip_review_text_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    op_tg_id = data.get('review_operator_id', 0)
    rating = data.get('review_rating', 5)

    await add_review(
        user_id=callback.from_user.id,
        rating=rating,
        review_text='Без комментария',
        session=session,
        operator_id=op_tg_id
    )
    await state.clear()

    await callback.message.edit_text(
        f'🎉 Спасибо! Ваша оценка ({rating} ⭐) сохранена и учтена в рейтинге оператора.',
        reply_markup=user_cabinet_kb()
    )

    try:
        await bot.send_message(
            chat_id=op_tg_id,
            text=f'🌟 Клиент оценил диалог с вами на <b>{rating}/5 ⭐</b> (без текстового комментария).',
            parse_mode='HTML'
        )
    except Exception:
        pass

    await callback.answer()


# Примечание: Принимает текст отзыва от клиента, сохраняет его в БД, пересчитывает рейтинг оператора и отправляет уведомление оператору.
@router.message(LeaveReview.review_text)
async def process_review_text_message(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    if not message.text:
        await message.answer('Пожалуйста, отправьте отзыв текстом или нажмите кнопку «Отправить оценку без текста».')
        return

    data = await state.get_data()
    op_tg_id = data.get('review_operator_id', 0)
    rating = data.get('review_rating', 5)
    review_text = message.text.strip()

    await add_review(
        user_id=message.from_user.id,
        rating=rating,
        review_text=review_text,
        session=session,
        operator_id=op_tg_id
    )
    await state.clear()

    await message.answer(
        f'🎉 Спасибо за ваш отзыв и оценку ({rating} ⭐)! Рейтинг оператора обновлен.',
        reply_markup=user_cabinet_kb()
    )

    try:
        await bot.send_message(
            chat_id=op_tg_id,
            text=(
                f'🌟 <b>Вы получили новый отзыв от клиента!</b>\n'
                f'⭐ Оценка: <b>{rating}/5</b>\n'
                f'💬 Отзыв: <i>{review_text}</i>'
            ),
            parse_mode='HTML'
        )
    except Exception:
        pass