from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import logging
import os

from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
from models.base import Base
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from models.subscription import Subscription

# Формирование строки подключения
# Для тестирования используем SQLite
DATABASE_URL = "sqlite+aiosqlite:///crypto_monitor.db"

# Создаем движок базы данных
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных и создание таблиц"""
    try:
        async with engine.begin() as conn:
            # Создание всех таблиц, которые еще не существуют
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

async def get_session():
    """Возвращает сессию базы данных"""
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка в сессии базы данных: {e}")
            raise
        finally:
            await session.close()

# Функции для работы с пользователями
async def get_or_create_user(session, user_id, username=None, full_name=None, language_code=None):
    """Получает существующего пользователя или создает нового"""
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalars().first()
    
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            full_name=full_name,
            language_code=language_code
        )
        session.add(user)
        await session.commit()
        logger.info(f"Создан новый пользователь: {user_id}")
    
    return user

# Функции для работы с кошельками
async def get_user_wallets(session, user_id):
    """Получает список кошельков пользователя"""
    result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
    return result.scalars().all()

async def get_wallets_count(session, user_id):
    """Возвращает количество кошельков пользователя"""
    result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallets = result.scalars().all()
    return len(wallets)

async def add_wallet(session, user_id, address, blockchain_type, label=None):
    """Добавляет новый кошелек для пользователя"""
    wallet = Wallet(
        user_id=user_id,
        address=address,
        blockchain_type=blockchain_type,
        label=label
    )
    session.add(wallet)
    await session.commit()
    return wallet

async def get_wallet_by_id(session, wallet_id):
    """Получает кошелек по его ID"""
    result = await session.execute(select(Wallet).where(Wallet.id == wallet_id))
    return result.scalars().first()

async def update_wallet_label(session, wallet_id, new_label):
    """Обновляет метку кошелька"""
    wallet = await get_wallet_by_id(session, wallet_id)
    if wallet:
        wallet.label = new_label
        await session.commit()
        return True
    return False

async def delete_wallet(session, wallet_id):
    """Удаляет кошелек по его ID"""
    wallet = await get_wallet_by_id(session, wallet_id)
    if wallet:
        await session.delete(wallet)
        await session.commit()
        return True
    return False 