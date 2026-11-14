# ==========================================
# ФАЙЛ app/keyboards/inline.py
# ==========================================
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ==========================================
# 1. ВХОД И ПРОФИЛЬ
# ==========================================

# Примечание: Клавиатура выбора роли при старте для админов и операторов.
def log_in_as(role: str):
    role_title = 'администратор' if role == 'admin' else 'оператор'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='👤 Зайти как пользователь', callback_data='log_in_as_user')],
        [InlineKeyboardButton(text=f'🔐 Зайти как {role_title}', callback_data=f'log_in_as_{role}')]
    ])


# Примечание: Кнопка входа в кабинет после смены пароля.
def come_in_cabinet(role: str = 'admin'):
    cb_data = 'admin_cabinet' if role == 'admin' else 'op_cabinet'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚪 Зайти в личный кабинет', callback_data=cb_data)]
    ])


# Примечание: Клавиатура редактирования личных данных (номера телефона, имени, описания для оператора).
def profile_update_kb(back_callback: str, is_operator: bool = False):
    buttons = [
        [InlineKeyboardButton(text='📞 Изменить номер телефона', callback_data='edit_phone')],
        [InlineKeyboardButton(text='✏️ Изменить имя', callback_data='edit_name')],
    ]
    if is_operator:
        buttons.append([InlineKeyboardButton(text='📝 Изменить описание (о себе)', callback_data='edit_op_desc')])
    buttons.append([InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Универсальная кнопка отмены любого шага FSM.
def cancel_fsm_kb(back_callback: str = 'cabinet'):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❌ Отмена', callback_data=f'cancel_fsm_{back_callback}')]
    ])


# ==========================================
# 2. КЛАВИАТУРЫ АДМИНИСТРАТОРА
# ==========================================

# Примечание: Главное меню кабинета администратора.
def admin_cabinet_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔑 Сменить пароль', callback_data='change_password')],
        [InlineKeyboardButton(text='📱 Обновить данные (телефон/имя)', callback_data='update_profile_admin')],
        [InlineKeyboardButton(text='🛡 Администраторы', callback_data='admin_info')],
        [InlineKeyboardButton(text='🎧 Операторы', callback_data='operator_info')],
        [InlineKeyboardButton(text='👥 Пользователи и FAQ', callback_data='users_info_admin')],
        [InlineKeyboardButton(text='👤 Зайти как пользователь', callback_data='log_in_as_user')]
    ])


