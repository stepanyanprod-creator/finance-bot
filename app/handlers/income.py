# app/handlers/income.py
import os
import re
from datetime import datetime, date, timedelta
from collections import defaultdict
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import (
    INCOME_MENU, INCOME_EDIT_MENU, INCOME_EDIT_DATE, INCOME_EDIT_SOURCE,
    INCOME_EDIT_AMOUNT, INCOME_EDIT_AMOUNT_CURRENCY, INCOME_EDIT_CATEGORY, 
    INCOME_EDIT_PAYMENT, INCOME_EDIT_DATE_MENU,
    INCOME_ADD_AMOUNT, INCOME_ADD_CURRENCY, INCOME_ADD_SOURCE, 
    INCOME_ADD_CATEGORY, INCOME_ADD_ACCOUNT, INCOME_ADD_DATE
)
from app.keyboards import (
    reply_menu_keyboard, income_menu_kb, edit_income_menu_kb, accounts_kb, 
    date_selection_kb, calendar_kb,
    income_add_amount_kb, income_add_currency_kb, income_add_source_kb,
    income_add_category_kb, income_add_account_kb
)
from app.categories import (
    income_categories_kb, get_income_categories_list, format_category_for_display,
    get_income_category_by_name, validate_and_normalize_income_category
)
from app.storage import (
    ensure_csv, read_rows, append_row_csv, undo_last_row,
    set_balance, get_balances, fmt_money,
    update_last_row, update_row_from_end, rebalance_on_edit,
    list_accounts, add_account, set_account_amount, inc_account,
    find_accounts_by_currency, format_accounts
)
from app.rules import apply_category_rules, load_rules, save_rules
from app.utils import get_user_id as _uid

# ──────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции для пересчёта баланса счетов при доходах
def rebalance_accounts_on_income_edit(user_id: int, old_row: dict, new_row: dict):
    """Пересчёт баланса счетов при редактировании дохода"""
    def _num(x):
        try: return float(x)
        except: return 0.0
    
    accs = list_accounts(user_id)
    old_acc = (old_row.get("payment_method") or "").strip()
    new_acc = (new_row.get("payment_method") or "").strip()
    old_total = _num(old_row.get("total", 0))
    new_total = _num(new_row.get("total", 0))
    
    # Отменить предыдущее изменение (убрать старую сумму дохода)
    if old_acc and old_acc in accs:
        cur = float(accs[old_acc]["amount"])
        set_account_amount(user_id, old_acc, cur - old_total)
    
    # Применить новое изменение (добавить новую сумму дохода)
    if new_acc and new_acc in accs:
        cur = float(list_accounts(user_id)[new_acc]["amount"])
        set_account_amount(user_id, new_acc, cur + new_total)

def inc_balance_for_income(user_id: int, amount: float, currency: str, category: str = None):
    """Увеличить баланс для дохода (положительная операция)"""
    # Читаем текущие балансы
    balances = get_balances(user_id)
    
    # Увеличиваем баланс (доход = положительная операция)
    if currency not in balances:
        balances[currency] = 0.0
    balances[currency] += amount
    
    # Сохраняем обновленный баланс
    set_balance(user_id, balances)

# ──────────────────────────────────────────────────────────────────────────────
# Базовые действия и меню «Доходы»
async def income_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в меню доходов"""
    await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
    return INCOME_MENU

async def income_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню из меню доходов"""
    await update.effective_message.reply_text("Главное меню:", reply_markup=reply_menu_keyboard())
    return ConversationHandler.END

