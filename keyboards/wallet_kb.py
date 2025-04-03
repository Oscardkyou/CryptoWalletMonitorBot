from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

def generate_wallets_keyboard(wallets: List) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру со списком кошельков пользователя
    """
    buttons = []
    
    for wallet in wallets:
        # Формируем сокращенную версию адреса
        short_address = f"{wallet.address[:6]}...{wallet.address[-4:]}"
        
        # Формируем текст кнопки
        button_text = f"{wallet.label or 'Без метки'} - {wallet.blockchain_type.value} ({short_address})"
        
        # Добавляем кнопку для каждого кошелька
        buttons.append([
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"wallet:{wallet.id}"
            )
        ])
    
    # Добавляем кнопку "Отмена"
    buttons.append([
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="wallets:back"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def generate_wallet_actions_keyboard(wallet_id: int) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру с действиями для выбранного кошелька
    """
    kb = [
        [
            InlineKeyboardButton(
                text="💰 Баланс",
                callback_data=f"wallet_action:{wallet_id}:balance"
            ),
            InlineKeyboardButton(
                text="📊 Транзакции",
                callback_data=f"wallet_action:{wallet_id}:transactions"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить метку",
                callback_data=f"wallet_action:{wallet_id}:edit_label"
            ),
            InlineKeyboardButton(
                text="🗑️ Удалить",
                callback_data=f"wallet_action:{wallet_id}:delete"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"wallet_action:{wallet_id}:back"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_transaction_limit_keyboard(wallet_id: int) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру для выбора количества транзакций
    """
    kb = [
        [
            InlineKeyboardButton(
                text="5",
                callback_data=f"tx_count:{wallet_id}:5"
            ),
            InlineKeyboardButton(
                text="10",
                callback_data=f"tx_count:{wallet_id}:10"
            ),
            InlineKeyboardButton(
                text="20",
                callback_data=f"tx_count:{wallet_id}:20"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"tx_count:{wallet_id}:back"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)