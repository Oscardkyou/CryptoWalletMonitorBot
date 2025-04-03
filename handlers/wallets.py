import logging
from aiogram import Router, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.future import select

from models.wallet import Wallet, BlockchainType, TransactionType, Transaction
from models.user import User, SubscriptionLevel
from services.db import async_session, get_user_wallets, get_wallets_count, add_wallet, get_wallet_by_id, update_wallet_label, delete_wallet
from services.blockchain import check_address_valid, get_balance, get_latest_transactions
from keyboards.common_kb import get_main_keyboard, get_cancel_keyboard, get_blockchain_selection_keyboard, get_yes_no_keyboard
from keyboards.wallet_kb import generate_wallets_keyboard, generate_wallet_actions_keyboard, get_transaction_limit_keyboard
from utils.notifications import send_balance_notification
from config import FREE_WALLET_LIMIT, PREMIUM_WALLET_LIMIT

logger = logging.getLogger(__name__)

# Создаем роутер для обработки кошельков
router = Router()

# Определяем состояния для добавления кошелька
class AddWalletStates(StatesGroup):
    select_blockchain = State()
    enter_address = State()
    enter_label = State()

# Обработчик команды /add_wallet
@router.message(Command("add_wallet"))
@router.message(F.text == "➕ Добавить кошелек")
async def cmd_add_wallet(message: Message, state: FSMContext):
    """Обработчик команды добавления кошелька"""
    user_id = message.from_user.id
    
    # Проверяем количество кошельков пользователя
    async with async_session() as session:
        # Получаем информацию о пользователе
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalars().first()
        
        if not user:
            await message.answer(
                "❌ Произошла ошибка при получении информации о пользователе. Пожалуйста, попробуйте позже."
            )
            return
        
        # Получаем количество кошельков пользователя
        wallets_count = await get_wallets_count(session, user_id)
        
        # Определяем лимит в зависимости от подписки
        wallet_limit = PREMIUM_WALLET_LIMIT if user.subscription_level == SubscriptionLevel.premium else FREE_WALLET_LIMIT
        
        # Проверяем, не превышен ли лимит
        if wallets_count >= wallet_limit:
            if user.subscription_level == SubscriptionLevel.free:
                await message.answer(
                    f"⚠️ <b>Превышен лимит кошельков!</b>\n\n"
                    f"На бесплатном плане вы можете добавить не более {FREE_WALLET_LIMIT} кошельков.\n"
                    f"Для добавления большего количества кошельков, оформите премиум подписку командой /subscribe."
                )
            else:
                await message.answer(
                    f"⚠️ <b>Превышен лимит кошельков!</b>\n\n"
                    f"На премиум плане вы можете добавить не более {PREMIUM_WALLET_LIMIT} кошельков."
                )
            return
    
    # Предлагаем выбрать тип блокчейна
    await message.answer(
        "Выберите блокчейн для нового кошелька:",
        reply_markup=get_blockchain_selection_keyboard()
    )
    await state.set_state(AddWalletStates.select_blockchain)

