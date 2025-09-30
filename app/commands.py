# app/commands.py
import os
import json
from telegram import Update, InputFile, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from app.utils import get_user_id
from app.storage import ensure_csv
from app.keyboards import reply_menu_keyboard
from app.logger import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    logger.info(f"User {get_user_id(update)} started the bot")
    
    await update.effective_message.reply_text(
        "Привет! Отправь фото чека или голосовое — запишу покупку.\n\n"
        "📋 Доступно 15 категорий расходов:\n"
        "🍎 Питание, 🏠 Жильё, 🧽 Бытовые товары, 🚗 Транспорт,\n"
        "📱 Коммунальные услуги, 💊 Здоровье, 👕 Одежда,\n"
        "📚 Образование, 🎬 Досуг, 🎁 Подарки, 📦 Прочие,\n"
        "🏦 Банковские операции, 💻 ПО, 📱 Техника, 🍽️ Еда вне дома\n\n"
        "Команды:\n"
        "• /export — выслать CSV-файл транзакций\n"
        "• /export_balances — экспорт балансов в CSV\n"
        "• /export_monthly [год] [месяц] — экспорт по месяцам с таблицами\n"
        "• /export_last_months [N] — экспорт за последние N месяцев\n"
        "• /sync — синхронизация данных с GitHub\n"
        "• /sync_status — статус синхронизации\n"
        "• /force_sync — принудительная синхронизация\n"
        "• /init_git — инициализация git репозитория\n"
        "• /check_data — проверить файлы данных\n"
        "• /upload_all — загрузить все изменения в GitHub\n"
        "• /setup_render_auth — настроить аутентификацию на Render\n"
        "• /import_csv — импорт балансов из CSV файла\n"
        "• /setbalance <amount> <currency> | /setbalance <amount> <category> <currency>\n"
        "• /balance — меню Баланс\n"
        "• /menu — показать клавиатуру\n"
        "• /hidemenu — скрыть клавиатуру\n\n"
        "Раздел «🛍 Расходы» — в подменю.\n"
        "Раздел «📋 Категории» — показывает доступные категории.",
        reply_markup=reply_menu_keyboard()
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /menu"""
    await update.effective_message.reply_text(
        "Меню включено. Выберите действие:", 
        reply_markup=reply_menu_keyboard()
    )


async def hide_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /hidemenu"""
    await update.effective_message.reply_text(
        "Меню скрыто.", 
        reply_markup=ReplyKeyboardRemove()
    )


async def export_csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export"""
    user_id = get_user_id(update)
    logger.info(f"User {user_id} requested CSV export")
    
    ensure_csv(user_id)
    path = os.path.join("data", str(user_id), "finance.csv")
    
    if not os.path.exists(path):
        return await update.effective_message.reply_text("Пока нет данных.")
    
    try:
        with open(path, "rb") as f:
            await update.effective_message.reply_document(
                InputFile(f, filename="finance.csv")
            )
        logger.info(f"CSV exported successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to export CSV for user {user_id}: {e}")
        await update.effective_message.reply_text("Ошибка при экспорте файла.")


async def rules_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /rules - показать список правил"""
    from app.rules import load_rules
    from app.utils import get_user_id
    
    user_id = get_user_id(update)
    rules = load_rules(user_id)
    
    if not rules:
        return await update.effective_message.reply_text("Правил пока нет. Добавьте через /setcat.")
    
    lines = ["🧩 Правила:"]
    for rule in rules:
        lines.append(
            f"#{rule.get('id', '?')} → {rule.get('category', '')}\n"
            f"  match: {json.dumps(rule.get('match', {}), ensure_ascii=False)}"
        )
    await update.effective_message.reply_text("\n".join(lines))


async def setcat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /setcat - добавить правило категоризации"""
    from app.rules import load_rules, save_rules
    from app.utils import get_user_id, generate_rule_id
    import json
    import re
    
    msg = update.effective_message
    text = (msg.text or "").strip()
    
    try:
        if "->" not in text:
            raise ValueError("Формат: /setcat merchant=...,item=... -> category")
        
        left, right = text.split("->", 1)
        category = right.strip()
        if not category:
            raise ValueError("Не указана категория после '->'.")

        left = left.replace("/setcat", "", 1).strip()
        parts = [p.strip() for p in re.split(r"\s+", left) if p.strip()]
        match = {}
        
        for part in parts:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key in ("merchant", "merchant_contains"):
                match["merchant_contains"] = [s.strip() for s in value.split(",") if s.strip()]
            elif key in ("item", "item_contains"):
                match["item_contains"] = [s.strip() for s in value.split(",") if s.strip()]
            elif key == "currency":
                match["currency_is"] = value
            elif key == "payment":
                match["payment_is"] = value
            elif key == "total_min":
                match["total_min"] = float(value.replace(",", "."))
            elif key == "total_max":
                match["total_max"] = float(value.replace(",", "."))
        
        if not match:
            raise ValueError("Не распознал условия. Примеры: merchant=REWE,lidl | item=кофе,латте | total_max=50")

        rules = load_rules(get_user_id(update))
        new_rule = {"id": generate_rule_id(rules), "category": category, "match": match}
        rules.append(new_rule)
        save_rules(get_user_id(update), rules)
        
        await msg.reply_text(
            f"✅ Правило добавлено: #{new_rule['id']} → {category}\n"
            f"match={json.dumps(match, ensure_ascii=False)}"
        )
    except Exception as e:
        await msg.reply_text(f"❌ {e}")


async def delrule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delrule - удалить правило"""
    from app.rules import load_rules, save_rules
    from app.utils import get_user_id
    
    msg = update.effective_message
    args = context.args
    
    if not args:
        return await msg.reply_text("Используйте: /delrule <id>")
    
    try:
        rule_id = int(args[0])
    except ValueError:
        return await msg.reply_text("id должен быть числом.")
    
    rules = load_rules(get_user_id(update))
    new_rules = [r for r in rules if int(r.get("id", 0)) != rule_id]
    
    if len(new_rules) == len(rules):
        return await msg.reply_text("Правило с таким id не найдено.")
    
    save_rules(get_user_id(update), new_rules)
    await msg.reply_text(f"🗑 Правило #{rule_id} удалено.")


async def setbalance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /setbalance - установить баланс"""
    from app.storage import set_balance
    from app.utils import get_user_id
    
    msg = update.effective_message
    
    try:
        # /setbalance 1000 EUR  |  /setbalance 300 groceries EUR
        args = context.args
        if len(args) == 2:
            amount, currency = args
            category = None
        elif len(args) == 3:
            amount, category, currency = args
        else:
            raise ValueError("Использование: /setbalance <amount> <currency> ИЛИ /setbalance <amount> <category> <currency>")
        
        amount = float(str(amount).replace(",", "."))
        key, val = set_balance(get_user_id(update), amount, currency, category)
        await msg.reply_text(f"✅ Баланс для '{key}' установлен: {val:.2f}")
    except Exception as e:
        await msg.reply_text(f"❌ {e}")


async def import_csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /import_csv - импорт балансов из CSV файла"""
    from app.services.csv_importer import import_csv_balances
    from app.storage import add_account
    from app.utils import get_user_id
    
    user_id = get_user_id(update)
    msg = update.effective_message
    
    # Проверяем, есть ли прикрепленный файл
    if not msg.document:
        return await msg.reply_text(
            "❌ Пожалуйста, прикрепите CSV файл с балансами.\n\n"
            "Формат файла:\n"
            "• Первая колонка: названия счетов\n"
            "• Остальные колонки: месяцы с балансами\n"
            "• Поддерживаемые валюты: EUR, UAH, USD, RUB\n\n"
            "Пример: /import_csv (и прикрепите файл)"
        )
    
    # Проверяем расширение файла
    if not msg.document.file_name.lower().endswith('.csv'):
        return await msg.reply_text("❌ Файл должен иметь расширение .csv")
    
    try:
        # Скачиваем файл
        file = await context.bot.get_file(msg.document.file_id)
        temp_path = f"temp_import_{user_id}.csv"
        
        await file.download_to_drive(temp_path)
        
        # Импортируем данные
        result = import_csv_balances(temp_path)
        
        if not result['success']:
            return await msg.reply_text(f"❌ {result['message']}")
        
        data = result['data']
        accounts_for_import = data['accounts_for_import']
        
        if not accounts_for_import:
            return await msg.reply_text("❌ В файле не найдено счетов для импорта")
        
        # Автоматически создаем счета
        from app.services.csv_importer import auto_create_accounts_from_csv
        create_result = auto_create_accounts_from_csv(user_id, data, overwrite_existing=False)
        
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # Формируем ответ
        response = f"✅ Импорт завершен!\n\n"
        response += f"📊 Создано счетов: {create_result['created']}\n"
        response += f"🔄 Обновлено счетов: {create_result['updated']}\n"
        response += f"⏭️ Пропущено счетов: {create_result['skipped']}\n"
        response += f"💰 Найдено валют: {len(data['currencies'])}\n"
        response += f"📅 Данные за период: {len(data['headers'])-1} месяцев\n\n"
        
        if create_result['errors']:
            response += f"⚠️ Ошибки при импорте:\n" + "\n".join(create_result['errors'][:5])
            if len(create_result['errors']) > 5:
                response += f"\n... и еще {len(create_result['errors'])-5} ошибок"
        
        response += f"\n\n💡 Используйте /balance для просмотра счетов"
        
        await msg.reply_text(response)
        logger.info(f"User {user_id} imported {create_result['created']} accounts from CSV")
        
    except Exception as e:
        logger.error(f"CSV import error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при импорте: {e}")
        
        # Удаляем временный файл в случае ошибки
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)


