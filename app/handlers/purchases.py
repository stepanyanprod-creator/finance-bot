# app/handlers/purchases.py
import os
import re
from datetime import datetime, date, timedelta
from collections import defaultdict
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from app.constants import (
    BAL_MENU, ADD_ACC_NAME, ADD_ACC_CURRENCY, EDIT_PICK_ACC, EDIT_NEW_AMOUNT,
    CHOOSE_ACC_FOR_RECEIPT, BUY_MENU, EDIT_MENU, EDIT_DATE, EDIT_MERCHANT,
    EDIT_AMOUNT, EDIT_AMOUNT_CURRENCY, EDIT_CATEGORY, EDIT_PAYMENT, EDIT_DATE_MENU,
    EXPENSE_ADD_AMOUNT, EXPENSE_ADD_CURRENCY, EXPENSE_ADD_MERCHANT, 
    EXPENSE_ADD_CATEGORY, EXPENSE_ADD_ACCOUNT, EXPENSE_ADD_DATE
)
from app.keyboards import (
    reply_menu_keyboard, purchases_menu_kb, edit_last_menu_kb, accounts_kb, categories_kb, 
    date_selection_kb, calendar_kb, expense_add_amount_kb, expense_add_currency_kb,
    expense_add_merchant_kb, expense_add_category_kb, expense_add_account_kb
)
from app.services.receipt_parser import parse_receipt
from app.storage import (
    ensure_csv, read_rows, append_row_csv, undo_last_row,
    set_balance, get_balances, dec_balance, fmt_money,
    update_last_row, update_row_from_end, rebalance_on_edit,
    list_accounts, add_account, set_account_amount, dec_account,
    find_accounts_by_currency, format_accounts
)
from app.rules import apply_category_rules, load_rules, save_rules

from app.utils import get_user_id as _uid

# ──────────────────────────────────────────────────────────────────────────────
# вспомогательное: пересчёт по СЧЕТАМ при изменениях суммы/оплаты
def rebalance_accounts_on_edit(user_id: int, old_row: dict, new_row: dict):
    def _num(x):
        try: return float(x)
        except: return 0.0
    accs = list_accounts(user_id)
    old_acc = (old_row.get("payment_method") or "").strip()
    new_acc = (new_row.get("payment_method") or "").strip()
    old_total = _num(old_row.get("total", 0))
    new_total = _num(new_row.get("total", 0))
    # Отменить предыдущее изменение (вернуть старую сумму)
    if old_acc and old_acc in accs:
        cur = float(accs[old_acc]["amount"])
        set_account_amount(user_id, old_acc, cur + old_total)
    # Применить новое изменение (отрицательная = расход, положительная = доход)
    if new_acc and new_acc in accs:
        cur = float(list_accounts(user_id)[new_acc]["amount"])
        set_account_amount(user_id, new_acc, cur - new_total)

# ──────────────────────────────────────────────────────────────────────────────
# Базовые действия и меню «Расходы»
async def purchases_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Меню расходов:", reply_markup=purchases_menu_kb())
    return BUY_MENU

async def purchases_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Главное меню:", reply_markup=reply_menu_keyboard())
    return ConversationHandler.END

