#!/usr/bin/env python3
"""
Тестовый скрипт для проверки синхронизации данных
"""

import os
import json
from pathlib import Path
from simple_data_sync import get_data_sync

def create_test_data():
    """Создание тестовых данных"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Создаем тестовый файл
    test_data = {
        "user_id": "test_user",
        "transactions": [
            {"date": "2025-01-01", "amount": 100, "category": "food"},
            {"date": "2025-01-02", "amount": 50, "category": "transport"}
        ],
        "last_updated": "2025-01-01T12:00:00Z"
    }
    
    test_file = data_dir / "test_user.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Создан тестовый файл: {test_file}")
    return test_file

def test_sync():
    """Тестирование синхронизации"""
    print("🧪 Тестирование синхронизации данных...")
    
    # Создаем тестовые данные
    test_file = create_test_data()
    
    # Получаем экземпляр синхронизации
    sync = get_data_sync()
    
    # Проверяем статус
    status = sync.get_status()
    print(f"📊 Статус: {status}")
    
    # Пытаемся синхронизировать
    print("🔄 Попытка синхронизации...")
    success = sync.sync_data()
    
    if success:
        print("✅ Синхронизация успешна!")
    else:
        print("❌ Ошибка синхронизации")
    
    return success

if __name__ == "__main__":
    test_sync()
