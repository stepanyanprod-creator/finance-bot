# app/database/service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import json

from .models import User, Account, Transaction, Rule, Balance, get_db


class DatabaseService:
    """Сервис для работы с базой данных"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== ПОЛЬЗОВАТЕЛИ ====================
    
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """Получить или создать пользователя"""
        user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            # Обновляем информацию о пользователе
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.updated_at = datetime.utcnow()
            self.db.commit()
        
        return user
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()
    
    # ==================== СЧЕТА ====================
    
    def create_account(self, user_id: int, name: str, currency: str = "EUR", 
                      balance: float = 0.0) -> Account:
        """Создать новый счет"""
        account = Account(
            user_id=user_id,
            name=name,
            currency=currency,
            balance=balance
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account
    
    def get_accounts(self, user_id: int) -> List[Account]:
        """Получить все счета пользователя"""
        return self.db.query(Account).filter(
            and_(Account.user_id == user_id, Account.is_active == True)
        ).all()
    
    def get_account(self, account_id: int) -> Optional[Account]:
        """Получить счет по ID"""
        return self.db.query(Account).filter(Account.id == account_id).first()
    
    def update_account_balance(self, account_id: int, new_balance: float):
        """Обновить баланс счета"""
        account = self.get_account(account_id)
        if account:
            account.balance = new_balance
            account.updated_at = datetime.utcnow()
            self.db.commit()
    
    def delete_account(self, account_id: int):
        """Удалить счет (мягкое удаление)"""
        account = self.get_account(account_id)
        if account:
            account.is_active = False
            account.updated_at = datetime.utcnow()
            self.db.commit()
    
    # ==================== ТРАНЗАКЦИИ ====================
    
    def create_transaction(self, user_id: int, date: datetime, total: float,
                          currency: str, category: str = None, merchant: str = None,
                          payment_method: str = None, source: str = None,
                          notes: str = None, account_id: int = None,
                          transaction_type: str = "expense") -> Transaction:
        """Создать новую транзакцию"""
        transaction = Transaction(
            user_id=user_id,
            account_id=account_id,
            date=date,
            total=total,
            currency=currency,
            category=category,
            merchant=merchant,
            payment_method=payment_method,
            source=source,
            notes=notes,
            transaction_type=transaction_type
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def get_transactions(self, user_id: int, limit: int = 100, 
                        offset: int = 0, transaction_type: str = None) -> List[Transaction]:
        """Получить транзакции пользователя"""
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        return query.order_by(desc(Transaction.date)).offset(offset).limit(limit).all()
    
    def get_transactions_by_date_range(self, user_id: int, start_date: date, 
                                      end_date: date) -> List[Transaction]:
        """Получить транзакции за период"""
        return self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).order_by(desc(Transaction.date)).all()
    
    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Получить транзакцию по ID"""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
    
    def update_transaction(self, transaction_id: int, **kwargs) -> Optional[Transaction]:
        """Обновить транзакцию"""
        transaction = self.get_transaction(transaction_id)
        if transaction:
            for key, value in kwargs.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
            transaction.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(transaction)
        return transaction
    
    def delete_transaction(self, transaction_id: int):
        """Удалить транзакцию"""
        transaction = self.get_transaction(transaction_id)
        if transaction:
            self.db.delete(transaction)
            self.db.commit()
    
    # ==================== ПРАВИЛА ====================
    
    def create_rule(self, user_id: int, category: str, match_conditions: Dict[str, Any]) -> Rule:
        """Создать новое правило категоризации"""
        rule = Rule(
            user_id=user_id,
            category=category,
            match_conditions=json.dumps(match_conditions, ensure_ascii=False)
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule
    
    def get_rules(self, user_id: int) -> List[Rule]:
        """Получить все правила пользователя"""
        return self.db.query(Rule).filter(
            and_(Rule.user_id == user_id, Rule.is_active == True)
        ).all()
    
    def get_rule(self, rule_id: int) -> Optional[Rule]:
        """Получить правило по ID"""
        return self.db.query(Rule).filter(Rule.id == rule_id).first()
    
    def update_rule(self, rule_id: int, **kwargs) -> Optional[Rule]:
        """Обновить правило"""
        rule = self.get_rule(rule_id)
        if rule:
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            rule.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(rule)
        return rule
    
    def delete_rule(self, rule_id: int):
        """Удалить правило"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.is_active = False
            rule.updated_at = datetime.utcnow()
            self.db.commit()
    
    # ==================== БАЛАНСЫ ====================
    
    def save_balance(self, user_id: int, account_id: int, balance: float, currency: str):
        """Сохранить баланс счета"""
        balance_record = Balance(
            user_id=user_id,
            account_id=account_id,
            balance=balance,
            currency=currency
        )
        self.db.add(balance_record)
        self.db.commit()
    
    def get_latest_balances(self, user_id: int) -> List[Balance]:
        """Получить последние балансы пользователя"""
        return self.db.query(Balance).filter(
            Balance.user_id == user_id
        ).order_by(desc(Balance.date)).all()
    
    # ==================== СТАТИСТИКА ====================
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику пользователя"""
        accounts_count = self.db.query(Account).filter(
            and_(Account.user_id == user_id, Account.is_active == True)
        ).count()
        
        transactions_count = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).count()
        
        rules_count = self.db.query(Rule).filter(
            and_(Rule.user_id == user_id, Rule.is_active == True)
        ).count()
        
        return {
            "accounts_count": accounts_count,
            "transactions_count": transactions_count,
            "rules_count": rules_count
        }
    
    def get_category_stats(self, user_id: int, start_date: date = None, 
                          end_date: date = None) -> Dict[str, float]:
        """Получить статистику по категориям"""
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        
        transactions = query.all()
        
        category_stats = {}
        for transaction in transactions:
            if transaction.category:
                if transaction.category not in category_stats:
                    category_stats[transaction.category] = 0.0
                category_stats[transaction.category] += abs(transaction.total)
        
        return category_stats


# Функция для получения сервиса базы данных
def get_database_service():
    """Получить сервис базы данных"""
    db = next(get_db())
    return DatabaseService(db)
