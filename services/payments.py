import logging
import uuid
import aiohttp
import json
from datetime import datetime, timedelta

from config import CRYPTO_PAYMENT_API_KEY, CRYPTO_PAYMENT_API_SECRET
from models.subscription import Subscription, SubscriptionStatus

logger = logging.getLogger(__name__)

# В учебных целях используем имитацию API платежной системы
# В реальном приложении здесь должны быть настоящие запросы к API платежных систем

# Имитируем хранилище платежей для тестирования
MOCK_PAYMENTS = {}

async def create_payment(user_id, amount, currency, payment_method, plan_type):
    """Создает новый платеж"""
    try:
        # Генерируем уникальный ID платежа
        payment_id = str(uuid.uuid4())
        
        # Создаем запись о платеже в нашем мок-хранилище
        MOCK_PAYMENTS[payment_id] = {
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "plan_type": plan_type
        }
        
        logger.info(f"Создан новый платеж: {payment_id} для пользователя {user_id}")
        
        return payment_id
    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        return None

async def get_payment_address(payment_id, crypto_currency):
    """Возвращает адрес для оплаты криптовалютой"""
    try:
        # Это мок-функция, в реальном приложении здесь будет запрос к API
        # для получения адреса кошелька для оплаты
        
        # Имитируем разные адреса для разных криптовалют
        addresses = {
            "BTC": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "ETH": "0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
            "USDT": "TNPeeaaFB7K9cmo4uQpcU32zBp8RJVMN9H"
        }
        
        # Обновляем информацию о платеже в нашем мок-хранилище
        if payment_id in MOCK_PAYMENTS:
            MOCK_PAYMENTS[payment_id]["crypto_currency"] = crypto_currency
            MOCK_PAYMENTS[payment_id]["address"] = addresses.get(crypto_currency)
            
            return {
                "status": "success",
                "address": addresses.get(crypto_currency),
                "amount": MOCK_PAYMENTS[payment_id]["amount"],
                "currency": crypto_currency
            }
        else:
            return {
                "status": "error",
                "message": "Платеж не найден"
            }
    except Exception as e:
        logger.error(f"Ошибка при получении адреса для оплаты: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

async def check_payment_status(payment_id):
    """Проверяет статус платежа"""
    try:
        # В реальном приложении здесь будет запрос к API платежной системы
        # Для тестирования просто вернем сохраненный статус
        
        if payment_id in MOCK_PAYMENTS:
            # С вероятностью 30% имитируем успешную оплату
            # В реальном приложении этого кода не будет
            import random
            if random.random() < 0.3 and MOCK_PAYMENTS[payment_id]["status"] == "pending":
                MOCK_PAYMENTS[payment_id]["status"] = "completed"
                MOCK_PAYMENTS[payment_id]["completed_at"] = datetime.utcnow()
            
            return {
                "status": "success",
                "payment_status": MOCK_PAYMENTS[payment_id]["status"],
                "payment_data": MOCK_PAYMENTS[payment_id]
            }
        else:
            return {
                "status": "error",
                "message": "Платеж не найден"
            }
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса платежа: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

async def cancel_payment(payment_id):
    """Отменяет платеж"""
    try:
        # В реальном приложении здесь будет запрос к API платежной системы
        
        if payment_id in MOCK_PAYMENTS:
            MOCK_PAYMENTS[payment_id]["status"] = "cancelled"
            MOCK_PAYMENTS[payment_id]["cancelled_at"] = datetime.utcnow()
            
            return {
                "status": "success",
                "message": "Платеж отменен"
            }
        else:
            return {
                "status": "error",
                "message": "Платеж не найден"
            }
    except Exception as e:
        logger.error(f"Ошибка при отмене платежа: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

async def activate_subscription(session, user_id, payment_id, plan_type):
    """Активирует подписку для пользователя после подтверждения платежа"""
    try:
        from models.user import User, SubscriptionLevel
        
        # Определяем срок действия подписки
        now = datetime.utcnow()
        if plan_type == "monthly":
            subscription_end = now + timedelta(days=30)
        elif plan_type == "yearly":
            subscription_end = now + timedelta(days=365)
        else:
            return False
        
        # Обновляем пользователя
        from sqlalchemy.future import select
        
        # Получаем пользователя
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        
        if user:
            # Обновляем его подписку
            user.subscription_level = SubscriptionLevel.premium
            user.subscription_expiry = subscription_end
            
            # Создаем запись о подписке
            subscription = Subscription(
                user_id=user_id,
                payment_method=MOCK_PAYMENTS[payment_id].get("payment_method", "unknown"),
                payment_id=payment_id,
                amount=MOCK_PAYMENTS[payment_id].get("amount", 0),
                currency=MOCK_PAYMENTS[payment_id].get("currency", "USD"),
                status=SubscriptionStatus.active,
                subscription_start=now,
                subscription_end=subscription_end
            )
            
            session.add(subscription)
            await session.commit()
            
            logger.info(f"Активирована подписка для пользователя {user_id}, план: {plan_type}")
            return True
        else:
            logger.error(f"Пользователь не найден: {user_id}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при активации подписки: {e}")
        await session.rollback()
        return False 