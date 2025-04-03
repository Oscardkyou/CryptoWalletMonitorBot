import logging
from aiogram import Bot
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def send_transaction_notification(bot: Bot, user_id: int, transaction, wallet):
    """Отправляет уведомление о новой транзакции пользователю"""
    try:
        # Определяем тип транзакции (входящая или исходящая)
        tx_type = "входящая" if wallet.address.lower() == transaction.to_address.lower() else "исходящая"
        
        # Определяем символ валюты в зависимости от типа блокчейна
        currency = {
            "ETH": "ETH",
            "BTC": "BTC",
            "BNB": "BNB"
        }.get(wallet.blockchain_type.value, "")
        
        # Форматируем сумму транзакции
        amount = f"{transaction.value:.8f}".rstrip('0').rstrip('.') if transaction.value else "0"
        
        # Форматируем дату и время транзакции
        timestamp = transaction.timestamp.strftime("%d.%m.%Y %H:%M:%S UTC") if transaction.timestamp else "неизвестно"
        
        # Сокращаем адреса для читаемости
        from_addr_short = f"{transaction.from_address[:8]}...{transaction.from_address[-6:]}" if transaction.from_address else "неизвестно"
        to_addr_short = f"{transaction.to_address[:8]}...{transaction.to_address[-6:]}" if transaction.to_address else "неизвестно"
        
        # Формируем текст уведомления
        message_text = (
            f"🔔 <b>Новая {tx_type} транзакция!</b>\n\n"
            f"<b>Кошелёк:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
            f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
            f"<b>Сумма:</b> {amount} {currency}\n"
            f"<b>От:</b> {from_addr_short}\n"
            f"<b>Кому:</b> {to_addr_short}\n"
            f"<b>Время:</b> {timestamp}\n\n"
            f"<b>Хеш транзакции:</b> {transaction.hash[:10]}...{transaction.hash[-8:]}"
        )
        
        # Формируем URL для просмотра транзакции в обозревателе блокчейна
        explorer_url = None
        if wallet.blockchain_type.value == "ETH":
            explorer_url = f"https://etherscan.io/tx/{transaction.hash}"
        elif wallet.blockchain_type.value == "BTC":
            explorer_url = f"https://www.blockchain.com/btc/tx/{transaction.hash}"
        elif wallet.blockchain_type.value == "BNB":
            explorer_url = f"https://bscscan.com/tx/{transaction.hash}"
        
        # Добавляем кнопку для просмотра транзакции, если есть URL
        if explorer_url:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Просмотреть транзакцию", url=explorer_url))
            
            # Отправляем сообщение с кнопкой
            await bot.send_message(user_id, message_text, parse_mode="HTML", reply_markup=keyboard)
        else:
            # Отправляем сообщение без кнопки
            await bot.send_message(user_id, message_text, parse_mode="HTML")
        
        logger.info(f"Отправлено уведомление о транзакции пользователю {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления: {e}")
        return False

async def format_transaction_notification(wallet, transaction) -> str:
    """
    Форматирует уведомление о новой транзакции
    
    :param wallet: Объект кошелька
    :param transaction: Данные транзакции
    :return: Отформатированный текст сообщения
    """
    # Определяем, входящая или исходящая транзакция
    is_incoming = wallet.address.lower() != transaction.get("from", "").lower()
    tx_type = "⬅️ Входящая" if is_incoming else "➡️ Исходящая"
    
    # Форматируем сумму
    value = transaction.get("value", 0)
    formatted_value = f"{value:.8f}".rstrip('0').rstrip('.')
    
    # Определяем символ валюты
    currency = wallet.blockchain_type.value
    
    # Форматируем время
    timestamp = transaction.get("timestamp")
    formatted_time = timestamp.strftime("%d.%m.%Y %H:%M:%S") if timestamp else datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Формируем сообщение
    message = (
        f"🔔 <b>Новая транзакция</b> 🔔\n\n"
        f"<b>Кошелек:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
        f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
        f"<b>Тип:</b> {tx_type}\n"
        f"<b>Сумма:</b> {formatted_value} {currency}\n"
    )
    
    # Добавляем информацию от кого/кому в зависимости от типа транзакции
    if is_incoming:
        from_addr = transaction.get("from", "неизвестно")
        from_addr_short = f"{from_addr[:8]}...{from_addr[-6:]}" if from_addr != "неизвестно" else "неизвестно"
        message += f"<b>От:</b> {from_addr_short}\n"
    else:
        to_addr = transaction.get("to", "неизвестно")
        to_addr_short = f"{to_addr[:8]}...{to_addr[-6:]}" if to_addr != "неизвестно" else "неизвестно"
        message += f"<b>Кому:</b> {to_addr_short}\n"
    
    # Добавляем информацию о времени и хеше транзакции
    message += (
        f"<b>Время:</b> {formatted_time}\n"
        f"<b>Хеш транзакции:</b> <code>{transaction.get('hash', 'неизвестно')}</code>\n"
    )
    
    # Добавляем ссылку на обозреватель блокчейна
    explorer_url = None
    
    if wallet.blockchain_type.value == "ETH":
        explorer_url = f"https://etherscan.io/tx/{transaction.get('hash')}"
    elif wallet.blockchain_type.value == "BTC":
        explorer_url = f"https://www.blockchain.com/btc/tx/{transaction.get('hash')}"
    elif wallet.blockchain_type.value == "BNB":
        explorer_url = f"https://bscscan.com/tx/{transaction.get('hash')}"
    
    if explorer_url:
        message += f"\n<a href='{explorer_url}'>Посмотреть на обозревателе</a>"
    
    return message

async def send_balance_notification(bot, user_id: int, wallet, balance: float) -> None:
    """
    Отправляет уведомление о текущем балансе кошелька
    
    :param bot: Объект бота
    :param user_id: ID пользователя
    :param wallet: Объект кошелька
    :param balance: Текущий баланс
    """
    try:
        # Форматируем сумму баланса
        formatted_balance = f"{balance:.8f}".rstrip('0').rstrip('.')
        
        # Создаем сообщение
        message = (
            f"💰 <b>Текущий баланс кошелька</b>\n\n"
            f"<b>Кошелек:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
            f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
            f"<b>Баланс:</b> {formatted_balance} {wallet.blockchain_type.value}\n"
        )
        
        # Формируем URL для просмотра кошелька в обозревателе блокчейна
        explorer_url = None
        if wallet.blockchain_type.value == "ETH":
            explorer_url = f"https://etherscan.io/address/{wallet.address}"
        elif wallet.blockchain_type.value == "BTC":
            explorer_url = f"https://www.blockchain.com/btc/address/{wallet.address}"
        elif wallet.blockchain_type.value == "BNB":
            explorer_url = f"https://bscscan.com/address/{wallet.address}"
        
        if explorer_url:
            message += f"\n<a href='{explorer_url}'>Посмотреть на обозревателе</a>"
        
        # Отправляем сообщение
        await bot.send_message(
            user_id,
            message,
            parse_mode="HTML"
        )
        
        logger.info(f"Отправлено уведомление о балансе для кошелька {wallet.address} пользователю {user_id}")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о балансе: {e}") 