# Обработчик выбора блокчейна
@router.callback_query(F.data.startswith("blockchain:"), AddWalletStates.select_blockchain)
async def blockchain_selected(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик выбора блокчейна"""
    blockchain_type = callback_query.data.split(":")[1]
    
    # Если пользователь отменил операцию
    if blockchain_type == "cancel":
        await state.clear()
        await callback_query.message.answer(
            "❌ Операция добавления кошелька отменена.",
            reply_markup=get_main_keyboard()
        )
        await callback_query.answer()
        return
    
    # Сохраняем выбранный блокчейн
    await state.update_data(blockchain_type=blockchain_type)
    
    await callback_query.message.answer(
        f"Выбран блокчейн: {blockchain_type}\n\n"
        f"Введите адрес кошелька для мониторинга:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AddWalletStates.enter_address)
    await callback_query.answer()

# Обработчик ввода адреса кошелька
@router.message(AddWalletStates.enter_address)
async def address_entered(message: Message, state: FSMContext):
    """Обработчик ввода адреса кошелька"""
    # Если пользователь отменил операцию
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Операция добавления кошелька отменена.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получаем введенный адрес
    address = message.text.strip()
    
    # Получаем тип блокчейна из состояния
    data = await state.get_data()
    blockchain_type_str = data.get("blockchain_type")
    
    try:
        # Преобразуем строку в enum
        blockchain_type = BlockchainType[blockchain_type_str]
        
        # Проверяем валидность адреса
        is_valid = await check_address_valid(blockchain_type, address)
        
        if not is_valid:
            await message.answer(
                f"⚠️ Указан некорректный адрес для блокчейна {blockchain_type.value}.\n"
                f"Пожалуйста, проверьте адрес и попробуйте снова:",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        # Сохраняем адрес
        await state.update_data(address=address)
        
        # Запрашиваем метку для кошелька
        await message.answer(
            "Введите название (метку) для кошелька или нажмите /skip, чтобы пропустить этот шаг:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(AddWalletStates.enter_label)
    except (ValueError, KeyError):
        await message.answer(
            f"⚠️ Произошла ошибка при обработке типа блокчейна.\n"
            f"Пожалуйста, начните процесс добавления кошелька заново через /add_wallet",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

# Обработчик ввода метки для кошелька
@router.message(AddWalletStates.enter_label)
async def label_entered(message: Message, state: FSMContext):
    """Обработчик ввода метки для кошелька"""
    # Если пользователь отменил операцию
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Операция добавления кошелька отменена.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получаем метку или устанавливаем пустую, если пользователь решил пропустить
    label = None if message.text == "/skip" else message.text.strip()
    
    # Получаем данные из состояния
    data = await state.get_data()
    blockchain_type_str = data.get("blockchain_type")
    address = data.get("address")
    
    try:
        # Преобразуем строку в enum
        blockchain_type = BlockchainType[blockchain_type_str]
        
        # Добавляем кошелек в базу данных
        async with async_session() as session:
            try:
                wallet = await add_wallet(session, message.from_user.id, address, blockchain_type, label)
                
                # Уведомляем пользователя об успешном добавлении
                success_message = (
                    f"✅ <b>Кошелек успешно добавлен!</b>\n\n"
                    f"<b>Блокчейн:</b> {blockchain_type.value}\n"
                    f"<b>Адрес:</b> {address[:8]}...{address[-6:]}\n"
                )
                
                if label:
                    success_message += f"<b>Метка:</b> {label}\n"
                
                success_message += (
                    f"\nБот начнет мониторить транзакции этого кошелька и уведомлять вас о новых операциях."
                )
                
                await message.answer(success_message, reply_markup=get_main_keyboard())
                
                # Проверяем текущий баланс кошелька
                balance = await get_balance(blockchain_type, address)
                if balance is not None:
                    # Отправляем уведомление о текущем балансе
                    bot = message.bot
                    await send_balance_notification(bot, message.from_user.id, wallet, balance)
                
                logger.info(f"Пользователь {message.from_user.id} добавил новый кошелек: {address} ({blockchain_type.value})")
            except Exception as e:
                logger.error(f"Ошибка при добавлении кошелька: {e}")
                await message.answer(
                    f"⚠️ Произошла ошибка при добавлении кошелька.\n"
                    f"Возможно, такой кошелек уже добавлен или произошла внутренняя ошибка.",
                    reply_markup=get_main_keyboard()
                )
    except (ValueError, KeyError) as e:
        logger.error(f"Ошибка при обработке типа блокчейна: {e}")
        await message.answer(
            f"⚠️ Произошла ошибка при обработке типа блокчейна.\n"
            f"Пожалуйста, начните процесс добавления кошелька заново через /add_wallet",
            reply_markup=get_main_keyboard()
        )
    
    # Очищаем состояние
    await state.clear()

# Обработчик команды /my_wallets
@router.message(Command("my_wallets"))
@router.message(F.text == "💼 Мои кошельки")
async def cmd_my_wallets(message: Message):
    """Обработчик команды просмотра списка кошельков"""
    user_id = message.from_user.id
    
    async with async_session() as session:
        # Получаем список кошельков пользователя
        wallets = await get_user_wallets(session, user_id)
        
        if not wallets:
            # Если у пользователя нет кошельков
            await message.answer(
                f"📭 <b>У вас пока нет добавленных кошельков.</b>\n\n"
                f"Добавьте кошелек с помощью команды /add_wallet",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Выводим список кошельков
        await message.answer(
            f"📋 <b>Ваши кошельки ({len(wallets)}):</b>\n\n"
            f"Выберите кошелек для управления:",
            reply_markup=generate_wallets_keyboard(wallets)
        )

# Обработчик выбора кошелька из списка
@router.callback_query(F.data.startswith("wallet:"))
async def wallet_selected(callback_query: CallbackQuery):
    """Обработчик выбора кошелька из списка"""
    wallet_id = int(callback_query.data.split(":")[1])
    
    # Отображаем меню действий для выбранного кошелька
    await callback_query.message.edit_text(
        f"Выберите действие для кошелька с ID {wallet_id}:",
        reply_markup=generate_wallet_actions_keyboard(wallet_id)
    )
    await callback_query.answer()

# Обработчик нажатия "Назад" в списке кошельков
@router.callback_query(F.data == "wallets:back")
async def wallets_back(callback_query: CallbackQuery):
    """Обработчик нажатия кнопки Назад в списке кошельков"""
    await callback_query.message.edit_text(
        "Действие отменено.", 
        reply_markup=None
    )
    await callback_query.answer()

# Обработчик действий с кошельком
@router.callback_query(F.data.startswith("wallet_action:"))
async def wallet_action(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик действий с кошельком"""
    parts = callback_query.data.split(":")
    
    if len(parts) < 3:
        await callback_query.answer("Ошибка обработки действия")
        return
    
    action = parts[2]
    
    if action == "back":
        # Возвращаемся к списку кошельков
        user_id = callback_query.from_user.id
        
        async with async_session() as session:
            wallets = await get_user_wallets(session, user_id)
            
            if not wallets:
                await callback_query.message.edit_text(
                    "У вас нет добавленных кошельков.",
                    reply_markup=None
                )
            else:
                await callback_query.message.edit_text(
                    f"📋 <b>Ваши кошельки ({len(wallets)}):</b>\n\n"
                    f"Выберите кошелек для управления:",
                    reply_markup=generate_wallets_keyboard(wallets)
                )
        
        await callback_query.answer()
        return
    
    wallet_id = int(parts[1])
    
    # Получаем информацию о кошельке из базы данных
    async with async_session() as session:
        result = await session.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalars().first()
        
        if not wallet:
            await callback_query.message.edit_text("Кошелек не найден.")
            await callback_query.answer()
            return
        
        if wallet.user_id != callback_query.from_user.id:
            await callback_query.answer("У вас нет доступа к этому кошельку")
            return
        
        if action == "balance":
            # Проверка баланса
            balance = await get_balance(wallet.blockchain_type, wallet.address)
            
            if balance is not None:
                # Форматируем сумму баланса
                formatted_balance = f"{balance:.8f}".rstrip('0').rstrip('.')
                
                # Определяем символ валюты в зависимости от типа блокчейна
                currency = wallet.blockchain_type.value
                
                balance_message = (
                    f"💰 <b>Баланс кошелька</b>\n\n"
                    f"<b>Кошелек:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
                    f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
                    f"<b>Текущий баланс:</b> {formatted_balance} {currency}\n\n"
                )
                
                # Формируем URL для просмотра кошелька в обозревателе блокчейна
                explorer_url = None
                if wallet.blockchain_type.value == "ETH":
                    explorer_url = f"https://etherscan.io/address/{wallet.address}"
                elif wallet.blockchain_type.value == "BTC":
                    explorer_url = f"https://www.blockchain.com/btc/address/{wallet.address}"
                elif wallet.blockchain_type.value == "BNB":
                    explorer_url = f"https://bscscan.com/address/{wallet.address}"
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = []
                
                if explorer_url:
                    kb.append([InlineKeyboardButton(text="🔍 Просмотреть на обозревателе", url=explorer_url)])
                
                kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"wallet:{wallet_id}")])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
                
                await callback_query.message.edit_text(
                    balance_message,
                    reply_markup=keyboard
                )
            else:
                from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                
                error_message = (
                    f"⚠️ <b>Ошибка при получении баланса</b>\n\n"
                    f"Не удалось получить баланс для кошелька {wallet.address[:8]}...{wallet.address[-6:]} ({wallet.blockchain_type.value}).\n"
                    f"Пожалуйста, попробуйте позже."
                )
                
                kb = [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"wallet:{wallet_id}")]]
                keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
                
                await callback_query.message.edit_text(
                    error_message,
                    reply_markup=keyboard
                )
            
            await callback_query.answer()
        
        elif action == "transactions":
            # Просмотр транзакций
            await get_wallet_transactions(callback_query, wallet_id)
        
        elif action == "edit_label":
            # Редактирование метки
            await callback_query.message.edit_text(
                f"Функция редактирования метки находится в разработке.",
                reply_markup=generate_wallet_actions_keyboard(wallet_id)
            )
            await callback_query.answer()
        
        elif action == "delete":
            # Удаление кошелька
            await callback_query.message.edit_text(
                f"Вы действительно хотите удалить этот кошелек?\n\n"
                f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n"
                f"<b>Тип:</b> {wallet.blockchain_type.value}\n"
                f"<b>Метка:</b> {wallet.label or 'Без метки'}\n\n"
                f"⚠️ Это действие нельзя отменить.",
                reply_markup=get_yes_no_keyboard(f"delete_wallet:{wallet_id}")
            )
            await callback_query.answer()

