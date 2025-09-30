#!/usr/bin/env python3
"""
Автоматический хук для сохранения данных в Finance Bot
Интегрируется с основными функциями бота для автоматической синхронизации
"""

import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AutoSaveHook:
    def __init__(self, data_sync, save_interval: int = 300):  # 5 минут по умолчанию
        self.data_sync = data_sync
        self.save_interval = save_interval
        self.last_save = datetime.now()
        self.running = False
        self.thread = None
        
    def start(self):
        """Запуск автоматического сохранения"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self.thread.start()
        logger.info(f"Автоматическое сохранение запущено (интервал: {self.save_interval}с)")
    
    def stop(self):
        """Остановка автоматического сохранения"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Автоматическое сохранение остановлено")
    
    def _auto_save_loop(self):
        """Основной цикл автоматического сохранения"""
        while self.running:
            try:
                time.sleep(self.save_interval)
                if self.running:
                    self.save_now()
            except Exception as e:
                logger.error(f"Ошибка в цикле автосохранения: {e}")
    
    def save_now(self, force: bool = False):
        """Немедленное сохранение данных"""
        try:
            success = self.data_sync.sync_data(force=force)
            if success:
                self.last_save = datetime.now()
                logger.info("Данные автоматически сохранены")
            return success
        except Exception as e:
            logger.error(f"Ошибка автосохранения: {e}")
            return False
    
    def get_status(self):
        """Получение статуса автосохранения"""
        return {
            "running": self.running,
            "save_interval": self.save_interval,
            "last_save": self.last_save.isoformat(),
            "next_save": (self.last_save + timedelta(seconds=self.save_interval)).isoformat()
        }

# Глобальный экземпляр для использования в боте
_auto_save_hook = None

def init_auto_save(data_sync, save_interval: int = 300):
    """Инициализация автоматического сохранения"""
    global _auto_save_hook
    _auto_save_hook = AutoSaveHook(data_sync, save_interval)
    _auto_save_hook.start()
    return _auto_save_hook

def get_auto_save_hook():
    """Получение экземпляра автосохранения"""
    return _auto_save_hook

def save_data_now(force: bool = False):
    """Немедленное сохранение данных"""
    if _auto_save_hook:
        return _auto_save_hook.save_now(force=force)
    return False

def stop_auto_save():
    """Остановка автоматического сохранения"""
    if _auto_save_hook:
        _auto_save_hook.stop()