async def export_balances_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export_balances - экспорт балансов в CSV"""
    from app.services.csv_importer import export_balances_to_csv
    from app.utils import get_user_id
    
    user_id = get_user_id(update)
    msg = update.effective_message
    
    try:
        # Экспортируем балансы
        result = export_balances_to_csv(user_id)
        
        if not result['success']:
            return await msg.reply_text(f"❌ {result['message']}")
        
        # Отправляем файл пользователю
        file_path = result['file_path']
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                await msg.reply_document(
                    InputFile(f, filename=f"balances_{user_id}.csv"),
                    caption=f"✅ Экспорт балансов завершен!\n\n"
                           f"📊 Счетов: {result['accounts_count']}\n"
                           f"💰 Валют: {result['currencies_count']}"
                )
            
            # Удаляем временный файл
            os.remove(file_path)
            logger.info(f"User {user_id} exported balances successfully")
        else:
            await msg.reply_text("❌ Ошибка: файл не найден после создания")
            
    except Exception as e:
        logger.error(f"Balance export error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при экспорте балансов: {e}")


async def export_monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export_monthly - экспорт данных за месяц"""
    from app.services.enhanced_exporter import export_current_month, create_export_archive
    from app.utils import get_user_id
    
    user_id = get_user_id(update)
    msg = update.effective_message
    args = context.args
    
    try:
        # Определяем период экспорта
        if len(args) == 2:
            # /export_monthly 2024 3
            year = int(args[0])
            month = int(args[1])
            if not (1 <= month <= 12):
                return await msg.reply_text("❌ Месяц должен быть от 1 до 12")
        elif len(args) == 1:
            # /export_monthly 3 (текущий год)
            from datetime import date
            year = date.today().year
            month = int(args[0])
            if not (1 <= month <= 12):
                return await msg.reply_text("❌ Месяц должен быть от 1 до 12")
        else:
            # /export_monthly (текущий месяц)
            from datetime import date
            today = date.today()
            year = today.year
            month = today.month
        
        # Создаем архив с данными
        result = create_export_archive(user_id, year, month)
        
        if not result['success']:
            return await msg.reply_text(f"❌ {result['message']}")
        
        # Отправляем архив пользователю
        archive_path = result['archive_path']
        if os.path.exists(archive_path):
            with open(archive_path, "rb") as f:
                await msg.reply_document(
                    InputFile(f, filename=f"finance_export_{year}_{month:02d}.zip"),
                    caption=f"✅ Экспорт за {year}-{month:02d} завершен!\n\n"
                           f"📁 Файлов в архиве: {result['files_count']}\n"
                           f"📊 Таблицы: доходы, расходы, счета, обмены, сводная"
                )
            
            # Удаляем архив
            os.remove(archive_path)
            logger.info(f"User {user_id} exported monthly data for {year}-{month}")
        else:
            await msg.reply_text("❌ Ошибка: архив не найден после создания")
            
    except ValueError as e:
        await msg.reply_text("❌ Неверный формат команды. Используйте:\n"
                           "• /export_monthly - текущий месяц\n"
                           "• /export_monthly 3 - март текущего года\n"
                           "• /export_monthly 2024 3 - март 2024")
    except Exception as e:
        logger.error(f"Monthly export error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при экспорте: {e}")


