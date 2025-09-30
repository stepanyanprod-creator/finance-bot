# app/handlers/voice.py
import tempfile
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from app.constants import CHOOSE_ACC_FOR_RECEIPT, CHOOSE_CATEGORY_FOR_RECEIPT
from app.keyboards import accounts_kb, categories_kb
from app.speech import ffmpeg_convert_to_mp3, transcribe_openai, parse_spoken_purchase
from app.rules import apply_category_rules
from app.storage import (
    append_row_csv, dec_balance, dec_account, inc_account,
    list_accounts, fmt_money
)

from app.utils import get_user_id as _uid

async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    voice = msg.voice or msg.audio
    if not voice:
        return
    tg_file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".oga", delete=False) as tmp_in:
        await tg_file.download_to_drive(tmp_in.name)
        in_path = tmp_in.name

    # ffmpeg → mp3
    try:
        out_path = ffmpeg_convert_to_mp3(in_path)
    except Exception as e:
        await msg.reply_text(f"❌ Не удалось конвертировать аудио: {e}")
        return

    await msg.reply_text("🎙 Распознаю речь…")
    try:
        text = transcribe_openai(out_path)
        if not text:
            await msg.reply_text("Не расслышал. Скажи ещё раз, пожалуйста.")
            return

        data = parse_spoken_purchase(text)

        # угадать счёт по подстроке, если не назван явно
        if not data.get("payment_method"):
            accounts = list_accounts(_uid(update))
            low = text.lower()
            for name in accounts.keys():
                if name.lower() in low:
                    data["payment_method"] = name
                    break

        if not data.get("category"):
            auto = apply_category_rules(data)
            if auto:
                # Валидируем, что категория существует в стандартных категориях
                from app.categories import validate_and_normalize_category
                validated_cat = validate_and_normalize_category(auto)
                if validated_cat:
                    data["category"] = validated_cat

        # если счёт существует и категория определена — проводим сразу
        accs = list_accounts(_uid(update))
        acc_name = (data.get("payment_method") or "").strip()
        if acc_name and acc_name in accs and data.get("category"):
            try:
                # Сохраняем транскрипцию в поле notes
                data_with_notes = data.copy()
                data_with_notes['notes'] = f"Голосовая запись: {text}"
                append_row_csv(_uid(update), data_with_notes, source=f"voice:{voice.file_id}")
                
                total = float(data.get("total", 0) or 0)
                currency = data.get("currency", "")
                
                # Определяем, доход это или расход
                if total > 0:
                    # Доход - увеличиваем баланс и счёт
                    from app.handlers.income import inc_balance_for_income
                    inc_balance_for_income(_uid(update), total, currency, data.get("category"))
                    inc_account(_uid(update), acc_name, total)
                    amount_display = f"💰 Доход: {total:.2f} {currency}"
                else:
                    # Расход - уменьшаем баланс и счёт
                    dec_balance(_uid(update), amount=abs(total), currency=currency,
                                category=(data.get("category") or None))
                    dec_account(_uid(update), acc_name, abs(total))
                    amount_display = f"💸 Расход: {abs(total):.2f} {currency}"
                
                await msg.reply_text(
                    f"📝 «{text}»\n"
                    f"✅ Добавлено: {data.get('merchant','?')} — "
                    f"{amount_display} от {data.get('date','')}\n"
                    f"Категория: {data.get('category') or '—'}\n"
                    f"Счёт: {acc_name}"
                )
                return
            except Exception as e:
                await msg.reply_text(f"❌ Ошибка при сохранении: {e}")
                return

        # иначе — просим выбрать категорию или счёт
        # Добавляем заметки к данным
        data_with_notes = data.copy()
        data_with_notes['notes'] = f"Голосовая запись: {text}"
        context.user_data["pending_receipt"] = {"data": data_with_notes, "photo_id": ""}
        
        # Если категория не определена, сначала предлагаем выбрать категорию
        if not data.get("category"):
            pretty = (
                f"Распознал: «{text}»\n"
                f"Дата: {data['date']}\n"
                f"Источник: {data.get('merchant') or '—'}\n"
                f"Сумма: {fmt_money(data.get('total',0), data.get('currency'))}\n\n"
                "Выберите категорию:"
            )
            await msg.reply_text(pretty, reply_markup=categories_kb(include_cancel=True))
            return CHOOSE_CATEGORY_FOR_RECEIPT
        
        # Если категория определена, но нет счета или счет не найден
        if not accs:
            await msg.reply_text("Нужен счёт: зайди в 💼 Баланс → «Добавить счёт».",
                                 reply_markup=ReplyKeyboardMarkup([["Открыть меню Баланс"], ["Отмена"]], resize_keyboard=True))
            return CHOOSE_ACC_FOR_RECEIPT

        # Определяем, доход это или расход
        total = float(data.get('total', 0) or 0)
        if total > 0:
            account_message = "Выберите счёт:"
        else:
            account_message = "Выберите счёт для оплаты:"
        
        pretty = (
            f"Распознал: «{text}»\n"
            f"Дата: {data['date']}\n"
            f"Источник: {data.get('merchant') or '—'}\n"
            f"Сумма: {fmt_money(data.get('total',0), data.get('currency'))}\n"
            f"Категория: {data.get('category') or '—'}\n\n"
            f"{account_message}"
        )
        await msg.reply_text(pretty, reply_markup=accounts_kb(list(accs.keys()), include_cancel=True))
        return CHOOSE_ACC_FOR_RECEIPT

    except Exception as e:
        await msg.reply_text(f"❌ Ошибка распознавания: {e}")

