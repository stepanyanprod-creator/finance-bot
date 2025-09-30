# app/handlers/export.py
"""Обработчики для меню экспорта данных"""

import os
from datetime import date, datetime
from telegram import Update, InputFile
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import EXPORT_MENU, EXPORT_MONTHLY_MENU, EXPORT_PERIOD_MENU
from app.keyboards import (
    reply_menu_keyboard, export_menu_kb, export_monthly_menu_kb, export_period_menu_kb
)
from app.utils import get_user_id as _uid
from app.logger import get_logger

logger = get_logger(__name__)


async def export_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в меню экспорта"""
    await update.effective_message.reply_text(
        "📤 Меню экспорта данных:\n\n"
        "• 📄 Простой CSV - обычный экспорт транзакций\n"
        "• 📊 По месяцам - детальный экспорт с таблицами\n"
        "• 📅 Текущий месяц - быстрый экспорт текущего месяца\n"
        "• 📆 Последние 3 месяца - экспорт за период\n"
        "• 💼 Балансы - экспорт балансов счетов",
        reply_markup=export_menu_kb()
    )
    return EXPORT_MENU


async def export_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для меню экспорта"""
    text = (update.effective_message.text or "").strip()
    
    if text == "📄 Простой CSV":
        return await export_simple_csv(update, context)
    elif text == "📊 По месяцам":
        return await export_monthly_menu_entry(update, context)
    elif text == "📅 Текущий месяц":
        return await export_current_month(update, context)
    elif text == "📆 Последние 3 месяца":
        return await export_last_3_months(update, context)
    elif text == "💼 Балансы":
        return await export_balances(update, context)
    elif text == "⬅️ Назад":
        return await export_back(update, context)
    
    return EXPORT_MENU


async def export_simple_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Простой экспорт CSV"""
    from app.commands import export_csv_command
    from app.keyboards import reply_menu_keyboard
    await export_csv_command(update, context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_balances(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт балансов"""
    from app.commands import export_balances_command
    from app.keyboards import reply_menu_keyboard
    await export_balances_command(update, context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_current_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт текущего месяца"""
    from app.commands import export_monthly_command
    from app.keyboards import reply_menu_keyboard
    
    # Создаем фиктивный контекст с пустыми аргументами
    class MockContext:
        def __init__(self):
            self.args = []
    
    mock_context = MockContext()
    await export_monthly_command(update, mock_context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_last_3_months(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт за последние 3 месяца"""
    from app.commands import export_last_months_command
    from app.keyboards import reply_menu_keyboard
    
    # Создаем фиктивный контекст с аргументом 3
    class MockContext:
        def __init__(self):
            self.args = ["3"]
    
    mock_context = MockContext()
    await export_last_months_command(update, mock_context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_monthly_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в меню выбора месяца для экспорта"""
    await update.effective_message.reply_text(
        "📊 Выберите месяц для экспорта:\n\n"
        "Экспорт включает отдельные таблицы:\n"
        "• 📈 Доходы\n"
        "• 💸 Расходы\n"
        "• 🏦 Счета\n"
        "• 💱 Обмены\n"
        "• 📋 Сводная",
        reply_markup=export_monthly_menu_kb()
    )
    return EXPORT_MONTHLY_MENU


async def export_monthly_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для меню выбора месяца"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        return await export_menu_entry(update, context)
    
    # Парсим выбранный месяц
    try:
        year, month = parse_month_selection(text)
        if year and month:
            return await export_specific_month(update, context, year, month)
    except Exception as e:
        logger.error(f"Error parsing month selection: {e}")
    
    await update.effective_message.reply_text(
        "❌ Не удалось определить месяц. Попробуйте еще раз.",
        reply_markup=export_monthly_menu_kb()
    )
    return EXPORT_MONTHLY_MENU


def parse_month_selection(text: str) -> tuple:
    """Парсит выбор месяца из текста кнопки"""
    from datetime import date
    
    # Убираем эмодзи и лишние пробелы
    text = text.replace("📅", "").strip()
    
    # Текущий месяц
    if "текущий" in text.lower() or text == date.today().strftime("%B %Y"):
        today = date.today()
        return today.year, today.month
    
    # Парсим название месяца и год
    month_names = {
        "январь": 1, "февраль": 2, "март": 3, "апрель": 4,
        "май": 5, "июнь": 6, "июль": 7, "август": 8,
        "сентябрь": 9, "октябрь": 10, "ноябрь": 11, "декабрь": 12
    }
    
    parts = text.split()
    if len(parts) >= 2:
        month_name = parts[0].lower()
        year_str = parts[1]
        
        if month_name in month_names:
            try:
                year = int(year_str)
                month = month_names[month_name]
                return year, month
            except ValueError:
                pass
    
    return None, None


async def export_specific_month(update: Update, context: ContextTypes.DEFAULT_TYPE, year: int, month: int):
    """Экспорт конкретного месяца"""
    from app.commands import export_monthly_command
    from app.keyboards import reply_menu_keyboard
    
    # Создаем фиктивный контекст с аргументами
    class MockContext:
        def __init__(self, year, month):
            self.args = [str(year), str(month)]
    
    mock_context = MockContext(year, month)
    await export_monthly_command(update, mock_context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_period_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в меню выбора периода для экспорта"""
    await update.effective_message.reply_text(
        "📆 Выберите период для экспорта:\n\n"
        "Экспорт включает данные за несколько месяцев\n"
        "с отдельными таблицами для каждого месяца.",
        reply_markup=export_period_menu_kb()
    )
    return EXPORT_PERIOD_MENU


async def export_period_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для меню выбора периода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        return await export_menu_entry(update, context)
    
    # Определяем количество месяцев
    months_count = None
    if "3 месяца" in text:
        months_count = 3
    elif "6 месяцев" in text:
        months_count = 6
    elif "12 месяцев" in text:
        months_count = 12
    
    if months_count:
        return await export_period(update, context, months_count)
    
    await update.effective_message.reply_text(
        "❌ Не удалось определить период. Попробуйте еще раз.",
        reply_markup=export_period_menu_kb()
    )
    return EXPORT_PERIOD_MENU


async def export_period(update: Update, context: ContextTypes.DEFAULT_TYPE, months_count: int):
    """Экспорт за период"""
    from app.commands import export_last_months_command
    from app.keyboards import reply_menu_keyboard
    
    # Создаем фиктивный контекст с аргументом
    class MockContext:
        def __init__(self, months):
            self.args = [str(months)]
    
    mock_context = MockContext(months_count)
    await export_last_months_command(update, mock_context)
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


async def export_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    await update.effective_message.reply_text(
        "Главное меню:",
        reply_markup=reply_menu_keyboard()
    )
    return ConversationHandler.END


# Фабрика ConversationHandler для main.py
def build_export_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📤 Экспорт$"), export_menu_entry),
        ],
        states={
            EXPORT_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, export_menu_router),
            ],
            EXPORT_MONTHLY_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, export_monthly_menu_router),
            ],
            EXPORT_PERIOD_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, export_period_menu_router),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬅️ Назад$"), export_back)],
        allow_reentry=True,
    )