async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать последний расход"""
    rows = read_rows(_uid(update))
    if not rows:
        return await update.effective_message.reply_text("Пока записей нет.")
    
    # Ищем последний расход (отрицательная сумма)
    expense_rows = [r for r in rows if float(r.get('total', 0) or 0) < 0]
    if not expense_rows:
        return await update.effective_message.reply_text("Записей о расходах пока нет.")
    
    r = expense_rows[-1]
    await update.effective_message.reply_text(
        "🧾 Последний расход:\n"
        f"• Дата: {r.get('date','')}\n"
        f"• Магазин: {r.get('merchant','')}\n"
        f"• Сумма: {fmt_money(r.get('total',0), r.get('currency',''))}\n"
        f"• Категория: {r.get('category') or '—'}\n"
        f"• Способ оплаты: {r.get('payment_method') or '—'}"
    )

async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok = undo_last_row(_uid(update))
    await update.effective_message.reply_text("↩️ Последняя запись удалена." if ok else "Удалять нечего.")

async def purchases_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.effective_message.text or "").strip()
    if text == "📊 Сегодня": return await today(update, context)
    if text == "🗓 Неделя":  return await week(update, context)
    if text == "📅 Месяц":   return await month(update, context)
    if text == "🧾 Последняя": return await last(update, context)
    if text == "↩️ Undo": return await undo(update, context)
    if text == "✏️ Править последнюю": return await edit_last_menu_entry(update, context)
    if text == "➕ Добавить расход": return await add_expense_entry(update, context)
    if text == "⬅️ Назад": return await purchases_back(update, context)
    return BUY_MENU

# ──────────────────────────────────────────────────────────────────────────────
# Статистика
def _parse_period(args):
    today = date.today()
    if not args:
        start = date(today.year, today.month, 1)
        end = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
        return start, end
    if len(args) == 1 and len(args[0]) == 7:
        y, m = map(int, args[0].split("-"))
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        return start, end
    if len(args) == 2:
        s = datetime.strptime(args[0], "%Y-%m-%d").date()
        e = datetime.strptime(args[1], "%Y-%m-%d").date()
        return s, e
    raise ValueError("Неверный формат. /stats, /stats YYYY-MM или /stats YYYY-MM-DD YYYY-MM-DD")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    try:
        start, end = _parse_period(context.args)
    except Exception as e:
        return await msg.reply_text(f"❌ {e}")

    rows = read_rows(_uid(update))
    selected = []
    for r in rows:
        try:
            d = datetime.strptime(r.get("date",""), "%Y-%m-%d").date()
        except Exception:
            continue
        if start <= d < end:
            selected.append(r)

    if not selected:
        return await msg.reply_text("За выбранный период ничего не найдено.")

    base_cur = selected[0].get("currency") or "EUR"
    total_sum = sum(float(r.get("total",0) or 0) for r in selected if (r.get("currency") or "") == base_cur)

    by_cat, by_merch = defaultdict(float), defaultdict(float)
    for r in selected:
        if (r.get("currency") or "") != base_cur:
            continue
        by_cat[r.get("category") or "—"] += float(r.get("total",0) or 0)
        by_merch[r.get("merchant") or "—"] += float(r.get("total",0) or 0)

    top_cat = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:10]
    top_merch = sorted(by_merch.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [f"📊 Статистика {start} — {end} (валюта: {base_cur})",
             f"• Всего расходов: {fmt_money(total_sum, base_cur)}"]
    if top_cat:
        lines.append("• По категориям:")
        for name, s in top_cat:
            lines.append(f"  — {name}: {fmt_money(s, base_cur)}")
    if top_merch:
        lines.append("• Топ торговых точек:")
        for name, s in top_merch:
            lines.append(f"  — {name}: {fmt_money(s, base_cur)}")
    await msg.reply_text("\n".join(lines))

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = date.today()
    context.args = [d.strftime("%Y-%m-%d"), (d + timedelta(days=1)).strftime("%Y-%m-%d")]
    return await stats(update, context)

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=7)
    context.args = [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")]
    return await stats(update, context)

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await stats(update, context)

# ──────────────────────────────────────────────────────────────────────────────
# «✏️ Править последнюю»
async def edit_last_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("Что правим в последней записи?", reply_markup=edit_last_menu_kb())
    return EDIT_MENU

async def edit_last_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = (update.effective_message.text or "").strip()
    if t == "Дата":
        await update.effective_message.reply_text("Выберите дату:", reply_markup=date_selection_kb(include_back=True))
        return EDIT_DATE_MENU
    if t == "Магазин":
        await update.effective_message.reply_text("Введите название магазина:", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return EDIT_MERCHANT
    if t == "Сумма":
        await update.effective_message.reply_text("Введите сумму (например 123.45):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return EDIT_AMOUNT
    if t == "Категория":
        await update.effective_message.reply_text("Выберите категорию:", reply_markup=categories_kb(include_back=True))
        return EDIT_CATEGORY
    if t == "Способ оплаты":
        acc = list_accounts(_uid(update))
        if not acc:
            await update.effective_message.reply_text("Счетов нет. Добавьте их в «💼 Баланс».", reply_markup=edit_last_menu_kb())
            return EDIT_MENU
        await update.effective_message.reply_text("Выберите счёт для оплаты:", reply_markup=accounts_kb(list(acc.keys()), include_back=True))
        return EDIT_PAYMENT
    if t == "⬅️ Назад":
        return await purchases_back(update, context)
    return EDIT_MENU

async def edit_date_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню выбора даты"""
    txt = (update.effective_message.text or "").strip()
    
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_last_menu_kb())
        return EDIT_MENU
    
    # Обработка "Сегодня"
    if txt.startswith("📅 Сегодня"):
        today = date.today().strftime("%Y-%m-%d")
        try:
            _, new_row = update_last_row(_uid(update), date=today)
            await update.effective_message.reply_text(f"✅ Дата обновлена: {new_row.get('date','')}", reply_markup=edit_last_menu_kb())
            return EDIT_MENU
        except Exception as e:
            await update.effective_message.reply_text(f"❌ {e}")
            return EDIT_DATE_MENU
    
    # Обработка "Календарь"
    if txt == "📆 Календарь":
        await update.effective_message.reply_text("Выберите дату из календаря:", reply_markup=calendar_kb())
        return EDIT_DATE
    
    # Обработка дат в формате ДД.ММ
    if re.match(r'^\d{1,2}\.\d{1,2}$', txt):
        try:
            day, month = txt.split('.')
            current_year = date.today().year
            selected_date = date(current_year, int(month), int(day))
            date_str = selected_date.strftime("%Y-%m-%d")
            
            _, new_row = update_last_row(_uid(update), date=date_str)
            await update.effective_message.reply_text(f"✅ Дата обновлена: {new_row.get('date','')}", reply_markup=edit_last_menu_kb())
            return EDIT_MENU
        except (ValueError, TypeError) as e:
            await update.effective_message.reply_text(f"❌ Неверная дата: {e}")
            return EDIT_DATE_MENU
    
    # Если не распознано, показываем меню снова
    await update.effective_message.reply_text("Выберите дату:", reply_markup=date_selection_kb(include_back=True))
    return EDIT_DATE_MENU

