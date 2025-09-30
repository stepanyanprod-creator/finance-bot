#!/usr/bin/env python3
"""
Скрипт для запуска Finance Bot
"""
import sys
import os

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import main
    print("🚀 Запуск Finance Bot...")
    main()
except KeyboardInterrupt:
    print("\n👋 Бот остановлен пользователем")
except Exception as e:
    print(f"❌ Ошибка при запуске бота: {e}")
    sys.exit(1)
