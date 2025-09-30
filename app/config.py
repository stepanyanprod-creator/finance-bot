# app/config.py
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class BotConfig:
    """Конфигурация бота"""
    token: str
    openai_api_key: Optional[str] = None
    data_dir: str = "data"
    debug: bool = False


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    data_dir: str
    csv_fields: list[str]


@dataclass
class AppConfig:
    """Основная конфигурация приложения"""
    bot: BotConfig
    database: DatabaseConfig


def load_config() -> AppConfig:
    """Загружает конфигурацию из переменных окружения"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не найден в переменных окружения")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        # Импортируем логгер только здесь, чтобы избежать циклических импортов
        import logging
        logging.warning("OPENAI_API_KEY не найден — голосовые команды не будут работать.")
    
    data_dir = os.getenv("DATA_DIR", "data")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    return AppConfig(
        bot=BotConfig(
            token=bot_token,
            openai_api_key=openai_key,
            data_dir=data_dir,
            debug=debug
        ),
        database=DatabaseConfig(
            data_dir=data_dir,
            csv_fields=["date", "merchant", "total", "currency", "category", "payment_method", "source"]
        )
    )


# Глобальная конфигурация
config = load_config()