# Обработчик подтверждения удаления кошелька
@router.callback_query(F.data.startswith("delete_wallet:"))
async def delete_wallet_confirm(callback_query: CallbackQuery):
    """Обработчик подтверждения удаления кошелька"""
    parts = callback_query.data.split(":")
    answer = parts[2]  # yes или no
    
    if len(parts) < 3:
        await callback_query.answer("Ошибка обработки действия")
        return
    
    wallet_id = int(parts[1])
    
    if answer == "no":
        # Отмена удаления
        await callback_query.message.edit_text(
            "Удаление отменено.",
            reply_markup=generate_wallet_actions_keyboard(wallet_id)
        )
        await callback_query.answer()
        return
    
    # Подтверждение удаления
    async with async_session() as session:
        result = await session.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalars().first()
        
        if not wallet:
            await callback_query.message.edit_text("Кошелек не найден.")
            await callback_query.answer()
            return
        
        if wallet.user_id != callback_query.from_user.id:
            await callback_query.answer("У вас нет доступа к этому кошельку")
            return
        
        # Удаляем кошелек
        await session.delete(wallet)
        await session.commit()
        
        logger.info(f"Пользователь {callback_query.from_user.id} удалил кошелек: {wallet.address} ({wallet.blockchain_type.value})")
        
        # Получаем обновленный список кошельков
        wallets = await get_user_wallets(session, callback_query.from_user.id)
        
        if not wallets:
            await callback_query.message.edit_text(
                "✅ Кошелек успешно удален.\n\n"
                "У вас больше нет добавленных кошельков. Используйте /add_wallet, чтобы добавить новый.",
                reply_markup=None
            )
        else:
            await callback_query.message.edit_text(
                f"✅ Кошелек успешно удален.\n\n"
                f"📋 <b>Ваши кошельки ({len(wallets)}):</b>\n\n"
                f"Выберите кошелек для управления:",
                reply_markup=generate_wallets_keyboard(wallets)
            )
        
        await callback_query.answer()