async def voice_choose_category_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик выбора категории для голосовых сообщений и фото"""
    msg = update.effective_message
    choice = (msg.text or "").strip()

    if choice == "Отмена":
        context.user_data.pop("pending_receipt", None)
        await msg.reply_text("Отменено.", reply_markup=reply_menu_keyboard())
        return ConversationHandler.END

    pend = context.user_data.get("pending_receipt")
    if not pend:
        await msg.reply_text("Нет ожидающих данных.", reply_markup=reply_menu_keyboard())
        return ConversationHandler.END

    # Извлекаем название категории из форматированной строки
    from app.categories import get_categories_list, format_category_for_display
    categories = get_categories_list()
    selected_category = None
    
    # Ищем точное совпадение с форматированной строкой
    for category in categories:
        if format_category_for_display(category) == choice:
            selected_category = category.name
            break
    
    # Если не найдено точное совпадение, используем текст как есть
    if not selected_category:
        selected_category = choice

    # Обновляем данные с выбранной категорией
    data = pend.get("data")
    if data:
        if hasattr(data, 'category'):
            # Для enhanced photo (объект)
            data.category = selected_category
        else:
            # Для voice (словарь)
            data["category"] = selected_category

    # Теперь переходим к выбору счета
    accs = list_accounts(_uid(update))
    if not accs:
        await msg.reply_text("Нужен счёт: зайди в 💼 Баланс → «Добавить счёт».",
                             reply_markup=ReplyKeyboardMarkup([["Открыть меню Баланс"], ["Отмена"]], resize_keyboard=True))
        return CHOOSE_ACC_FOR_RECEIPT

    # Определяем, доход это или расход
    data = pend.get("data")
    total = 0
    if data:
        if hasattr(data, 'total'):
            # Для enhanced photo (объект)
            total = float(data.total or 0)
        else:
            # Для voice (словарь)
            total = float(data.get('total', 0) or 0)
    
    if total > 0:
        account_message = "Выберите счёт:"
    else:
        account_message = "Выберите счёт для оплаты:"
    
    pretty = (
        f"Категория: {selected_category}\n\n"
        f"{account_message}"
    )
    await msg.reply_text(pretty, reply_markup=accounts_kb(list(accs.keys()), include_cancel=True))
    return CHOOSE_ACC_FOR_RECEIPT
