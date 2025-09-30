"""
Команды для синхронизации данных
"""

from telegram import Update
from telegram.ext import ContextTypes
from app.logger import get_logger
from data_sync import DataSync
from auto_save_hook import get_auto_save_hook, save_data_now

logger = get_logger(__name__)

async def sync_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручной синхронизации данных"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил синхронизацию данных")
        
        # Создаем экземпляр синхронизации
        data_sync = DataSync()
        
        # Получаем статус
        status = data_sync.get_sync_status()
        
        if not status["has_changes"]:
            await update.message.reply_text(
                "📊 **Статус синхронизации**\n\n"
                "✅ Нет изменений для синхронизации\n"
                f"📁 Файлов данных: {status['data_files']}\n"
                f"🔄 Статус git: {status['git_status']}"
            )
            return
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🔄 Синхронизация данных...")
        
        # Выполняем синхронизацию
        success = data_sync.sync_data()
        
        if success:
            await progress_msg.edit_text(
                "✅ **Синхронизация завершена**\n\n"
                "📊 Данные успешно сохранены в GitHub\n"
                "🔄 Изменения отправлены в репозиторий"
            )
        else:
            await progress_msg.edit_text(
                "❌ **Ошибка синхронизации**\n\n"
                "Не удалось сохранить данные в GitHub\n"
                "Попробуйте позже или обратитесь к администратору"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде синхронизации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при синхронизации данных"
        )

async def sync_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки статуса синхронизации"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил статус синхронизации")
        
        # Получаем статус автосохранения
        auto_save = get_auto_save_hook()
        if auto_save:
            auto_status = auto_save.get_status()
        else:
            auto_status = {"running": False, "last_save": "Неизвестно"}
        
        # Получаем статус синхронизации
        data_sync = DataSync()
        sync_status = data_sync.get_sync_status()
        
        # Формируем ответ
        status_text = "📊 **Статус синхронизации данных**\n\n"
        
        if auto_status["running"]:
            status_text += "🔄 **Автосохранение:** Активно\n"
            status_text += f"⏰ **Интервал:** {auto_status['save_interval']}с\n"
            status_text += f"📅 **Последнее сохранение:** {auto_status['last_save']}\n\n"
        else:
            status_text += "⏸️ **Автосохранение:** Неактивно\n\n"
        
        status_text += f"📁 **Файлов данных:** {sync_status['data_files']}\n"
        status_text += f"🔄 **Статус git:** {sync_status['git_status']}\n"
        
        if sync_status["has_changes"]:
            status_text += "⚠️ **Есть несохраненные изменения**\n"
            status_text += "Используйте /sync для ручного сохранения"
        else:
            status_text += "✅ **Все данные синхронизированы**"
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Ошибка в команде статуса: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении статуса"
        )

async def force_sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для принудительной синхронизации"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил принудительную синхронизацию")
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🔄 Принудительная синхронизация...")
        
        # Выполняем принудительную синхронизацию
        success = save_data_now(force=True)
        
        if success:
            await progress_msg.edit_text(
                "✅ **Принудительная синхронизация завершена**\n\n"
                "📊 Все данные принудительно сохранены\n"
                "🔄 Изменения отправлены в GitHub"
            )
        else:
            await progress_msg.edit_text(
                "❌ **Ошибка принудительной синхронизации**\n\n"
                "Не удалось выполнить принудительное сохранение"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде принудительной синхронизации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при принудительной синхронизации"
        )