async def income_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать последний доход"""
    rows = read_rows(_uid(update))
    if not rows:
        return await update.effective_message.reply_text("Пока записей нет.")
    
    # Ищем последний доход (положительная сумма)
    income_rows = [r for r in rows if float(r.get('total', 0) or 0) > 0]
    if not income_rows:
        return await update.effective_message.reply_text("Записей о доходах пока нет.")
    
    r = income_rows[-1]
    await update.effective_message.reply_text(
        "💰 Последний доход:\n"
        f"• Дата: {r.get('date','')}\n"
        f"• Источник: {r.get('merchant','')}\n"
        f"• Сумма: {fmt_money(r.get('total',0), r.get('currency',''))}\n"
        f"• Категория: {r.get('category') or '—'}\n"
        f"• Счёт: {r.get('payment_method') or '—'}"
    )

async def income_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменить последний доход"""
    rows = read_rows(_uid(update))
    if not rows:
        return await update.effective_message.reply_text("Удалять нечего.")
    
    # Ищем последний доход (положительная сумма)
    income_rows = [r for r in rows if float(r.get('total', 0) or 0) > 0]
    if not income_rows:
        return await update.effective_message.reply_text("Записей о доходах для удаления нет.")
    
    # Находим индекс последнего дохода в общем списке
    last_income = income_rows[-1]
    last_income_index = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i] == last_income:
            last_income_index = i
            break
    
    if last_income_index is not None:
        # Удаляем запись и корректируем балансы
        removed_row = rows.pop(last_income_index)
        
        # Пересохраняем CSV
        import csv
        csv_path = f"data/{_uid(update)}/finance.csv"
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        # Корректируем баланс
        amount = float(removed_row.get('total', 0) or 0)
        currency = removed_row.get('currency', 'EUR')
        inc_balance_for_income(_uid(update), -amount, currency)  # Вычитаем доход
        
        # Корректируем счёт
        account = removed_row.get('payment_method')
        if account:
            accounts = list_accounts(_uid(update))
            if account in accounts:
                current_amount = float(accounts[account]["amount"])
                set_account_amount(_uid(update), account, current_amount - amount)
        
        await update.effective_message.reply_text("↩️ Последний доход удалён.")
    else:
        await update.effective_message.reply_text("Ошибка при удалении дохода.")

async def income_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для меню доходов"""
    text = (update.effective_message.text or "").strip()
    
    if text == "📊 Сегодня": 
        return await income_today(update, context)
    if text == "🗓 Неделя":  
        return await income_week(update, context)
    if text == "📅 Месяц":   
        return await income_month(update, context)
    if text == "💰 Последний": 
        return await income_last(update, context)
    if text == "↩️ Undo": 
        return await income_undo(update, context)
    if text == "✏️ Править последний": 
        return await edit_income_menu_entry(update, context)
    if text == "➕ Добавить доход":
        return await add_income_entry(update, context)
    if text == "⬅️ Назад": 
        return await income_back(update, context)
    
    return INCOME_MENU

# ──────────────────────────────────────────────────────────────────────────────
# Статистика доходов
async def income_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, start_date: date, end_date: date):
    """Показать статистику доходов за период"""
    rows = read_rows(_uid(update))
    selected = []
    
    for r in rows:
        try:
            d = datetime.strptime(r.get("date",""), "%Y-%m-%d").date()
            amount = float(r.get("total", 0) or 0)
            # Учитываем только доходы (положительные суммы)
            if amount > 0 and start_date <= d < end_date:
                selected.append(r)
        except Exception:
            continue

    if not selected:
        return await update.effective_message.reply_text("За выбранный период доходов не найдено.")

    base_cur = selected[0].get("currency") or "EUR"
    total_sum = sum(float(r.get("total",0) or 0) for r in selected if (r.get("currency") or "") == base_cur)

    by_cat, by_source = defaultdict(float), defaultdict(float)
    for r in selected:
        if (r.get("currency") or "") != base_cur:
            continue
        by_cat[r.get("category") or "—"] += float(r.get("total",0) or 0)
        by_source[r.get("merchant") or "—"] += float(r.get("total",0) or 0)

    top_cat = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:10]
    top_source = sorted(by_source.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [f"💰 Статистика доходов {start_date} — {end_date} (валюта: {base_cur})",
             f"• Всего доходов: {fmt_money(total_sum, base_cur)}"]
    
    if top_cat:
        lines.append("• По категориям:")
        for name, s in top_cat:
            lines.append(f"  — {name}: {fmt_money(s, base_cur)}")
    
    if top_source:
        lines.append("• Топ источников доходов:")
        for name, s in top_source:
            lines.append(f"  — {name}: {fmt_money(s, base_cur)}")
    
    await update.effective_message.reply_text("\n".join(lines))

async def income_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика доходов за сегодня"""
    d = date.today()
    return await income_stats(update, context, d, d + timedelta(days=1))

