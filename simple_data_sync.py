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
            
            # Настройка для работы с HTTPS
            subprocess.run(["git", "config", "credential.helper", "store"], check=True)
            
            # Настройка безопасного режима для HTTPS
            subprocess.run(["git", "config", "http.sslVerify", "false"], check=True)
            
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
                logger.error("Не удалось настроить git")
                return False
            
            # Проверяем изменения
            if not self.has_changes():
                logger.info("Нет изменений для синхронизации")
                return True
            
            # Добавляем все файлы данных
            try:
                subprocess.run(["git", "add", str(self.data_dir)], check=True)
                logger.info("Файлы добавлены в git")
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка добавления файлов: {e}")
                return False
            
            # Коммитим изменения
            try:
                commit_message = f"Auto-sync data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_message], check=True)
                logger.info("Изменения закоммичены")
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка коммита: {e}")
                return False
            
            # Пытаемся push в репозиторий
            try:
                result = subprocess.run(["git", "push", "origin", "main"], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    logger.info("Данные успешно синхронизированы с GitHub")
                    return True
                else:
                    logger.error(f"Ошибка push: {result.stderr}")
                    
                    # Пытаемся альтернативный метод
                    logger.info("Пробуем альтернативный метод push...")
                    return self._alternative_push()
                    
            except subprocess.TimeoutExpired:
                logger.error("Таймаут при push в GitHub")
                return False
            except subprocess.CalledProcessError as e:
                logger.error(f"Ошибка push: {e}")
                return self._alternative_push()
                
        except Exception as e:
            logger.error(f"Общая ошибка синхронизации: {e}")
            return False
    
    def _alternative_push(self):
        """Альтернативный метод push"""
        try:
            logger.info("Пробуем альтернативный метод синхронизации...")
            
            # Пытаемся force push
            result = subprocess.run(["git", "push", "--force", "origin", "main"], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("Альтернативный push успешен")
                return True
            else:
                logger.error(f"Альтернативный push не удался: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка альтернативного push: {e}")
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