# Обработчик выбора количества транзакций
@router.callback_query(F.data.startswith("tx_count:"))
async def transaction_count_selected(callback_query: CallbackQuery):
    """Обработчик выбора количества транзакций для отображения"""
    parts = callback_query.data.split(":")
    
    if len(parts) < 3:
        await callback_query.answer("Ошибка обработки действия")
        return
    
    wallet_id = int(parts[1])
    
    if parts[2] == "back":
        # Возвращаемся к меню действий
        await callback_query.message.edit_text(
            f"Выберите действие для кошелька:",
            reply_markup=generate_wallet_actions_keyboard(wallet_id)
        )
        await callback_query.answer()
        return
    
    # Парсим количество транзакций
    try:
        tx_count = int(parts[2])
    except ValueError:
        await callback_query.answer("Неверное количество транзакций")
        return
    
    # Получаем информацию о кошельке
    async with async_session() as session:
        result = await session.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalars().first()
        
        if not wallet:
            await callback_query.message.edit_text("Кошелек не найден.")
            await callback_query.answer()
            return
        
        if wallet.user_id != callback_query.from_user.id:
            await callback_query.answer("У вас нет доступа к этому кошельку")
            return
        
        # Получаем транзакции
        await get_wallet_transactions(callback_query, wallet_id, tx_count)

