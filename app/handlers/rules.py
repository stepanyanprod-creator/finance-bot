# app/handlers/rules.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils import get_user_id
from app.logger import get_logger
from app.commands import rules_list_command
from app.categories import format_categories_list, get_categories_list

logger = get_logger(__name__)


async def rules_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки '🧩 Правила' - показывает категории"""
    logger.info(f"User {get_user_id(update)} opened categories menu")
    
    # Показываем только категории
    categories_text = format_categories_list()
    
    # Создаем клавиатуру для возврата
    keyboard = ReplyKeyboardMarkup(
        [["⬅️ Назад"]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    
    await update.effective_message.reply_text(
        f"{categories_text}\n\n"
        "Эти категории используются для автоматической сортировки ваших расходов.",
        reply_markup=keyboard
    )




async def rules_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    logger.info(f"User {get_user_id(update)} returned to main menu")
    
    from app.keyboards import reply_menu_keyboard
    
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
