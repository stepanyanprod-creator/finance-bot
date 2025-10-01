#!/usr/bin/env python3
"""
Простая миграция данных из CSV файлов в базу данных
"""
import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.models import init_database
from app.database.service import get_database_service


def parse_csv_date(date_str: str) -> datetime:
    """Парсинг даты из CSV"""
    try:
        # Пробуем разные форматы дат
        formats = [
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Если ничего не подошло, возвращаем текущую дату
        return datetime.now()
    except:
        return datetime.now()


def migrate_user_data(user_id: int, data_dir: Path) -> Dict[str, Any]:
    """Миграция данных пользователя"""
    print(f"📁 Мигрируем данные пользователя {user_id}...")
    
    db_service = get_database_service()
    
    # Создаем или получаем пользователя
    user = db_service.get_or_create_user(telegram_id=user_id)
    
    # Мигрируем счета из accounts.json
    accounts_file = data_dir / "accounts.json"
    accounts_created = 0
    if accounts_file.exists():
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                accounts_data = json.load(f)
            
            for account_name, account_info in accounts_data.items():
                currency = account_info.get('currency', 'EUR')
                balance = float(account_info.get('amount', 0.0))
                
                # Создаем счет в БД
                db_service.create_account(
                    user_id=user.id,
                    name=account_name,
                    currency=currency,
                    balance=balance
                )
                accounts_created += 1
                
        except Exception as e:
            print(f"⚠️ Ошибка при миграции счетов: {e}")
    
    # Мигрируем транзакции из finance.csv
    transactions_created = 0
    csv_file = data_dir / "finance.csv"
    if csv_file.exists():
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Парсим дату
                    date = parse_csv_date(row.get('date', ''))
                    
                    # Определяем тип транзакции
                    total = float(row.get('total', 0))
                    transaction_type = "income" if total > 0 else "expense"
                    
                    # Создаем транзакцию
                    db_service.create_transaction(
                        user_id=user.id,
                        date=date,
                        total=abs(total),
                        currency=row.get('currency', 'EUR'),
                        category=row.get('category'),
                        merchant=row.get('merchant'),
                        payment_method=row.get('payment_method'),
                        source=row.get('source'),
                        notes=row.get('notes'),
                        transaction_type=transaction_type
                    )
                    transactions_created += 1
                    
        except Exception as e:
            print(f"⚠️ Ошибка при миграции транзакций: {e}")
    
    # Мигрируем правила из rules.json
    rules_created = 0
    rules_file = data_dir / "rules.json"
    if rules_file.exists():
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            for rule in rules_data:
                db_service.create_rule(
                    user_id=user.id,
                    category=rule.get('category', ''),
                    match_conditions=rule.get('match', {})
                )
                rules_created += 1
                
        except Exception as e:
            print(f"⚠️ Ошибка при миграции правил: {e}")
    
    return {
        "user_id": user_id,
        "accounts_created": accounts_created,
        "transactions_created": transactions_created,
        "rules_created": rules_created
    }


def main():
    """Основная функция миграции"""
    print("🚀 Начинаем миграцию данных в базу данных...")
    
    # Инициализируем базу данных
    init_database()
    print("✅ База данных инициализирована")
    
    # Находим всех пользователей
    data_dir = Path("data")
    if not data_dir.exists():
        print("❌ Папка data не найдена")
        return
    
    user_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    
    if not user_dirs:
        print("❌ Пользователи не найдены в папке data")
        return
    
    print(f"👥 Найдено пользователей: {len(user_dirs)}")
    
    # Мигрируем данные каждого пользователя
    total_stats = {
        "users_migrated": 0,
        "accounts_created": 0,
        "transactions_created": 0,
        "rules_created": 0
    }
    
    for user_dir in user_dirs:
        user_id = int(user_dir.name)
        try:
            stats = migrate_user_data(user_id, user_dir)
            total_stats["users_migrated"] += 1
            total_stats["accounts_created"] += stats["accounts_created"]
            total_stats["transactions_created"] += stats["transactions_created"]
            total_stats["rules_created"] += stats["rules_created"]
            
            print(f"✅ Пользователь {user_id}: {stats['accounts_created']} счетов, "
                  f"{stats['transactions_created']} транзакций, {stats['rules_created']} правил")
                  
        except Exception as e:
            print(f"❌ Ошибка при миграции пользователя {user_id}: {e}")
    
    # Выводим итоговую статистику
    print("\n🎉 Миграция завершена!")
    print(f"📊 Итого мигрировано:")
    print(f"   👥 Пользователей: {total_stats['users_migrated']}")
    print(f"   🏦 Счетов: {total_stats['accounts_created']}")
    print(f"   💰 Транзакций: {total_stats['transactions_created']}")
    print(f"   🧩 Правил: {total_stats['rules_created']}")
    
    print("\n💡 Теперь можно использовать базу данных вместо файлов!")


if __name__ == "__main__":
    main()
