import logging
import aiohttp
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import os
from aiohttp import ClientSession

from models.wallet import BlockchainType, TransactionType, Transaction
from config import ETHERSCAN_API_KEY, BSCSCAN_API_KEY

logger = logging.getLogger(__name__)

# API URLs
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
BSCSCAN_API_URL = "https://api.bscscan.com/api"
BLOCKCHAIN_INFO_URL = "https://blockchain.info/rawaddr"
BLOCKCYPHER_API_URL = "https://api.blockcypher.com/v1/btc/main"
BLOCKCYPHER_API_KEY = os.getenv("BLOCKCYPHER_API_KEY")

logger = logging.getLogger(__name__)

# API URLs
ETHERSCAN_API_URL = "https://api.etherscan.io/api"
BSCSCAN_API_URL = "https://api.bscscan.com/api"
BLOCKCHAIN_INFO_URL = "https://blockchain.info/rawaddr"

async def validate_address(blockchain_type: BlockchainType, address: str) -> bool:
    """
    Проверяет валидность адреса для указанного блокчейна
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес для проверки
    :return: True, если адрес валиден, иначе False
    """
    try:
        if blockchain_type == BlockchainType.ETH:
            # Базовая проверка формата Ethereum-адреса
            address = address.lower()
            if not address.startswith('0x'):
                return False
            
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            
            # Проверяем, что все символы после 0x - шестнадцатеричные
            try:
                int(address[2:], 16)
                return True
            except ValueError:
                return False
        
        elif blockchain_type == BlockchainType.BTC:
            # Базовая проверка формата Bitcoin-адреса
            # Bitcoin-адреса могут начинаться с 1, 3 или bc1
            if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
                return False
            
            if len(address) < 26 or len(address) > 35:
                return False
                
            return True
        
        elif blockchain_type == BlockchainType.BNB:
            # Адреса BNB на Binance Smart Chain имеют такой же формат, как и Ethereum
            address = address.lower()
            if not address.startswith('0x'):
                return False
            
            if len(address) != 42:  # 0x + 40 hex chars
                return False
            
            # Проверяем, что все символы после 0x - шестнадцатеричные
            try:
                int(address[2:], 16)
                return True
            except ValueError:
                return False
        
        return False
    
    except Exception as e:
        logger.error(f"Ошибка при валидации адреса {address} для {blockchain_type.value}: {e}")
        return False

async def check_address_valid(blockchain_type: BlockchainType, address: str) -> bool:
    """
    Проверяет валидность адреса для указанного блокчейна
    Алиас для функции validate_address
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес для проверки
    :return: True, если адрес валиден, иначе False
    """
    return await validate_address(blockchain_type, address)

async def check_balance(blockchain_type: BlockchainType, address: str) -> Optional[float]:
    """
    Получает текущий баланс кошелька
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес кошелька
    :return: Баланс кошелька в криптовалюте или None в случае ошибки
    """
    try:
        if blockchain_type == BlockchainType.ETH:
            return await check_eth_balance(address)
        elif blockchain_type == BlockchainType.BTC:
            return await check_btc_balance(address)
        elif blockchain_type == BlockchainType.BNB:
            return await check_bnb_balance(address)
        
        return None
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса для {address} ({blockchain_type.value}): {e}")
        return None

async def get_balance(blockchain_type: BlockchainType, address: str) -> Optional[float]:
    """
    Получает текущий баланс кошелька
    Алиас для функции check_balance
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес кошелька
    :return: Баланс кошелька в криптовалюте или None в случае ошибки
    """
    return await check_balance(blockchain_type, address)

