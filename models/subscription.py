from sqlalchemy import Column, Integer, BigInteger, String, Enum, DateTime, ForeignKey, Numeric
from models.base import BaseModel, Base
import enum

class SubscriptionStatus(enum.Enum):
    pending = "pending"
    active = "active" 
    cancelled = "cancelled"
    expired = "expired"

class Subscription(BaseModel):
    """Модель подписки пользователя"""
    __tablename__ = 'subscriptions'

    subscription_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'))
    payment_method = Column(String(255), nullable=False)
    payment_id = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.pending)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Subscription(id={self.subscription_id}, user_id={self.user_id}, status={self.status})>" 