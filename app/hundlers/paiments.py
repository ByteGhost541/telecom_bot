# ==========================================
# ФАЙЛ app/hundlers/paiments.py
# ==========================================
from aiogram import Router, F
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from config import PAYMENT_TOKEN
from app.keyboards.inline import replenish_up_kb, user_cabinet_kb
from app.database.request import freeze_check, freezeTrue, freezeFalse, top_up

router = Router()


# Примечание: Замораживает баланс пользователя в БД, если он еще не заморожен.
@router.callback_query(F.data == 'freeze')
async def freeze(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    if await freeze_check(user_id, session):
        await callback.answer('Ваш счёт уже заморожен!', show_alert=True)
        return
    await freezeTrue(user_id, session)
    await callback.message.edit_text('❄️ Ваш счёт успешно заморожен!', reply_markup=user_cabinet_kb())
    await callback.answer()


# Примечание: Размораживает баланс пользователя в БД, если он был заморожен.
@router.callback_query(F.data == 'unfreeze')
async def unfreeze(callback: CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id
    if not await freeze_check(user_id, session):
        await callback.answer('Ваш счёт уже разморожен!', show_alert=True)
        return
    await freezeFalse(user_id, session)
    await callback.message.edit_text('🔥 Ваш счёт успешно разморожен!', reply_markup=user_cabinet_kb())
    await callback.answer()


# Примечание: Обновляет сумму пополнения на клавиатуре при нажатии кнопок +1/-1, +10/-10, +100/-100.
@router.callback_query(F.data.startswith('replenish_'))
async def replenish(callback: CallbackQuery):
    cost = int(callback.data.split('_')[1])
    if cost < 0:
        cost = 0
    await callback.message.edit_text(
        f'💳 Сумма пополнения: <b>{cost} сом</b>',
        reply_markup=replenish_up_kb(cost, 'balance'),
        parse_mode='HTML'
    )
    await callback.answer()


# Примечание: Формирует и отправляет платежный счет (invoice) пользователю через Telegram Payments.
@router.callback_query(F.data.startswith('balance_up_'))
async def replanish_proccess(callback: CallbackQuery, session: AsyncSession):
    cost = int(callback.data.split('_')[2])
    user_id = callback.from_user.id
    if cost <= 0:
        await callback.answer('Сумма пополнения должна быть больше нуля!', show_alert=True)
        return

    if await freeze_check(user_id, session):
        await callback.answer('❄️ Ваш счёт заморожен! Сначала разморозьте его.', show_alert=True)
        return

    prices = [LabeledPrice(label=f'Пополнение на {cost} сом', amount=cost * 100)]
    await callback.message.answer_invoice(
        title='Пополнение баланса',
        description='Пополнение лицевого счёта абонента в боте',
        payload=f'deposit_{cost}',
        provider_token=PAYMENT_TOKEN,
        currency='KGS',
        prices=prices
    )
    await callback.answer()


# Примечание: Подтверждает готовность к проведению транзакции перед списанием средств.
@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery, session: AsyncSession):
    user_id = pre_checkout_query.from_user.id
    if await freeze_check(user_id, session):
        await pre_checkout_query.answer(ok=False, error_message='Ваш счёт заморожен')
        return
    await pre_checkout_query.answer(ok=True)


# Примечание: Зачисляет средства на баланс абонента в БД после успешной оплаты.
@router.message(F.successful_payment)
async def proccess_successful_payment(message: Message, session: AsyncSession):
    amount = message.successful_payment.total_amount // 100
    user_id = message.from_user.id
    await top_up(user_id, amount, session)
    await message.answer(
        f'✅ Баланс успешно пополнен на <b>{amount} сом</b>!',
        reply_markup=user_cabinet_kb(),
        parse_mode='HTML'
    )