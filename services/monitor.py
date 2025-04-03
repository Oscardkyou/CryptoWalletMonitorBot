import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import MONITOR_INTERVAL
from models.wallet import Wallet, BlockchainType
from models.transaction import Transaction
from services.blockchain import get_transactions
from services.db import async_session
from utils.notifications import send_transaction_notification

logger = logging.getLogger(__name__)

async def check_wallet_transactions(bot, wallet, session):
    """Проверяет новые транзакции для кошелька и отправляет уведомления"""
    logger.info(f"Проверка транзакций для кошелька {wallet.address} ({wallet.blockchain_type.value})")
    
    # Определяем время последней проверки
    from_timestamp = wallet.last_checked_timestamp
    
    # Получаем транзакции
    transactions = await get_transactions(wallet.blockchain_type, wallet.address, from_timestamp)
    
    # Если транзакции обнаружены
    if transactions:
        logger.info(f"Обнаружено {len(transactions)} новых транзакций для кошелька {wallet.address}")
        
        # Обрабатываем каждую транзакцию
        for tx_data in transactions:
            # Проверяем, существует ли уже такая транзакция
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == tx_data["tx_id"])
            )
            existing_tx = result.scalars().first()
            
            if not existing_tx:
                # Создаем новую запись о транзакции
                new_tx = Transaction(
                    tx_id=tx_data["tx_id"],
                    wallet_id=wallet.wallet_id,
                    hash=tx_data["hash"],
                    from_address=tx_data["from"],
                    to_address=tx_data["to"],
                    value=tx_data["value"],
                    timestamp=tx_data["timestamp"],
                    block_number=tx_data["block_number"],
                    notification_sent=False
                )
                
                session.add(new_tx)
                await session.commit()
                
                # Отправляем уведомление
                await send_transaction_notification(bot, wallet.user_id, new_tx, wallet)
                
                # Отмечаем, что уведомление отправлено
                new_tx.notification_sent = True
                await session.commit()
    
    # Обновляем время последней проверки
    wallet.last_checked_timestamp = datetime.utcnow()
    await session.commit()

async def monitor_wallets(bot):
    """Периодически проверяет все кошельки на наличие новых транзакций"""
    logger.info("Запуск мониторинга кошельков")
    
    while True:
        try:
            async with async_session() as session:
                # Получаем все кошельки из базы данных
                result = await session.execute(select(Wallet))
                wallets = result.scalars().all()
                
                if wallets:
                    logger.info(f"Проверка {len(wallets)} кошельков")
                    
                    # Запускаем проверку кошельков параллельно
                    tasks = [check_wallet_transactions(bot, wallet, session) for wallet in wallets]
                    await asyncio.gather(*tasks)
                else:
                    logger.info("Нет кошельков для мониторинга")
                
        except Exception as e:
            logger.error(f"Ошибка при мониторинге кошельков: {e}")
        
        # Ждем перед следующей проверкой
        await asyncio.sleep(MONITOR_INTERVAL)

async def start_wallet_monitor(bot):
    """Запускает мониторинг кошельков в фоновом режиме"""
    try:
        await monitor_wallets(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске мониторинга кошельков: {e}")
        # Перезапуск при сбое
        await asyncio.sleep(5)
        await start_wallet_monitor(bot) 