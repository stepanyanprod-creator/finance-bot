# app/database/models.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# База данных SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///finance_bot.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    rules = relationship("Rule", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    """Модель счета/аккаунта"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    currency = Column(String(10), nullable=False, default="EUR")
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Transaction(Base):
    """Модель транзакции"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    
    # Основные поля транзакции
    date = Column(DateTime, nullable=False)
    merchant = Column(String(255), nullable=True)
    total = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="EUR")
    category = Column(String(100), nullable=True)
    payment_method = Column(String(100), nullable=True)
    source = Column(String(255), nullable=True)  # Для доходов
    notes = Column(Text, nullable=True)
    
    # Метаданные
    transaction_type = Column(String(20), nullable=False, default="expense")  # expense, income, transfer
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class Rule(Base):
    """Модель правил категоризации"""
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(100), nullable=False)
    match_conditions = Column(Text, nullable=False)  # JSON строка с условиями
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="rules")


class Balance(Base):
    """Модель для хранения балансов по счетам"""
    __tablename__ = "balances"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    balance = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Связи
    user = relationship("User")
    account = relationship("Account")


# Функции для работы с базой данных
def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Создать все таблицы в базе данных"""
    Base.metadata.create_all(bind=engine)


def init_database():
    """Инициализировать базу данных"""
    create_tables()
    print("✅ База данных инициализирована")


if __name__ == "__main__":
    init_database()