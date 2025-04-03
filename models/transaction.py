from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from models.base import BaseModel, Base

class Transaction(BaseModel):
    """Модель транзакции криптовалюты"""
    __tablename__ = 'transactions'

    tx_id = Column(String(255), primary_key=True)
    wallet_id = Column(Integer, ForeignKey('wallets.id', ondelete='CASCADE'))
    hash = Column(String(255), nullable=False)
    from_address = Column(String(255), nullable=True)
    to_address = Column(String(255), nullable=True)
    value = Column(Numeric(30, 18), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    block_number = Column(Integer, nullable=True)
    notification_sent = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Transaction(tx_id={self.tx_id}, hash={self.hash}, value={self.value})>" 