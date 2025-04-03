import enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

from models.base import BaseModel, Base


class BlockchainType(enum.Enum):
    """Тип блокчейна (BTC, ETH, BNB)"""
    BTC = "BTC"
    ETH = "ETH"
    BNB = "BNB"


class TransactionType(enum.Enum):
    """
    Тип транзакции (входящая или исходящая)
    """
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class Transaction:
    """
    Класс для представления транзакции
    """
    def __init__(
        self,
        txid: str,
        date: datetime,
        amount: float,
        fee: float,
        confirmations: int,
        type: TransactionType,
        address: str,
        blockchain_type: BlockchainType
    ):
        self.txid = txid
        self.date = date
        self.amount = amount
        self.fee = fee
        self.confirmations = confirmations
        self.type = type
        self.address = address
        self.blockchain_type = blockchain_type


class Wallet(BaseModel):
    """Модель криптовалютного кошелька"""
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    address = Column(String(255), nullable=False)
    label = Column(String(255))
    blockchain_type = Column(SQLAlchemyEnum(BlockchainType), nullable=False)
    last_checked_timestamp = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'address', name='uix_user_address'),
    )

    # Связь с пользователем
    user = relationship("User", back_populates="wallets")

    def __repr__(self):
        return f"<Wallet {self.address[:8]}...{self.address[-8:]} ({self.blockchain_type})>" 