#!/usr/bin/env python3
"""
Простая инициализация базы данных без зависимостей
"""
import os
import sys
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.models import init_database
from app.database.service import get_database_service


def main():
    """Инициализация базы данных"""
    print("🚀 Инициализация базы данных...")
    
    try:
        # Создаем таблицы
        init_database()
        print("✅ База данных успешно инициализирована!")
        print("📊 Созданы таблицы: users, accounts, transactions, rules, balances")
        
        # Проверяем подключение
        db_service = get_database_service()
        
        # Тестируем создание пользователя
        test_user = db_service.get_or_create_user(
            telegram_id=999999,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Тестовый пользователь создан: {test_user.telegram_id}")
        
        # Создаем тестовый счет
        test_account = db_service.create_account(
            user_id=test_user.id,
            name="Test Account",
            currency="EUR",
            balance=100.0
        )
        print(f"✅ Тестовый счет создан: {test_account.name}")
        
        # Удаляем тестовые данные
        db_service.delete_account(test_account.id)
        db_service.db.delete(test_user)
        db_service.db.commit()
        print("🧹 Тестовые данные удалены")
        
        print("\n🎉 База данных готова к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
