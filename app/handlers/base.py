# app/handlers/base.py
from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes
from typing import Optional

from app.utils import get_user_id
from app.logger import get_logger


class BaseHandler(ABC):
    """Базовый класс для всех обработчиков"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной метод обработки"""
        pass
    
    def get_user_id(self, update: Update) -> int:
        """Получить ID пользователя"""
        return get_user_id(update)
    
    async def send_error_message(self, update: Update, error: str):
        """Отправить сообщение об ошибке"""
        self.logger.error(f"Error in {self.__class__.__name__}: {error}")
        await update.effective_message.reply_text(f"❌ {error}")
    
    async def send_success_message(self, update: Update, message: str):
        """Отправить сообщение об успехе"""
        await update.effective_message.reply_text(f"✅ {message}")


class ConversationHandler(BaseHandler):
    """Базовый класс для обработчиков с состояниями"""
    
    def __init__(self):
        super().__init__()
        self.current_state: Optional[str] = None
    
    def set_state(self, state: str):
        """Установить текущее состояние"""
        self.current_state = state
        self.logger.debug(f"State changed to: {state}")
    
    def get_state(self) -> Optional[str]:
        """Получить текущее состояние"""
        return self.current_state
