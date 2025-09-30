# app/handlers/enhanced_photo.py
import tempfile
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from app.utils import get_user_id
from app.logger import get_logger
from app.exceptions import ReceiptParsingError, ValidationError
from app.services.enhanced_receipt_parser import EnhancedReceiptParser
from app.services.smart_categorization import SmartCategorizationService
from app.services.receipt_validator import ReceiptValidator
from app.storage import list_accounts
from app.keyboards import accounts_kb, categories_kb
from app.constants import CHOOSE_ACC_FOR_RECEIPT, CHOOSE_CATEGORY_FOR_RECEIPT

logger = get_logger(__name__)


async def enhanced_on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик фото чеков"""
    msg = update.effective_message
    user_id = get_user_id(update)
    
    if not msg.photo:
        await msg.reply_text("❌ Не удалось получить фото.", parse_mode='HTML')
        return
    
    # Получаем фото наилучшего качества
    photo = msg.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)
    
    # Скачиваем во временный файл
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await tg_file.download_to_drive(tmp.name)
        local_path = tmp.name
    
    try:
        await msg.reply_text("🔍 Анализирую чек...", parse_mode='HTML')
        
        # Инициализируем сервисы
        parser = EnhancedReceiptParser()
        validator = ReceiptValidator()
        categorizer = SmartCategorizationService(user_id)
        
        # Парсим чек
        parsing_result = parser.parse_receipt(local_path, user_id)
        
        if not parsing_result.success:
            await msg.reply_text(
                f"❌ Ошибка при анализе чека:\n" + 
                "\n".join(f"• {error}" for error in parsing_result.errors)
            )
            return
        
        receipt_data = parsing_result.data
        
        # Валидируем данные
        validation_result = validator.validate_receipt(receipt_data)
        
        # Показываем результаты валидации
        if validation_result.warnings:
            warning_text = "⚠️ Предупреждения:\n" + "\n".join(f"• {w}" for w in validation_result.warnings[:3])
            await msg.reply_text(warning_text)
        
        if validation_result.errors:
            error_text = "❌ Ошибки в данных:\n" + "\n".join(f"• {e}" for e in validation_result.errors[:3])
            await msg.reply_text(error_text)
            
            # Предлагаем исправления
            suggestions = validator.suggest_corrections(receipt_data)
            if suggestions:
                suggestion_text = "💡 Предложения по исправлению:\n"
                for field, value in suggestions.items():
                    suggestion_text += f"• {field}: {value}\n"
                await msg.reply_text(suggestion_text)
            
            return
        
        # Категоризация
        category_suggestion = categorizer.categorize_receipt(receipt_data)
        if category_suggestion.category:
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category(category_suggestion.category)
            if validated_cat:
                receipt_data.category = validated_cat
        
        # Показываем результат анализа
        confidence_emoji = "🟢" if validation_result.confidence_score > 0.8 else "🟡" if validation_result.confidence_score > 0.5 else "🔴"
        
        analysis_text = (
            f"{confidence_emoji} <b>Анализ чека завершен</b>\n\n"
            f"📅 <b>Дата:</b> {receipt_data.date}\n"
            f"🏪 <b>Источник:</b> {receipt_data.merchant}\n"
            f"💰 <b>Сумма:</b> {receipt_data.total:.2f} {receipt_data.currency}\n"
            f"📂 <b>Категория:</b> {receipt_data.category}\n"
            f"🎯 <b>Уверенность:</b> {validation_result.confidence_score:.0%}\n"
            f"📦 <b>Товаров:</b> {len(receipt_data.items)}"
        )
        
        if receipt_data.items:
            analysis_text += "\n\n🛒 <b>Товары:</b>\n"
            for i, item in enumerate(receipt_data.items[:5]):  # Показываем первые 5 товаров
                analysis_text += f"• {item.name} - {item.qty}×{item.price:.2f}\n"
            
            if len(receipt_data.items) > 5:
                analysis_text += f"... и еще {len(receipt_data.items) - 5} товаров"
        
        await msg.reply_text(analysis_text, parse_mode='HTML')
        
        # Сохраняем данные для выбора счета
        context.user_data["pending_receipt"] = {
            "data": receipt_data,
            "photo_id": photo.file_id,
            "parsing_result": parsing_result,
            "validation_result": validation_result,
            "category_suggestion": category_suggestion
        }
        
        # Если категория не определена, сначала предлагаем выбрать категорию
        if not receipt_data.category:
            await msg.reply_text(
                "📂 <b>Выберите категорию для транзакции:</b>",
                reply_markup=categories_kb(include_cancel=True),
                parse_mode='HTML'
            )
            return CHOOSE_CATEGORY_FOR_RECEIPT
        
        # Проверяем наличие счетов
        accounts = list_accounts(user_id)
        if not accounts:
            from app.keyboards import reply_menu_keyboard
            await msg.reply_text(
                "💼 <b>Нужен счет для оплаты</b>\n\n"
                "У вас пока нет счетов. Добавьте их в меню «💼 Баланс» → «Добавить счёт».",
                reply_markup=reply_menu_keyboard(),
                parse_mode='HTML'
            )
            return -1
        
        # Определяем, доход это или расход
        total = float(receipt_data.total or 0)
        if total > 0:
            account_message = "💳 <b>Выберите счет для зачисления:</b>"
        else:
            account_message = "💳 <b>Выберите счет для списания:</b>"
        
        # Показываем выбор счета
        await msg.reply_text(
            account_message,
            reply_markup=accounts_kb(list(accounts.keys()), include_cancel=True),
            parse_mode='HTML'
        )
        return CHOOSE_ACC_FOR_RECEIPT
        
    except ReceiptParsingError as e:
        logger.error(f"Receipt parsing error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при анализе чека: {e}", parse_mode='HTML')
        
    except ValidationError as e:
        logger.error(f"Validation error for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка валидации данных: {e}", parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Unexpected error in photo processing for user {user_id}: {e}")
        await msg.reply_text("❌ Произошла неожиданная ошибка при обработке фото.", parse_mode='HTML')
        
    finally:
        # Удаляем временный файл
        try:
            import os
            os.unlink(local_path)
        except:
            pass


async def enhanced_receipt_choose_account_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик выбора счета"""
    msg = update.effective_message
    user_id = get_user_id(update)
    choice = (msg.text or "").strip()
    
    if choice in {"Отмена", "❌ Отмена"}:
        context.user_data.pop("pending_receipt", None)
        context.user_data.pop("pending_income", None)
        from app.keyboards import reply_menu_keyboard
        await msg.reply_text(
            "❌ Отменено.",
            reply_markup=reply_menu_keyboard()
        )
        return -1
    
    if choice == "💼 Баланс":
        from app.handlers.balance import balance_menu_entry
        context.user_data.pop("pending_receipt", None)
        return await balance_menu_entry(update, context)
    
    # Получаем данные чека или дохода
    pending_data = context.user_data.get("pending_receipt")
    pending_income = context.user_data.get("pending_income")
    
    if not pending_data and not pending_income:
        await msg.reply_text("❌ Данные транзакции не найдены.", parse_mode='HTML')
        return -1
    
    accounts = list_accounts(user_id)
    
    if choice not in accounts:
        await msg.reply_text(
            "❌ Выберите счет из списка:",
            reply_markup=accounts_kb(list(accounts.keys()), include_cancel=True)
        )
        return CHOOSE_ACC_FOR_RECEIPT
    
    try:
        # Обрабатываем доход
        if pending_income:
            from app.storage import append_row_csv, inc_account
            from app.handlers.income import inc_balance_for_income
            
            income_data = pending_income.copy()
            income_data["payment_method"] = choice
            
            # Сохраняем доход
            append_row_csv(user_id, income_data, source="manual_income")
            
            # Увеличиваем баланс и счёт (доход)
            inc_balance_for_income(user_id, income_data["total"], income_data["currency"], income_data.get("category"))
            inc_account(user_id, choice, income_data["total"])
            
            success_text = (
                f"✅ <b>Доход сохранён!</b>\n\n"
                f"📅 {income_data['date']}\n"
                f"📍 {income_data['merchant']}\n"
                f"💰 Доход: {income_data['total']:.2f} {income_data['currency']}\n"
                f"📂 {income_data['category']}\n"
                f"💳 Счет: {choice}"
            )
            
            await msg.reply_text(success_text, parse_mode='HTML')
            context.user_data.pop("pending_income", None)
            
            from app.keyboards import reply_menu_keyboard
            await msg.reply_text(
                "✅ Доход успешно добавлен!",
                reply_markup=reply_menu_keyboard(),
                parse_mode='HTML'
            )
            return -1
        
        # Обрабатываем чек (расход)
        elif pending_data:
            from app.storage import append_row_csv, dec_balance, dec_account
            
            receipt_data = pending_data["data"]
            
            # Проверяем тип данных - объект или словарь
            if hasattr(receipt_data, 'payment_method'):
                # Это объект (из enhanced photo) - не изменяем объект напрямую
                pass
            else:
                # Это словарь (из voice)
                receipt_data["payment_method"] = choice
            
            # Конвертируем в старый формат для совместимости
            if hasattr(receipt_data, 'payment_method'):
                # Это объект (из enhanced photo)
                
                # Формируем список товаров для заметок
                items_list = []
                if receipt_data.items:
                    for item in receipt_data.items:
                        if item.name.strip():  # Только товары с названием
                            items_list.append(f"{item.name} ({item.qty}x{item.price:.2f})")
                
                items_text = "; ".join(items_list) if items_list else ""
                notes_text = f"Фото чека: {receipt_data.merchant}"
                if items_text:
                    notes_text += f" | Товары: {items_text}"
                
                transaction_data = {
                    "date": receipt_data.date,
                    "merchant": receipt_data.merchant,
                    "total": receipt_data.total,
                    "currency": receipt_data.currency,
                    "category": receipt_data.category,
                    "payment_method": choice,  # Используем выбранный счет
                    "notes": notes_text
                }
            else:
                # Это словарь (из voice)
                transaction_data = receipt_data.copy()
            
            # Сохраняем в CSV
            source = f"enhanced_photo:{pending_data.get('photo_id', '')}" if hasattr(receipt_data, 'payment_method') else f"voice:{pending_data.get('photo_id', '')}"
            append_row_csv(user_id, transaction_data, source=source)
            
            # Обновляем балансы
            if hasattr(receipt_data, 'total'):
                # Объект
                total = receipt_data.total
                currency = receipt_data.currency
                category = receipt_data.category
            else:
                # Словарь
                total = receipt_data.get("total", 0)
                currency = receipt_data.get("currency", "")
                category = receipt_data.get("category", "")
            
            # Определяем, доход это или расход
            if total > 0:
                # Доход - увеличиваем баланс и счёт
                from app.handlers.income import inc_balance_for_income
                inc_balance_for_income(user_id, total, currency, category)
                from app.storage import inc_account
                inc_account(user_id, choice, total)
            else:
                # Расход - уменьшаем баланс и счёт
                dec_balance(user_id, total, currency, category)
                dec_account(user_id, choice, total)
            
            # Показываем результат
            if total > 0:
                amount_display = f"💰 Доход: {total:.2f} {currency}"
            else:
                amount_display = f"💸 Расход: {abs(total):.2f} {currency}"
                
            # Получаем данные для отображения
            if hasattr(receipt_data, 'date'):
                # Объект
                date_str = receipt_data.date
                merchant = receipt_data.merchant
                category = receipt_data.category
                items_count = len(receipt_data.items) if hasattr(receipt_data, 'items') else 0
            else:
                # Словарь
                date_str = receipt_data.get("date", "")
                merchant = receipt_data.get("merchant", "")
                category = receipt_data.get("category", "")
                items_count = 0
            
            success_text = (
                f"✅ <b>Транзакция сохранена!</b>\n\n"
                f"📅 {date_str}\n"
                f"🏪 {merchant}\n"
                f"{amount_display}\n"
                f"📂 {category}\n"
                f"💳 Счет: {choice}"
            )
            
            if items_count > 0:
                success_text += f"\n📦 Товаров: {items_count}"
            
            # Добавляем информацию о качестве распознавания
            validation_result = pending_data.get("validation_result")
            if validation_result:
                confidence_emoji = "🟢" if validation_result.confidence_score > 0.8 else "🟡" if validation_result.confidence_score > 0.5 else "🔴"
                success_text += f"\n{confidence_emoji} Качество: {validation_result.confidence_score:.0%}"
            
            await msg.reply_text(success_text, parse_mode='HTML')
            
            # Обучаем систему на основе результата (только для объектов)
            if hasattr(receipt_data, 'category'):
                categorizer = SmartCategorizationService(user_id)
                categorizer.learn_from_feedback(receipt_data, receipt_data.category)
            
            # Очищаем временные данные
            context.user_data.pop("pending_receipt", None)
            
            # Показываем главное меню
            from app.keyboards import reply_menu_keyboard
            await msg.reply_text(
                "✅ Транзакция успешно сохранена!",
                reply_markup=reply_menu_keyboard(),
                parse_mode='HTML'
            )
            
            return -1
        
    except Exception as e:
        logger.error(f"Error saving transaction for user {user_id}: {e}")
        await msg.reply_text(f"❌ Ошибка при сохранении: {e}", parse_mode='HTML')
        return CHOOSE_ACC_FOR_RECEIPT


