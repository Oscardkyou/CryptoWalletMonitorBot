from sqlalchemy import Column, BigInteger, String, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from models.base import BaseModel, Base
import enum

class SubscriptionLevel(enum.Enum):
    free = "free"
    premium = "premium"

class User(BaseModel):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    subscription_level = Column(Enum(SubscriptionLevel), default=SubscriptionLevel.free)
    subscription_expiry = Column(DateTime, nullable=True)
    notification_settings = Column(JSON, nullable=True)
    
    # Отношение к кошелькам пользователя
    wallets = relationship("Wallet", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>" 