from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import MONTHLY_SUBSCRIPTION_PRICE, YEARLY_SUBSCRIPTION_PRICE

def get_subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора плана подписки"""
    kb = [
        [InlineKeyboardButton(text="📆 Месячная подписка (3$)", callback_data="subscription:monthly")],
        [InlineKeyboardButton(text="📅 Годовая подписка (30$)", callback_data="subscription:yearly")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="subscription:cancel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_payment_methods_keyboard(plan_type: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа оплаты"""
    kb = [
        [InlineKeyboardButton(text="💰 Криптовалюта", callback_data=f"payment:{plan_type}:crypto")],
        [InlineKeyboardButton(text="💳 Банковская карта", callback_data=f"payment:{plan_type}:card")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"payment:{plan_type}:back")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="subscription:cancel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_crypto_selection_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора криптовалюты для оплаты"""
    kb = [
        [InlineKeyboardButton(text="₿ Bitcoin (BTC)", callback_data=f"crypto:{payment_id}:btc")],
        [InlineKeyboardButton(text="Ξ Ethereum (ETH)", callback_data=f"crypto:{payment_id}:eth")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"crypto:{payment_id}:back")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="subscription:cancel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_check_payment_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для проверки статуса платежа"""
    kb = [
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment:{payment_id}")],
        [InlineKeyboardButton(text="❌ Отменить платеж", callback_data=f"cancel_payment:{payment_id}")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=kb) 