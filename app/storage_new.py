# storage.py — база данных хранилище
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.database.service import get_database_service
from app.utils import format_money as fmt_money

# ──────────────────────────────────────────────────────────────────────────────
# ОСНОВНЫЕ ФУНКЦИИ ХРАНИЛИЩА
# ──────────────────────────────────────────────────────────────────────────────

def ensure_csv(user_id: int):
    """Обеспечиваем совместимость - создаем CSV файл из БД"""
    # Эта функция больше не нужна, но оставляем для совместимости
    pass

def add_transaction(user_id: int, date: datetime, merchant: str, total: float, 
                   currency: str, category: str = None, payment_method: str = None,
                   source: str = None, notes: str = None, account_id: int = None) -> int:
    """Добавить транзакцию в базу данных"""
    db_service = get_database_service()
    
    # Определяем тип транзакции
    transaction_type = "income" if total > 0 else "expense"
    
    transaction = db_service.create_transaction(
        user_id=user_id,
        date=date,
        total=abs(total),
        currency=currency,
        category=category,
        merchant=merchant,
        payment_method=payment_method,
        source=source,
        notes=notes,
        account_id=account_id,
        transaction_type=transaction_type
    )
    
    return transaction.id

def get_transactions(user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Получить транзакции пользователя"""
    db_service = get_database_service()
    transactions = db_service.get_transactions(user_id, limit=limit)
    
    result = []
    for t in transactions:
        result.append({
            'id': t.id,
            'date': t.date,
            'merchant': t.merchant,
            'total': t.total,
            'currency': t.currency,
            'category': t.category,
            'payment_method': t.payment_method,
            'source': t.source,
            'notes': t.notes,
            'transaction_type': t.transaction_type
        })
    
    return result

def get_last_transaction(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить последнюю транзакцию"""
    transactions = get_transactions(user_id, limit=1)
    return transactions[0] if transactions else None

def delete_transaction(transaction_id: int):
    """Удалить транзакцию"""
    db_service = get_database_service()
    db_service.delete_transaction(transaction_id)

def update_transaction(transaction_id: int, **kwargs):
    """Обновить транзакцию"""
    db_service = get_database_service()
    return db_service.update_transaction(transaction_id, **kwargs)

# ──────────────────────────────────────────────────────────────────────────────
# СЧЕТА И БАЛАНСЫ
# ──────────────────────────────────────────────────────────────────────────────

def add_account(user_id: int, name: str, currency: str = "EUR", balance: float = 0.0) -> int:
    """Добавить счет"""
    db_service = get_database_service()
    account = db_service.create_account(user_id, name, currency, balance)
    return account.id

def get_accounts(user_id: int) -> List[Dict[str, Any]]:
    """Получить все счета пользователя"""
    db_service = get_database_service()
    accounts = db_service.get_accounts(user_id)
    
    result = []
    for a in accounts:
        result.append({
            'id': a.id,
            'name': a.name,
            'currency': a.currency,
            'balance': a.balance,
            'is_active': a.is_active
        })
    
    return result

def set_balance(user_id: int, amount: float, currency: str, category: str = None) -> tuple:
    """Установить баланс (совместимость со старым API)"""
    db_service = get_database_service()
    
    # Если указана категория, ищем счет по категории
    if category:
        accounts = db_service.get_accounts(user_id)
        for account in accounts:
            if account.name.lower() == category.lower():
                db_service.update_account_balance(account.id, amount)
                return (account.name, amount)
    
    # Иначе создаем новый счет
    account_name = f"Account {currency}"
    account = db_service.create_account(user_id, account_name, currency, amount)
    return (account.name, amount)

def get_balance(user_id: int, currency: str = "EUR") -> float:
    """Получить общий баланс по валюте"""
    db_service = get_database_service()
    accounts = db_service.get_accounts(user_id)
    
    total_balance = 0.0
    for account in accounts:
        if account.currency == currency:
            total_balance += account.balance
    
    return total_balance

# ──────────────────────────────────────────────────────────────────────────────
# ПРАВИЛА КАТЕГОРИЗАЦИИ
# ──────────────────────────────────────────────────────────────────────────────

def add_rule(user_id: int, category: str, match_conditions: Dict[str, Any]) -> int:
    """Добавить правило категоризации"""
    db_service = get_database_service()
    rule = db_service.create_rule(user_id, category, match_conditions)
    return rule.id

def get_rules(user_id: int) -> List[Dict[str, Any]]:
    """Получить правила пользователя"""
    db_service = get_database_service()
    rules = db_service.get_rules(user_id)
    
    result = []
    for r in rules:
        import json
        result.append({
            'id': r.id,
            'category': r.category,
            'match': json.loads(r.match_conditions),
            'is_active': r.is_active
        })
    
    return result

def delete_rule(rule_id: int):
    """Удалить правило"""
    db_service = get_database_service()
    db_service.delete_rule(rule_id)

# ──────────────────────────────────────────────────────────────────────────────
# СТАТИСТИКА
# ──────────────────────────────────────────────────────────────────────────────

def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Получить статистику пользователя"""
    db_service = get_database_service()
    return db_service.get_user_stats(user_id)

def get_category_stats(user_id: int, start_date: datetime = None, end_date: datetime = None) -> Dict[str, float]:
    """Получить статистику по категориям"""
    db_service = get_database_service()
    return db_service.get_category_stats(user_id, start_date, end_date)

# ──────────────────────────────────────────────────────────────────────────────
# ЭКСПОРТ ДАННЫХ
# ──────────────────────────────────────────────────────────────────────────────

def export_to_csv(user_id: int) -> str:
    """Экспортировать данные в CSV (для совместимости)"""
    import csv
    import tempfile
    
    # Создаем временный файл
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8')
    
    # Получаем транзакции
    transactions = get_transactions(user_id)
    
    if not transactions:
        temp_file.close()
        return None
    
    # Записываем CSV
    fieldnames = ['date', 'merchant', 'total', 'currency', 'category', 'payment_method', 'source', 'notes']
    writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
    writer.writeheader()
    
    for t in transactions:
        writer.writerow({
            'date': t['date'].strftime('%Y-%m-%d %H:%M:%S'),
            'merchant': t['merchant'] or '',
            'total': t['total'],
            'currency': t['currency'],
            'category': t['category'] or '',
            'payment_method': t['payment_method'] or '',
            'source': t['source'] or '',
            'notes': t['notes'] or ''
        })
    
    temp_file.close()
    return temp_file.name

# ──────────────────────────────────────────────────────────────────────────────
# СОВМЕСТИМОСТЬ СО СТАРЫМ API
# ──────────────────────────────────────────────────────────────────────────────

def load_rules(user_id: int) -> List[Dict[str, Any]]:
    """Загрузить правила (совместимость)"""
    return get_rules(user_id)

def save_rules(user_id: int, rules: List[Dict[str, Any]]):
    """Сохранить правила (совместимость)"""
    # Удаляем старые правила
    old_rules = get_rules(user_id)
    for rule in old_rules:
        delete_rule(rule['id'])
    
    # Добавляем новые
    for rule in rules:
        add_rule(user_id, rule['category'], rule['match'])

def load_accounts(user_id: int) -> Dict[str, Dict[str, Any]]:
    """Загрузить счета в старом формате"""
    accounts = get_accounts(user_id)
    result = {}
    
    for account in accounts:
        result[account['name']] = {
            'currency': account['currency'],
            'amount': account['balance']
        }
    
    return result

def save_accounts(user_id: int, accounts: Dict[str, Dict[str, Any]]):
    """Сохранить счета в старом формате"""
    # Удаляем старые счета
    old_accounts = get_accounts(user_id)
    for account in old_accounts:
        db_service = get_database_service()
        db_service.delete_account(account['id'])
    
    # Добавляем новые
    for name, data in accounts.items():
        add_account(user_id, name, data['currency'], data['amount'])
