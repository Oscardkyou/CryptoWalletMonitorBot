# Руководство по разработке CryptoWalletMonitor Bot

## Обзор проекта

**CryptoWalletMonitor Bot** — это Telegram-бот на aiogram для отслеживания активности криптовалютных адресов с системой платной подписки.

**Ключевые функции:**

- Мониторинг адресов ETH, BTC, BNB
- Уведомления о транзакциях в реальном времени
- Бесплатный план (до 3 кошельков) и премиум (до 20 кошельков)
- Приём оплаты в криптовалюте

**Сроки:** 1-2 дня

## Структура проекта

```
crypto_monitor_bot/
├── app.py                 # Основная точка входа
├── config.py              # Конфигурация и константы
├── handlers/              # Обработчики команд
├── keyboards/             # Клавиатуры и кнопки
├── middlewares/           # Мидлвари (проверка подписки)
├── models/                # Модели данных
├── services/              # Сервисы (блокчейн, платежи)
└── utils/                 # Вспомогательные функции

```

## Ключевые компоненты и API

### Aiogram 2.x

```python
# Базовый пример инициализации бота
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

```

### Blockchain API

Используйте aiohttp для асинхронных запросов:

```python
async def check_eth_balance(address):
    url = f"<https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={ETHERSCAN_API_KEY}>"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data["status"] == "1":
                return int(data["result"]) / 10**18
    return None

```

### База данных

Используйте SQLAlchemy с asyncio:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
engine = create_async_engine(f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}")
async_session = sessionmaker(engine, class_=AsyncSession)

async def get_session():
    async with async_session() as session:
        yield session

```

## Таблицы базы данных (краткая схема)

1. **users** - Пользователи бота
    - user_id (PK), username, subscription_level, subscription_expiry
2. **wallets** - Кошельки для мониторинга
    - wallet_id (PK), user_id (FK), address, blockchain_type, label
3. **transactions** - История транзакций
    - tx_id (PK), wallet_id (FK), hash, from_address, to_address, value
4. **subscriptions** - Платежная информация
    - subscription_id (PK), user_id (FK), payment_method, payment_id, status

## Основные пользовательские сценарии

### 1. Регистрация и добавление кошелька

- /start → ознакомление
- /add_wallet → выбор блокчейна → ввод адреса → ввод метки

### 2. Мониторинг и уведомления

- Фоновая задача проверяет новые транзакции каждую минуту
- При обнаружении транзакции - отправка уведомления пользователю

### 3. Оформление подписки

- /subscribe → выбор плана → выбор способа оплаты → оплата → активация премиум

## Критические моменты

### Асинхронность

- **Используйте только async/await**, никаких блокирующих операций
- Помните о `asyncio.gather()` для параллельных задач

### Обработка ошибок

- Всегда оборачивайте сетевые запросы в try/except
- Логируйте ошибки для дебага

```python
try:
    result = await some_blockchain_request()
except Exception as e:
    logger.error(f"Ошибка при запросе к блокчейну: {str(e)}")
    # Обработка ошибки

```

### Мониторинг кошельков

- Используйте кэширование результатов когда возможно
- Сохраняйте время последней проверки для оптимизации запросов

### Платежная система

- Для тестирования используйте моки платежей
- Всегда сохраняйте ID платежа и его статус в БД

## Рекомендации по коду

1. **Комментируйте сложную логику**
2. **Разделяйте бизнес-логику и представление**
3. **Используйте константы из [config.py](http://config.py/)** вместо "магических чисел"
4. **Добавляйте информативные сообщения пользователю** при ошибках
5. **Обрабатывайте отмену действий** через кнопку "Отмена" или команду /cancel

## Тестовый запуск

При первом запуске используйте ручное тестирование:

1. Проверьте добавление кошельков (бесплатный/премиум лимиты)
2. Проверьте форматы уведомлений
3. Протестируйте моковые платежи

## Оптимизация для быстрой разработки

1. Начните с базовой структуры и минимального функционала
2. Сначала реализуйте базовые команды, затем систему мониторинга
3. В последнюю очередь добавьте платежную систему
4. Используйте простые инлайн-клавиатуры вместо сложных интерфейсов

## Дополнительные рекомендации

- По умолчанию бот должен работать даже при ошибках API
- Добавьте команду /help с описанием всех возможностей
- Создайте понятные сообщения об ошибках
- Предусмотрите защиту от флуда и частых запросов