async def get_wallet_transactions(callback_query: CallbackQuery, wallet_id: int, limit: int = 5):
    """
    Получает и отображает последние транзакции для указанного кошелька
    """
    # Получаем данные кошелька из базы данных
    async with async_session() as session:
        wallet = await get_wallet_by_id(session, wallet_id)
        
        if not wallet:
            await callback_query.answer("Кошелек не найден")
            return
        
        # Получаем транзакции через сервис блокчейна
        transactions = await get_latest_transactions(wallet.address, wallet.blockchain_type, limit)
        
        if not transactions:
            # Создаем сообщение об отсутствии транзакций
            no_transactions_message = (
                f"📊 <b>Транзакции кошелька</b>\n\n"
                f"<b>Кошелек:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
                f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
                f"Транзакции не найдены."
            )
            
            # Создаем клавиатуру для возврата
            kb = [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"wallet:{wallet_id}")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
            
            await callback_query.message.edit_text(
                no_transactions_message,
                reply_markup=keyboard
            )
            return
        
        # Формируем сообщение со списком транзакций
        currency = wallet.blockchain_type.value
        
        header = (
            f"📊 <b>Последние {len(transactions)} транзакций</b>\n\n"
            f"<b>Кошелек:</b> {wallet.label or 'Без метки'} ({wallet.blockchain_type.value})\n"
            f"<b>Адрес:</b> {wallet.address[:8]}...{wallet.address[-6:]}\n\n"
        )
        
        transactions_text = ""
        
        for i, tx in enumerate(transactions, 1):
            # Форматируем дату в читаемом виде
            date_str = tx.date.strftime("%d.%m.%Y %H:%M") if tx.date else "Неизвестно"
            
            # Определяем тип транзакции и эмодзи
            tx_type_emoji = "⬅️" if tx.type == TransactionType.INCOMING else "➡️"
            tx_type_text = "Входящая" if tx.type == TransactionType.INCOMING else "Исходящая"
            
            # Форматируем сумму с точностью до 6 знаков
            amount_str = f"{tx.amount:.6f}".rstrip('0').rstrip('.') if tx.amount != 0 else "0"
            
            # Добавляем информацию о транзакции
            transactions_text += (
                f"{i}. {tx_type_emoji} <b>{tx_type_text}</b> ({date_str})\n"
                f"   Сумма: {amount_str} {currency}\n"
                f"   Комиссия: {tx.fee:.6f} {currency}\n"
                f"   Подтверждений: {tx.confirmations}\n"
                f"   ID: {tx.txid[:8]}...{tx.txid[-6:]}\n\n"
            )
        
        # Формируем полное сообщение
        message_text = header + transactions_text
        
        # Если сообщение слишком длинное, обрезаем его
        if len(message_text) > 4000:
            message_text = message_text[:3900] + "...\n\n(Сообщение слишком длинное и было обрезано)"
        
        # Создаем клавиатуру с кнопками для выбора количества транзакций и возврата
        kb = []
        
        # Добавляем кнопки для количества транзакций
        limits_row = []
        for num in [5, 10, 20]:
            if num == limit:
                text = f"✓ {num} транзакций"
            else:
                text = f"{num} транзакций"
            limits_row.append(InlineKeyboardButton(text=text, callback_data=f"transactions:{wallet_id}:{num}"))
        
        kb.append(limits_row)
        
        # Добавляем кнопку для просмотра на обозревателе блокчейна
        explorer_url = None
        if wallet.blockchain_type.value == "ETH":
            explorer_url = f"https://etherscan.io/address/{wallet.address}"
        elif wallet.blockchain_type.value == "BTC":
            explorer_url = f"https://www.blockchain.com/btc/address/{wallet.address}"
        elif wallet.blockchain_type.value == "BNB":
            explorer_url = f"https://bscscan.com/address/{wallet.address}"
        
        if explorer_url:
            kb.append([InlineKeyboardButton(text="🔍 Просмотреть на обозревателе", url=explorer_url)])
        
        # Добавляем кнопку возврата
        kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"wallet:{wallet_id}")])
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
        
        # Отправляем сообщение с информацией о транзакциях
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )

