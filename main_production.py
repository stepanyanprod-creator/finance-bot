#!/usr/bin/env python3
"""
Production версия Finance Bot с улучшенной обработкой ошибок и мониторингом
"""
import os
import sys
import signal
import time
from pathlib import Path

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

# Наши модули
from app.config import config
from app.logger import get_logger
from app.commands import (
    start_command, menu_command, hide_menu_command, export_csv_command,
    rules_list_command, setcat_command, delrule_command, setbalance_command,
    import_csv_command, export_balances_command, export_monthly_command, export_last_months_command
)
from app.handlers.balance import build_balance_conv
from app.handlers.transfer import build_transfer_conv
from app.handlers.purchases import (
    purchases_menu_entry, purchases_back, purchases_router,
    last, undo, stats, today, week, month,
    edit_last_menu_entry, edit_last_router, edit_last_set_date, edit_last_set_merchant,
    edit_last_set_amount, edit_last_set_amount_currency, edit_last_set_category, edit_last_set_payment,
    edit_date_menu_handler, on_photo, receipt_choose_account_finish,
    add_expense_entry, expense_add_amount_handler, expense_add_currency_handler,
    expense_add_merchant_handler, expense_add_category_handler, expense_add_account_handler,
    expense_add_date_handler
)
from app.handlers.income import (
    income_menu_entry, income_back, income_router,
    edit_income_menu_entry, edit_income_router, edit_income_set_source,
    edit_income_set_amount, edit_income_set_amount_currency, edit_income_set_category, edit_income_set_payment,
    income_add_amount_handler, income_add_currency_handler, income_add_source_handler,
    income_add_category_handler, income_add_account_handler, income_add_date_handler
)
from app.handlers.export import build_export_conv
from app.handlers.enhanced_photo import (
    enhanced_on_photo, enhanced_receipt_choose_account_finish
)
from app.handlers.voice import on_voice, voice_choose_category_finish
from app.handlers.rules import rules_menu_handler, rules_back
from app.handlers.balance_menu import balance_menu_handler
from app.keyboards import reply_menu_keyboard
from app.constants import (
    BAL_MENU, ADD_ACC_NAME, ADD_ACC_CURRENCY, EDIT_PICK_ACC, EDIT_NEW_AMOUNT,
    TRANSFER_FROM_ACC, TRANSFER_TO_ACC, TRANSFER_AMOUNT, TRANSFER_SECOND_AMOUNT, TRANSFER_CONFIRM,
    CHOOSE_ACC_FOR_RECEIPT, CHOOSE_CATEGORY_FOR_RECEIPT, BUY_MENU, EDIT_MENU, EDIT_DATE, EDIT_MERCHANT,
    EDIT_AMOUNT, EDIT_AMOUNT_CURRENCY, EDIT_CATEGORY, EDIT_PAYMENT, EDIT_DATE_MENU,
    INCOME_MENU, INCOME_EDIT_MENU, INCOME_EDIT_DATE, INCOME_EDIT_SOURCE,
    INCOME_EDIT_AMOUNT, INCOME_EDIT_AMOUNT_CURRENCY, INCOME_EDIT_CATEGORY, 
    INCOME_EDIT_PAYMENT, INCOME_EDIT_DATE_MENU,
    INCOME_ADD_AMOUNT, INCOME_ADD_CURRENCY, INCOME_ADD_SOURCE, 
    INCOME_ADD_CATEGORY, INCOME_ADD_ACCOUNT, INCOME_ADD_DATE,
    EXPENSE_ADD_AMOUNT, EXPENSE_ADD_CURRENCY, EXPENSE_ADD_MERCHANT,
    EXPENSE_ADD_CATEGORY, EXPENSE_ADD_ACCOUNT, EXPENSE_ADD_DATE,
    EXPORT_MENU, EXPORT_MONTHLY_MENU, EXPORT_PERIOD_MENU
)

logger = get_logger(__name__)

# Глобальная переменная для graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global shutdown_requested
    logger.info(f"Получен сигнал {signum}. Инициируем graceful shutdown...")
    shutdown_requested = True