async def show_receipt_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальный анализ чека"""
    pending_data = context.user_data.get("pending_receipt")
    if not pending_data:
        await update.effective_message.reply_text("❌ Нет данных для анализа.", parse_mode='HTML')
        return
    
    receipt_data = pending_data["data"]
    parsing_result = pending_data.get("parsing_result")
    validation_result = pending_data.get("validation_result")
    category_suggestion = pending_data.get("category_suggestion")
    
    analysis_text = "🔍 <b>Детальный анализ чека</b>\n\n"
    
    # Информация о парсинге
    if parsing_result:
        analysis_text += f"🤖 <b>Парсинг:</b>\n"
        analysis_text += f"• Тип чека: {parsing_result.receipt_type.value}\n"
        analysis_text += f"• Успех: {'✅' if parsing_result.success else '❌'}\n"
        if parsing_result.errors:
            analysis_text += f"• Ошибки: {', '.join(parsing_result.errors[:2])}\n"
        analysis_text += "\n"
    
    # Информация о валидации
    if validation_result:
        analysis_text += f"✅ <b>Валидация:</b>\n"
        analysis_text += f"• Корректность: {validation_result.confidence_score:.0%}\n"
        if validation_result.warnings:
            analysis_text += f"• Предупреждения: {len(validation_result.warnings)}\n"
        if validation_result.suggestions:
            analysis_text += f"• Предложения: {len(validation_result.suggestions)}\n"
        analysis_text += "\n"
    
    # Информация о категоризации
    if category_suggestion:
        analysis_text += f"📂 <b>Категоризация:</b>\n"
        analysis_text += f"• Категория: {category_suggestion.category}\n"
        analysis_text += f"• Уверенность: {category_suggestion.confidence:.0%}\n"
        analysis_text += f"• Источник: {category_suggestion.source}\n"
        analysis_text += f"• Причина: {category_suggestion.reason}\n"
    
    await update.effective_message.reply_text(analysis_text, parse_mode='HTML')