async def get_transactions(blockchain_type: BlockchainType, address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получает список транзакций для указанного адреса
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес кошелька
    :param limit: Максимальное количество транзакций
    :return: Список транзакций
    """
    try:
        if blockchain_type == BlockchainType.ETH:
            return await get_eth_transactions(address, limit)
        elif blockchain_type == BlockchainType.BTC:
            return await get_btc_transactions(address, limit)
        elif blockchain_type == BlockchainType.BNB:
            return await get_bnb_transactions(address, limit)
        
        return []
    
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций для {address} ({blockchain_type.value}): {e}")
        return []

async def check_new_transactions(blockchain_type: BlockchainType, address: str, last_checked: datetime = None) -> List[Dict[str, Any]]:
    """
    Проверяет новые транзакции с момента последней проверки
    
    :param blockchain_type: Тип блокчейна (ETH, BTC, BNB)
    :param address: Адрес кошелька
    :param last_checked: Время последней проверки
    :return: Список новых транзакций
    """
    try:
        transactions = await get_transactions(blockchain_type, address, 20)
        
        if not last_checked:
            return transactions[:5]  # Возвращаем только 5 последних транзакций, если нет времени последней проверки
        
        # Фильтруем транзакции, которые произошли после последней проверки
        new_transactions = []
        for tx in transactions:
            tx_timestamp = tx.get('timestamp')
            if tx_timestamp and tx_timestamp > last_checked:
                new_transactions.append(tx)
        
        return new_transactions
    
    except Exception as e:
        logger.error(f"Ошибка при проверке новых транзакций для {address} ({blockchain_type.value}): {e}")
        return []

# Ethereum-specific functions
async def check_eth_balance(address: str) -> Optional[float]:
    """
    Получает баланс Ethereum-адреса
    
    :param address: Ethereum-адрес
    :return: Баланс в ETH или None в случае ошибки
    """
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ETHERSCAN_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API Etherscan ({response.status}): {await response.text()}")
                    return None
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_message = data.get("message", "Unknown error")
                    logger.error(f"Ошибка API Etherscan: {error_message}")
                    return None
                
                # Convert wei to ETH (1 ETH = 10^18 wei)
                balance_wei = int(data.get("result", "0"))
                balance_eth = balance_wei / 10**18
                
                return balance_eth
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса ETH для {address}: {e}")
        return None

async def get_eth_transactions(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получает список транзакций для Ethereum-адреса
    
    :param address: Ethereum-адрес
    :param limit: Максимальное количество транзакций
    :return: Список транзакций
    """
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "page": "1",
        "offset": str(min(limit, 100)),  # Максимум 100 транзакций
        "sort": "desc",  # От новых к старым
        "apikey": ETHERSCAN_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ETHERSCAN_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API Etherscan ({response.status}): {await response.text()}")
                    return []
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_message = data.get("message", "Unknown error")
                    
                    # Если транзакций нет, это не ошибка
                    if "No transactions found" in error_message:
                        return []
                    
                    logger.error(f"Ошибка API Etherscan: {error_message}")
                    return []
                
                transactions = data.get("result", [])
                formatted_transactions = []
                
                for tx in transactions[:limit]:
                    # Convert timestamp to datetime
                    timestamp = datetime.fromtimestamp(int(tx.get("timeStamp", 0)))
                    
                    # Convert value from wei to ETH
                    value_wei = int(tx.get("value", "0"))
                    value_eth = value_wei / 10**18
                    
                    formatted_tx = {
                        "hash": tx.get("hash"),
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value": value_eth,
                        "timestamp": timestamp,
                        "confirmations": int(tx.get("confirmations", 0)),
                        "block_number": int(tx.get("blockNumber", 0)),
                        "block_hash": tx.get("blockHash"),
                        "gas": int(tx.get("gas", 0)),
                        "gas_price": int(tx.get("gasPrice", 0)) / 10**9,  # Convert wei to gwei
                        "is_error": tx.get("isError") == "1"
                    }
                    
                    formatted_transactions.append(formatted_tx)
                
                return formatted_transactions
    
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций ETH для {address}: {e}")
        return []

# Bitcoin-specific functions
async def check_btc_balance(address: str) -> Optional[float]:
    """
    Получает баланс Bitcoin-адреса
    
    :param address: Bitcoin-адрес
    :return: Баланс в BTC или None в случае ошибки
    """
    params = {
        "token": BLOCKCYPHER_API_KEY,
        "address": address
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BLOCKCYPHER_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API BlockCypher ({response.status}): {await response.text()}")
                    return None
                
                data = await response.json()
                
                if data.get("error"):
                    error_message = data.get("error", "Unknown error")
                    logger.error(f"Ошибка API BlockCypher: {error_message}")
                    return None
                
                # Convert satoshi to BTC (1 BTC = 10^8 satoshi)
                balance_sat = int(data.get("final_balance", "0"))
                balance_btc = balance_sat / 10**8
                
                return balance_btc
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса BTC для {address}: {e}")
        return None

async def get_btc_transactions(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получает список транзакций для Bitcoin-адреса
    
    :param address: Bitcoin-адрес
    :param limit: Максимальное количество транзакций
    :return: Список транзакций
    """
    params = {
        "token": BLOCKCYPHER_API_KEY,
        "limit": limit
    }
    
    try:
        url = f"{BLOCKCYPHER_API_URL}/addrs/{address}/full"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API BlockCypher ({response.status}): {await response.text()}")
                    return []
                
                data = await response.json()
                
                if data.get("error"):
                    error_message = data.get("error", "Unknown error")
                    logger.error(f"Ошибка API BlockCypher: {error_message}")
                    return []
                
                transactions = []
                
                # Обрабатываем каждую транзакцию
                for tx in data.get("txs", [])[:limit]:
                    # Получаем временную метку транзакции
                    timestamp = tx.get("received")
                    if timestamp:
                        tx_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        tx_date = datetime.now()
                    
                    # Пропускаем транзакции без временной метки
                    if not tx_date:
                        continue
                    
                    # Определяем тип транзакции (входящая или исходящая)
                    tx_type = None
                    value = 0
                    
                    # Проверяем входы и выходы транзакции
                    is_sender = False
                    is_receiver = False
                    
                    # Проверяем, является ли адрес отправителем
                    for input_tx in tx.get("inputs", []):
                        input_addresses = input_tx.get("addresses", [])
                        if address in input_addresses:
                            is_sender = True
                            break
                    
                    # Проверяем, является ли адрес получателем
                    for output_tx in tx.get("outputs", []):
                        output_addresses = output_tx.get("addresses", [])
                        if address in output_addresses:
                            is_receiver = True
                            value += output_tx.get("value", 0)
                    
                    # Определяем тип транзакции
                    if is_sender and is_receiver:
                        # Это может быть самоотправка или сдача
                        tx_type = TransactionType.OUTGOING
                    elif is_sender:
                        tx_type = TransactionType.OUTGOING
                    elif is_receiver:
                        tx_type = TransactionType.INCOMING
                    else:
                        # Пропускаем транзакции, не связанные с этим адресом
                        continue
                    
                    # Конвертируем сатоши в BTC
                    value_btc = value / 10**8
                    
                    # Определяем адрес контрагента
                    counterparty_address = ""
                    if tx_type == TransactionType.OUTGOING:
                        # Для исходящих транзакций ищем первый адрес получателя, отличный от нашего
                        for output in tx.get("outputs", []):
                            for addr in output.get("addresses", []):
                                if addr != address:
                                    counterparty_address = addr
                                    break
                            if counterparty_address:
                                break
                    else:
                        # Для входящих транзакций ищем первый адрес отправителя
                        for input_tx in tx.get("inputs", []):
                            for addr in input_tx.get("addresses", []):
                                if addr != address:
                                    counterparty_address = addr
                                    break
                            if counterparty_address:
                                break
                    
                    # Создаем объект транзакции
                    transaction = {
                        "hash": tx.get("hash", ""),
                        "from": address if tx_type == TransactionType.OUTGOING else counterparty_address,
                        "to": counterparty_address if tx_type == TransactionType.OUTGOING else address,
                        "value": value_btc,
                        "timestamp": tx_date,
                        "confirmations": tx.get("confirmations", 0),
                        "block_number": tx.get("block_height", 0),
                        "block_hash": tx.get("block_hash", ""),
                        "fee": tx.get("fees", 0) / 10**8  # Конвертируем сатоши в BTC
                    }
                    
                    transactions.append(transaction)
                
                return transactions
                
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций BTC для {address}: {e}")
        return []

# Binance Smart Chain-specific functions
async def check_bnb_balance(address: str) -> Optional[float]:
    """
    Получает баланс Binance Smart Chain-адреса
    
    :param address: BSC-адрес
    :return: Баланс в BNB или None в случае ошибки
    """
    params = {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest",
        "apikey": BSCSCAN_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BSCSCAN_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API BscScan ({response.status}): {await response.text()}")
                    return None
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_message = data.get("message", "Unknown error")
                    logger.error(f"Ошибка API BscScan: {error_message}")
                    return None
                
                # Convert wei to BNB (1 BNB = 10^18 wei)
                balance_wei = int(data.get("result", "0"))
                balance_bnb = balance_wei / 10**18
                
                return balance_bnb
    
    except Exception as e:
        logger.error(f"Ошибка при получении баланса BNB для {address}: {e}")
        return None

async def get_bnb_transactions(address: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Получает список транзакций для Binance Smart Chain-адреса
    
    :param address: BSC-адрес
    :param limit: Максимальное количество транзакций
    :return: Список транзакций
    """
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "page": "1",
        "offset": str(min(limit, 100)),  # Максимум 100 транзакций
        "sort": "desc",  # От новых к старым
        "apikey": BSCSCAN_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BSCSCAN_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"Ошибка API BscScan ({response.status}): {await response.text()}")
                    return []
                
                data = await response.json()
                
                if data.get("status") != "1":
                    error_message = data.get("message", "Unknown error")
                    
                    # Если транзакций нет, это не ошибка
                    if "No transactions found" in error_message:
                        return []
                    
                    logger.error(f"Ошибка API BscScan: {error_message}")
                    return []
                
                transactions = data.get("result", [])
                formatted_transactions = []
                
                for tx in transactions[:limit]:
                    # Convert timestamp to datetime
                    timestamp = datetime.fromtimestamp(int(tx.get("timeStamp", 0)))
                    
                    # Convert value from wei to BNB
                    value_wei = int(tx.get("value", "0"))
                    value_bnb = value_wei / 10**18
                    
                    formatted_tx = {
                        "hash": tx.get("hash"),
                        "from": tx.get("from"),
                        "to": tx.get("to"),
                        "value": value_bnb,
                        "timestamp": timestamp,
                        "confirmations": int(tx.get("confirmations", 0)),
                        "block_number": int(tx.get("blockNumber", 0)),
                        "block_hash": tx.get("blockHash"),
                        "gas": int(tx.get("gas", 0)),
                        "gas_price": int(tx.get("gasPrice", 0)) / 10**9,  # Convert wei to gwei
                        "is_error": tx.get("isError") == "1"
                    }
                    
                    formatted_transactions.append(formatted_tx)
                
                return formatted_transactions
    
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций BNB для {address}: {e}")
        return []

async def get_latest_transactions(address: str, blockchain_type: BlockchainType, limit: int = 5) -> List[Transaction]:
    """
    Получает последние транзакции для указанного адреса кошелька.
    
    Args:
        address: Адрес кошелька
        blockchain_type: Тип блокчейна
        limit: Количество транзакций для получения
    
    Returns:
        Список объектов Transaction с информацией о транзакциях
    """
    logger.info(f"Получение {limit} последних транзакций для {address} ({blockchain_type.value})")
    
    if blockchain_type == BlockchainType.ETH:
        try:
            api_key = os.getenv("ETHERSCAN_API_KEY")
            if not api_key:
                logger.error("ETHERSCAN_API_KEY не найден в переменных окружения")
                return []
                
            # Формируем URL для API Etherscan
            base_url = "https://api.etherscan.io/api"
            
            # Получаем транзакции, где адрес является отправителем
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "page": 1,
                "offset": limit,
                "sort": "desc",
                "apikey": api_key
            }
            
            async with ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка API Etherscan: {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    if data["status"] != "1":
                        logger.error(f"Ошибка API Etherscan: {data.get('message', 'Неизвестная ошибка')}")
                        return []
                    
                    transactions = []
                    
                    # Обрабатываем каждую транзакцию
                    for tx in data["result"][:limit]:
                        # Конвертируем временную метку из строки в число
                        timestamp = int(tx.get("timeStamp", 0)) if tx.get("timeStamp") else 0
                        
                        # Пропускаем транзакции без временной метки
                        if timestamp == 0:
                            continue
                            
                        tx_date = datetime.fromtimestamp(timestamp) if timestamp else None
                        
                        # Пропускаем, если дата не определена
                        if not tx_date:
                            continue
                        
                        # Конвертируем значение из Wei в Ether
                        value_wei = int(tx.get("value", "0"))
                        value_eth = value_wei / 10**18
                        
                        # Определяем тип транзакции (входящая или исходящая)
                        tx_type = TransactionType.OUTGOING if tx.get("from", "").lower() == address.lower() else TransactionType.INCOMING
                        
                        # Создаем объект транзакции
                        transaction = Transaction(
                            txid=tx.get("hash", ""),
                            date=tx_date,
                            amount=value_eth,
                            fee=float(tx.get("gasPrice", 0)) * float(tx.get("gasUsed", 0)) / 10**18,
                            confirmations=int(tx.get("confirmations", 0)) if tx.get("confirmations") else 0,
                            type=tx_type,
                            address=tx.get("to" if tx_type == TransactionType.OUTGOING else "from", ""),
                            blockchain_type=blockchain_type
                        )
                        
                        transactions.append(transaction)
                    
                    return transactions
                        
        except Exception as e:
            logger.error(f"Ошибка при получении транзакций ETH: {e}")
            return []
            
    elif blockchain_type == BlockchainType.BTC:
        try:
            # Получаем транзакции через BlockCypher API
            raw_transactions = await get_btc_transactions(address, limit)
            
            if not raw_transactions:
                return []
            
            transactions = []
            
            # Преобразуем сырые данные транзакций в объекты Transaction
            for tx in raw_transactions:
                # Получаем дату транзакции
                tx_date = tx.get("timestamp")
                if not isinstance(tx_date, datetime):
                    continue
                
                # Получаем сумму транзакции
                value_btc = tx.get("value", 0)
                
                # Определяем тип транзакции
                from_address = tx.get("from", "")
                to_address = tx.get("to", "")
                
                if from_address.lower() == address.lower():
                    tx_type = TransactionType.OUTGOING
                    counterparty_address = to_address
                else:
                    tx_type = TransactionType.INCOMING
                    counterparty_address = from_address
                
                # Создаем объект транзакции
                transaction = Transaction(
                    txid=tx.get("hash", ""),
                    date=tx_date,
                    amount=value_btc,
                    fee=tx.get("fee", 0),
                    confirmations=tx.get("confirmations", 0),
                    type=tx_type,
                    address=counterparty_address,
                    blockchain_type=blockchain_type
                )
                
                transactions.append(transaction)
            
            return transactions
            
        except Exception as e:
            logger.error(f"Ошибка при получении транзакций BTC: {e}")
            return []
            
    elif blockchain_type == BlockchainType.BNB:
        # Заглушка для BNB
        logger.warning("Получение транзакций для BNB пока не реализовано")
        return []
        
    return [] 