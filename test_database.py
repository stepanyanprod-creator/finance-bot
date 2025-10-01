#!/usr/bin/env python3
"""
Тест работы базы данных
"""
import os
import sys
from datetime import datetime

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.service import get_database_service


def test_database():
    """Тестируем работу базы данных"""
    print("🧪 Тестируем базу данных...")
    
    db_service = get_database_service()
    
    # Получаем статистику
    stats = db_service.get_user_stats(1)  # Тестируем с user_id=1
    print(f"📊 Статистика пользователя 1: {stats}")
    
    # Получаем всех пользователей
    from app.database.models import get_db
    db = next(get_db())
    from app.database.models import User
    
    users = db.query(User).all()
    print(f"👥 Всего пользователей в БД: {len(users)}")
    
    for user in users:
        print(f"   - ID: {user.telegram_id}, Имя: {user.first_name}")
        
        # Получаем счета пользователя
        accounts = db_service.get_accounts(user.id)
        print(f"     🏦 Счетов: {len(accounts)}")
        
        # Получаем транзакции пользователя
        transactions = db_service.get_transactions(user.id, limit=5)
        print(f"     💰 Транзакций: {len(transactions)}")
        
        # Получаем правила пользователя
        rules = db_service.get_rules(user.id)
        print(f"     🧩 Правил: {len(rules)}")
    
    print("\n✅ База данных работает корректно!")


if __name__ == "__main__":
    test_database()
