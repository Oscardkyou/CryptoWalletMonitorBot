from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Генерирует основную клавиатуру с главными функциями
    """
    kb = [
        [
            KeyboardButton(text="💼 Мои кошельки"),
            KeyboardButton(text="➕ Добавить кошелек")
        ],
        [
            KeyboardButton(text="💰 Проверить баланс"),
            KeyboardButton(text="📊 Транзакции")
        ],
        [
            KeyboardButton(text="⭐ Подписка"),
            KeyboardButton(text="⚙️ Настройки")
        ],
        [
            KeyboardButton(text="ℹ️ Помощь")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Генерирует клавиатуру с единственной кнопкой отмены
    """
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру с кнопкой возврата назад
    """
    kb = [[KeyboardButton(text="◀️ Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_blockchain_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру для выбора типа блокчейна
    """
    kb = [
        [
            InlineKeyboardButton(
                text="ETH (Ethereum)",
                callback_data="blockchain:ETH"
            ),
            InlineKeyboardButton(
                text="BTC (Bitcoin)",
                callback_data="blockchain:BTC"
            )
        ],
        [
            InlineKeyboardButton(
                text="BNB (Binance Smart Chain)",
                callback_data="blockchain:BNB"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="blockchain:cancel"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_yes_no_keyboard(action_prefix: str) -> InlineKeyboardMarkup:
    """
    Генерирует инлайн-клавиатуру для подтверждения действия (Да/Нет)
    
    :param action_prefix: Префикс для callback_data (например, "delete_wallet:123")
    :return: Клавиатура с кнопками Да и Нет
    """
    kb = [
        [
            InlineKeyboardButton(
                text="✅ Да",
                callback_data=f"{action_prefix}:yes"
            ),
            InlineKeyboardButton(
                text="❌ Нет",
                callback_data=f"{action_prefix}:no"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb) 