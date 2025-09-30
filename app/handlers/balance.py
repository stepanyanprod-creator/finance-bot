# app/handlers/balance.py
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import (
    BAL_MENU, ADD_ACC_NAME, ADD_ACC_CURRENCY, EDIT_PICK_ACC, EDIT_NEW_AMOUNT,
    EDIT_ACC_MENU, EDIT_ACC_CURRENCY, DELETE_ACC_CONFIRM
)
from app.keyboards import (
    balance_menu_kb, reply_menu_keyboard, accounts_kb, account_edit_menu_kb,
    currency_selection_kb, delete_confirmation_kb
)
from app.storage import (
    list_accounts, add_account, set_account_amount, format_accounts,
    delete_account, update_account_currency
)

from app.utils import get_user_id as _uid

# ──────────────────────────────────────────────────────────────────────────────
# Состояния «Баланс»

async def balance_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """💼 <b>Управление балансом</b>

Здесь вы можете:
• 📊 Просматривать все счета
• ➕ Добавлять новые счета  
• ✏️ Редактировать существующие
• 🗑️ Удалять ненужные счета
• 💱 Переводить между счетами

Выберите действие:"""
    
    await update.effective_message.reply_text(
        welcome_text, 
        reply_markup=balance_menu_kb(),
        parse_mode='HTML'
    )
    return BAL_MENU

async def bal_show_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        format_accounts(_uid(update)),
        reply_markup=balance_menu_kb(),
        parse_mode='HTML'
    )
    return BAL_MENU

async def bal_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_acc"] = {}
    await update.effective_message.reply_text(
        "➕ <b>Добавление нового счета</b>\n\n"
        "Введите название счёта:\n"
        "💡 Например: Monobank, Приват24, Наличные",
        parse_mode='HTML'
    )
    return ADD_ACC_NAME

async def bal_add_got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text(
            "❌ Пустое название.\n\nВведите название счёта:",
            parse_mode='HTML'
        )
        return ADD_ACC_NAME
    context.user_data["new_acc"]["name"] = name
    await update.effective_message.reply_text(
        f"✅ Название: <b>{name}</b>\n\n"
        "💱 Введите валюту счёта:\n"
        "💡 Например: UAH, EUR, USD, RUB",
        parse_mode='HTML'
    )
    return ADD_ACC_CURRENCY