async def edit_last_set_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик календаря для выбора даты"""
    txt = (update.effective_message.text or "").strip()
    
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Выберите дату:", reply_markup=date_selection_kb(include_back=True))
        return EDIT_DATE_MENU
    
    # Обработка навигации по месяцам
    if "◀️" in txt or "▶️" in txt:
        # Парсим навигацию по месяцам
        if "◀️" in txt:
            # Предыдущий месяц
            month_name = txt.replace("◀️ ", "").strip()
            month_names = [
                "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
            ]
            try:
                month = month_names.index(month_name) + 1
                current_year = date.today().year
                if month == 12:  # Если переходим к декабрю, значит это предыдущий год
                    current_year -= 1
                await update.effective_message.reply_text("Выберите дату из календаря:", reply_markup=calendar_kb(current_year, month))
                return EDIT_DATE
            except ValueError:
                pass
        elif "▶️" in txt:
            # Следующий месяц
            month_name = txt.replace(" ▶️", "").strip()
            month_names = [
                "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
            ]
            try:
                month = month_names.index(month_name) + 1
                current_year = date.today().year
                if month == 1:  # Если переходим к январю, значит это следующий год
                    current_year += 1
                await update.effective_message.reply_text("Выберите дату из календаря:", reply_markup=calendar_kb(current_year, month))
                return EDIT_DATE
            except ValueError:
                pass
    
    # Обработка выбора дня
    if txt.isdigit() and 1 <= int(txt) <= 31:
        try:
            day = int(txt)
            # Получаем текущий месяц и год из контекста или используем текущие
            current_date = date.today()
            selected_date = date(current_date.year, current_date.month, day)
            date_str = selected_date.strftime("%Y-%m-%d")
            
            _, new_row = update_last_row(_uid(update), date=date_str)
            await update.effective_message.reply_text(f"✅ Дата обновлена: {new_row.get('date','')}", reply_markup=edit_last_menu_kb())
            return EDIT_MENU
        except (ValueError, TypeError) as e:
            await update.effective_message.reply_text(f"❌ Неверная дата: {e}")
            return EDIT_DATE
    
    # Если не распознано, показываем календарь снова
    await update.effective_message.reply_text("Выберите дату из календаря:", reply_markup=calendar_kb())
    return EDIT_DATE

async def edit_last_set_merchant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_last_menu_kb()); return EDIT_MENU
    try:
        _, new_row = update_last_row(_uid(update), merchant=txt)
        await update.effective_message.reply_text(f"✅ Магазин: {new_row.get('merchant','')}", reply_markup=edit_last_menu_kb())
        return EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВведите название магазина или «⬅️ Назад».")
        return EDIT_MERCHANT

async def edit_last_set_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_last_menu_kb()); return EDIT_MENU
    try:
        amount = float(txt.replace(",", "."))
        context.user_data["edit_amount_tmp"] = amount
        await update.effective_message.reply_text("Введите валюту (UAH, EUR, USD):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return EDIT_AMOUNT_CURRENCY
    except:
        await update.effective_message.reply_text("❌ Неверная сумма. Введите число или «⬅️ Назад».")
        return EDIT_AMOUNT

async def edit_last_set_amount_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = (update.effective_message.text or "").strip().upper()
    if cur == "⬅️ Назад":
        await update.effective_message.reply_text("Введите сумму (например 123.45):", reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True))
        return EDIT_AMOUNT
    try:
        amount = float(context.user_data.get("edit_amount_tmp"))
        old_row, new_row = update_last_row(_uid(update), total=amount, currency=cur)
        rebalance_on_edit(_uid(update), old_row, new_row)
        rebalance_accounts_on_edit(_uid(update), old_row, new_row)
        await update.effective_message.reply_text(
            f"✅ Сумма обновлена: {fmt_money(new_row.get('total',0), new_row.get('currency',''))}",
            reply_markup=edit_last_menu_kb()
        )
        context.user_data.pop("edit_amount_tmp", None)
        return EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВведите валюту заново или «⬅️ Назад».")
        return EDIT_AMOUNT_CURRENCY

async def edit_last_set_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.effective_message.text or "").strip()
    if txt == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_last_menu_kb()); return EDIT_MENU
    
    # Извлекаем название категории из форматированной строки (убираем эмодзи)
    from app.categories import get_categories_list, format_category_for_display
    categories = get_categories_list()
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
        await update.effective_message.reply_text(f"✅ Категория: {new_row.get('category','')}", reply_markup=edit_last_menu_kb())
        return EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}\nВыберите категорию из списка или «⬅️ Назад».")
        return EDIT_CATEGORY

async def edit_last_set_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = (update.effective_message.text or "").strip()
    if choice == "⬅️ Назад":
        await update.effective_message.reply_text("Что правим?", reply_markup=edit_last_menu_kb()); return EDIT_MENU
    acc = list_accounts(_uid(update))
    if choice not in acc:
        await update.effective_message.reply_text("Выберите счёт для оплаты:", reply_markup=accounts_kb(list(acc.keys()), include_back=True))
        return EDIT_PAYMENT
    try:
        old_row, new_row = update_last_row(_uid(update), payment_method=choice)
        rebalance_accounts_on_edit(_uid(update), old_row, new_row)
        await update.effective_message.reply_text(f"✅ Оплата теперь со счёта: {choice}", reply_markup=edit_last_menu_kb())
        return EDIT_MENU
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")
        return EDIT_PAYMENT

# ──────────────────────────────────────────────────────────────────────────────
# Фото чеков → выбор счёта (общая логика с голосом делит состояние CHOOSE_ACC_FOR_RECEIPT)
async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    photo = msg.photo[-1]
    tg_file = await context.bot.get_file(photo.file_id)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        await tg_file.download_to_drive(tmp.name)
        local_path = tmp.name

    await msg.reply_text("🔍 Обрабатываю чек…")
    try:
        data = parse_receipt(local_path)
        auto_cat = apply_category_rules(data)
        if auto_cat and auto_cat != (data.get("category") or ""):
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category(auto_cat)
            if validated_cat:
                data["category"] = validated_cat

        context.user_data["pending_receipt"] = {"data": data, "photo_id": photo.file_id}

        acc = list_accounts(_uid(update))
        if not acc:
            await msg.reply_text("Сначала добавьте счёт: 💼 Баланс → «Добавить счёт».",
                                 reply_markup=ReplyKeyboardMarkup([["Открыть меню Баланс"], ["Отмена"]], resize_keyboard=True))
            return CHOOSE_ACC_FOR_RECEIPT

        await msg.reply_text("Чем оплатил? Выбери счёт:",
                             reply_markup=accounts_kb(list(acc.keys()), include_cancel=True))
        return CHOOSE_ACC_FOR_RECEIPT

    except ValueError as ve:
        if str(ve) == "duplicate":
            await msg.reply_text("⚠️ Этот чек уже есть. Запись не добавлена.")
        else:
            await msg.reply_text(f"❌ Ошибка: {ve}")
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}")

async def receipt_choose_account_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    choice = (msg.text or "").strip()

    if choice in {"Отмена", "Открыть меню Баланс"}:
        context.user_data.pop("pending_receipt", None)
        if choice == "Открыть меню Баланс":
            from app.handlers.balance import balance_menu_entry
            return await balance_menu_entry(update, context)
        await msg.reply_text("Отменено.", reply_markup=reply_menu_keyboard())
        return ConversationHandler.END

    pend = context.user_data.get("pending_receipt")
    if not pend:
        await msg.reply_text("Нет ожидающего чека.", reply_markup=reply_menu_keyboard())
        return ConversationHandler.END

    acc = list_accounts(_uid(update))
    if choice not in acc:
        await msg.reply_text("Выбери счёт из списка или «Отмена».",
                             reply_markup=accounts_kb(list(acc.keys()), include_cancel=True))
        return CHOOSE_ACC_FOR_RECEIPT

    data = pend["data"]
    data["payment_method"] = choice

    try:
        append_row_csv(_uid(update), data, source=f"photo:{pend.get('photo_id','')}")
        dec_balance(_uid(update), amount=data.get("total", 0), currency=data.get("currency"),
                    category=(data.get("category") or None))
        dec_account(_uid(update), choice, float(data.get("total", 0) or 0))

        total = data.get('total', 0)
        currency = data.get('currency', '')
        amount_display = f"{total:.2f} {currency}"
        if total < 0:
            amount_display = f"💰 Расход: {amount_display}"
        else:
            amount_display = f"💵 Доход: {amount_display}"
            
        await msg.reply_text(
            f"✅ Добавлено: {data.get('merchant','?')} — "
            f"{amount_display} от {data.get('date','')}\n"
            f"💳 Оплачено со счёта: {choice}",
            reply_markup=reply_menu_keyboard()
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка при сохранении: {e}", reply_markup=reply_menu_keyboard())

    context.user_data.pop("pending_receipt", None)
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────────
# Пошаговое добавление расхода
async def add_expense_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс добавления расхода (пошагово)"""
    # Инициализируем данные для нового расхода
    context.user_data["new_expense"] = {
        "amount": None,
        "currency": None,
        "merchant": None,
        "category": None,
        "account": None
    }
    
    await update.effective_message.reply_text(
        "💸 Добавление расхода\n\n"
        "Шаг 1/6: Введите сумму расхода\n\n"
        "Например: 150, 25.50, 1000",
        reply_markup=expense_add_amount_kb()
    )
    return EXPENSE_ADD_AMOUNT