# Примечание: Список активных администраторов (передает telegram_id).
def administrators_kb(admins):
    buttons = [
        [InlineKeyboardButton(text=f'🛡 {admin.name}', callback_data=f'admin_id_{admin.telegram_id}')]
        for admin in admins if admin.is_active
    ]
    buttons.extend([
        [InlineKeyboardButton(text='🚫 Заблокированные администраторы', callback_data='blocked_admins')],
        [InlineKeyboardButton(text='➕ Добавить администратора', callback_data='admin_add_invite')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Список заблокированных администраторов (передает telegram_id).
def blocked_admins(admins):
    buttons = [
        [InlineKeyboardButton(text=f'🔒 {admin.name}', callback_data=f'admin_id_{admin.telegram_id}')]
        for admin in admins if not admin.is_active
    ]
    buttons.extend([
        [InlineKeyboardButton(text='🔓 Разблокировать всех', callback_data='unblock_all')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data='admin_info')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Управление карточкой активного администратора по telegram_id.
def administrator_kb_active(admin):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚫 Заблокировать администратора', callback_data=f'admin-{admin.telegram_id}')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data='admin_info')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Управление карточкой заблокированного администратора по telegram_id.
def administrator_kb_inactive(admin):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔓 Разблокировать администратора', callback_data=f'admin_unblock_{admin.telegram_id}')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data='blocked_admins')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Возврат к списку администраторов.
def block_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⬅️ К списку администраторов', callback_data='admin_info')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Список всех операторов (передает telegram_id).
def operators_kb(operators):
    buttons = [
        [InlineKeyboardButton(text=f'🎧 {operator.name} (⭐ {operator.rating})', callback_data=f'op_id_{operator.telegram_id}')]
        for operator in operators
    ]
    buttons.extend([
        [InlineKeyboardButton(text='➕ Добавить оператора', callback_data='operator+')],
        [InlineKeyboardButton(text='🏆 Рейтинг операторов', callback_data='operators_rating')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Управление конкретным оператором по его telegram_id.
def operator_kb(operator):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📝 Посмотреть отзывы на оператора', callback_data=f'operator_review_{operator.telegram_id}')],
        [InlineKeyboardButton(text='❌ Убрать с роли оператора', callback_data=f'operator-{operator.telegram_id}')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data='operator_info')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Кнопки возврата к списку операторов.
def back_to_operators_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⬅️ К списку операторов', callback_data='operator_info')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Меню управления пользователями, тарифами, FAQ и отзывами для администратора.
def admin_users_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📊 Рейтинг тарифов', callback_data='tariffs_info')],
        [InlineKeyboardButton(text='❓ Частые вопросы (FAQ)', callback_data='users_questions')],
        [InlineKeyboardButton(text='➕ Добавить частый вопрос', callback_data='add_faq')],
        [InlineKeyboardButton(text='🌟 Отзывы пользователей', callback_data='users_review')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# Примечание: Возврат в меню пользователей для администратора.
def back_to_admin_users_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⬅️ Назад в меню пользователей', callback_data='users_info_admin')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='admin_cabinet')]
    ])


# ==========================================
# 3. КЛАВИАТУРЫ ОПЕРАТОРА И ЖИВОГО ЧАТА
# ==========================================

# Примечание: Главное меню кабинета оператора со статистикой, отзывами, очередью и настройками профиля.
def operator_cabinet_kb(is_continuing: bool = False):
    start_text = '▶️ Продолжить смену' if is_continuing else '🟢 Начать работу (выйти на линию)'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=start_text, callback_data='start_work')],
        [InlineKeyboardButton(text='📊 Моя статистика и анкета', callback_data='op_my_stats')],
        [InlineKeyboardButton(text='📝 Посмотреть отзывы на меня', callback_data='reviews')],
        [InlineKeyboardButton(text='👥 Абоненты и очередь', callback_data='users_info_op')],
        [InlineKeyboardButton(text='📱 Обновить данные (телефон/имя/о себе)', callback_data='update_profile_operator')],
        [InlineKeyboardButton(text='🔑 Сменить пароль', callback_data='change_password')],
        [InlineKeyboardButton(text='👤 Зайти как пользователь', callback_data='log_in_as_user')]
    ])


# Примечание: Панель оператора на активной рабочей смене.
def operator_wait_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💬 Следующий чат (взять из очереди)', callback_data='next_chat')],
        [InlineKeyboardButton(text='🔄 Обновить статус очереди', callback_data='refresh_queue')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='op_cabinet')],
        [InlineKeyboardButton(text='🔴 Завершить рабочий день', callback_data='finish_work')]
    ])


# Примечание: Кнопка завершения активного чата (доступна и оператору, и клиенту).
def finish_chat_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🛑 Завершить чат', callback_data='end_chat')]
    ])


# ==========================================
# 4. КЛАВИАТУРЫ ПОЛЬЗОВАТЕЛЯ, ИИ И ОТЗЫВОВ
# ==========================================

# Примечание: Главное меню личного кабинета абонента.
def user_cabinet_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💰 Мой баланс', callback_data='balance')],
        [InlineKeyboardButton(text='🔄 Сменить тариф', callback_data='tariffs')],
        [InlineKeyboardButton(text='📱 Мои данные (телефон/имя)', callback_data='update_profile_user')],
        [InlineKeyboardButton(text='🆘 Помощь и поддержка', callback_data='help')]
    ])


# Примечание: Список доступных тарифов для подключения.
def get_tariffs_kb(tariffs):
    buttons = [
        [InlineKeyboardButton(text=f'📦 {tarif[1]}', callback_data=f'tarif_{tarif[0]}')]
        for tarif in tariffs
    ]
    buttons.append([InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Подтверждение смены тарифа.
def agree_form_kb(tariff_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='✅ Да', callback_data=f'yes_{tariff_id}'),
            InlineKeyboardButton(text='❌ Нет', callback_data='tariffs')
        ],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')]
    ])


