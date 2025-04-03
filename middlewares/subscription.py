import logging
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.future import select

from models.user import User, SubscriptionLevel
from models.wallet import Wallet
from services.db import async_session
from config import FREE_WALLET_LIMIT, PREMIUM_WALLET_LIMIT

logger = logging.getLogger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки пользователя"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем ID пользователя из сообщения или колбэка
        user_id = event.from_user.id
        
        # Если это команда /start или /help, пропускаем проверку
        if isinstance(event, Message) and event.text and event.text.lower() in ['/start', '/help']:
            return await handler(event, data)
        
        # Если это обработка подписки, пропускаем проверку
        if isinstance(event, CallbackQuery) and event.data and (
            event.data.startswith('subscription:') or 
            event.data.startswith('payment:') or 
            event.data.startswith('crypto:') or 
            event.data.startswith('check_payment:') or 
            event.data.startswith('cancel_payment:')
        ):
            return await handler(event, data)
        
        # Проверяем подписку пользователя
        async with async_session() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalars().first()
            
            if not user:
                # Пользователь не найден, пропускаем для создания пользователя
                return await handler(event, data)
            
            # Проверяем, не просрочена ли подписка
            if user.subscription_level == SubscriptionLevel.premium and user.subscription_expiry and user.subscription_expiry < datetime.utcnow():
                # Подписка истекла, переключаем на бесплатный план
                user.subscription_level = SubscriptionLevel.free
                await session.commit()
                
                # Получаем количество кошельков пользователя
                result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
                wallets = result.scalars().all()
                wallet_count = len(wallets)
                
                # Если у пользователя больше кошельков, чем разрешено на бесплатном плане, уведомляем
                if wallet_count > FREE_WALLET_LIMIT:
                    text = (
                        f"⚠️ <b>Ваша премиум подписка истекла</b>\n\n"
                        f"Вы перешли на бесплатный план. На этом плане можно использовать не более {FREE_WALLET_LIMIT} кошельков.\n"
                        f"У вас сейчас {wallet_count} кошельков.\n\n"
                        f"Пожалуйста, удалите лишние кошельки или продлите подписку командой /subscribe, чтобы продолжить мониторинг всех кошельков."
                    )
                    
                    if isinstance(event, Message):
                        await event.answer(text)
                    elif isinstance(event, CallbackQuery):
                        await event.message.answer(text)
            
            # Проверяем, не пытается ли пользователь добавить слишком много кошельков
            if isinstance(event, Message) and event.text and event.text.startswith('/add_wallet'):
                result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
                wallets = result.scalars().all()
                wallet_count = len(wallets)
                
                # Определяем лимит кошельков в зависимости от подписки
                wallet_limit = PREMIUM_WALLET_LIMIT if user.subscription_level == SubscriptionLevel.premium else FREE_WALLET_LIMIT
                
                if wallet_count >= wallet_limit:
                    # Превышен лимит кошельков
                    if user.subscription_level == SubscriptionLevel.free:
                        text = (
                            f"⚠️ <b>Превышен лимит кошельков</b>\n\n"
                            f"На бесплатном плане вы можете добавить до {FREE_WALLET_LIMIT} кошельков.\n"
                            f"Для добавления большего количества кошельков, оформите премиум подписку командой /subscribe."
                        )
                    else:
                        text = (
                            f"⚠️ <b>Превышен лимит кошельков</b>\n\n"
                            f"На премиум плане вы можете добавить до {PREMIUM_WALLET_LIMIT} кошельков.\n"
                            f"Вы достигли максимального количества кошельков для мониторинга."
                        )
                    
                    await event.answer(text)
                    # Останавливаем обработку
                    return
        
        # Продолжаем обработку
        return await handler(event, data) 