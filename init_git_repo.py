#!/usr/bin/env python3
"""
Скрипт для инициализации git репозитория на Render
"""

import subprocess
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def init_git_repository():
    """Инициализация git репозитория для синхронизации"""
    try:
        print("🔧 Инициализация git репозитория для синхронизации...")
        
        # Проверяем, есть ли уже git репозиторий
        if Path('.git').exists():
            print("✅ Git репозиторий уже существует")
        else:
            print("📁 Создаю новый git репозиторий...")
            subprocess.run(['git', 'init'], check=True)
            print("✅ Git репозиторий создан")
        
        # Настраиваем git
        print("⚙️ Настраиваю git...")
        subprocess.run(['git', 'config', 'user.name', 'Finance Bot'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'bot@finance.local'], check=True)
        subprocess.run(['git', 'config', 'pull.rebase', 'false'], check=True)
        subprocess.run(['git', 'config', 'credential.helper', 'store'], check=True)
        print("✅ Git настроен")
        
        # Добавляем remote origin
        print("🔗 Настраиваю remote origin...")
        try:
            # Проверяем, есть ли уже origin
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                # Добавляем origin
                github_url = "https://github.com/stepanyanprod-creator/finance-bot.git"
                subprocess.run(['git', 'remote', 'add', 'origin', github_url], check=True)
                print(f"✅ Remote origin добавлен: {github_url}")
            else:
                print(f"✅ Remote origin уже настроен: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Ошибка настройки remote: {e}")
            return False
        
        # Создаем .gitignore если его нет
        gitignore_content = """# Данные пользователей (будут синхронизироваться)
# data/

# Логи
*.log
logs/

# Временные файлы
*.tmp
*.temp

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Резервные копии (кроме важных)
backups/
!backups/.gitkeep
"""
        
        if not Path('.gitignore').exists():
            with open('.gitignore', 'w', encoding='utf-8') as f:
                f.write(gitignore_content)
            print("✅ Создан .gitignore")
        
        # Создаем папку data если её нет
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # Создаем файл .gitkeep в data
        (data_dir / '.gitkeep').touch()
        print("✅ Папка data создана")
        
        # Добавляем все файлы
        print("📦 Добавляю файлы в git...")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Первый коммит
        try:
            subprocess.run(['git', 'commit', '-m', 'Initial commit with data structure'], check=True)
            print("✅ Первый коммит создан")
        except subprocess.CalledProcessError:
            print("ℹ️ Коммит уже существует или нет изменений")
        
        print("🎉 Git репозиторий успешно инициализирован!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации git: {e}")
        return False

def test_git_connection():
    """Тестирование подключения к GitHub"""
    try:
        print("🧪 Тестирую подключение к GitHub...")
        
        # Проверяем remote
        result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"📡 Remote repositories:")
            print(result.stdout)
        else:
            print("❌ Remote repositories не настроены")
            return False
        
        # Пытаемся fetch
        print("🔄 Тестирую fetch...")
        fetch_result = subprocess.run(['git', 'fetch', 'origin'], 
                                    capture_output=True, text=True, timeout=30)
        
        if fetch_result.returncode == 0:
            print("✅ Подключение к GitHub работает")
            return True
        else:
            print(f"❌ Ошибка fetch: {fetch_result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ИНИЦИАЛИЗАЦИЯ GIT РЕПОЗИТОРИЯ ДЛЯ СИНХРОНИЗАЦИИ")
    print("=" * 60)
    
    # Инициализация
    if init_git_repository():
        print("\n" + "=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ")
        print("=" * 60)
        
        # Тестирование
        if test_git_connection():
            print("\n🎉 ВСЕ ГОТОВО! Синхронизация с GitHub настроена!")
        else:
            print("\n⚠️ Git настроен, но подключение к GitHub не работает")
            print("💡 Возможно, нужны права доступа или токен аутентификации")
    else:
        print("\n❌ Не удалось инициализировать git репозиторий")
        sys.exit(1)
