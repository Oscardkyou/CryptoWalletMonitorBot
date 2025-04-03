import logging
from aiogram import Router, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from sqlalchemy.future import select

from models.user import User, SubscriptionLevel
from config import MONTHLY_SUBSCRIPTION_PRICE, YEARLY_SUBSCRIPTION_PRICE, PREMIUM_WALLET_LIMIT
from services.db import async_session
from services.payments import create_payment, get_payment_address, check_payment_status, cancel_payment, activate_subscription
from keyboards.common_kb import get_main_keyboard
from keyboards.subscription_kb import get_subscription_plans_keyboard, get_payment_methods_keyboard, get_crypto_selection_keyboard, get_check_payment_keyboard

logger = logging.getLogger(__name__)

# Создаем роутер для обработки подписок
router = Router()

# Обработчик команды /subscribe
@router.message(Command("subscribe"))
@router.message(F.text == "⭐ Подписка")
async def cmd_subscribe(message: Message):
    """Обработчик команды оформления подписки"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже активная подписка
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        
        if not user:
            await message.answer("Ошибка: пользователь не найден. Пожалуйста, используйте /start для начала работы.")
            return
        
        # Если у пользователя уже есть активная премиум подписка
        if user.subscription_level == SubscriptionLevel.premium and user.subscription_expiry and user.subscription_expiry > datetime.utcnow():
            remaining_days = (user.subscription_expiry - datetime.utcnow()).days
            
            await message.answer(
                f"✅ <b>У вас уже есть активная премиум подписка</b>\n\n"
                f"Срок действия: до {user.subscription_expiry.strftime('%d.%m.%Y %H:%M')}\n"
                f"Осталось дней: {remaining_days}\n\n"
                f"С премиум подпиской вы можете добавить до {PREMIUM_WALLET_LIMIT} кошельков для мониторинга."
            )
            return
    
    # Отправляем информацию о тарифах
    await message.answer(
        f"💳 <b>Тарифные планы:</b>\n\n"
        f"<b>Бесплатный план (текущий):</b>\n"
        f"• До 3 кошельков для мониторинга\n"
        f"• Базовые уведомления о транзакциях\n\n"
        f"<b>Премиум план:</b>\n"
        f"• До 20 кошельков для мониторинга\n"
        f"• Расширенные уведомления\n"
        f"• Приоритетная поддержка\n\n"
        f"Выберите тариф для оформления подписки:",
        reply_markup=get_subscription_plans_keyboard()
    )
    
    logger.info(f"Пользователь {user_id} запросил информацию о подписке")

# Обработчик выбора плана подписки
@router.callback_query(F.data.startswith("subscription:"))
async def process_subscription_plan(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора плана подписки"""
    await callback_query.answer()
    
    # Получаем выбранный план
    plan_type = callback_query.data.split(':')[1]
    
    if plan_type == "cancel":
        await callback_query.message.edit_text(
            "❌ Оформление подписки отменено.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Сохраняем выбранный план в состоянии
    await state.update_data(plan_type=plan_type)
    
    # Определяем стоимость подписки
    price = MONTHLY_SUBSCRIPTION_PRICE if plan_type == "monthly" else YEARLY_SUBSCRIPTION_PRICE
    plan_name = "Месячная" if plan_type == "monthly" else "Годовая"
    
    # Предлагаем выбрать способ оплаты
    await callback_query.message.edit_text(
        f"💰 <b>Оплата подписки</b>\n\n"
        f"План: <b>{plan_name} подписка</b>\n"
        f"Стоимость: <b>{price}$</b>\n\n"
        f"Выберите способ оплаты:",
        reply_markup=get_payment_methods_keyboard(plan_type)
    )
    
    logger.info(f"Пользователь {callback_query.from_user.id} выбрал план подписки: {plan_type}")

# Обработчик выбора способа оплаты
@router.callback_query(F.data.startswith("payment:"))
async def process_payment_method(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора способа оплаты"""
    await callback_query.answer()
    
    # Разбираем данные колбэка
    parts = callback_query.data.split(':')
    plan_type = parts[1]
    payment_method = parts[2]
    
    # Если пользователь нажал "Назад"
    if payment_method == "back":
        await callback_query.message.edit_text(
            f"💳 <b>Тарифные планы:</b>\n\n"
            f"<b>Бесплатный план (текущий):</b>\n"
            f"• До 3 кошельков для мониторинга\n"
            f"• Базовые уведомления о транзакциях\n\n"
            f"<b>Премиум план:</b>\n"
            f"• До 20 кошельков для мониторинга\n"
            f"• Расширенные уведомления\n"
            f"• Приоритетная поддержка\n\n"
            f"Выберите тариф для оформления подписки:",
            reply_markup=get_subscription_plans_keyboard()
        )
        return
    
    # Сохраняем способ оплаты в состоянии
    await state.update_data(payment_method=payment_method)
    
    # Определяем стоимость подписки
    price = MONTHLY_SUBSCRIPTION_PRICE if plan_type == "monthly" else YEARLY_SUBSCRIPTION_PRICE
    
    if payment_method == "crypto":
        # Создаем платеж
        payment_id = await create_payment(
            callback_query.from_user.id,
            price,
            "USD",
            "crypto",
            plan_type
        )
        
        if not payment_id:
            await callback_query.message.edit_text(
                "❌ Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Сохраняем ID платежа в состоянии
        await state.update_data(payment_id=payment_id)
        
        # Предлагаем выбрать криптовалюту для оплаты
        await callback_query.message.edit_text(
            f"💰 <b>Оплата криптовалютой</b>\n\n"
            f"Выберите криптовалюту для оплаты:",
            reply_markup=get_crypto_selection_keyboard(payment_id)
        )
        
        logger.info(f"Пользователь {callback_query.from_user.id} выбрал способ оплаты: {payment_method}")
    
    elif payment_method == "card":
        # В нашем примере мы не реализуем оплату картой, просто сообщаем, что эта функция недоступна
        await callback_query.message.edit_text(
            f"💳 <b>Оплата банковской картой</b>\n\n"
            f"Извините, в данный момент оплата банковской картой недоступна.\n"
            f"Пожалуйста, выберите оплату криптовалютой.",
            reply_markup=get_payment_methods_keyboard(plan_type)
        )

# Обработчик выбора криптовалюты
@router.callback_query(F.data.startswith("crypto:"))
async def process_crypto_selection(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора криптовалюты для оплаты"""
    await callback_query.answer()
    
    # Разбираем данные колбэка
    parts = callback_query.data.split(':')
    payment_id = parts[1]
    crypto = parts[2]
    
    # Если пользователь нажал "Назад"
    if crypto == "back":
        # Получаем данные из состояния
        data = await state.get_data()
        plan_type = data.get('plan_type')
        
        # Возвращаемся к выбору способа оплаты
        await callback_query.message.edit_text(
            f"💰 <b>Оплата подписки</b>\n\n"
            f"План: <b>{plan_type} подписка</b>\n"
            f"Выберите способ оплаты:",
            reply_markup=get_payment_methods_keyboard(plan_type)
        )
        return
    
    # Сохраняем выбранную криптовалюту в состоянии
    await state.update_data(crypto=crypto)
    
    # Получаем адрес для оплаты
    result = await get_payment_address(payment_id, crypto)
    
    if result.get("status") == "success":
        address = result.get("address")
        amount = result.get("amount")
        
        # Отображаем информацию для оплаты
        await callback_query.message.edit_text(
            f"💰 <b>Оплата {crypto}</b>\n\n"
            f"Для завершения оплаты, отправьте <b>{amount} {crypto}</b> на следующий адрес:\n\n"
            f"<code>{address}</code>\n\n"
            f"⚠️ <b>Важно:</b>\n"
            f"1. Отправляйте точную сумму\n"
            f"2. Дождитесь подтверждения транзакции\n"
            f"3. Нажмите 'Проверить оплату' после отправки\n\n"
            f"Платеж будет автоматически подтвержден после получения средств.",
            reply_markup=get_check_payment_keyboard(payment_id)
        )
        
        logger.info(f"Пользователь {callback_query.from_user.id} выбрал криптовалюту: {crypto}")
    else:
        # В случае ошибки
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при получении адреса для оплаты. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

# Обработчик проверки статуса платежа
@router.callback_query(F.data.startswith("check_payment:"))
async def process_check_payment(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик проверки статуса платежа"""
    await callback_query.answer()
    
    # Получаем ID платежа из callback_data
    payment_id = callback_query.data.split(':')[1]
    
    # Проверяем статус платежа
    result = await check_payment_status(payment_id)
    
    if result.get("status") == "success":
        payment_status = result.get("payment_status")
        
        if payment_status == "completed":
            # Если платеж завершен успешно
            # Получаем данные из состояния
            data = await state.get_data()
            plan_type = data.get('plan_type')
            
            # Активируем подписку
            async with async_session() as session:
                success = await activate_subscription(
                    session,
                    callback_query.from_user.id,
                    payment_id,
                    plan_type
                )
                
                if success:
                    # Определяем срок действия подписки
                    subscription_end = datetime.utcnow()
                    if plan_type == "monthly":
                        subscription_end += timedelta(days=30)
                    else:
                        subscription_end += timedelta(days=365)
                    
                    # Отправляем сообщение об успешной активации
                    await callback_query.message.edit_text(
                        f"✅ <b>Подписка успешно активирована!</b>\n\n"
                        f"Тип подписки: <b>Премиум</b>\n"
                        f"Срок действия: до {subscription_end.strftime('%d.%m.%Y %H:%M')}\n\n"
                        f"Теперь вы можете добавить до 20 кошельков для мониторинга.",
                        reply_markup=get_main_keyboard()
                    )
                    
                    # Очищаем состояние
                    await state.clear()
                    
                    logger.info(f"Подписка активирована для пользователя {callback_query.from_user.id}")
                else:
                    # В случае ошибки при активации
                    await callback_query.message.edit_text(
                        "❌ Произошла ошибка при активации подписки. Пожалуйста, обратитесь в поддержку.",
                        reply_markup=get_main_keyboard()
                    )
        elif payment_status == "pending":
            # Если платеж все еще в обработке
            await callback_query.message.edit_text(
                f"⏳ <b>Платеж в обработке</b>\n\n"
                f"Ваш платеж пока не подтвержден. Пожалуйста, подождите или проверьте позже.\n\n"
                f"Если вы только что отправили средства, может потребоваться несколько минут для подтверждения транзакции.",
                reply_markup=get_check_payment_keyboard(payment_id)
            )
        else:
            # Если платеж отменен или произошла ошибка
            await callback_query.message.edit_text(
                f"❌ <b>Ошибка оплаты</b>\n\n"
                f"Статус платежа: {payment_status}\n\n"
                f"Пожалуйста, попробуйте снова или обратитесь в поддержку.",
                reply_markup=get_main_keyboard()
            )
    else:
        # В случае ошибки при проверке статуса
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при проверке статуса платежа. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

# Обработчик отмены платежа
@router.callback_query(F.data.startswith("cancel_payment:"))
async def process_cancel_payment(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик отмены платежа"""
    await callback_query.answer()
    
    # Получаем ID платежа из callback_data
    payment_id = callback_query.data.split(':')[1]
    
    # Отменяем платеж
    result = await cancel_payment(payment_id)
    
    if result.get("status") == "success":
        await callback_query.message.edit_text(
            "✅ Платеж успешно отменен.",
            reply_markup=get_main_keyboard()
        )
        
        # Очищаем состояние
        await state.clear()
        
        logger.info(f"Пользователь {callback_query.from_user.id} отменил платеж {payment_id}")
    else:
        # В случае ошибки при отмене
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при отмене платежа. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

# Функция для активации бесплатной тестовой подписки (только для тестирования)
@router.message(Command("test_premium"))
async def cmd_test_premium(message: Message):
    """Активирует премиум подписку для тестирования (временная функция)"""
    user_id = message.from_user.id
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        
        if not user:
            await message.answer("Ошибка: пользователь не найден. Пожалуйста, используйте /start для начала работы.")
            return
        
        # Активируем премиум подписку на 1 день для тестирования
        user.subscription_level = SubscriptionLevel.premium
        user.subscription_expiry = datetime.utcnow() + timedelta(days=1)
        
        await session.commit()
        
        await message.answer(
            f"✅ <b>Тестовая премиум подписка активирована!</b>\n\n"
            f"Срок действия: 1 день (до {user.subscription_expiry.strftime('%d.%m.%Y %H:%M')})\n\n"
            f"Теперь вы можете добавить до 20 кошельков для мониторинга."
        )
        
        logger.info(f"Тестовая премиум подписка активирована для пользователя {user_id}")

def register_subscription_handlers(dp: Dispatcher):
    """Регистрация обработчиков для работы с подписками"""
    dp.include_router(router) 