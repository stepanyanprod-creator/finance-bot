#!/usr/bin/env python3
"""
Простая система резервного копирования данных
Альтернатива синхронизации с GitHub
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataBackup:
    def __init__(self, data_dir="data", backup_dir="backups"):
        self.data_dir = Path(data_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self):
        """Создание резервной копии данных"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{timestamp}"
            backup_path.mkdir(exist_ok=True)
            
            # Копируем все файлы данных
            if self.data_dir.exists():
                for file_path in self.data_dir.glob("*"):
                    if file_path.is_file():
                        shutil.copy2(file_path, backup_path / file_path.name)
                        logger.info(f"Скопирован файл: {file_path.name}")
            
            # Создаем метаданные бэкапа
            metadata = {
                "timestamp": timestamp,
                "created_at": datetime.now().isoformat(),
                "files_count": len(list(backup_path.glob("*"))),
                "data_dir": str(self.data_dir)
            }
            
            with open(backup_path / "backup_info.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Создана резервная копия: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            return None
    
    def get_backup_status(self):
        """Получение статуса резервного копирования"""
        try:
            backups = list(self.backup_dir.glob("backup_*"))
            latest_backup = None
            
            if backups:
                latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
            
            return {
                "backups_count": len(backups),
                "latest_backup": latest_backup.name if latest_backup else None,
                "data_dir": str(self.data_dir),
                "backup_dir": str(self.backup_dir)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            return {"backups_count": 0, "latest_backup": None}
    
    def cleanup_old_backups(self, keep_count=10):
        """Очистка старых бэкапов"""
        try:
            backups = list(self.backup_dir.glob("backup_*"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Удаляем старые бэкапы
            for backup in backups[keep_count:]:
                shutil.rmtree(backup)
                logger.info(f"Удален старый бэкап: {backup.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")
            return False

# Глобальный экземпляр
_data_backup = None

def get_data_backup():
    """Получение экземпляра резервного копирования"""
    global _data_backup
    if _data_backup is None:
        _data_backup = DataBackup()
    return _data_backup

def backup_data_now():
    """Немедленное резервное копирование данных"""
    backup = get_data_backup()
    return backup.create_backup()

def get_backup_status():
    """Получение статуса резервного копирования"""
    backup = get_data_backup()
    return backup.get_backup_status()