async def export_last_months_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export_last_months - экспорт данных за последние N месяцев"""
    from app.services.enhanced_exporter import export_last_n_months
    from app.utils import get_user_id
    
    user_id = get_user_id(update)
    msg = update.effective_message
    args = context.args
    
    try:
        if not args:
            months_count = 3  # По умолчанию 3 месяца
        else:
            months_count = int(args[0])
            if months_count <= 0 or months_count > 12:
                return await msg.reply_text("❌ Количество месяцев должно быть от 1 до 12")
        
        # Экспортируем данные
        result = export_last_n_months(user_id, months_count)
        
        if not result['success']:
            return await msg.reply_text(f"❌ {result['message']}")
        
        # Создаем архив с данными за все месяцы
        import zipfile
        from datetime import date
        
        output_dir = f"exports/{user_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        archive_name = f"finance_export_{user_id}_last_{months_count}_months.zip"
        archive_path = os.path.join(output_dir, archive_name)
        
        # Собираем все файлы из результатов экспорта
        all_files = []
        for export_result in result.get('results', []):
            if export_result.get('success'):
                all_files.extend(export_result.get('files_created', []))
        
        if not all_files:
            return await msg.reply_text("❌ Нет данных для экспорта за указанный период")
        
        # Создаем архив
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in all_files:
                if os.path.exists(file_path):
                    # Добавляем файл в архив с относительным путем
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        
        # Удаляем отдельные файлы после архивирования
        for file_path in all_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Отправляем архив пользователю
        if os.path.exists(archive_path):
            with open(archive_path, "rb") as f:
                await msg.reply_document(
                    InputFile(f, filename=f"finance_export_last_{months_count}_months.zip"),
                    caption=f"✅ Экспорт за {months_count} месяцев завершен!\n\n"
                           f"📁 Файлов в архиве: {len(all_files)}\n"
                           f"📊 Успешных экспортов: {result['successful_count']}/{result['total_count']}"
                )
            
            # Удаляем архив
            os.remove(archive_path)
            logger.info(f"User {user_id} exported data for last {months_count} months")
        else:
            await msg.reply_text("❌ Ошибка: архив не найден после создания")
            
    except ValueError as e:
        await msg.reply_text("❌ Неверный формат команды. Используйте:\n"
                           "• /export_last_months - последние 3 месяца\n"
                           "• /export_last_months 6 - последние 6 месяцев")
    except Exception as e:
        logger.error(f"Last months export error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при экспорте: {e}")


# ==================== КОМАНДЫ СИНХРОНИЗАЦИИ ДАННЫХ ====================

async def sync_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручной синхронизации данных"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил синхронизацию данных")
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🔄 Синхронизация данных...")
        
        # Пытаемся синхронизацию с GitHub
        try:
            from simple_data_sync import sync_data_now, get_sync_status
            
            # Получаем статус
            status = get_sync_status()
            
            if not status["has_changes"]:
                await progress_msg.edit_text(
                    "📊 **Статус синхронизации**\n\n"
                    "✅ Нет изменений для синхронизации\n"
                    f"📁 Директория данных: {status['data_dir']}\n"
                    f"🔄 Статус git: {status['git_status']}\n\n"
                    "💡 Все данные уже синхронизированы"
                )
                return
            
            # Выполняем синхронизацию
            success = sync_data_now()
            
            if success:
                await progress_msg.edit_text(
                    "✅ **Синхронизация завершена**\n\n"
                    "📊 Данные успешно сохранены в GitHub\n"
                    "🔄 Изменения отправлены в репозиторий\n\n"
                    "💡 Используйте /sync_status для проверки"
                )
            else:
                # Если синхронизация с GitHub не удалась, используем резервное копирование
                await progress_msg.edit_text("🔄 Синхронизация с GitHub не удалась, создаем резервную копию...")
                
                try:
                    from backup_data import backup_data_now
                    backup_path = backup_data_now()
                    
                    if backup_path:
                        await progress_msg.edit_text(
                            "✅ **Резервная копия создана**\n\n"
                            f"📁 Путь к бэкапу: {backup_path}\n"
                            "💾 Данные сохранены локально\n\n"
                            "💡 GitHub синхронизация недоступна, но данные защищены"
                        )
                    else:
                        await progress_msg.edit_text(
                            "❌ **Ошибка сохранения данных**\n\n"
                            "Не удалось создать резервную копию\n"
                            "Обратитесь к администратору"
                        )
                except ImportError:
                    await progress_msg.edit_text(
                        "❌ **Ошибка синхронизации**\n\n"
                        "Не удалось сохранить данные в GitHub\n"
                        "Резервное копирование недоступно\n"
                        "Попробуйте позже"
                    )
                
        except ImportError:
            await progress_msg.edit_text(
                "⚠️ **Синхронизация недоступна**\n\n"
                "Модуль синхронизации не найден\n"
                "Обратитесь к администратору"
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
        
        # Импортируем и получаем реальный статус
        try:
            from simple_data_sync import get_sync_status
            
            status = get_sync_status()
            
            # Формируем ответ
            status_text = "📊 **Статус синхронизации данных**\n\n"
            status_text += f"📁 **Директория данных:** {status['data_dir']}\n"
            status_text += f"🔄 **Статус git:** {status['git_status']}\n"
            
            if status["has_changes"]:
                status_text += "⚠️ **Есть несохраненные изменения**\n"
                status_text += "Используйте /sync для ручной синхронизации"
            else:
                status_text += "✅ **Все данные синхронизированы**\n"
                status_text += "💡 Используйте /sync для принудительной синхронизации"
            
            await update.message.reply_text(status_text)
            
        except ImportError:
            await update.message.reply_text(
                "⚠️ **Синхронизация недоступна**\n\n"
                "Модуль синхронизации не найден\n"
                "Обратитесь к администратору"
            )
        
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
        progress_msg = await update.message.reply_text("🔄 Принудительная синхронизация всех файлов...")
        
        # Импортируем и используем реальную синхронизацию
        try:
            from simple_data_sync import SimpleDataSync
            
            # Создаем экземпляр синхронизации
            sync = SimpleDataSync()
            
            # Принудительно добавляем все файлы
            await progress_msg.edit_text("📁 Добавляю все файлы данных в git...")
            sync._add_all_data_files()
            
            # Принудительно коммитим все изменения
            await progress_msg.edit_text("💾 Коммичу все изменения...")
            try:
                import subprocess
                from datetime import datetime
                
                # Добавляем все файлы
                subprocess.run(["git", "add", "."], check=True)
                
                # Коммитим
                commit_message = f"Force sync all data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(["git", "commit", "-m", commit_message], check=True)
                
                # Push
                await progress_msg.edit_text("🚀 Отправляю изменения в GitHub...")
                result = subprocess.run(["git", "push", "origin", "main"], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    await progress_msg.edit_text(
                        "✅ **Принудительная синхронизация завершена**\n\n"
                        "📊 ВСЕ файлы данных принудительно сохранены\n"
                        "🔄 Изменения отправлены в GitHub\n"
                        "📁 Включая accounts.json и другие файлы\n\n"
                        "💡 Проверьте GitHub репозиторий"
                    )
                else:
                    await progress_msg.edit_text(
                        "❌ **Ошибка отправки в GitHub**\n\n"
                        f"Ошибка: {result.stderr}\n"
                        "💡 Попробуйте /init_git для настройки"
                    )
                    
            except subprocess.CalledProcessError as e:
                await progress_msg.edit_text(
                    "❌ **Ошибка принудительной синхронизации**\n\n"
                    f"Ошибка: {e}\n"
                    "💡 Попробуйте /init_git для настройки"
                )
                
        except ImportError:
            await progress_msg.edit_text(
                "⚠️ **Синхронизация недоступна**\n\n"
                "Модуль синхронизации не найден\n"
                "Обратитесь к администратору"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде принудительной синхронизации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при принудительной синхронизации"
        )

async def init_git_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для инициализации git репозитория"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил инициализацию git")
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🔧 Инициализация git репозитория...")
        
        try:
            from init_git_repo import init_git_repository, test_git_connection
            
            # Инициализируем git репозиторий
            if init_git_repository():
                await progress_msg.edit_text("🧪 Тестирую подключение к GitHub...")
                
                # Тестируем подключение
                if test_git_connection():
                    await progress_msg.edit_text(
                        "✅ **Git репозиторий инициализирован**\n\n"
                        "🔗 Подключение к GitHub работает\n"
                        "📁 Папка data готова для синхронизации\n\n"
                        "💡 Теперь используйте /sync для синхронизации данных"
                    )
                else:
                    await progress_msg.edit_text(
                        "⚠️ **Git репозиторий создан, но GitHub недоступен**\n\n"
                        "📁 Локальный git репозиторий настроен\n"
                        "❌ Подключение к GitHub не работает\n\n"
                        "💡 Возможно, нужны права доступа или токен"
                    )
            else:
                await progress_msg.edit_text(
                    "❌ **Ошибка инициализации git**\n\n"
                    "Не удалось создать git репозиторий\n"
                    "Обратитесь к администратору"
                )
                
        except ImportError:
            await progress_msg.edit_text(
                "⚠️ **Модуль инициализации недоступен**\n\n"
                "Модуль init_git_repo не найден\n"
                "Обратитесь к администратору"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде инициализации git: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при инициализации git"
        )

async def check_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки файлов данных"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил проверку данных")
        
        from pathlib import Path
        import json
        
        data_dir = Path("data")
        if not data_dir.exists():
            await update.message.reply_text(
                "❌ **Папка data не найдена**\n\n"
                "Создайте папку data и добавьте файлы пользователей"
            )
            return
        
        # Собираем информацию о файлах
        info_text = "📊 **Информация о файлах данных**\n\n"
        
        # Проверяем папки пользователей
        user_dirs = [d for d in data_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        info_text += f"👥 **Пользователей:** {len(user_dirs)}\n"
        
        total_files = 0
        for user_dir in user_dirs:
            files = list(user_dir.glob("*"))
            total_files += len(files)
            
            # Проверяем accounts.json
            accounts_file = user_dir / "accounts.json"
            if accounts_file.exists():
                try:
                    with open(accounts_file, 'r', encoding='utf-8') as f:
                        accounts = json.load(f)
                    info_text += f"📁 **{user_dir.name}:** {len(files)} файлов, {len(accounts)} аккаунтов\n"
                except:
                    info_text += f"📁 **{user_dir.name}:** {len(files)} файлов, accounts.json поврежден\n"
            else:
                info_text += f"📁 **{user_dir.name}:** {len(files)} файлов, нет accounts.json\n"
        
        info_text += f"\n📈 **Всего файлов:** {total_files}\n"
        
        # Проверяем git статус
        try:
            import subprocess
            result = subprocess.run(["git", "status", "--porcelain"], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                info_text += f"\n🔄 **Git статус:** Есть изменения\n"
                info_text += f"📋 **Файлы с изменениями:**\n"
                for line in result.stdout.strip().split('\n')[:5]:  # Показываем первые 5
                    info_text += f"   {line}\n"
                if len(result.stdout.strip().split('\n')) > 5:
                    info_text += f"   ... и еще {len(result.stdout.strip().split('\n')) - 5} файлов\n"
            else:
                info_text += f"\n✅ **Git статус:** Нет изменений\n"
        except:
            info_text += f"\n⚠️ **Git статус:** Не удалось проверить\n"
        
        await update.message.reply_text(info_text)
        
    except Exception as e:
        logger.error(f"Ошибка в команде проверки данных: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при проверке данных"
        )

async def upload_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для загрузки всех изменений в GitHub"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил загрузку всех изменений")
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🚀 Загружаю все изменения в GitHub...")
        
        try:
            import subprocess
            from datetime import datetime
            
            # Проверяем git статус
            await progress_msg.edit_text("🔍 Проверяю изменения...")
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                        capture_output=True, text=True)
            
            if not status_result.stdout.strip():
                await progress_msg.edit_text(
                    "✅ **Нет изменений для загрузки**\n\n"
                    "Все файлы уже синхронизированы с GitHub"
                )
                return
            
            # Показываем найденные изменения
            changes_count = len(status_result.stdout.strip().split('\n'))
            await progress_msg.edit_text(f"📋 Найдено {changes_count} изменений...")
            
            # Добавляем все файлы
            await progress_msg.edit_text("📁 Добавляю все файлы...")
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Создаем коммит
            await progress_msg.edit_text("💾 Создаю коммит...")
            commit_message = f"Auto-upload all changes: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push в GitHub
            await progress_msg.edit_text("🚀 Отправляю в GitHub...")
            push_result = subprocess.run(['git', 'push', 'origin', 'main'], 
                                       capture_output=True, text=True, timeout=60)
            
            if push_result.returncode == 0:
                await progress_msg.edit_text(
                    "✅ **ВСЕ ИЗМЕНЕНИЯ ЗАГРУЖЕНЫ В GITHUB!**\n\n"
                    f"📊 **Загружено файлов:** {changes_count}\n"
                    f"💾 **Коммит:** {commit_message}\n"
                    f"🔗 **Репозиторий:** https://github.com/stepanyanprod-creator/finance-bot\n\n"
                    "💡 Все ваши данные теперь в GitHub!"
                )
            else:
                await progress_msg.edit_text(
                    "❌ **Ошибка загрузки в GitHub**\n\n"
                    f"Ошибка: {push_result.stderr}\n\n"
                    "💡 Попробуйте /init_git для настройки"
                )
                
        except subprocess.CalledProcessError as e:
            await progress_msg.edit_text(
                "❌ **Ошибка git операции**\n\n"
                f"Ошибка: {e}\n\n"
                "💡 Попробуйте /init_git для настройки"
            )
        except Exception as e:
            await progress_msg.edit_text(
                "❌ **Общая ошибка**\n\n"
                f"Ошибка: {e}\n\n"
                "💡 Обратитесь к администратору"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде загрузки: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при загрузке в GitHub"
        )

async def setup_render_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для настройки аутентификации на Render"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил настройку аутентификации на Render")
        
        await update.message.reply_text(
            "🔧 **НАСТРОЙКА АУТЕНТИФИКАЦИИ НА RENDER**\n\n"
            "📋 **Инструкция:**\n"
            "1. Откройте Render Dashboard: https://dashboard.render.com\n"
            "2. Выберите ваш сервис 'finance-bot'\n"
            "3. Перейдите в раздел 'Environment'\n"
            "4. Добавьте переменную окружения:\n"
            "   • **Key:** `GITHUB_TOKEN`\n"
            "   • **Value:** `YOUR_GITHUB_TOKEN` (замените на ваш токен)\n"
            "5. Нажмите 'Save Changes'\n"
            "6. Дождитесь перезапуска сервиса\n\n"
            "💡 **После настройки:**\n"
            "• Используйте /setup_auth для проверки\n"
            "• Используйте /force_sync для синхронизации\n\n"
            "🔗 **Альтернатива:** Настройте токен в Render Dashboard"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде настройки Render аутентификации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе инструкции"
        )

async def setup_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для настройки аутентификации GitHub"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил настройку аутентификации")
        
        # Показываем прогресс
        progress_msg = await update.message.reply_text("🔐 Настраиваю аутентификацию GitHub...")
        
        try:
            import subprocess
            import os
            
            # Проверяем токен
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                await progress_msg.edit_text("🔑 Найден GITHUB_TOKEN, настраиваю аутентификацию...")
                
                # Настраиваем URL с токеном
                repo_url = f"https://{github_token}@github.com/stepanyanprod-creator/finance-bot.git"
                subprocess.run(['git', 'remote', 'set-url', 'origin', repo_url], check=True)
                
                # Тестируем подключение
                await progress_msg.edit_text("🧪 Тестирую подключение...")
                result = subprocess.run(['git', 'fetch', 'origin'], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    await progress_msg.edit_text(
                        "✅ **АУТЕНТИФИКАЦИЯ НАСТРОЕНА!**\n\n"
                        "🔑 Используется GITHUB_TOKEN\n"
                        "🔗 Подключение к GitHub работает\n\n"
                        "💡 Теперь используйте /sync для синхронизации"
                    )
                else:
                    await progress_msg.edit_text(
                        "❌ **Ошибка аутентификации**\n\n"
                        f"Ошибка: {result.stderr}\n\n"
                        "💡 Проверьте GITHUB_TOKEN в Render"
                    )
            else:
                await progress_msg.edit_text("🔄 Токен не найден, пробую простую настройку...")
                
                # Простая настройка без токена
                repo_url = "https://github.com/stepanyanprod-creator/finance-bot.git"
                subprocess.run(['git', 'remote', 'set-url', 'origin', repo_url], check=True)
                
                # Тестируем подключение
                await progress_msg.edit_text("🧪 Тестирую подключение...")
                result = subprocess.run(['git', 'fetch', 'origin'], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    await progress_msg.edit_text(
                        "✅ **ПРОСТАЯ АУТЕНТИФИКАЦИЯ РАБОТАЕТ!**\n\n"
                        "🔗 Подключение к GitHub работает\n"
                        "📁 Репозиторий доступен публично\n\n"
                        "💡 Теперь используйте /sync для синхронизации"
                    )
                else:
                    await progress_msg.edit_text(
                        "❌ **АУТЕНТИФИКАЦИЯ НЕ РАБОТАЕТ**\n\n"
                        f"Ошибка: {result.stderr}\n\n"
                        "💡 Решения:\n"
                        "1. Установите GITHUB_TOKEN в Render\n"
                        "2. Проверьте права доступа к репозиторию\n"
                        "3. Убедитесь, что репозиторий публичный"
                    )
                
        except subprocess.CalledProcessError as e:
            await progress_msg.edit_text(
                "❌ **Ошибка настройки аутентификации**\n\n"
                f"Ошибка: {e}\n\n"
                "💡 Обратитесь к администратору"
            )
        except Exception as e:
            await progress_msg.edit_text(
                "❌ **Общая ошибка**\n\n"
                f"Ошибка: {e}\n\n"
                "💡 Обратитесь к администратору"
            )
            
    except Exception as e:
        logger.error(f"Ошибка в команде настройки аутентификации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при настройке аутентификации"
        )

async def set_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для установки GitHub токена"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил установку токена")
        
        # Показываем инструкцию
        await update.message.reply_text(
            "🔑 **НАСТРОЙКА GITHUB TOKEN**\n\n"
            "📋 **Инструкция:**\n"
            "1. Перейдите: https://github.com/settings/tokens\n"
            "2. Нажмите 'Generate new token (classic)'\n"
            "3. Выберите 'repo' scope\n"
            "4. Скопируйте токен\n\n"
            "💡 **После получения токена:**\n"
            "• Используйте /setup_auth для автоматической настройки\n"
            "• Или настройте вручную через терминал\n\n"
            "🔗 **Альтернатива:** Загрузите .gitignore вручную через веб-интерфейс GitHub"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в команде установки токена: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при показе инструкции"
        )
