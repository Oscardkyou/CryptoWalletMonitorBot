import logging
from aiogram import Router, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.future import select

from models.user import User
from services.db import async_session
from keyboards.common_kb import get_main_keyboard

logger = logging.getLogger(__name__)

# Создаем роутер для общих команд
router = Router()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
    language_code = message.from_user.language_code
    
    try:
        # Проверяем, существует ли пользователь в базе
        async with async_session() as session:
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalars().first()
            
            if not user:
                # Создаем нового пользователя
                new_user = User(
                    user_id=user_id,
                    username=username,
                    full_name=full_name,
                    language_code=language_code
                )
                session.add(new_user)
                await session.commit()
                
                logger.info(f"Создан новый пользователь: {user_id} ({username})")
                
                welcome_message = (
                    f"👋 <b>Добро пожаловать в CryptoWalletMonitor Bot!</b>\n\n"
                    f"Этот бот поможет вам отслеживать активность ваших криптовалютных кошельков и получать уведомления о новых транзакциях.\n\n"
                    f"<b>Что умеет этот бот:</b>\n"
                    f"• Мониторинг ETH и BSC кошельков\n"
                    f"• Уведомления о новых транзакциях\n"
                    f"• Проверка баланса кошельков\n"
                    f"• Просмотр истории транзакций\n\n"
                    f"<b>Начните работу с ботом:</b>\n"
                    f"1) Добавьте кошелек через команду /add_wallet\n"
                    f"2) Настройте уведомления через /settings\n"
                    f"3) Просматривайте информацию через /my_wallets"
                )
            else:
                # Обновляем информацию о пользователе, если она изменилась
                if user.username != username or user.full_name != full_name or user.language_code != language_code:
                    user.username = username
                    user.full_name = full_name
                    user.language_code = language_code
                    await session.commit()
                    logger.info(f"Обновлена информация о пользователе: {user_id} ({username})")
                
                welcome_message = (
                    f"👋 <b>С возвращением!</b>\n\n"
                    f"Вы снова с CryptoWalletMonitor Bot. Выберите действие из меню ниже."
                )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /start: {e}")
        welcome_message = (
            f"👋 <b>Добро пожаловать в CryptoWalletMonitor Bot!</b>\n\n"
            f"К сожалению, произошла ошибка при работе с базой данных. Пожалуйста, попробуйте позже."
        )
    
    # Отправляем приветственное сообщение
    await message.answer(
        welcome_message,
        reply_markup=get_main_keyboard()
    )
    
    logger.info(f"Пользователь {user_id} запустил бота")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        f"🔍 <b>Справка по командам бота:</b>\n\n"
        f"/start - Начать работу с ботом\n"
        f"/add_wallet - Добавить новый кошелек для мониторинга\n"
        f"/my_wallets - Просмотр списка ваших кошельков\n"
        f"/balance - Проверка баланса кошельков\n"
        f"/transactions - Просмотр последних транзакций\n"
        f"/settings - Настройка уведомлений\n"
        f"/subscribe - Оформить премиум подписку\n"
        f"/test_premium - Активировать тестовую подписку\n"
        f"/help - Показать эту справку\n\n"
        f"<b>Дополнительная информация:</b>\n"
        f"• Бесплатная версия: до 3 кошельков\n"
        f"• Премиум версия: до 20 кошельков\n\n"
        f"По всем вопросам обращайтесь к @admin"
    )
    
    await message.answer(
        help_text,
        reply_markup=get_main_keyboard()
    )
    
    logger.info(f"Пользователь {message.from_user.id} запросил справку")

# Обработчик неизвестных команд
@router.message(F.text.startswith('/'))
async def cmd_unknown(message: Message):
    """Обработчик неизвестных команд"""
    await message.answer(
        "❓ Неизвестная команда. Воспользуйтесь /help для просмотра доступных команд.",
        reply_markup=get_main_keyboard()
    )

def register_common_handlers(dp: Dispatcher):
    """Регистрация обработчиков общих команд"""
    dp.include_router(router) 