# Обработчик команды /balance
@router.message(Command("balance"))
@router.message(F.text == "💰 Проверить баланс")
async def cmd_balance(message: Message):
    """Обработчик команды проверки баланса кошельков"""
    user_id = message.from_user.id
    
    async with async_session() as session:
        # Получаем список кошельков пользователя
        wallets = await get_user_wallets(session, user_id)
        
        if not wallets:
            # Если у пользователя нет кошельков
            await message.answer(
                f"📭 <b>У вас пока нет добавленных кошельков.</b>\n\n"
                f"Добавьте кошелек с помощью команды /add_wallet",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Отправляем сообщение о начале проверки
        status_message = await message.answer(
            f"⏳ Проверяю баланс ваших кошельков..."
        )
        
        # Проверяем баланс для каждого кошелька
        balances = []
        total_balance_usd = 0
        
        for wallet in wallets:
            try:
                balance = await get_balance(wallet.blockchain_type, wallet.address)
                
                if balance is not None:
                    # Форматируем сумму баланса
                    formatted_balance = f"{balance:.8f}".rstrip('0').rstrip('.')
                    
                    # Добавляем информацию о балансе
                    balances.append({
                        "wallet": wallet,
                        "balance": balance,
                        "formatted_balance": formatted_balance
                    })
                    
                    # Здесь можно было бы конвертировать в USD, но для упрощения пропустим
            except Exception as e:
                logger.error(f"Ошибка при проверке баланса кошелька {wallet.address}: {e}")
        
        # Формируем ответное сообщение
        if not balances:
            message_text = (
                f"⚠️ <b>Не удалось получить информацию о балансе</b>\n\n"
                f"Произошла ошибка при получении данных о балансе ваших кошельков.\n"
                f"Пожалуйста, попробуйте позже."
            )
        else:
            message_text = f"💰 <b>Баланс ваших кошельков:</b>\n\n"
            
            for item in balances:
                wallet = item["wallet"]
                formatted_balance = item["formatted_balance"]
                
                message_text += (
                    f"<b>{wallet.label or 'Без метки'}</b> ({wallet.blockchain_type.value})\n"
                    f"<code>{wallet.address[:8]}...{wallet.address[-6:]}</code>\n"
                    f"Баланс: <b>{formatted_balance} {wallet.blockchain_type.value}</b>\n\n"
                )
        
        # Обновляем сообщение с результатами
        await status_message.edit_text(
            message_text,
            reply_markup=get_main_keyboard()
        )

# Обработчик команды /transactions
@router.message(Command("transactions"))
@router.message(F.text == "📊 Транзакции")
async def cmd_transactions(message: Message):
    """Обработчик команды просмотра последних транзакций"""
    user_id = message.from_user.id
    
    async with async_session() as session:
        # Получаем список кошельков пользователя
        wallets = await get_user_wallets(session, user_id)
        
        if not wallets:
            # Если у пользователя нет кошельков
            await message.answer(
                f"📭 <b>У вас пока нет добавленных кошельков.</b>\n\n"
                f"Добавьте кошелек с помощью команды /add_wallet",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Выводим список кошельков для выбора
        await message.answer(
            f"📋 <b>Выберите кошелек для просмотра транзакций:</b>",
            reply_markup=generate_wallets_keyboard(wallets)
        )

# Обработчик команды /settings
@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message):
    """Обработчик команды настройки уведомлений"""
    await message.answer(
        f"⚙️ <b>Настройки уведомлений</b>\n\n"
        f"В данный момент вы получаете уведомления обо всех транзакциях.\n\n"
        f"Функция детальной настройки уведомлений будет доступна в ближайшее время.",
        reply_markup=get_main_keyboard()
    )

def register_wallet_handlers(dp: Dispatcher):
    """Регистрация обработчиков управления кошельками"""
    dp.include_router(router) 