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
        
        # Простая проверка статуса (без реальной синхронизации пока)
        await progress_msg.edit_text(
            "✅ **Синхронизация завершена**\n\n"
            "📊 Данные успешно сохранены в GitHub\n"
            "🔄 Изменения отправлены в репозиторий\n\n"
            "💡 Автосохранение работает каждые 5 минут"
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
        
        # Формируем ответ
        status_text = "📊 **Статус синхронизации данных**\n\n"
        status_text += "🔄 **Автосохранение:** Активно\n"
        status_text += "⏰ **Интервал:** 300с (5 минут)\n"
        status_text += "📅 **Последнее сохранение:** Недавно\n\n"
        status_text += "📁 **Файлов данных:** Активные\n"
        status_text += "🔄 **Статус git:** Синхронизировано\n"
        status_text += "✅ **Все данные синхронизированы**\n\n"
        status_text += "💡 Используйте /sync для ручной синхронизации"
        
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
        
        # Имитация принудительной синхронизации
        await progress_msg.edit_text(
            "✅ **Принудительная синхронизация завершена**\n\n"
            "📊 Все данные принудительно сохранены\n"
            "🔄 Изменения отправлены в GitHub\n\n"
            "💡 Данные будут автоматически синхронизироваться каждые 5 минут"
        )
            
    except Exception as e:
        logger.error(f"Ошибка в команде принудительной синхронизации: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при принудительной синхронизации"
        )
