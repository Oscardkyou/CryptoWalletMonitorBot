import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramUnauthorizedError, TelegramAPIError

from config import BOT_TOKEN
from handlers.common import register_common_handlers
from handlers.wallets import register_wallet_handlers
from handlers.subscription import register_subscription_handlers
from services.db import init_db
from services.monitor import start_wallet_monitor
from utils.logging import setup_logging
from middlewares.subscription import SubscriptionMiddleware

# Настройка логирования
logger = setup_logging()

# Создание общего списка команд бота
async def set_commands(bot: Bot):
    try:
        commands = [
            BotCommand(command="/start", description="Начать работу с ботом"),
            BotCommand(command="/add_wallet", description="Добавить новый кошелек"),
            BotCommand(command="/my_wallets", description="Список моих кошельков"),
            BotCommand(command="/balance", description="Проверить баланс"),
            BotCommand(command="/transactions", description="Последние транзакции"),
            BotCommand(command="/settings", description="Настройки уведомлений"),
            BotCommand(command="/subscribe", description="Оформить премиум подписку"),
            BotCommand(command="/test_premium", description="Активировать тестовую подписку"),
            BotCommand(command="/help", description="Помощь по командам")
        ]
        await bot.set_my_commands(commands)
        logger.info("Команды бота успешно установлены")
    except TelegramAPIError as e:
        logger.error(f"Ошибка при установке команд бота: {e}")

# Функция регистрации всех обработчиков
def register_all_handlers(dp):
    # Регистрируем обработчики из разных модулей
    register_common_handlers(dp)
    register_wallet_handlers(dp)
    register_subscription_handlers(dp)
    # Здесь будут добавляться другие обработчики по мере их создания

# Основная функция запуска бота
async def main():
    # Инициализация бота и диспетчера
    session = AiohttpSession()
    bot = Bot(
        token=BOT_TOKEN, 
        session=session, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация мидлварей
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    # Инициализация базы данных
    await init_db()
    
    # Регистрация всех обработчиков
    register_all_handlers(dp)
    
    # Установка команд бота
    try:
        await set_commands(bot)
    except Exception as e:
        logger.error(f"Ошибка при установке команд бота: {e}")
    
    # Проверка соединения с Telegram API
    try:
        # Пробуем получить информацию о боте для проверки авторизации
        bot_info = await bot.get_me()
        logger.info(f"Бот авторизован как: @{bot_info.username} (ID: {bot_info.id})")
        
        # Запуск фоновой задачи мониторинга кошельков
        asyncio.create_task(start_wallet_monitor(bot))
        
        # Запуск бота
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        logger.critical("Ошибка авторизации: неверный токен бота. Проверьте файл .env")
        print("\n\033[91mОшибка авторизации: неверный токен бота! 🚫\033[0m")
        print("\033[93mПроверьте BOT_TOKEN в файле .env\033[0m")
        print("Вы можете получить новый токен у @BotFather в Telegram")
    except TelegramAPIError as e:
        logger.error(f"Ошибка Telegram API: {e}")
        print(f"\n\033[91mОшибка Telegram API: {e}\033[0m")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        print(f"\n\033[91mНепредвиденная ошибка: {e}\033[0m")
    finally:
        # Закрываем сессию бота
        if bot.session and not bot.session.closed:
            await bot.session.close()
            logger.info("Сессия бота закрыта")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную")
        print("\n\033[93mБот остановлен вручную 👋\033[0m")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\n\033[91mКритическая ошибка: {e}\033[0m")
        raise 