async def income_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика доходов за неделю"""
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=7)
    return await income_stats(update, context, start, end)

async def income_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика доходов за месяц"""
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
    return await income_stats(update, context, start, end)

# ──────────────────────────────────────────────────────────────────────────────
# Добавление дохода
async def add_income_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс добавления дохода (пошагово)"""
    # Инициализируем данные для нового дохода
    context.user_data["new_income"] = {
        "amount": None,
        "currency": None,
        "source": None,
        "category": None,
        "account": None
    }
    
    await update.effective_message.reply_text(
        "💰 Добавление дохода\n\n"
        "Шаг 1/6: Введите сумму дохода\n\n"
        "Например: 5000, 1500.50, 300",
        reply_markup=income_add_amount_kb()
    )
    return INCOME_ADD_AMOUNT


# ──────────────────────────────────────────────────────────────────────────────
# Редактирование последнего дохода
async def edit_income_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню редактирования последнего дохода"""
    await update.effective_message.reply_text("Что правим в последнем доходе?", reply_markup=edit_income_menu_kb())
    return INCOME_EDIT_MENU

async def edit_income_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для редактирования дохода"""
    t = (update.effective_message.text or "").strip()
    
    if t == "Дата":
        await update.effective_message.reply_text("Выберите дату:", reply_markup=date_selection_kb(include_back=True))
        return INCOME_EDIT_DATE_MENU
    if t == "Источник":
        await update.effective_message.reply_text("Введите источник дохода:", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return INCOME_EDIT_SOURCE
    if t == "Сумма":
        await update.effective_message.reply_text("Введите сумму (например 1500.00):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return INCOME_EDIT_AMOUNT
    if t == "Категория":
        await update.effective_message.reply_text("Выберите категорию:", reply_markup=income_categories_kb(include_back=True))
        return INCOME_EDIT_CATEGORY
    if t == "Счёт":
        acc = list_accounts(_uid(update))
        if not acc:
            await update.effective_message.reply_text("Счетов нет. Добавьте их в «💼 Баланс».", reply_markup=edit_income_menu_kb())
            return INCOME_EDIT_MENU
        await update.effective_message.reply_text("Выберите счёт:", reply_markup=accounts_kb(list(acc.keys()), include_back=True))
        return INCOME_EDIT_PAYMENT
    if t == "⬅️ Назад":
        return await income_back(update, context)
    
    return INCOME_EDIT_MENU

# Функции редактирования отдельных полей (аналогично purchases.py, но для доходов)
async def edit_income_set_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить источник дохода"""
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    
    try:
        # Находим последний доход
        rows = read_rows(_uid(update))
        income_rows = [r for r in rows if float(r.get('total', 0) or 0) > 0]
        if not income_rows:
            await update.effective_message.reply_text("Записей о доходах нет.")
            return INCOME_EDIT_MENU
        
        # Обновляем источник
        _, new_row = update_last_row(_uid(update), merchant=txt)
        await update.effective_message.reply_text(f"✅ Источник обновлён: {new_row.get('merchant','')}", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВведите источник дохода или «⬅️ Назад».")
        return INCOME_EDIT_SOURCE

async def edit_income_set_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить сумму дохода"""
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    
    try:
        amount = float(txt.replace(",", "."))
        if amount <= 0:
            await update.effective_message.reply_text("❌ Сумма дохода должна быть положительной.")
            return INCOME_EDIT_AMOUNT
        
        context.user_data["edit_income_amount_tmp"] = amount
        await update.effective_message.reply_text("Введите валюту (UAH, EUR, USD):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return INCOME_EDIT_AMOUNT_CURRENCY
    except:
        await update.effective_message.reply_text("❌ Неверная сумма. Введите число или «⬅️ Назад».")
        return INCOME_EDIT_AMOUNT

async def edit_income_set_amount_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить валюту для суммы дохода"""
    cur = (update.effective_message.text or "").strip().upper()
    if cur == "⬅️ НАЗАД":
        await update.effective_message.reply_text("Введите сумму (например 1500.00):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return INCOME_EDIT_AMOUNT
    
    try:
        amount = float(context.user_data.get("edit_income_amount_tmp"))
        old_row, new_row = update_last_row(_uid(update), total=amount, currency=cur)
        
        # Пересчитываем балансы для дохода
        rebalance_on_edit(_uid(update), old_row, new_row)
        rebalance_accounts_on_income_edit(_uid(update), old_row, new_row)
        
        await update.effective_message.reply_text(
            f"✅ Сумма обновлена: {fmt_money(new_row.get('total',0), new_row.get('currency',''))}",
            reply_markup=edit_income_menu_kb()
        )
        context.user_data.pop("edit_income_amount_tmp", None)
        return INCOME_EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВведите валюту заново или «⬅️ Назад».")
        return INCOME_EDIT_AMOUNT_CURRENCY

async def edit_income_set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить категорию дохода"""
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    
    # Извлекаем название категории из форматированной строки (убираем эмодзи)
    categories = get_income_categories_list()
    selected_category = None
    
    # Ищем точное совпадение с форматированной строкой
    for category in categories:
        if format_category_for_display(category) == txt:
            selected_category = category.name
            break
    
    # Если не найдено точное совпадение, используем текст как есть
    if not selected_category:
        selected_category = txt
    
    try:
        _, new_row = update_last_row(_uid(update), category=selected_category)
        await update.effective_message.reply_text(f"✅ Категория: {new_row.get('category','')}", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВыберите категорию из списка или «⬅️ Назад».")
        return INCOME_EDIT_CATEGORY

async def edit_income_set_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменить счёт для дохода"""
    choice = (update.effective_message.text or "").strip()
    if choice == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    
    acc = list_accounts(_uid(update))
    if choice not in acc:
        await update.effective_message.reply_text("Выберите счёт из списка:", reply_markup=accounts_kb(list(acc.keys()), include_back=True))
        return INCOME_EDIT_PAYMENT
    
    try:
        old_row, new_row = update_last_row(_uid(update), payment_method=choice)
        rebalance_accounts_on_income_edit(_uid(update), old_row, new_row)
        await update.effective_message.reply_text(f"✅ Счёт обновлён: {choice}", reply_markup=edit_income_menu_kb())
        return INCOME_EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")
        return INCOME_EDIT_PAYMENT

# ──────────────────────────────────────────────────────────────────────────────
# Пошаговое добавление дохода
async def income_add_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода суммы дохода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    if text == "❌ Отмена":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            await update.effective_message.reply_text(
                "❌ Сумма дохода должна быть положительной.\n\n"
                "Введите сумму еще раз:"
            )
            return INCOME_ADD_AMOUNT
        
        # Сохраняем сумму
        context.user_data["new_income"]["amount"] = amount
        
        await update.effective_message.reply_text(
            f"✅ Сумма: {amount:.2f}\n\n"
            "Шаг 2/5: Выберите валюту",
            reply_markup=income_add_currency_kb()
        )
        return INCOME_ADD_CURRENCY
        
    except ValueError:
        await update.effective_message.reply_text(
            "❌ Неверный формат суммы.\n\n"
            "Введите число (например: 5000, 1500.50, 300):"
        )
        return INCOME_ADD_AMOUNT

async def income_add_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора валюты дохода"""
    text = (update.effective_message.text or "").strip().upper()
    
    if text == "⬅️ НАЗАД":
        amount = context.user_data.get("new_income", {}).get("amount")
        if amount:
            await update.effective_message.reply_text(
                f"Шаг 1/5: Введите сумму дохода\n\n"
                f"Текущая сумма: {amount:.2f}\n"
                f"Введите новую сумму или используйте текущую:",
                reply_markup=income_add_amount_kb()
            )
        else:
            await update.effective_message.reply_text(
                "Шаг 1/5: Введите сумму дохода\n\n"
                "Например: 5000, 1500.50, 300",
                reply_markup=income_add_amount_kb()
            )
        return INCOME_ADD_AMOUNT
    
    if text == "❌ ОТМЕНА":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    # Проверяем, что валюта в списке поддерживаемых
    supported_currencies = ["UAH", "USD", "EUR", "RUB", "PLN", "GBP"]
    if text not in supported_currencies:
        await update.effective_message.reply_text(
            "❌ Неподдерживаемая валюта.\n\n"
            "Выберите валюту из списка:",
            reply_markup=income_add_currency_kb()
        )
        return INCOME_ADD_CURRENCY
    
    # Сохраняем валюту
    context.user_data["new_income"]["currency"] = text
    amount = context.user_data["new_income"]["amount"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {text}\n\n"
        "Шаг 3/6: Выберите дату дохода",
        reply_markup=date_selection_kb(include_back=True)
    )
    return INCOME_ADD_DATE

async def income_add_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора даты дохода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        currency = context.user_data.get("new_income", {}).get("currency")
        await update.effective_message.reply_text(
            f"Шаг 2/6: Выберите валюту\n\n"
            f"Текущая валюта: {currency}",
            reply_markup=income_add_currency_kb()
        )
        return INCOME_ADD_CURRENCY
    
    if text == "❌ Отмена":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    # Обработка выбора даты
    from datetime import datetime, date
    selected_date = None
    
    if "Сегодня" in text:
        selected_date = date.today()
    elif "📆 Календарь" in text:
        await update.effective_message.reply_text(
            "Выберите дату из календаря:",
            reply_markup=calendar_kb()
        )
        return INCOME_ADD_DATE
    else:
        # Обработка календаря
        if text.isdigit() and 1 <= int(text) <= 31:
            # Выбор дня из календаря
            try:
                day = int(text)
                current_date = date.today()
                selected_date = date(current_date.year, current_date.month, day)
            except (ValueError, TypeError):
                pass
        elif "◀️" in text or "▶️" in text:
            # Навигация по календарю - показываем календарь снова
            await update.effective_message.reply_text(
                "Выберите дату из календаря:",
                reply_markup=calendar_kb()
            )
            return INCOME_ADD_DATE
        else:
            # Парсим дату в формате ДД.ММ
            try:
                if "." in text and len(text.split(".")) == 2:
                    day, month = text.split(".")
                    current_year = date.today().year
                    selected_date = date(current_year, int(month), int(day))
            except (ValueError, TypeError):
                pass
    
    if not selected_date:
        await update.effective_message.reply_text(
            "❌ Неверный формат даты.\n\n"
            "Выберите дату из предложенных вариантов:",
            reply_markup=date_selection_kb(include_back=True)
        )
        return INCOME_ADD_DATE
    
    # Сохраняем дату
    context.user_data["new_income"]["date"] = selected_date.strftime("%Y-%m-%d")
    amount = context.user_data["new_income"]["amount"]
    currency = context.user_data["new_income"]["currency"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
        "Шаг 4/6: Введите источник дохода\n\n"
        "Например: название проекта, имя человека, уроки гитары, продажа на Ebay",
        reply_markup=income_add_source_kb()
    )
    return INCOME_ADD_SOURCE

async def income_add_source_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода источника дохода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        date_str = context.user_data.get("new_income", {}).get("date")
        await update.effective_message.reply_text(
            f"Шаг 3/6: Выберите дату дохода\n\n"
            f"Текущая дата: {date_str}",
            reply_markup=date_selection_kb(include_back=True)
        )
        return INCOME_ADD_DATE
    
    if text == "❌ Отмена":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    if not text:
        await update.effective_message.reply_text(
            "❌ Источник дохода не может быть пустым.\n\n"
            "Введите источник дохода:"
        )
        return INCOME_ADD_SOURCE
    
    # Сохраняем источник
    context.user_data["new_income"]["source"] = text
    amount = context.user_data["new_income"]["amount"]
    currency = context.user_data["new_income"]["currency"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Источник: {text}\n\n"
        "Шаг 5/6: Выберите категорию дохода",
        reply_markup=income_add_category_kb(include_back=True, include_cancel=True)
    )
    return INCOME_ADD_CATEGORY

async def income_add_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора категории дохода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        source = context.user_data.get("new_income", {}).get("source")
        await update.effective_message.reply_text(
            f"Шаг 4/6: Введите источник дохода\n\n"
            f"Текущий источник: {source}",
            reply_markup=income_add_source_kb()
        )
        return INCOME_ADD_SOURCE
    
    if text == "❌ Отмена":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    # Извлекаем название категории из форматированной строки (убираем эмодзи)
    categories = get_income_categories_list()
    selected_category = None
    
    # Ищем точное совпадение с форматированной строкой
    for category in categories:
        if format_category_for_display(category) == text:
            selected_category = category.name
            break
    
    # Если не найдено точное совпадение, используем текст как есть
    if not selected_category:
        selected_category = text
    
    # Сохраняем категорию
    context.user_data["new_income"]["category"] = selected_category
    amount = context.user_data["new_income"]["amount"]
    currency = context.user_data["new_income"]["currency"]
    source = context.user_data["new_income"]["source"]
    
    # Проверяем наличие счетов
    accounts = list_accounts(_uid(update))
    if not accounts:
        await update.effective_message.reply_text(
            "❌ Нет доступных счетов для зачисления дохода.\n\n"
            "Перейдите в 💼 Баланс → «Добавить счёт» для создания счета.",
            reply_markup=income_menu_kb()
        )
        context.user_data.pop("new_income", None)
        return INCOME_MENU
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Источник: {source}\n"
        f"✅ Категория: {selected_category}\n\n"
        "Шаг 6/6: Выберите счёт",
        reply_markup=income_add_account_kb(list(accounts.keys()), include_back=True, include_cancel=True)
    )
    return INCOME_ADD_ACCOUNT

async def income_add_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора счета для зачисления дохода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        category = context.user_data.get("new_income", {}).get("category")
        await update.effective_message.reply_text(
            f"Шаг 5/6: Выберите категорию дохода\n\n"
            f"Текущая категория: {category}",
            reply_markup=income_add_category_kb(include_back=True, include_cancel=True)
        )
        return INCOME_ADD_CATEGORY
    
    if text == "❌ Отмена":
        context.user_data.pop("new_income", None)
        await update.effective_message.reply_text("💰 Меню доходов:", reply_markup=income_menu_kb())
        return INCOME_MENU
    
    # Проверяем, что выбранный счет существует
    accounts = list_accounts(_uid(update))
    if text not in accounts:
        await update.effective_message.reply_text(
            "❌ Выбранный счёт не найден.\n\n"
            "Выберите счёт из списка:",
            reply_markup=income_add_account_kb(list(accounts.keys()), include_back=True, include_cancel=True)
        )
        return INCOME_ADD_ACCOUNT
    
    # Сохраняем счет
    context.user_data["new_income"]["account"] = text
    
    # Создаем запись о доходе
    income_data = context.user_data["new_income"]
    data = {
        "date": income_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "merchant": income_data["source"],
        "total": income_data["amount"],
        "currency": income_data["currency"],
        "category": income_data["category"],
        "payment_method": income_data["account"]
    }
    
    try:
        # Сохраняем доход в CSV
        append_row_csv(_uid(update), data, source="manual_income")
        
        # Обновляем баланс
        inc_balance_for_income(_uid(update), income_data["amount"], income_data["currency"], income_data["category"])
        
        # Обновляем счет
        inc_account(_uid(update), income_data["account"], income_data["amount"])
        
        await update.effective_message.reply_text(
            f"✅ Доход успешно добавлен!\n\n"
            f"💰 Сумма: {income_data['amount']:.2f} {income_data['currency']}\n"
            f"📍 Источник: {income_data['source']}\n"
            f"📂 Категория: {income_data['category']}\n"
            f"🏦 Счёт: {income_data['account']}",
            reply_markup=income_menu_kb()
        )
        
        # Очищаем временные данные
        context.user_data.pop("new_income", None)
        return INCOME_MENU
        
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ Ошибка при сохранении дохода: {e}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=income_menu_kb()
        )
        context.user_data.pop("new_income", None)
        return INCOME_MENU
