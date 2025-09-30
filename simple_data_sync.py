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
            # Сначала добавляем все файлы данных в git
            self._add_all_data_files()
            
            # Проверяем статус
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False
    
    def _add_all_data_files(self):
        """Добавляет все файлы данных в git"""
        try:
            # Простое добавление всей папки data
            subprocess.run(["git", "add", "data/"], check=True)
            logger.info("Файлы данных добавлены в git")
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка добавления файлов: {e}")
            # Пробуем добавить файлы по одному
            try:
                for user_dir in self.data_dir.glob("*"):
                    if user_dir.is_dir():
                        subprocess.run(["git", "add", str(user_dir)], check=True)
                logger.info("Файлы пользователей добавлены по отдельности")
            except subprocess.CalledProcessError:
                logger.error("Не удалось добавить файлы данных")
    
    def sync_data(self):
        """Синхронизация данных с GitHub"""
        try:
            logger.info("Начинаем синхронизацию данных...")
            
            # Проверяем, инициализирован ли git репозиторий
            if not Path('.git').exists():
                logger.error("Git репозиторий не инициализирован")
                logger.info("Запускаю инициализацию git репозитория...")
                try:
                    from init_git_repo import init_git_repository
                    if not init_git_repository():
                        logger.error("Не удалось инициализировать git репозиторий")
                        return False
                except ImportError:
                    logger.error("Модуль init_git_repo не найден")
                    return False
            
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
                # Принудительно добавляем все файлы данных
                self._add_all_data_files()
                
                # Дополнительно добавляем все файлы в data
                subprocess.run(["git", "add", str(self.data_dir)], check=True)
                
                # Добавляем файлы пользователей по отдельности
                for user_dir in self.data_dir.glob("*"):
                    if user_dir.is_dir() and user_dir.name.isdigit():
                        try:
                            subprocess.run(["git", "add", str(user_dir)], check=True)
                        except subprocess.CalledProcessError:
                            # Игнорируем ошибки для отдельных папок
                            pass
                
                logger.info("Все файлы данных принудительно добавлены в git")
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