# Примечание: Управление балансом абонента.
def balance_action_kb(is_frozen: bool = False):
    freeze_text = '🔥 Разморозить баланс' if is_frozen else '❄️ Заморозить баланс'
    freeze_cb = 'unfreeze' if is_frozen else 'freeze'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💳 Пополнить', callback_data='replenish_0')],
        [InlineKeyboardButton(text=freeze_text, callback_data=freeze_cb)],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')]
    ])


# Примечание: Регулировка суммы пополнения баланса.
def replenish_up_kb(cost: int, back_command: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='+1', callback_data=f'replenish_{cost + 1}'),
            InlineKeyboardButton(text='-1', callback_data=f'replenish_{cost - 1}')
        ],
        [
            InlineKeyboardButton(text='+10', callback_data=f'replenish_{cost + 10}'),
            InlineKeyboardButton(text='-10', callback_data=f'replenish_{cost - 10}')
        ],
        [
            InlineKeyboardButton(text='+100', callback_data=f'replenish_{cost + 100}'),
            InlineKeyboardButton(text='-100', callback_data=f'replenish_{cost - 100}')
        ],
        [InlineKeyboardButton(text=f'✅ Подтвердить пополнение ({cost} сом)', callback_data=f'balance_up_{cost}')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data=back_command)],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')]
    ])


# Примечание: Меню раздела помощи пользователя.
def help_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='❓ Частые вопросы (FAQ)', callback_data='questions')],
        [InlineKeyboardButton(text='🎧 Связь с оператором', callback_data='operator')],
        [InlineKeyboardButton(text='🤖 Консультация с ИИ-ботом', callback_data='chatbot')],
        [InlineKeyboardButton(text='📝 Оставить отзыв оператору', callback_data='leave_review')],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')]
    ])


# Примечание: Клавиатура при отсутствии свободных операторов.
def wait_operator_kb(back_command: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⏳ Встать в очередь ожидания', callback_data='operator_wait')],
        [InlineKeyboardButton(text='🤖 Спросить ИИ-помощника', callback_data='chatbot')],
        [InlineKeyboardButton(text='⬅️ Вернуться назад', callback_data=back_command)],
        [InlineKeyboardButton(text='🔙 Вернуться в кабинет', callback_data='cabinet')]
    ])


# Примечание: Клавиатура для клиента, который находится в очереди ожидания оператора.
def in_queue_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🤖 Пока жду — спросить ИИ-бота', callback_data='chatbot')],
        [InlineKeyboardButton(text='❌ Покинуть очередь ожидания', callback_data='leave_queue')]
    ])


# Примечание: Клавиатура управления диалогом с ИИ-помощником.
def chatbot_active_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎧 Переключить на живого оператора', callback_data='operator')],
        [InlineKeyboardButton(text='🛑 Завершить диалог с ИИ', callback_data='stop_chatbot')]
    ])


# Примечание: Клавиатура выбора оператора, если пользователь нажал «Оставить отзыв» из меню помощи.
def choose_operator_for_review_kb(operators):
    buttons = [
        [InlineKeyboardButton(text=f'🎧 {op.name} (⭐ {op.rating})', callback_data=f'select_rev_op_{op.telegram_id}')]
        for op in operators
    ]
    buttons.append([InlineKeyboardButton(text='🔙 Назад в раздел помощи', callback_data='help')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Примечание: Клавиатура оценки конкретного оператора от 1 до 5 звезд (появляется сразу после завершения чата).
def rate_operator_kb(operator_telegram_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text='1 ⭐', callback_data=f'rate_op_{operator_telegram_id}_1'),
            InlineKeyboardButton(text='2 ⭐', callback_data=f'rate_op_{operator_telegram_id}_2'),
            InlineKeyboardButton(text='3 ⭐', callback_data=f'rate_op_{operator_telegram_id}_3'),
            InlineKeyboardButton(text='4 ⭐', callback_data=f'rate_op_{operator_telegram_id}_4'),
            InlineKeyboardButton(text='5 ⭐', callback_data=f'rate_op_{operator_telegram_id}_5'),
        ],
        [InlineKeyboardButton(text='Пропустить оценку ⏭', callback_data='cabinet')]
    ])


# Примечание: Кнопка пропуска текстового комментария (если клиент хочет оставить только звезды).
def skip_review_text_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⏭ Отправить оценку без текста', callback_data='skip_review_text')]
    ])