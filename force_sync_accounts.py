#!/usr/bin/env python3
"""
Принудительная синхронизация accounts.json с GitHub
"""

import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def force_sync_accounts():
    """Принудительная синхронизация файлов accounts.json"""
    try:
        logger.info("Начинаем принудительную синхронизацию accounts.json...")
        
        # Настраиваем git пользователя
        try:
            from setup_git_config import setup_git_config, force_git_config
            
            # Пробуем обычную настройку
            if not setup_git_config():
                logger.warning("Обычная настройка не удалась, пробуем принудительную")
                if not force_git_config():
                    logger.error("Не удалось настроить git пользователя")
                    return False
            
            logger.info("Git пользователь настроен")
        except ImportError:
            # Fallback к старому методу
            try:
                subprocess.run(['git', 'config', 'user.name', 'Finance Bot'], check=True)
                subprocess.run(['git', 'config', 'user.email', 'bot@finance.local'], check=True)
                subprocess.run(['git', 'config', '--global', 'user.name', 'Finance Bot'], check=True)
                subprocess.run(['git', 'config', '--global', 'user.email', 'bot@finance.local'], check=True)
                logger.info("Git пользователь настроен (fallback)")
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка настройки git пользователя: {e}")
                return False
        except Exception as e:
            logger.error(f"Ошибка настройки git пользователя: {e}")
            return False
        
        # Находим все файлы accounts.json
        data_dir = Path("data")
        accounts_files = list(data_dir.glob("*/accounts.json"))
        
        if not accounts_files:
            logger.warning("Файлы accounts.json не найдены")
            return False
        
        logger.info(f"Найдено {len(accounts_files)} файлов accounts.json")
        
        # Добавляем все файлы accounts.json
        for accounts_file in accounts_files:
            try:
                subprocess.run(['git', 'add', str(accounts_file)], check=True)
                logger.info(f"Добавлен в git: {accounts_file}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка добавления {accounts_file}: {e}")
                return False
        
        # Проверяем статус
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if not result.stdout.strip():
            logger.info("Нет изменений для синхронизации")
            return True
        
        # Коммитим изменения
        commit_message = f"Force sync accounts.json: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        logger.info("Изменения закоммичены")
        
        # Push в GitHub
        try:
            result = subprocess.run(['git', 'push', 'origin', 'main'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("Файлы accounts.json успешно синхронизированы с GitHub")
                return True
            else:
                logger.error(f"Ошибка push: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Таймаут при push в GitHub")
            return False
            
    except Exception as e:
        logger.error(f"Общая ошибка синхронизации: {e}")
        return False

def get_accounts_status():
    """Получение статуса файлов accounts.json"""
    try:
        data_dir = Path("data")
        accounts_files = list(data_dir.glob("*/accounts.json"))
        
        status = {
            "accounts_files_count": len(accounts_files),
            "accounts_files": [str(f) for f in accounts_files],
            "data_dir": str(data_dir)
        }
        
        # Проверяем git статус
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        status["git_status"] = result.stdout.strip() or "clean"
        status["has_changes"] = bool(result.stdout.strip())
        
        return status
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    print("Принудительная синхронизация accounts.json...")
    success = force_sync_accounts()
    if success:
        print("✅ Синхронизация успешна")
    else:
        print("❌ Ошибка синхронизации")
    
    print("\nСтатус файлов accounts.json:")
    status = get_accounts_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
