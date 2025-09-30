# app/database/models.py
"""SQLAlchemy модели для Finance Bot"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10), default='ru')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    transactions = relationship("Transaction", back_populates="user")
    accounts = relationship("Account", back_populates="user")
    rules = relationship("CategoryRule", back_populates="user")


class Transaction(Base):
    """Модель транзакции"""
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    merchant = Column(String(255))
    total = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    category = Column(String(255))
    payment_method = Column(String(255))
    source = Column(String(100))  # photo, voice, manual
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction")


class TransactionItem(Base):
    """Модель позиции в транзакции"""
    __tablename__ = 'transaction_items'
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    price = Column(Float, nullable=False)
    
    # Связи
    transaction = relationship("Transaction", back_populates="items")


class Account(Base):
    """Модель счета"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="accounts")


class CategoryRule(Base):
    """Модель правила категоризации"""
    __tablename__ = 'category_rules'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category = Column(String(255), nullable=False)
    match_conditions = Column(Text)  # JSON строка с условиями
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="rules")
