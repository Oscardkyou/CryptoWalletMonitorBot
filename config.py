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