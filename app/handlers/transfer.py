# app/handlers/transfer.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import (
    TRANSFER_FROM_ACC, TRANSFER_TO_ACC, TRANSFER_AMOUNT, 
    TRANSFER_SECOND_AMOUNT, TRANSFER_CONFIRM
)
from app.keyboards import (
    balance_menu_kb, accounts_kb, transfer_amount_kb, transfer_confirm_kb
)
from app.storage import (
    list_accounts, transfer_between_accounts, format_accounts
)
from app.utils import get_user_id as _uid

# ──────────────────────────────────────────────────────────────────────────────
# Состояния «Обмен между счетами»

async def transfer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса обмена между счетами"""
    acc = list_accounts(_uid(update))
    if len(acc) < 2:
        await update.effective_message.reply_text(
            "❌ Для обмена между счетами необходимо минимум 2 счета. Сначала добавьте еще один счет.",
            reply_markup=balance_menu_kb()
        )
        return ConversationHandler.END
    
    context.user_data["transfer"] = {}
    await update.effective_message.reply_text(
        "💱 Обмен между счетами\n\nВыберите счет-источник (откуда переводим):",
        reply_markup=accounts_kb(list(acc.keys()), include_back=True)
    )
    return TRANSFER_FROM_ACC

async def transfer_from_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор счета-источника"""
    text = (update.effective_message.text or "").strip()
    
    if text == "Назад" or text == "⬅️ Назад":
        await update.effective_message.reply_text(
            "💼 <b>Управление балансом</b>\n\nВыберите действие:",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    acc = list_accounts(_uid(update))
    if text not in acc:
        await update.effective_message.reply_text(
            "Такого счёта нет. Выберите из списка:",
            reply_markup=accounts_kb(list(acc.keys()), include_back=True)
        )
        return TRANSFER_FROM_ACC
    
    context.user_data["transfer"]["from_account"] = text
    from_acc = acc[text]
    
    # Исключаем выбранный счет из списка получателей
    to_accounts = [name for name in acc.keys() if name != text]
    
    await update.effective_message.reply_text(
        f"✅ Счет-источник: {text} ({from_acc['amount']:.2f} {from_acc['currency']})\n\n"
        f"Выберите счет-получатель (куда переводим):",
        reply_markup=accounts_kb(to_accounts, include_back=True)
    )
    return TRANSFER_TO_ACC

async def transfer_to_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор счета-получателя"""
    text = (update.effective_message.text or "").strip()
    
    if text == "Назад" or text == "⬅️ Назад":
        acc = list_accounts(_uid(update))
        await update.effective_message.reply_text(
            "Выберите счет-источник (откуда переводим):",
            reply_markup=accounts_kb(list(acc.keys()), include_back=True)
        )
        return TRANSFER_FROM_ACC
    
    acc = list_accounts(_uid(update))
    from_account = context.user_data["transfer"]["from_account"]
    to_accounts = [name for name in acc.keys() if name != from_account]
    
    if text not in to_accounts:
        await update.effective_message.reply_text(
            "Такого счёта нет. Выберите из списка:",
            reply_markup=accounts_kb(to_accounts, include_back=True)
        )
        return TRANSFER_TO_ACC
    
    context.user_data["transfer"]["to_account"] = text
    from_acc = acc[from_account]
    to_acc = acc[text]
    
    # Проверяем валюты
    from_currency = from_acc["currency"]
    to_currency = to_acc["currency"]
    
    if from_currency == to_currency:
        # Одинаковые валюты - просим одну сумму
        await update.effective_message.reply_text(
            f"✅ Счет-получатель: {text} ({to_acc['amount']:.2f} {to_currency})\n\n"
            f"💱 Перевод: {from_account} → {text}\n"
            f"💰 Валюта: {from_currency}\n\n"
            f"Введите сумму для перевода:",
            reply_markup=transfer_amount_kb()
        )
    else:
        # Разные валюты - просим сумму для счета-источника
        await update.effective_message.reply_text(
            f"✅ Счет-получатель: {text} ({to_acc['amount']:.2f} {to_currency})\n\n"
            f"💱 Перевод: {from_account} ({from_currency}) → {text} ({to_currency})\n\n"
            f"⚠️ Валюты разные! Сначала введите сумму для списания с «{from_account}» ({from_currency}):",
            reply_markup=transfer_amount_kb()
        )
    
    return TRANSFER_AMOUNT

async def transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод суммы перевода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "Назад" or text == "⬅️ Назад":
        acc = list_accounts(_uid(update))
        from_account = context.user_data["transfer"]["from_account"]
        to_accounts = [name for name in acc.keys() if name != from_account]
        await update.effective_message.reply_text(
            "Выберите счет-получатель (куда переводим):",
            reply_markup=accounts_kb(to_accounts, include_back=True)
        )
        return TRANSFER_TO_ACC
    
    if text == "❌ Отмена":
        await update.effective_message.reply_text("Обмен отменен.", reply_markup=balance_menu_kb())
        return ConversationHandler.END
    
    try:
        amount = float(str(text).replace(",", "."))
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        
        context.user_data["transfer"]["amount"] = amount
        
        # Проверяем валюты
        acc = list_accounts(_uid(update))
        from_account = context.user_data["transfer"]["from_account"]
        to_account = context.user_data["transfer"]["to_account"]
        
        from_currency = acc[from_account]["currency"]
        to_currency = acc[to_account]["currency"]
        
        if from_currency == to_currency:
            # Одинаковые валюты - переходим к подтверждению
            return await transfer_confirm_same_currency(update, context)
        else:
            # Разные валюты - просим вторую сумму
            await update.effective_message.reply_text(
                f"✅ Сумма для списания: {amount:.2f} {from_currency}\n\n"
                f"Теперь введите сумму для зачисления на «{to_account}» ({to_currency}):",
                reply_markup=transfer_amount_kb()
            )
            return TRANSFER_SECOND_AMOUNT
            
    except ValueError as e:
        await update.effective_message.reply_text(
            f"❌ {e}\nВведите корректную сумму:",
            reply_markup=transfer_amount_kb()
        )
        return TRANSFER_AMOUNT

async def transfer_second_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод второй суммы для разных валют"""
    text = (update.effective_message.text or "").strip()
    
    if text == "Назад" or text == "⬅️ Назад":
        acc = list_accounts(_uid(update))
        from_account = context.user_data["transfer"]["from_account"]
        to_account = context.user_data["transfer"]["to_account"]
        from_currency = acc[from_account]["currency"]
        await update.effective_message.reply_text(
            f"Введите сумму для списания с «{from_account}» ({from_currency}):",
            reply_markup=transfer_amount_kb()
        )
        return TRANSFER_AMOUNT
    
    if text == "❌ Отмена":
        await update.effective_message.reply_text("Обмен отменен.", reply_markup=balance_menu_kb())
        return ConversationHandler.END
    
    try:
        second_amount = float(str(text).replace(",", "."))
        if second_amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        
        context.user_data["transfer"]["second_amount"] = second_amount
        return await transfer_confirm_different_currencies(update, context)
        
    except ValueError as e:
        await update.effective_message.reply_text(
            f"❌ {e}\nВведите корректную сумму:",
            reply_markup=transfer_amount_kb()
        )
        return TRANSFER_SECOND_AMOUNT

async def transfer_confirm_same_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение перевода для одинаковых валют"""
    transfer_data = context.user_data["transfer"]
    acc = list_accounts(_uid(update))
    
    from_account = transfer_data["from_account"]
    to_account = transfer_data["to_account"]
    amount = transfer_data["amount"]
    
    from_acc = acc[from_account]
    to_acc = acc[to_account]
    currency = from_acc["currency"]
    
    # Проверяем достаточность средств
    if float(from_acc["amount"]) < amount:
        await update.effective_message.reply_text(
            f"❌ Недостаточно средств на счете «{from_account}».\n"
            f"Доступно: {from_acc['amount']:.2f} {currency}\n"
            f"Требуется: {amount:.2f} {currency}",
            reply_markup=balance_menu_kb()
        )
        return ConversationHandler.END
    
    # Показываем подтверждение
    new_from_balance = float(from_acc["amount"]) - amount
    new_to_balance = float(to_acc["amount"]) + amount
    
    await update.effective_message.reply_text(
        f"💱 Подтверждение перевода:\n\n"
        f"📤 Списываем с «{from_account}»: {amount:.2f} {currency}\n"
        f"   Баланс после: {new_from_balance:.2f} {currency}\n\n"
        f"📥 Зачисляем на «{to_account}»: {amount:.2f} {currency}\n"
        f"   Баланс после: {new_to_balance:.2f} {currency}\n\n"
        f"Подтвердить перевод?",
        reply_markup=transfer_confirm_kb()
    )
    return TRANSFER_CONFIRM

async def transfer_confirm_different_currencies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение перевода для разных валют"""
    transfer_data = context.user_data["transfer"]
    acc = list_accounts(_uid(update))
    
    from_account = transfer_data["from_account"]
    to_account = transfer_data["to_account"]
    amount = transfer_data["amount"]
    second_amount = transfer_data["second_amount"]
    
    from_acc = acc[from_account]
    to_acc = acc[to_account]
    from_currency = from_acc["currency"]
    to_currency = to_acc["currency"]
    
    # Проверяем достаточность средств
    if float(from_acc["amount"]) < amount:
        await update.effective_message.reply_text(
            f"❌ Недостаточно средств на счете «{from_account}».\n"
            f"Доступно: {from_acc['amount']:.2f} {from_currency}\n"
            f"Требуется: {amount:.2f} {from_currency}",
            reply_markup=balance_menu_kb()
        )
        return ConversationHandler.END
    
    # Показываем подтверждение
    new_from_balance = float(from_acc["amount"]) - amount
    new_to_balance = float(to_acc["amount"]) + second_amount
    
    await update.effective_message.reply_text(
        f"💱 Подтверждение перевода:\n\n"
        f"📤 Списываем с «{from_account}»: {amount:.2f} {from_currency}\n"
        f"   Баланс после: {new_from_balance:.2f} {from_currency}\n\n"
        f"📥 Зачисляем на «{to_account}»: {second_amount:.2f} {to_currency}\n"
        f"   Баланс после: {new_to_balance:.2f} {to_currency}\n\n"
        f"Подтвердить перевод?",
        reply_markup=transfer_confirm_kb()
    )
    return TRANSFER_CONFIRM

async def transfer_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение перевода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "✅ Подтвердить":
        try:
            transfer_data = context.user_data["transfer"]
            from_account = transfer_data["from_account"]
            to_account = transfer_data["to_account"]
            amount = transfer_data["amount"]
            second_amount = transfer_data.get("second_amount")
            
            result = transfer_between_accounts(
                _uid(update), from_account, to_account, amount, second_amount
            )
            
            await update.effective_message.reply_text(
                f"✅ Перевод выполнен успешно!\n\n"
                f"📤 Списали с «{result['from_account']}»: {result['from_amount']:.2f} {result['from_currency']}\n"
                f"📥 Зачислили на «{result['to_account']}»: {result['to_amount']:.2f} {result['to_currency']}",
                reply_markup=balance_menu_kb()
            )
            
        except Exception as e:
            await update.effective_message.reply_text(
                f"❌ Ошибка при выполнении перевода: {e}",
                reply_markup=balance_menu_kb()
            )
    
    elif text == "❌ Отмена" or text == "⬅️ Назад":
        await update.effective_message.reply_text("Перевод отменен.", reply_markup=balance_menu_kb())
    
    else:
        await update.effective_message.reply_text(
            "Выберите действие:",
            reply_markup=transfer_confirm_kb()
        )
        return TRANSFER_CONFIRM
    
    return ConversationHandler.END

async def transfer_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    await update.effective_message.reply_text("Главное меню:", reply_markup=balance_menu_kb())
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────────
# Фабрика ConversationHandler для main.py

def build_transfer_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💱 Обмен между счетами$"), transfer_start),
        ],
        states={
            TRANSFER_FROM_ACC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_from_account),
            ],
            TRANSFER_TO_ACC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_to_account),
            ],
            TRANSFER_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount),
            ],
            TRANSFER_SECOND_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_second_amount),
            ],
            TRANSFER_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_execute),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Назад$"), transfer_back)],
        allow_reentry=True,
    )
