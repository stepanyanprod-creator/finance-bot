# app/middleware.py
"""Middleware для обработки запросов и безопасности"""

import time
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes

from app.logger import get_logger
from app.exceptions import FinanceBotError

logger = get_logger(__name__)


class RateLimiter:
    """Простой rate limiter для пользователей"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """Проверить, разрешен ли запрос от пользователя"""
        current_time = time.time()
        
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        
        # Очищаем старые запросы
        self.user_requests[user_id] = [
            req_time for req_time in self.user_requests[user_id]
            if current_time - req_time < self.time_window
        ]
        
        # Проверяем лимит
        if len(self.user_requests[user_id]) >= self.max_requests:
            return False
        
        # Добавляем текущий запрос
        self.user_requests[user_id].append(current_time)
        return True


# Глобальный rate limiter
rate_limiter = RateLimiter()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


async def rate_limit_middleware(handler: Callable) -> Callable:
    """Middleware для rate limiting"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        user_id = update.effective_user.id if update.effective_user else 0
        
        if not rate_limiter.is_allowed(user_id):
            await update.effective_message.reply_text(
                "⏰ Слишком много запросов. Подождите минуту."
            )
            return
        
        return await handler(update, context)
    
    return wrapper


async def logging_middleware(handler: Callable) -> Callable:
    """Middleware для логирования"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        user_id = update.effective_user.id if update.effective_user else 0
        username = update.effective_user.username if update.effective_user else "unknown"
        
        start_time = time.time()
        
        try:
            logger.info(f"Processing request from user {user_id} (@{username})")
            result = await handler(update, context)
            
            duration = time.time() - start_time
            logger.info(f"Request completed in {duration:.2f}s for user {user_id}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request failed after {duration:.2f}s for user {user_id}: {e}")
            raise
    
    return wrapper


def validate_user_input(text: str, max_length: int = 1000) -> bool:
    """Валидация пользовательского ввода"""
    if not text or len(text.strip()) == 0:
        return False
    
    if len(text) > max_length:
        return False
    
    # Проверка на потенциально опасные символы
    dangerous_chars = ['<', '>', '&', '"', "'", '\\', '/', ';', '|', '`']
    if any(char in text for char in dangerous_chars):
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от опасных символов"""
    import re
    # Удаляем все символы кроме букв, цифр, точек, дефисов и подчеркиваний
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Ограничиваем длину
    return sanitized[:100]