def setup_handlers(app: Application):
    """Настройка всех обработчиков"""
    
    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("hidemenu", hide_menu_command))
    app.add_handler(CommandHandler("export", export_csv_command))
    
    # Команды для правил и баланса
    app.add_handler(CommandHandler("rules", rules_list_command))
    app.add_handler(CommandHandler("setcat", setcat_command))
    app.add_handler(CommandHandler("delrule", delrule_command))
    app.add_handler(CommandHandler("setbalance", setbalance_command))
    app.add_handler(CommandHandler("import_csv", import_csv_command))
    app.add_handler(CommandHandler("export_balances", export_balances_command))
    app.add_handler(CommandHandler("export_monthly", export_monthly_command))
    app.add_handler(CommandHandler("export_last_months", export_last_months_command))
    
    # Конверсейшн: обмен между счетами (должен быть ПЕРЕД балансом)
    transfer_conv = build_transfer_conv()
    app.add_handler(transfer_conv)
    
    # Конверсейшн: меню экспорта
    export_conv = build_export_conv()
    app.add_handler(export_conv)
    
    # Обработчик баланса
    app.add_handler(build_balance_conv())
    
    # Конверсейшн: меню Расходы
    purchases_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛍 Расходы$"), purchases_menu_entry)],
        states={
            BUY_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchases_router)],
            EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_router)],
            EDIT_DATE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date_menu_handler)],
            EDIT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_date)],
            EDIT_MERCHANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_merchant)],
            EDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_amount)],
            EDIT_AMOUNT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_amount_currency)],
            EDIT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_category)],
            EDIT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_set_payment)],
            EXPENSE_ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_amount_handler)],
            EXPENSE_ADD_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_currency_handler)],
            EXPENSE_ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_date_handler)],
            EXPENSE_ADD_MERCHANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_merchant_handler)],
            EXPENSE_ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_category_handler)],
            EXPENSE_ADD_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_add_account_handler)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬅️ Назад$"), purchases_back)],
        allow_reentry=True,
    )
    app.add_handler(purchases_conv)

    # Конверсейшн: меню Доходы
    income_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💰 Доходы$"), income_menu_entry)],
        states={
            INCOME_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_router)],
            INCOME_EDIT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_router)],
            INCOME_EDIT_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_set_source)],
            INCOME_EDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_set_amount)],
            INCOME_EDIT_AMOUNT_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_set_amount_currency)],
            INCOME_EDIT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_set_category)],
            INCOME_EDIT_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_income_set_payment)],
            # Новые состояния для пошагового добавления дохода
            INCOME_ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_amount_handler)],
            INCOME_ADD_CURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_currency_handler)],
            INCOME_ADD_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_date_handler)],
            INCOME_ADD_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_source_handler)],
            INCOME_ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_category_handler)],
            INCOME_ADD_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_add_account_handler)],
        },
        fallbacks=[MessageHandler(filters.Regex("^⬅️ Назад$"), income_back)],
        allow_reentry=True,
    )
    app.add_handler(income_conv)

    # Конверсейшн: приём фото/голоса → выбор счёта (улучшенная версия)
    receipt_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.PHOTO, enhanced_on_photo),  # Используем улучшенный обработчик
            MessageHandler(filters.VOICE | filters.AUDIO, on_voice),
        ],
        states={
            CHOOSE_ACC_FOR_RECEIPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_receipt_choose_account_finish),
            ],
            CHOOSE_CATEGORY_FOR_RECEIPT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, voice_choose_category_finish),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Отмена$"), enhanced_receipt_choose_account_finish)],
        allow_reentry=True,
    )
    app.add_handler(receipt_conv)

    # Общий роутер текста — после всех конверсейшнов
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_menu_router))


async def reply_menu_router(update, context: ContextTypes.DEFAULT_TYPE):
    """Главный роутер текстовых сообщений"""
    text = (update.effective_message.text or "").strip()
    
    # Проверяем, есть ли ожидающие данные для обработки
    if context.user_data.get("pending_income") or context.user_data.get("pending_receipt"):
        # Если есть ожидающие данные, обрабатываем их через enhanced_receipt_choose_account_finish
        return await enhanced_receipt_choose_account_finish(update, context)
    
    if text == "🛍 Расходы":
        return await purchases_menu_entry(update, context)
    if text == "💰 Доходы":
        return await income_menu_entry(update, context)
    if text == "📤 Экспорт":
        from app.handlers.export import export_menu_entry
        return await export_menu_entry(update, context)
    if text == "💼 Баланс":
        return await balance_menu_handler(update, context)
    if text == "❌ Скрыть меню":
        return await hide_menu_command(update, context)
    
    # Обработчик для возврата из меню категорий
    if text == "⬅️ Назад":
        return await rules_back(update, context)


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик ошибок для production"""
    error = context.error
    logger.error(f"Exception while handling an update: {error}")
    
    # Логируем дополнительную информацию
    if update and update.effective_user:
        logger.error(f"User ID: {update.effective_user.id}, Username: {update.effective_user.username}")
    
    # Если это конфликт с другим экземпляром бота
    if "Conflict" in str(error) and "getUpdates" in str(error):
        logger.error("Обнаружен конфликт с другим экземпляром бота. Остановка...")
        logger.error("Убедитесь, что запущен только один экземпляр бота.")
        logger.error("Используйте Docker или systemd для управления процессами.")
        sys.exit(1)
    
    # Для других ошибок - продолжаем работу
    logger.error(f"Продолжаем работу после ошибки: {error}")


def main():
    """Главная функция для production"""
    global shutdown_requested
    
    # Настраиваем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Finance Bot in production mode...")
    
    # Проверяем переменные окружения
    if not config.bot.token:
        logger.error("BOT_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
    # Создаем необходимые директории
    data_dir = Path(config.bot.data_dir)
    data_dir.mkdir(exist_ok=True)
    (data_dir / "exports").mkdir(exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)
    
    try:
        # Создаем приложение
        app = Application.builder().token(config.bot.token).build()
        
        # Настраиваем обработчики
        setup_handlers(app)
        
        # Добавляем обработчик ошибок
        app.add_error_handler(error_handler)
        
        logger.info("Bot started successfully")
        logger.info("Бот запущен в production режиме")
        
        # Запускаем бота с обработкой graceful shutdown
        app.run_polling(
            stop_signals=None,  # Отключаем встроенную обработку сигналов
            close_loop=False    # Не закрываем event loop автоматически
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        logger.info("Bot shutdown complete")
        logger.info("Завершение работы бота")


if __name__ == "__main__":
    main()