async def expense_add_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода суммы расхода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    if text == "❌ Отмена":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    try:
        amount = float(text.replace(",", "."))
        if amount <= 0:
            await update.effective_message.reply_text(
                "❌ Сумма расхода должна быть положительной.\n\n"
                "Введите сумму еще раз:"
            )
            return EXPENSE_ADD_AMOUNT
        
        # Сохраняем сумму
        context.user_data["new_expense"]["amount"] = amount
        
        await update.effective_message.reply_text(
            f"✅ Сумма: {amount:.2f}\n\n"
            "Шаг 2/5: Выберите валюту",
            reply_markup=expense_add_currency_kb()
        )
        return EXPENSE_ADD_CURRENCY
        
    except ValueError:
        await update.effective_message.reply_text(
            "❌ Неверный формат суммы.\n\n"
            "Введите число (например: 150, 25.50, 1000):"
        )
        return EXPENSE_ADD_AMOUNT


async def expense_add_currency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора валюты расхода"""
    text = (update.effective_message.text or "").strip().upper()
    
    if text == "⬅️ НАЗАД":
        amount = context.user_data.get("new_expense", {}).get("amount")
        if amount:
            await update.effective_message.reply_text(
                f"Шаг 1/5: Введите сумму расхода\n\n"
                f"Текущая сумма: {amount:.2f}\n"
                f"Введите новую сумму или используйте текущую:",
                reply_markup=expense_add_amount_kb()
            )
        else:
            await update.effective_message.reply_text(
                "Шаг 1/5: Введите сумму расхода\n\n"
                "Например: 150, 25.50, 1000",
                reply_markup=expense_add_amount_kb()
            )
        return EXPENSE_ADD_AMOUNT
    
    if text == "❌ ОТМЕНА":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    # Проверяем, что валюта в списке поддерживаемых
    supported_currencies = ["UAH", "USD", "EUR", "RUB", "PLN", "GBP"]
    if text not in supported_currencies:
        await update.effective_message.reply_text(
            "❌ Неподдерживаемая валюта.\n\n"
            "Выберите валюту из списка:",
            reply_markup=expense_add_currency_kb()
        )
        return EXPENSE_ADD_CURRENCY
    
    # Сохраняем валюту
    context.user_data["new_expense"]["currency"] = text
    amount = context.user_data["new_expense"]["amount"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {text}\n\n"
        "Шаг 3/6: Выберите дату расхода",
        reply_markup=date_selection_kb(include_back=True)
    )
    return EXPENSE_ADD_DATE

async def expense_add_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора даты расхода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        currency = context.user_data.get("new_expense", {}).get("currency")
        await update.effective_message.reply_text(
            f"Шаг 2/6: Выберите валюту\n\n"
            f"Текущая валюта: {currency}",
            reply_markup=expense_add_currency_kb()
        )
        return EXPENSE_ADD_CURRENCY
    
    if text == "❌ Отмена":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
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
        return EXPENSE_ADD_DATE
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
            return EXPENSE_ADD_DATE
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
        return EXPENSE_ADD_DATE
    
    # Сохраняем дату
    context.user_data["new_expense"]["date"] = selected_date.strftime("%Y-%m-%d")
    amount = context.user_data["new_expense"]["amount"]
    currency = context.user_data["new_expense"]["currency"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
        "Шаг 4/6: Введите название магазина\n\n"
        "Например: Ашан, McDonald's, АЗС",
        reply_markup=expense_add_merchant_kb()
    )
    return EXPENSE_ADD_MERCHANT

async def expense_add_merchant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода магазина расхода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        date_str = context.user_data.get("new_expense", {}).get("date")
        await update.effective_message.reply_text(
            f"Шаг 3/6: Выберите дату расхода\n\n"
            f"Текущая дата: {date_str}",
            reply_markup=date_selection_kb(include_back=True)
        )
        return EXPENSE_ADD_DATE
    
    if text == "❌ Отмена":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    if not text:
        await update.effective_message.reply_text(
            "❌ Название магазина не может быть пустым.\n\n"
            "Введите название магазина:"
        )
        return EXPENSE_ADD_MERCHANT
    
    # Сохраняем магазин
    context.user_data["new_expense"]["merchant"] = text
    amount = context.user_data["new_expense"]["amount"]
    currency = context.user_data["new_expense"]["currency"]
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Магазин: {text}\n\n"
        "Шаг 5/6: Выберите категорию расхода",
        reply_markup=expense_add_category_kb(include_back=True, include_cancel=True)
    )
    return EXPENSE_ADD_CATEGORY


async def expense_add_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора категории расхода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        merchant = context.user_data.get("new_expense", {}).get("merchant")
        await update.effective_message.reply_text(
            f"Шаг 4/6: Введите название магазина\n\n"
            f"Текущий магазин: {merchant}",
            reply_markup=expense_add_merchant_kb()
        )
        return EXPENSE_ADD_MERCHANT
    
    if text == "❌ Отмена":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    # Извлекаем название категории из форматированной строки (убираем эмодзи)
    from app.categories import get_categories_list, format_category_for_display
    categories = get_categories_list()
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
    context.user_data["new_expense"]["category"] = selected_category
    amount = context.user_data["new_expense"]["amount"]
    currency = context.user_data["new_expense"]["currency"]
    merchant = context.user_data["new_expense"]["merchant"]
    
    # Проверяем наличие счетов
    accounts = list_accounts(_uid(update))
    if not accounts:
        await update.effective_message.reply_text(
            "❌ Нет доступных счетов для списания расхода.\n\n"
            "Перейдите в 💼 Баланс → «Добавить счёт» для создания счета.",
            reply_markup=purchases_menu_kb()
        )
        context.user_data.pop("new_expense", None)
        return BUY_MENU
    
    await update.effective_message.reply_text(
        f"✅ Сумма: {amount:.2f} {currency}\n"
        f"✅ Магазин: {merchant}\n"
        f"✅ Категория: {selected_category}\n\n"
        "Шаг 6/6: Выберите счёт для оплаты",
        reply_markup=expense_add_account_kb(list(accounts.keys()), include_back=True, include_cancel=True)
    )
    return EXPENSE_ADD_ACCOUNT


async def expense_add_account_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора счета для списания расхода"""
    text = (update.effective_message.text or "").strip()
    
    if text == "⬅️ Назад":
        category = context.user_data.get("new_expense", {}).get("category")
        await update.effective_message.reply_text(
            f"Шаг 5/6: Выберите категорию расхода\n\n"
            f"Текущая категория: {category}",
            reply_markup=expense_add_category_kb(include_back=True, include_cancel=True)
        )
        return EXPENSE_ADD_CATEGORY
    
    if text == "❌ Отмена":
        context.user_data.pop("new_expense", None)
        await update.effective_message.reply_text("🛍 Меню расходов:", reply_markup=purchases_menu_kb())
        return BUY_MENU
    
    # Проверяем, что выбранный счет существует
    accounts = list_accounts(_uid(update))
    if text not in accounts:
        await update.effective_message.reply_text(
            "❌ Выбранный счёт не найден.\n\n"
            "Выберите счёт из списка:",
            reply_markup=expense_add_account_kb(list(accounts.keys()), include_back=True, include_cancel=True)
        )
        return EXPENSE_ADD_ACCOUNT
    
    # Сохраняем счет
    context.user_data["new_expense"]["account"] = text
    
    # Создаем запись о расходе
    expense_data = context.user_data["new_expense"]
    data = {
        "date": expense_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "merchant": expense_data["merchant"],
        "total": -expense_data["amount"],  # Отрицательная сумма для расхода
        "currency": expense_data["currency"],
        "category": expense_data["category"],
        "payment_method": expense_data["account"]
    }
    
    try:
        # Сохраняем расход в CSV
        append_row_csv(_uid(update), data, source="manual_expense")
        
        # Обновляем баланс
        dec_balance(_uid(update), amount=expense_data["amount"], currency=expense_data["currency"], category=expense_data["category"])
        
        # Обновляем счет
        dec_account(_uid(update), expense_data["account"], expense_data["amount"])
        
        await update.effective_message.reply_text(
            f"✅ Расход успешно добавлен!\n\n"
            f"💸 Сумма: {expense_data['amount']:.2f} {expense_data['currency']}\n"
            f"🏪 Магазин: {expense_data['merchant']}\n"
            f"📂 Категория: {expense_data['category']}\n"
            f"🏦 Счёт: {expense_data['account']}",
            reply_markup=purchases_menu_kb()
        )
        
        # Очищаем временные данные
        context.user_data.pop("new_expense", None)
        return BUY_MENU
        
    except Exception as e:
        await update.effective_message.reply_text(
            f"❌ Ошибка при сохранении расхода: {e}\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=purchases_menu_kb()
        )
        context.user_data.pop("new_expense", None)
        return BUY_MENU
