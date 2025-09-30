# app/handlers/balance_menu.py
from telegram import Update
from telegram.ext import ContextTypes

from app.utils import get_user_id
from app.logger import get_logger
from app.handlers.balance import balance_menu_entry

logger = get_logger(__name__)


async def balance_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки '💼 Баланс'"""
    logger.info(f"User {get_user_id(update)} opened balance menu")
    return await balance_menu_entry(update, context)