async def bal_add_got_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = (update.effective_message.text or "").strip().upper()
    if not cur:
        await update.effective_message.reply_text(
            "❌ Пустая валюта.\n\nВведите валюту счёта:",
            parse_mode='HTML'
        )
        return ADD_ACC_CURRENCY
    name = context.user_data["new_acc"]["name"]
    try:
        add_account(_uid(update), name, cur, 0.0)
        await update.effective_message.reply_text(
            f"🎉 <b>Счёт успешно создан!</b>\n\n"
            f"📝 Название: <b>{name}</b>\n"
            f"💱 Валюта: <b>{cur}</b>\n"
            f"💰 Баланс: <b>0.00 {cur}</b>\n\n"
            f"💡 Теперь вы можете пополнить счёт или начать отслеживать расходы.",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ <b>Ошибка при создании счёта:</b>\n{e}",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
    return BAL_MENU

async def bal_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc = list_accounts(_uid(update))
    if not acc:
        await update.effective_message.reply_text(
            "📊 <b>Счетов пока нет</b>\n\n"
            "💡 Сначала добавьте счёт, чтобы начать работу с балансом.",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
        return BAL_MENU
    # меню выбора счёта
    await update.effective_message.reply_text(
        "✏️ <b>Редактирование счета</b>\n\n"
        "Выберите счёт для редактирования:",
        reply_markup=accounts_kb(list(acc.keys()), include_back=True),
        parse_mode='HTML'
    )
    return EDIT_PICK_ACC

async def bal_edit_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.effective_message.text or "").strip()
    if name == "Назад" or name == "⬅️ Назад":
        await update.effective_message.reply_text(
            "💼 <b>Управление балансом</b>\n\nВыберите действие:",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
        return BAL_MENU

    acc = list_accounts(_uid(update))
    if name not in acc:
        await update.effective_message.reply_text(
            "Такого счёта нет. Выберите из списка:",
            reply_markup=accounts_kb(list(acc.keys()), include_back=True)
        )
        return EDIT_PICK_ACC

    context.user_data["edit_acc_name"] = name
    acc_info = acc[name]
    await update.effective_message.reply_text(
        f"Редактирование счёта «{name}»:\n"
        f"Текущая сумма: {acc_info['amount']:.2f} {acc_info['currency']}\n\n"
        f"Что хотите изменить?",
        reply_markup=account_edit_menu_kb()
    )
    return EDIT_ACC_MENU

async def bal_edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню редактирования счета"""
    text = (update.effective_message.text or "").strip()
    name = context.user_data.get("edit_acc_name")
    
    if text == "⬅️ Назад":
        acc = list_accounts(_uid(update))
        await update.effective_message.reply_text(
            "Выберите счёт для редактирования:",
            reply_markup=accounts_kb(list(acc.keys()), include_back=True)
        )
        return EDIT_PICK_ACC
    elif text == "💰 Сумма":
        await update.effective_message.reply_text(
            f"Введите новую сумму для «{name}» (число):"
        )
        return EDIT_NEW_AMOUNT
    elif text == "💱 Валюта":
        await update.effective_message.reply_text(
            f"Выберите новую валюту для «{name}»:",
            reply_markup=currency_selection_kb()
        )
        return EDIT_ACC_CURRENCY
    else:
        await update.effective_message.reply_text(
            "Выберите действие из меню:",
            reply_markup=account_edit_menu_kb()
        )
        return EDIT_ACC_MENU

async def bal_edit_new_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(str((update.effective_message.text or "").strip()).replace(",", "."))
        name = context.user_data.get("edit_acc_name")
        _, acc = set_account_amount(_uid(update), name, amount)
        await update.effective_message.reply_text(
            f"✅ <b>Баланс обновлен!</b>\n\n"
            f"📝 Счёт: <b>{name}</b>\n"
            f"💰 Новый баланс: <b>{acc['amount']:,.2f} {acc['currency']}</b>",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ <b>Ошибка:</b> {e}\n\n"
            f"💡 Введите корректное число ещё раз.",
            parse_mode='HTML'
        )
        return EDIT_NEW_AMOUNT
    return BAL_MENU

async def bal_edit_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изменения валюты счета"""
    text = (update.effective_message.text or "").strip()
    name = context.user_data.get("edit_acc_name")
    
    if text == "⬅️ Назад":
        await update.effective_message.reply_text(
            f"Редактирование счёта «{name}»:\nЧто хотите изменить?",
            reply_markup=account_edit_menu_kb()
        )
        return EDIT_ACC_MENU
    
    # Проверяем, что выбрана валидная валюта
    valid_currencies = ["UAH", "USD", "EUR", "RUB", "PLN", "GBP"]
    if text.upper() not in valid_currencies:
        await update.effective_message.reply_text(
            "Выберите валюту из предложенных:",
            reply_markup=currency_selection_kb()
        )
        return EDIT_ACC_CURRENCY
    
    try:
        _, acc = update_account_currency(_uid(update), name, text.upper())
        await update.effective_message.reply_text(
            f"✅ <b>Валюта обновлена!</b>\n\n"
            f"📝 Счёт: <b>{name}</b>\n"
            f"💱 Новая валюта: <b>{acc['currency']}</b>\n"
            f"💰 Баланс: <b>{acc['amount']:,.2f} {acc['currency']}</b>",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ <b>Ошибка:</b> {e}",
            parse_mode='HTML'
        )
        return EDIT_ACC_CURRENCY
    return BAL_MENU

async def bal_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса удаления счета"""
    acc = list_accounts(_uid(update))
    if not acc:
        await update.effective_message.reply_text(
            "📊 <b>Счетов пока нет</b>\n\n"
            "💡 Сначала добавьте счёт, чтобы начать работу с балансом.",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
        return BAL_MENU
    
    await update.effective_message.reply_text(
        "🗑️ <b>Удаление счета</b>\n\n"
        "⚠️ <b>Внимание:</b> Это действие нельзя отменить!\n\n"
        "Выберите счёт для удаления:",
        reply_markup=accounts_kb(list(acc.keys()), include_back=True),
        parse_mode='HTML'
    )
    return DELETE_ACC_CONFIRM

async def bal_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления счета"""
    text = (update.effective_message.text or "").strip()
    
    if text == "Назад" or text == "⬅️ Назад":
        await update.effective_message.reply_text(
            "💼 <b>Управление балансом</b>\n\nВыберите действие:",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
        return BAL_MENU
    
    # Проверяем, это кнопки подтверждения или выбор счета
    if text in ["✅ Да, удалить", "❌ Отмена"]:
        return await bal_delete_execute(update, context)
    
    acc = list_accounts(_uid(update))
    if text not in acc:
        await update.effective_message.reply_text(
            "Такого счёта нет. Выберите из списка:",
            reply_markup=accounts_kb(list(acc.keys()), include_back=True)
        )
        return DELETE_ACC_CONFIRM
    
    context.user_data["delete_acc_name"] = text
    acc_info = acc[text]
    await update.effective_message.reply_text(
        f"⚠️ Вы уверены, что хотите удалить счёт «{text}»?\n"
        f"Текущий баланс: {acc_info['amount']:.2f} {acc_info['currency']}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=delete_confirmation_kb()
    )
    return DELETE_ACC_CONFIRM

async def bal_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления счета"""
    text = (update.effective_message.text or "").strip()
    name = context.user_data.get("delete_acc_name")
    
    if text == "✅ Да, удалить":
        try:
            delete_account(_uid(update), name)
            await update.effective_message.reply_text(
                f"🗑️ <b>Счёт удален!</b>\n\n"
                f"📝 Удаленный счёт: <b>{name}</b>\n\n"
                f"💡 Все данные по этому счёту были удалены безвозвратно.",
                reply_markup=balance_menu_kb(),
                parse_mode='HTML'
            )
        except Exception as e:
            await update.effective_message.reply_text(
                f"❌ <b>Ошибка:</b> {e}",
                reply_markup=balance_menu_kb(),
                parse_mode='HTML'
            )
    elif text == "❌ Отмена" or text == "⬅️ Назад":
        await update.effective_message.reply_text(
            "✅ <b>Удаление отменено</b>\n\n"
            "💡 Счёт остался без изменений.",
            reply_markup=balance_menu_kb(),
            parse_mode='HTML'
        )
    else:
        await update.effective_message.reply_text(
            "Выберите действие:",
            reply_markup=delete_confirmation_kb()
        )
        return DELETE_ACC_CONFIRM
    
    return BAL_MENU

async def bal_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Главное меню:", reply_markup=reply_menu_keyboard())
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────────
# Фабрика ConversationHandler для main.py

def build_balance_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^💼 Баланс$"), balance_menu_entry),
        ],
        states={
            BAL_MENU: [
                MessageHandler(filters.Regex("^💼 Все счета$"), bal_show_all),
                MessageHandler(filters.Regex("^➕ Добавить счёт$"), bal_add_start),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), bal_edit_start),
                MessageHandler(filters.Regex("^🗑️ Удалить счёт$"), bal_delete_start),
                MessageHandler(filters.Regex("^⬅️ Назад$"), bal_back),
            ],
            ADD_ACC_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_add_got_name),
            ],
            ADD_ACC_CURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_add_got_currency),
            ],
            EDIT_PICK_ACC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_edit_pick),
            ],
            EDIT_ACC_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_edit_menu_handler),
            ],
            EDIT_NEW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_edit_new_amount),
            ],
            EDIT_ACC_CURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_edit_currency),
            ],
            DELETE_ACC_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bal_delete_confirm),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Назад$"), bal_back)],
        allow_reentry=True,
    )
