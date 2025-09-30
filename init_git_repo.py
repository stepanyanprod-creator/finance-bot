#!/usr/bin/env python3
"""
Модуль для инициализации git репозитория
"""

import subprocess
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def init_git_repository():
    """Инициализация git репозитория"""
    try:
        logger.info("Инициализация git репозитория...")
        
        # Проверяем, есть ли уже git репозиторий
        if Path('.git').exists():
            logger.info("Git репозиторий уже существует")
            return True
        
        # Инициализируем git репозиторий
        subprocess.run(['git', 'init'], check=True)
        logger.info("Git репозиторий инициализирован")
        
        # Настраиваем пользователя git
        subprocess.run(['git', 'config', 'user.name', 'Finance Bot'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'bot@finance.local'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Finance Bot'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@finance.local'], check=True)
        logger.info("Git пользователь настроен (локально и глобально)")
        
        # Добавляем remote origin
        repo_url = "https://github.com/stepanyanprod-creator/finance-bot.git"
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
        logger.info("Remote origin добавлен")
        
        # Настраиваем безопасный режим
        subprocess.run(['git', 'config', 'pull.rebase', 'false'], check=True)
        subprocess.run(['git', 'config', 'credential.helper', 'store'], check=True)
        subprocess.run(['git', 'config', 'http.sslVerify', 'false'], check=True)
        logger.info("Git настройки применены")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка инициализации git: {e}")
        return False
    except Exception as e:
        logger.error(f"Общая ошибка инициализации: {e}")
        return False

def test_git_connection():
    """Тестирование подключения к GitHub"""
    try:
        logger.info("Тестирование подключения к GitHub...")
        
        # Пытаемся получить информацию о репозитории
        result = subprocess.run(['git', 'fetch', 'origin'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("Подключение к GitHub работает")
            return True
        else:
            logger.error(f"Ошибка подключения: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Таймаут при подключении к GitHub")
        return False
    except Exception as e:
        logger.error(f"Ошибка тестирования подключения: {e}")
        return False

if __name__ == "__main__":
    print("Инициализация git репозитория...")
    success = init_git_repository()
    if success:
        print("Git репозиторий инициализирован")
        test_success = test_git_connection()
        if test_success:
            print("Подключение к GitHub работает")
        else:
            print("Подключение к GitHub не работает")
    else:
        print("Ошибка инициализации git репозитория")