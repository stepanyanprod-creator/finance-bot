#!/usr/bin/env python3
"""
Система синхронизации данных между Render и GitHub
Автоматически сохраняет изменения данных в репозиторий
"""

import os
import json
import csv
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSync:
    def __init__(self, data_dir: str = "data", repo_dir: str = ".", git_user: str = "Finance Bot", git_email: str = "bot@finance.local"):
        self.data_dir = Path(data_dir)
        self.repo_dir = Path(repo_dir)
        self.git_user = git_user
        self.git_email = git_email
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def setup_git_config(self):
        """Настройка git конфигурации"""
        try:
            subprocess.run(["git", "config", "user.name", self.git_user], 
                         cwd=self.repo_dir, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", self.git_email], 
                         cwd=self.repo_dir, check=True, capture_output=True)
            logger.info("Git конфигурация настроена")
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка настройки git: {e}")
    
    def create_backup(self) -> str:
        """Создание резервной копии данных"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Копируем все файлы данных
        for file_path in self.data_dir.glob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                shutil.copy2(file_path, backup_path / file_path.name)
        
        logger.info(f"Создана резервная копия: {backup_path}")
        return str(backup_path)
    
    def get_data_files(self) -> list:
        """Получение списка файлов данных для синхронизации"""
        data_files = []
        for file_path in self.data_dir.glob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                data_files.append(file_path)
        return data_files
    
    def has_changes(self) -> bool:
        """Проверка наличия изменений в данных"""
        try:
            result = subprocess.run(["git", "status", "--porcelain"], 
                                 cwd=self.repo_dir, capture_output=True, text=True)
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False
    
    def commit_and_push(self, message: str = None) -> bool:
        """Коммит и push изменений"""
        if not message:
            message = f"Auto-sync data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            # Добавляем все файлы данных
            subprocess.run(["git", "add", str(self.data_dir)], 
                         cwd=self.repo_dir, check=True, capture_output=True)
            
            # Коммитим изменения
            subprocess.run(["git", "commit", "-m", message], 
                         cwd=self.repo_dir, check=True, capture_output=True)
            
            # Push в репозиторий
            result = subprocess.run(["git", "push", "origin", "main"], 
                                  cwd=self.repo_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Данные успешно синхронизированы с GitHub")
                return True
            else:
                logger.error(f"Ошибка push: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка коммита: {e}")
            return False
    
    def pull_changes(self) -> bool:
        """Получение изменений из репозитория"""
        try:
            result = subprocess.run(["git", "pull", "origin", "main"], 
                                  cwd=self.repo_dir, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Изменения получены из GitHub")
                return True
            else:
                logger.error(f"Ошибка pull: {result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка получения изменений: {e}")
            return False
    
    def sync_data(self, force: bool = False) -> bool:
        """Основная функция синхронизации данных"""
        logger.info("Начинаем синхронизацию данных...")
        
        # Создаем резервную копию
        self.create_backup()
        
        # Проверяем наличие изменений
        if not force and not self.has_changes():
            logger.info("Нет изменений для синхронизации")
            return True
        
        # Настраиваем git
        self.setup_git_config()
        
        # Синхронизируем изменения
        success = self.commit_and_push()
        
        if success:
            logger.info("Синхронизация данных завершена успешно")
        else:
            logger.error("Ошибка синхронизации данных")
        
        return success
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации"""
        status = {
            "has_changes": self.has_changes(),
            "data_files": len(self.get_data_files()),
            "last_backup": None,
            "git_status": "unknown"
        }
        
        # Получаем информацию о последнем бэкапе
        backups = list(self.backup_dir.glob("backup_*"))
        if backups:
            latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
            status["last_backup"] = latest_backup.name
        
        # Получаем статус git
        try:
            result = subprocess.run(["git", "status", "--short"], 
                                  cwd=self.repo_dir, capture_output=True, text=True)
            status["git_status"] = result.stdout.strip() or "clean"
        except subprocess.CalledProcessError:
            status["git_status"] = "error"
        
        return status

def main():
    """Основная функция для запуска синхронизации"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Синхронизация данных Finance Bot")
    parser.add_argument("--data-dir", default="data", help="Директория с данными")
    parser.add_argument("--force", action="store_true", help="Принудительная синхронизация")
    parser.add_argument("--status", action="store_true", help="Показать статус синхронизации")
    
    args = parser.parse_args()
    
    sync = DataSync(data_dir=args.data_dir)
    
    if args.status:
        status = sync.get_sync_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        success = sync.sync_data(force=args.force)
        exit(0 if success else 1)

if __name__ == "__main__":
    main()
