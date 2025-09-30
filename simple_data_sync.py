#!/usr/bin/env python3
"""
Простая система синхронизации данных с GitHub
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SimpleDataSync:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def setup_git(self):
        """Настройка git для синхронизации"""
        try:
            # Настройка пользователя git
            subprocess.run(["git", "config", "user.name", "Finance Bot"], check=True)
            subprocess.run(["git", "config", "user.email", "bot@finance.local"], check=True)
            
            # Настройка безопасного режима
            subprocess.run(["git", "config", "pull.rebase", "false"], check=True)
            
            logger.info("Git настроен для синхронизации")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка настройки git: {e}")
            return False
    
    def has_changes(self):
        """Проверка наличия изменений"""
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False
    
    def sync_data(self):
        """Синхронизация данных с GitHub"""
        try:
            logger.info("Начинаем синхронизацию данных...")
            
            # Настраиваем git
            if not self.setup_git():
                return False
            
            # Проверяем изменения
            if not self.has_changes():
                logger.info("Нет изменений для синхронизации")
                return True
            
            # Добавляем все файлы данных
            subprocess.run(["git", "add", str(self.data_dir)], check=True)
            
            # Коммитим изменения
            commit_message = f"Auto-sync data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            
            # Push в репозиторий
            result = subprocess.run(["git", "push", "origin", "main"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Данные успешно синхронизированы с GitHub")
                return True
            else:
                logger.error(f"Ошибка push: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка синхронизации: {e}")
            return False
    
    def get_status(self):
        """Получение статуса синхронизации"""
        try:
            result = subprocess.run(["git", "status", "--short"], 
                                  capture_output=True, text=True)
            return {
                "has_changes": self.has_changes(),
                "git_status": result.stdout.strip() or "clean",
                "data_dir": str(self.data_dir)
            }
        except subprocess.CalledProcessError:
            return {"has_changes": False, "git_status": "error", "data_dir": str(self.data_dir)}

# Глобальный экземпляр
_data_sync = None

def get_data_sync():
    """Получение экземпляра синхронизации"""
    global _data_sync
    if _data_sync is None:
        _data_sync = SimpleDataSync()
    return _data_sync

def sync_data_now():
    """Немедленная синхронизация данных"""
    sync = get_data_sync()
    return sync.sync_data()

def get_sync_status():
    """Получение статуса синхронизации"""
    sync = get_data_sync()
    return sync.get_status()
