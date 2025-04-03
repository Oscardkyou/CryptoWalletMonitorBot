
## 1. Общее описание проекта

**Название проекта:** CryptoWalletMonitor Bot

**Цель:** Разработать Telegram-бота на aiogram, который позволяет пользователям отслеживать активность на криптовалютных адресах (ETH, BTC, BNB) с оповещениями о транзакциях и системой платной подписки.

**Сроки реализации:** 1-2 дня

## 2. Технический стек (уточненный)

- **Язык программирования:** Python 3.9+
- **Фреймворк для бота:** aiogram 2.25.1 или новее
- **База данных:** MySQL с SQLAlchemy ORM
- **Blockchain API:**
    - Etherscan API (Ethereum)
    - [Blockchain.info](http://blockchain.info/) API (Bitcoin)
    - BscScan API (Binance Smart Chain)
- **Платежная система:** CryptoPayments API (основной) и/или Stripe
- **Хостинг:** Любой VPS с Ubuntu 20.04+

## 3. Структура проекта

```
crypto_monitor_bot/
├── app.py                 # Точка входа приложения
├── config.py              # Конфигурационный файл
├── requirements.txt       # Зависимости проекта
├── alembic/               # Миграции базы данных
├── handlers/
│   ├── __init__.py
│   ├── common.py          # Общие обработчики (start, help)
│   ├── wallets.py         # Обработчики для управления кошельками
│   ├── transactions.py    # Обработчики для просмотра транзакций
│   └── subscription.py    # Обработчики для подписок
├── keyboards/
│   ├── __init__.py
│   ├── common_kb.py       # Клавиатуры для общих команд
│   ├── wallet_kb.py       # Клавиатуры для управления кошельками
│   └── subscription_kb.py # Клавиатуры для подписок
├── middlewares/
│   ├── __init__.py
│   └── subscription.py    # Мидлвари для проверки подписки
├── models/
│   ├── __init__.py
│   ├── base.py            # Базовый класс модели
│   ├── user.py            # Модель пользователя
│   ├── wallet.py          # Модель кошелька
│   ├── transaction.py     # Модель транзакции
│   └── subscription.py    # Модель подписки
├── services/
│   ├── __init__.py
│   ├── db.py              # Сервис базы данных
│   ├── blockchain.py      # Сервис для работы с блокчейном
│   ├── monitor.py         # Сервис мониторинга адресов
│   └── payments.py        # Сервис обработки платежей
└── utils/
    ├── __init__.py
    ├── logging.py         # Настройка логирования
    └── notifications.py   # Утилиты для уведомлений

```

## 4. Структура базы данных

```sql
-- Таблица пользователей
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    full_name VARCHAR(255),
    language_code VARCHAR(10),
    subscription_level ENUM('free', 'premium') DEFAULT 'free',
    subscription_expiry DATETIME NULL,
    notification_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Таблица кошельков
CREATE TABLE wallets (
    wallet_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    address VARCHAR(255),
    blockchain_type ENUM('ETH', 'BTC', 'BNB'),
    label VARCHAR(255),
    last_checked_timestamp DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE KEY (user_id, address)
);

-- Таблица транзакций
CREATE TABLE transactions (
    tx_id VARCHAR(255) PRIMARY KEY,
    wallet_id INT,
    hash VARCHAR(255),
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    value DECIMAL(30, 18),
    timestamp DATETIME,
    block_number INT,
    notification_sent BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (wallet_id) REFERENCES wallets(wallet_id)
);

-- Таблица подписок
CREATE TABLE subscriptions (
    subscription_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,
    payment_method VARCHAR(255),
    payment_id VARCHAR(255),
    amount DECIMAL(10, 2),
    currency VARCHAR(10),
    status ENUM('pending', 'active', 'cancelled', 'expired') DEFAULT 'pending',
    subscription_start DATETIME,
    subscription_end DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

```

## 5. Основные компоненты кода

### 5.1 Файл конфигурации ([config.py](http://config.py/))

```python
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Blockchain API Keys
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY")

# Платежные системы
CRYPTO_PAYMENT_API_KEY = os.getenv("CRYPTO_PAYMENT_API_KEY")
CRYPTO_PAYMENT_API_SECRET = os.getenv("CRYPTO_PAYMENT_API_SECRET")

# База данных
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "crypto_monitor")

# Настройки ограничений
FREE_WALLET_LIMIT = 3
PREMIUM_WALLET_LIMIT = 20

# Стоимость подписки
MONTHLY_SUBSCRIPTION_PRICE = 3.0
YEARLY_SUBSCRIPTION_PRICE = 30.0

# Параметры мониторинга
MONITOR_INTERVAL = 60  # секунды между проверками кошельков

```

### 5.2 Точка входа ([app.py](http://app.py/))

```python
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from handlers import register_all_handlers
from services.db import init_db
from services.monitor import start_wallet_monitor
from utils.logging import setup_logging

# Настройка логирования
logger = setup_logging()

# Список команд бота
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/add_wallet", description="Добавить новый кошелек"),
        BotCommand(command="/my_wallets", description="Список моих кошельков"),
        BotCommand(command="/balance", description="Проверить баланс"),
        BotCommand(command="/transactions", description="Последние транзакции"),
        BotCommand(command="/settings", description="Настройки уведомлений"),
        BotCommand(command="/subscribe", description="Оформить премиум подписку"),
        BotCommand(command="/help", description="Помощь по командам")
    ]
    await bot.set_my_commands(commands)

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    # Инициализация базы данных
    await init_db()

    # Регистрация всех обработчиков
    register_all_handlers(dp)

    # Установка команд бота
    await set_commands(bot)

    # Запуск фоновой задачи мониторинга кошельков
    asyncio.create_task(start_wallet_monitor(bot))

    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")

```

### 5.3 Обработчики команд (handlers/wallets.py)

```python
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from models.wallet import Wallet
from models.user import User
from services.blockchain import validate_address, check_balance
from services.db import get_user_wallets_count
from keyboards.wallet_kb import generate_wallets_keyboard
from config import FREE_WALLET_LIMIT, PREMIUM_WALLET_LIMIT

# Создаем класс состояний для добавления кошелька
class AddWalletStates(StatesGroup):
    waiting_for_blockchain = State()
    waiting_for_address = State()
    waiting_for_label = State()

# Обработчик команды /add_wallet
async def cmd_add_wallet(message: types.Message):
    user_id = message.from_user.id

    # Проверяем количество уже добавленных кошельков
    wallets_count = await get_user_wallets_count(user_id)
    user = await User.get_or_create(user_id)

    # Определяем лимит в зависимости от подписки
    wallet_limit = PREMIUM_WALLET_LIMIT if user.subscription_level == 'premium' else FREE_WALLET_LIMIT

    if wallets_count >= wallet_limit:
        if user.subscription_level == 'free':
            await message.answer(
                "Вы достигли лимита кошельков на бесплатном тарифе (3).\\n"
                "Оформите премиум-подписку чтобы добавить до 20 кошельков.\\n"
                "Используйте команду /subscribe для подробностей."
            )
        else:
            await message.answer(f"Вы достигли лимита кошельков ({wallet_limit}).")
        return

    # Запрашиваем тип блокчейна
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("ETH (Ethereum)"),
        types.KeyboardButton("BTC (Bitcoin)")
    )
    markup.row(
        types.KeyboardButton("BNB (Binance Smart Chain)"),
        types.KeyboardButton("Отмена")
    )

    await message.answer(
        "Выберите тип блокчейна для добавления кошелька:",
        reply_markup=markup
    )
    await AddWalletStates.waiting_for_blockchain.set()

# Обработчик выбора блокчейна
async def process_blockchain_selection(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await state.finish()
        await message.answer("Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    blockchain_map = {
        "ETH (Ethereum)": "ETH",
        "BTC (Bitcoin)": "BTC",
        "BNB (Binance Smart Chain)": "BNB"
    }

    if message.text not in blockchain_map:
        await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
        return

    blockchain_type = blockchain_map[message.text]

    # Сохраняем выбранный блокчейн
    await state.update_data(blockchain_type=blockchain_type)

    # Запрашиваем адрес кошелька
    await message.answer(
        f"Введите адрес {blockchain_type}-кошелька для мониторинга:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await AddWalletStates.waiting_for_address.set()

# Обработчик ввода адреса кошелька
async def process_wallet_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    data = await state.get_data()
    blockchain_type = data['blockchain_type']

    # Проверяем валидность адреса
    if not await validate_address(blockchain_type, address):
        await message.answer(f"Адрес не соответствует формату {blockchain_type}. Пожалуйста, проверьте и введите правильный адрес.")
        return

    # Проверяем наличие средств на адресе
    balance = await check_balance(blockchain_type, address)
    if balance is None:
        await message.answer("Не удалось проверить баланс кошелька. Пожалуйста, попробуйте другой адрес.")
        return

    # Сохраняем адрес
    await state.update_data(address=address, balance=balance)

    # Запрашиваем метку для кошелька
    await message.answer("Введите название (метку) для этого кошелька:")
    await AddWalletStates.waiting_for_label.set()

# Обработчик ввода метки кошелька
async def process_wallet_label(message: types.Message, state: FSMContext):
    label = message.text.strip()
    user_id = message.from_user.id

    # Получаем сохраненные данные
    data = await state.get_data()
    blockchain_type = data['blockchain_type']
    address = data['address']
    balance = data['balance']

    # Сохраняем кошелек в базу данных
    try:
        wallet = await Wallet.create(
            user_id=user_id,
            address=address,
            blockchain_type=blockchain_type,
            label=label
        )

        await message.answer(
            f"✅ Кошелек успешно добавлен!\\n\\n"
            f"Тип: {blockchain_type}\\n"
            f"Адрес: {address}\\n"
            f"Название: {label}\\n"
            f"Текущий баланс: {balance} {blockchain_type}\\n\\n"
            f"Теперь вы будете получать уведомления о транзакциях на этом кошельке."
        )
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении кошелька: {str(e)}")

    # Завершаем машину состояний
    await state.finish()

# Обработчик команды /my_wallets
async def cmd_my_wallets(message: types.Message):
    user_id = message.from_user.id

    # Получаем все кошельки пользователя
    wallets = await Wallet.get_user_wallets(user_id)

    if not wallets:
        await message.answer(
            "У вас пока нет добавленных кошельков.\\n"
            "Используйте команду /add_wallet чтобы добавить новый кошелек."
        )
        return

    # Формируем сообщение и клавиатуру
    message_text = "Ваши кошельки для мониторинга:\\n\\n"

    for i, wallet in enumerate(wallets, 1):
        balance = await check_balance(wallet.blockchain_type, wallet.address)
        balance_str = f"{balance} {wallet.blockchain_type}" if balance is not None else "Не удалось получить"

        message_text += (
            f"{i}. {wallet.label} ({wallet.blockchain_type})\\n"
            f"   Адрес: {wallet.address[:10]}...{wallet.address[-8:]}\\n"
            f"   Баланс: {balance_str}\\n\\n"
        )

    # Добавляем информацию о лимитах
    user = await User.get_or_create(user_id)
    wallet_limit = PREMIUM_WALLET_LIMIT if user.subscription_level == 'premium' else FREE_WALLET_LIMIT
    message_text += f"Использовано {len(wallets)} из {wallet_limit} доступных кошельков."

    # Создаем инлайн-клавиатуру для управления кошельками
    markup = await generate_wallets_keyboard(wallets)

    await message.answer(message_text, reply_markup=markup)

# Регистрация обработчиков
def register_wallet_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_add_wallet, commands=["add_wallet"])
    dp.register_message_handler(process_blockchain_selection, state=AddWalletStates.waiting_for_blockchain)
    dp.register_message_handler(process_wallet_address, state=AddWalletStates.waiting_for_address)
    dp.register_message_handler(process_wallet_label, state=AddWalletStates.waiting_for_label)
    dp.register_message_handler(cmd_my_wallets, commands=["my_wallets"])

```

### 5.4 Сервис мониторинга (services/monitor.py)

```python
import asyncio
from datetime import datetime
import logging

from aiogram import Bot
from aiogram.utils.exceptions import BotBlocked, ChatNotFound

from config import MONITOR_INTERVAL
from models.wallet import Wallet
from models.transaction import Transaction
from services.blockchain import get_new_transactions
from utils.notifications import format_transaction_notification

logger = logging.getLogger(__name__)

async def monitor_wallet(bot: Bot, wallet):
    """Мониторинг отдельного кошелька и отправка уведомлений о новых транзакциях"""
    try:
        # Получаем новые транзакции
        new_transactions = await get_new_transactions(
            wallet.blockchain_type,
            wallet.address,
            wallet.last_checked_timestamp
        )

        if not new_transactions:
            # Если новых транзакций нет, просто обновляем время проверки
            await wallet.update_last_checked()
            return

        # Для каждой новой транзакции сохраняем в БД и отправляем уведомление
        for tx_data in new_transactions:
            try:
                # Проверяем, не обрабатывали ли мы уже эту транзакцию
                existing_tx = await Transaction.get_by_hash(tx_data['hash'])
                if existing_tx:
                    continue

                # Сохраняем транзакцию в базу данных
                tx = await Transaction.create(
                    wallet_id=wallet.wallet_id,
                    hash=tx_data['hash'],
                    from_address=tx_data['from'],
                    to_address=tx_data['to'],
                    value=tx_data['value'],
                    timestamp=tx_data['timestamp'],
                    block_number=tx_data.get('blockNumber')
                )

                # Форматируем и отправляем уведомление пользователю
                notification_text = await format_transaction_notification(wallet, tx_data)

                await bot.send_message(
                    wallet.user_id,
                    notification_text,
                    parse_mode='HTML'
                )

                # Отмечаем, что уведомление отправлено
                await tx.mark_notification_sent()

            except Exception as tx_error:
                logger.error(f"Ошибка при обработке транзакции {tx_data.get('hash')}: {tx_error}")

        # Обновляем время последней проверки кошелька
        await wallet.update_last_checked()

    except (BotBlocked, ChatNotFound):
        logger.warning(f"Не удалось отправить сообщение пользователю {wallet.user_id} (заблокировал бота)")
    except Exception as e:
        logger.error(f"Ошибка при мониторинге кошелька {wallet.address}: {str(e)}")

async def start_wallet_monitor(bot: Bot):
    """Запуск фонового процесса мониторинга всех кошельков"""
    logger.info("Запущен фоновый мониторинг кошельков")

    while True:
        try:
            # Получаем все активные кошельки для мониторинга
            wallets = await Wallet.get_all_active_wallets()

            # Запускаем мониторинг для каждого кошелька
            monitor_tasks = []
            for wallet in wallets:
                task = asyncio.create_task(monitor_wallet(bot, wallet))
                monitor_tasks.append(task)

            # Ждем завершения всех задач мониторинга
            if monitor_tasks:
                await asyncio.gather(*monitor_tasks)

            logger.debug(f"Цикл мониторинга завершен, проверено {len(wallets)} кошельков")

        except Exception as e:
            logger.error(f"Ошибка в цикле мониторинга: {str(e)}")

        # Ждем указанный интервал перед следующей проверкой
        await asyncio.sleep(MONITOR_INTERVAL)

```

### 5.5 Система подписок (handlers/subscription.py)

```python
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta

from models.user import User
from models.subscription import Subscription
from services.payments import create_crypto_payment, check_payment_status
from keyboards.subscription_kb import generate_subscription_keyboard
from config import MONTHLY_SUBSCRIPTION_PRICE, YEARLY_SUBSCRIPTION_PRICE

# Создаем класс состояний для оформления подписки
class SubscriptionStates(StatesGroup):
    selecting_plan = State()
    selecting_payment_method = State()
    awaiting_payment = State()

# Обработчик команды /subscribe
async def cmd_subscribe(message: types.Message):
    user_id = message.from_user.id
    user = await User.get_or_create(user_id)

    # Проверяем, есть ли у пользователя активная подписка
    if user.subscription_level == 'premium' and user.subscription_expiry and user.subscription_expiry > datetime.now():
        expiry_date = user.subscription_expiry.strftime('%d.%m.%Y')
        await message.answer(
            f"У вас уже есть активная премиум-подписка!\\n"
            f"Срок действия: до {expiry_date}\\n\\n"
            f"Хотите продлить подписку?",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("Продлить подписку", callback_data="extend_subscription"),
                types.InlineKeyboardButton("Не сейчас", callback_data="cancel")
            )
        )
        return

    # Если подписки нет, предлагаем оформить
    await show_subscription_plans(message)
    await SubscriptionStates.selecting_plan.set()

# Функция отображения тарифных планов
async def show_subscription_plans(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            f"Месячная подписка - ${MONTHLY_SUBSCRIPTION_PRICE}/мес",
            callback_data="plan:monthly"
        ),
        types.InlineKeyboardButton(
            f"Годовая подписка - ${YEARLY_SUBSCRIPTION_PRICE}/год (экономия 17%)",
            callback_data="plan:yearly"
        ),
        types.InlineKeyboardButton("Отмена", callback_data="cancel")
    )

    await message.answer(
        "🌟 <b>Премиум-подписка</b> 🌟\\n\\n"
        "С премиум-подпиской вы получаете:\\n"
        "✅ Мониторинг до 20 криптовалютных адресов\\n"
        "✅ Настраиваемые уведомления\\n"
        "✅ Расширенную аналитику и статистику\\n"
        "✅ Оповещения о подозрительной активности\\n"
        "✅ Отчеты о движении средств\\n\\n"
        "Выберите подходящий тарифный план:",
        reply_markup=markup,
        parse_mode='HTML'
    )

# Обработчик выбора тарифного плана
async def process_subscription_plan(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    if callback_query.data == "cancel":
        await state.finish()
        await callback_query.message.answer("Оформление подписки отменено.")
        return

    plan_type = callback_query.data.split(':')[1]  # monthly или yearly

    # Сохраняем выбранный план
    if plan_type == "monthly":
        await state.update_data(plan="monthly", amount=MONTHLY_SUBSCRIPTION_PRICE)
    else:
        await state.update_data(plan="yearly", amount=YEARLY_SUBSCRIPTION_PRICE)

    # Предлагаем выбрать способ оплаты
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Оплата криптовалютой", callback_data="payment:crypto"),
        types.InlineKeyboardButton("Отмена", callback_data="cancel")
    )

    await callback_query.message.edit_text(
        f"Вы выбрали {'месячную' if plan_type == 'monthly' else 'годовую'} подписку.\\n"
        f"Выберите способ оплаты:",
        reply_markup=markup
    )

    await SubscriptionStates.selecting_payment_method.set()

# Обработчик выбора способа оплаты
async def process_payment_method(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    if callback_query.data == "cancel":
        await state.finish()
        await callback_query.message.edit_text("Оформление подписки отменено.")
        return

    payment_method = callback_query.data.split(':')[1]  # crypto или другие методы
    user_id = callback_query.from_user.id

    # Получаем данные о выбранном плане
    data = await state.get_data()
    plan = data['plan']
    amount = data['amount']

    # Создаем запись о подписке в базе данных
    subscription_start = datetime.now()
    subscription_end = subscription_start + timedelta(days=30 if plan == "monthly" else 365)

    subscription = await Subscription.create(
        user_id=user_id,
        payment_method=payment_method,
        amount=amount,
        currency="USD",
        status="pending",
        subscription_start=subscription_start,
        subscription_end=subscription_end
    )

    # Сохраняем ID подписки в состоянии
    await state.update_data(subscription_id=subscription.subscription_id)

    # Создаем платеж в зависимости от выбранного метода
    if payment_method == "crypto":
        payment_url = await create_crypto_payment(
            user_id=user_id,
            amount=amount,
            currency="USDT",
            item_name=f"CryptoMonitorBot {'Monthly' if plan == 'monthly' else 'Yearly'} Subscription",
            payment_id=str(subscription.subscription_id)
        )

        # Обновляем информацию о платеже
        await subscription.update_payment_id(payment_url['payment_id'])

        # Отправляем пользователю ссылку на оплату
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Оплатить", url=payment_url['payment_url']),
            types.InlineKeyboardButton("Я оплатил", callback_data=f"check_payment:{subscription.subscription_id}")
        )

        await callback_query.message.edit_text(
            "Для завершения оформления подписки, пожалуйста, произведите оплату по ссылке ниже.\\n"
            "После оплаты нажмите кнопку «Я оплатил» для проверки статуса платежа.",
            reply_markup=markup
        )

        await SubscriptionStates.awaiting_payment.set()

# Обработчик проверки статуса платежа
async def check_payment_status_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Проверяем статус платежа...")

    subscription_id = int(callback_query.data.split(':')[1])
    subscription = await Subscription.get_by_id(subscription_id)

    if not subscription:
        await callback_query.message.edit_text("Не удалось найти информацию о подписке.")
        await state.finish()
        return

    # Проверяем статус платежа через API
    payment_status = await check_payment_status(subscription.payment_id)

    if payment_status == "completed":
        # Обновляем статус подписки и уровень пользователя
        await subscription.update_status("active")
        await User.update_subscription(
            user_id=subscription.user_id,
            level="premium",
            expiry=subscription.subscription_end
        )

        end_date = subscription.subscription_end.strftime("%d.%m.%Y")

        await callback_query.message.edit_text(
            "🎉 Поздравляем! Ваша премиум-подписка успешно активирована!\\n\\n"
            f"Срок действия: до {end_date}\\n"
            "Теперь вы можете добавить до 20 кошельков и использовать все премиум-функции.\\n\\n"
            "Используйте команду /add_wallet чтобы добавить новые кошельки или /my_wallets чтобы управлять существующими."
        )
        await state.finish()

    elif payment_status == "pending":
        # Платеж в обработке
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Проверить снова", callback_data=f"check_payment:{subscription_id}"),
            types.InlineKeyboardButton("Отмена", callback_data="cancel")
        )

        await callback_query.message.edit_text(
            "Ваш платеж находится в обработке. Это может занять некоторое время.\\n"
            "Пожалуйста, нажмите «Проверить снова» через несколько минут.",
            reply_markup=markup
        )

    else:
        # Платеж не найден или отклонен
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Попробовать снова", callback_data="retry_payment"),
            types.InlineKeyboardButton("Отмена", callback_data="cancel")
        )

        await callback_query.message.edit_text(
            "К сожалению, мы не смогли найти ваш платеж или он был отклонен.\\n"
            "Пожалуйста, убедитесь, что вы завершили процесс оплаты.",
            reply_markup=markup
        )

# Регистрация обработчиков
def register_subscription_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_subscribe, commands=["subscribe"])
    dp.register_callback_query_handler(process_subscription_plan, lambda c: c.data.startswith("plan:") or c.data == "cancel", state=SubscriptionStates.selecting_plan)
    dp.register_callback_query_handler(process_payment_method, lambda c: c.data.startswith("payment:") or c.data == "cancel", state=SubscriptionStates.selecting_payment_method)
    dp.register_callback_query_handler(check_payment_status_handler, lambda c: c.data.startswith("check_payment:"), state=SubscriptionStates.awaiting_payment)
    dp.register_callback_query_handler(lambda c, s: s.finish() and c.message.edit_text("Действие отменено."), lambda c: c.data == "cancel", state=SubscriptionStates)

```

## 6. Blockchain сервис (services/blockchain.py)

```python
import aiohttp
import logging
from datetime import datetime
import json
from web3 import Web3

from config import ETHERSCAN_API_KEY, BSCSCAN_API_KEY

logger = logging.getLogger(__name__)

# Адреса API
ETHERSCAN_API_URL = "<https://api.etherscan.io/api>"
BSCSCAN_API_URL = "<https://api.bscscan.com/api>"
BLOCKCHAIN_INFO_API_URL = "<https://blockchain.info/rawaddr>"

# Валидация адреса кошелька
async def validate_address(blockchain_type, address):
    """Проверяет валидность адреса кошелька для соответствующего блокчейна"""
    try:
        if blockchain_type == "ETH" or blockchain_type == "BNB":
            return Web3.is_address(address)
        elif blockchain_type == "BTC":
            # Базовая проверка формата Bitcoin-адреса
            return (address.startswith('1') or address.startswith('3') or address.startswith('bc1')) and len(address) >= 26 and len(address) <= 35
        return False
    except Exception as e:
        logger.error(f"Ошибка валидации адреса: {str(e)}")
        return False

# Проверка баланса кошелька
async def check_balance(blockchain_type, address):
    """Получает текущий баланс кошелька"""
    try:
        if blockchain_type == "ETH":
            return await check_eth_balance(address)
        elif blockchain_type == "BTC":
            return await check_btc_balance(address)
        elif blockchain_type == "BNB":
            return await check_bnb_balance(address)
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении баланса: {str(e)}")
        return None

# Получение новых транзакций
async def get_new_transactions(blockchain_type, address, last_checked=None):
    """Получает новые транзакции для адреса с момента последней проверки"""
    try:
        if blockchain_type == "ETH":
            return await get_eth_transactions(address, last_checked)
        elif blockchain_type == "BTC":
            return await get_btc_transactions(address, last_checked)
        elif blockchain_type == "BNB":
            return await get_bnb_transactions(address, last_checked)
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций: {str(e)}")
        return []

# Ethereum-специфичные функции
async def check_eth_balance(address):
    """Получает баланс Ethereum-адреса"""
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(ETHERSCAN_API_URL, params=params) as response:
            if response.status != 200:
                return None

            data = await response.json()
            if data["status"] != "1":
                return None

            # Конвертируем wei в ETH
            balance_in_eth = int(data["result"]) / 10**18
            return round(balance_in_eth, 6)

async def get_eth_transactions(address, last_checked=None):
    """Получает транзакции для Ethereum-адреса"""
    # Определяем startblock в зависимости от времени последней проверки
    startblock = "0"
    if last_checked:
        # Здесь можно добавить логику определения блока по timestamp
        # Для простоты используем 0 чтобы получить все транзакции
        pass

    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": startblock,
        "endblock": "99999999",
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(ETHERSCAN_API_URL, params=params) as response:
            if response.status != 200:
                return []

            data = await response.json()
            if data["status"] != "1":
                return []

            transactions = data["result"]

            # Фильтруем транзакции по времени последней проверки
            if last_checked:
                filtered_transactions = []
                for tx in transactions:
                    tx_timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))
                    if tx_timestamp > last_checked:
                        # Добавляем информацию о сумме в ETH
                        tx["value_eth"] = float(tx["value"]) / 10**18
                        filtered_transactions.append(tx)
                return filtered_transactions
            else:
                # Добавляем информацию о сумме в ETH для всех транзакций
                for tx in transactions:
                    tx["value_eth"] = float(tx["value"]) / 10**18
                return transactions[:10]  # Возвращаем только 10 последних транзакций

# Bitcoin-специфичные функции
async def check_btc_balance(address):
    """Получает баланс Bitcoin-адреса"""
    url = f"{BLOCKCHAIN_INFO_API_URL}/{address}?limit=0"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None

            data = await response.json()

            # Баланс в BTC (конвертируем из сатоши)
            balance_in_btc = data.get("final_balance", 0) / 10**8
            return round(balance_in_btc, 8)

async def get_btc_transactions(address, last_checked=None):
    """Получает транзакции для Bitcoin-адреса"""
    url = f"{BLOCKCHAIN_INFO_API_URL}/{address}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return []

            data = await response.json()
            transactions = data.get("txs", [])

            # Преобразуем данные в общий формат
            formatted_transactions = []
            for tx in transactions:
                tx_time = datetime.fromtimestamp(tx["time"])

                # Пропускаем транзакции старше последней проверки
                if last_checked and tx_time <= last_checked:
                    continue

                # Определяем, входящая или исходящая транзакция
                is_incoming = False
                value = 0

                for output in tx.get("out", []):
                    if output.get("addr") == address:
                        is_incoming = True
                        value += output.get("value", 0)

                for input in tx.get("inputs", []):
                    addr = input.get("prev_out", {}).get("addr")
                    if addr == address:
                        is_incoming = False
                        value += input.get("prev_out", {}).get("value", 0)

                formatted_tx = {
                    "hash": tx["hash"],
                    "from": tx.get("inputs", [{}])[0].get("prev_out", {}).get("addr", "Unknown"),
                    "to": tx.get("out", [{}])[0].get("addr", "Unknown"),
                    "value": value,
                    "value_btc": value / 10**8,
                    "timestamp": tx_time,
                    "confirmations": tx.get("confirmations", 0)
                }

                formatted_transactions.append(formatted_tx)

            return formatted_transactions

# Binance Smart Chain-специфичные функции
async def check_bnb_balance(address):
    """Получает баланс BNB-адреса"""
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": BSCSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BSCSCAN_API_URL, params=params) as response:
            if response.status != 200:
                return None

            data = await response.json()
            if data["status"] != "1":
                return None

            # Конвертируем wei в BNB
            balance_in_bnb = int(data["result"]) / 10**18
            return round(balance_in_bnb, 6)

async def get_bnb_transactions(address, last_checked=None):
    """Получает транзакции для BNB-адреса (аналогично Ethereum)"""
    # Определяем startblock в зависимости от времени последней проверки
    startblock = "0"
    if last_checked:
        pass

    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": startblock,
        "endblock": "99999999",
        "sort": "desc",
        "apikey": BSCSCAN_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(BSCSCAN_API_URL, params=params) as response:
            if response.status != 200:
                return []

            data = await response.json()
            if data["status"] != "1":
                return []

            transactions = data["result"]

            # Фильтруем транзакции по времени последней проверки
            if last_checked:
                filtered_transactions = []
                for tx in transactions:
                    tx_timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))
                    if tx_timestamp > last_checked:
                        # Добавляем информацию о сумме в BNB
                        tx["value_bnb"] = float(tx["value"]) / 10**18
                        filtered_transactions.append(tx)
                return filtered_transactions
            else:
                # Добавляем информацию о сумме в BNB для всех транзакций
                for tx in transactions:
                    tx["value_bnb"] = float(tx["value"]) / 10**18
                return transactions[:10]  # Возвращаем только 10 последних транзакций

```

## 7. Платежный сервис (services/payments.py)

```python
import time
import uuid
import hmac
import hashlib
import json
import logging
import aiohttp
from urllib.parse import urlencode

from config import CRYPTO_PAYMENT_API_KEY, CRYPTO_PAYMENT_API_SECRET

logger = logging.getLogger(__name__)

# Интеграция с API криптовалютных платежей
async def create_crypto_payment(user_id, amount, currency="USDT", item_name="Premium Subscription", payment_id=None):
    """
    Создает платеж через криптовалютный процессинг
    Возвращает payment_id и payment_url для перенаправления пользователя
    """
    if not payment_id:
        payment_id = f"PM-{int(time.time())}-{user_id}"

    # Создаем данные для запроса к API
    payment_data = {
        "amount": amount,
        "currency1": "USD",
        "currency2": currency,
        "buyer_email": f"user{user_id}@example.com",  # Генерируем временный email
        "item_name": item_name,
        "item_number": payment_id,
        "ipn_url": f"<https://your-bot-api.com/ipn/crypto/{payment_id}>",
        "success_url": f"<https://t.me/YourCryptoMonitorBot?start=payment_success>",
        "cancel_url": f"<https://t.me/YourCryptoMonitorBot?start=payment_cancel>"
    }

    # Подписываем запрос
    hmac_signature = generate_hmac_signature(payment_data, CRYPTO_PAYMENT_API_SECRET)
    headers = {
        "HMAC": hmac_signature,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # Отправляем запрос к API для создания платежа
        api_url = "<https://www.coinpayments.net/api/v1/create_transaction>"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                data=urlencode(payment_data),
                headers=headers
            ) as response:

                if response.status != 200:
                    logger.error(f"Ошибка при создании платежа: {await response.text()}")
                    # Для тестирования возвращаем тестовый URL
                    return {
                        "payment_id": payment_id,
                        "payment_url": f"<https://example.com/pay/{payment_id}>"
                    }

                result = await response.json()
                if result.get("error") != "ok":
                    logger.error(f"Ошибка API при создании платежа: {result.get('error')}")
                    # Для тестирования возвращаем тестовый URL
                    return {
                        "payment_id": payment_id,
                        "payment_url": f"<https://example.com/pay/{payment_id}>"
                    }

                # Возвращаем URL для оплаты и ID платежа
                return {
                    "payment_id": result.get("result", {}).get("txn_id", payment_id),
                    "payment_url": result.get("result", {}).get("checkout_url", f"<https://example.com/pay/{payment_id}>")
                }
    except Exception as e:
        logger.error(f"Исключение при создании платежа: {str(e)}")
        # Для тестирования возвращаем тестовый URL
        return {
            "payment_id": payment_id,
            "payment_url": f"<https://example.com/pay/{payment_id}>"
        }

# Проверка статуса платежа
async def check_payment_status(payment_id):
    """
    Проверяет статус платежа через API криптовалютных платежей
    Возвращает: 'completed', 'pending', или 'failed'
    """
    # Для тестирования можно возвращать статус на основе payment_id
    # В реальном сценарии здесь будет запрос к API платежной системы

    try:
        # Запрос к API для проверки статуса платежа
        # ...

        # Для тестирования считаем, что 30% платежей успешны сразу
        if int(payment_id) % 10 < 3:
            return "completed"
        # 60% платежей находятся в обработке
        elif int(payment_id) % 10 < 9:
            return "pending"
        # 10% платежей не найдены или отклонены
        else:
            return "failed"

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса платежа: {str(e)}")
        return "pending"  # В случае ошибки считаем, что платеж в обработке

# Вспомогательная функция для генерации HMAC-подписи
def generate_hmac_signature(data, secret):
    """Генерирует HMAC-подпись для запроса к API"""
    message = urlencode(data).encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return signature

```

## 8. .env файл (пример)

```
# Telegram Bot
BOT_TOKEN=1234567890:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQrr

# Blockchain API Keys
ETHERSCAN_API_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456
BSCSCAN_API_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456

# Платежные системы
CRYPTO_PAYMENT_API_KEY=your_crypto_payment_api_key
CRYPTO_PAYMENT_API_SECRET=your_crypto_payment_api_secret

# База данных
DB_USER=cryptomonitor
DB_PASSWORD=password123
DB_HOST=localhost
DB_PORT=3306
DB_NAME=crypto_monitor

```

## 9. Дополнительные рекомендации по развертыванию

### 9.1 Инструкция по установке на Ubuntu 20.04

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y python3 python3-pip python3-dev mysql-server libmysqlclient-dev git screen

# Настройка MySQL
sudo mysql_secure_installation

# Создание базы данных и пользователя
sudo mysql -e "CREATE DATABASE crypto_monitor;"
sudo mysql -e "CREATE USER 'cryptomonitor'@'localhost' IDENTIFIED BY 'password123';"
sudo mysql -e "GRANT ALL PRIVILEGES ON crypto_monitor.* TO 'cryptomonitor'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Клонирование репозитория (если используется)
git clone <https://your-repo.git>
cd crypto_monitor_bot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Создание .env файла
nano .env
# Добавьте все необходимые переменные окружения

# Запуск бота в фоновом режиме с помощью screen
screen -S cryptobot
python app.py

# Отключение от screen (бот продолжит работать)
# Нажмите Ctrl+A, затем D

# Чтобы вернуться к боту:
screen -r cryptobot

```

### 9.2 Пример файла requirements.txt

```
aiogram==2.25.1
aiohttp==3.8.5
python-dotenv==1.0.0
sqlalchemy==2.0.19
alembic==1.11.1
pymysql==1.1.0
web3==6.5.0
pycryptodome==3.18.0
cryptography==41.0.3

```

## 10. Заключение

Это детальное техническое задание должно быть достаточным для реализации Telegram-бота для мониторинга криптовалютных кошельков с использованием aiogram.

Бот имеет:

1. Функционал мониторинга адресов в трех популярных блокчейнах
2. Систему оповещений о транзакциях
3. Систему управления кошельками
4. Детальную систему подписок с оплатой
5. Разделение на бесплатный и премиум функционал

Все компоненты структурированы так, чтобы ИИ-агент мог легко понять взаимосвязи между ними и реализовать проект за 1-2 дня.

посмотри тех задание оцени хорошее ли оно