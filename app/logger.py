# app/logger.py
import logging
import sys
from typing import Optional
from app.config import config


def setup_logging(level: Optional[str] = None) -> logging.Logger:
    """Настроить систему логирования"""
    
    # Определяем уровень логирования
    if level is None:
        level = "DEBUG" if config.bot.debug else "INFO"
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Файловый обработчик (если не в режиме отладки)
    if not config.bot.debug:
        file_handler = logging.FileHandler('finance_bot.log', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.WARNING)  # В файл только предупреждения и ошибки
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Получить логгер для модуля"""
    return logging.getLogger(name)


# Настраиваем логирование при импорте модуля
logger = setup_logging()
