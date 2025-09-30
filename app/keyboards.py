# app/keyboards.py
from telegram import ReplyKeyboardMarkup
from app.categories import get_categories_list, format_category_for_display
from datetime import date, timedelta

def reply_menu_keyboard() -> ReplyKeyboardMarkup:
    # Без пункта «Скрыть меню»
    return ReplyKeyboardMarkup(
        [
            ["🛍 Расходы", "💰 Доходы"],
            ["📤 Экспорт", "💼 Баланс"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )

def purchases_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📊 Сегодня", "🗓 Неделя", "📅 Месяц"],
            ["🧾 Последняя", "↩️ Undo", "✏️ Править последнюю"],
            ["➕ Добавить расход"],
            ["⬅️ Назад"],
        ],
        resize_keyboard=True
    )

def income_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["📊 Сегодня", "🗓 Неделя", "📅 Месяц"],
            ["💰 Последний", "↩️ Undo", "✏️ Править последний"],
            ["➕ Добавить доход"],
            ["⬅️ Назад"],
        ],
        resize_keyboard=True
    )

def balance_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["💼 Все счета", "➕ Добавить счёт"],
            ["✏️ Редактировать", "🗑️ Удалить счёт"],
            ["💱 Обмен между счетами"],
            ["⬅️ Назад"]
        ],
        resize_keyboard=True
    )

def edit_last_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Дата", "Магазин"],
         ["Сумма", "Категория"],
         ["Способ оплаты"],
         ["⬅️ Назад"]],
        resize_keyboard=True
    )

def edit_income_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["Дата", "Источник"],
         ["Сумма", "Категория"],
         ["Счёт"],
         ["⬅️ Назад"]],
        resize_keyboard=True
    )

def accounts_kb(names, *, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    rows = [[n] for n in names]
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("Отмена")
    if tail:
        rows.append(tail)
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def categories_kb(*, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора категорий из сохраненных"""
    categories = get_categories_list()
    # Создаем кнопки по 2 в ряд для экономии места
    rows = []
    for i in range(0, len(categories), 2):
        row = [format_category_for_display(categories[i])]
        if i + 1 < len(categories):
            row.append(format_category_for_display(categories[i + 1]))
        rows.append(row)
    
    # Добавляем кнопки навигации
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def date_selection_kb(*, include_back=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора даты"""
    today = date.today()
    
    # Создаем кнопки с датами
    rows = []
    
    # Сегодняшняя дата
    today_str = today.strftime("%d.%m.%Y")
    rows.append([f"📅 Сегодня ({today_str})"])
    
    # Последние 7 дней
    recent_dates = []
    for i in range(1, 8):
        d = today - timedelta(days=i)
        recent_dates.append(d.strftime("%d.%m"))
    
    # Разбиваем на строки по 3 даты
    for i in range(0, len(recent_dates), 3):
        row = recent_dates[i:i+3]
        rows.append(row)
    
    # Добавляем кнопку "Календарь" и "Назад"
    tail = ["📆 Календарь"]
    if include_back:
        tail.append("⬅️ Назад")
    rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def calendar_kb(year: int = None, month: int = None) -> ReplyKeyboardMarkup:
    """Клавиатура календаря для выбора даты"""
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month
    
    # Создаем календарь
    import calendar
    
    # Заголовок с месяцем и годом
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    rows = []
    
    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    next_month = month + 1 if month < 12 else 1
    prev_year = year - 1 if month == 1 else year
    next_year = year + 1 if month == 12 else year
    
    nav_row = [f"◀️ {month_names[prev_month-1]}", f"{month_names[month-1]} {year}", f"{month_names[next_month-1]} ▶️"]
    rows.append(nav_row)
    
    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    rows.append(weekdays)
    
    # Дни месяца
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(" ")
            else:
                # Выделяем сегодняшний день
                today = date.today()
                if year == today.year and month == today.month and day == today.day:
                    week_row.append(f"🔸{day}")
                else:
                    week_row.append(str(day))
        rows.append(week_row)
    
    # Кнопки навигации
    rows.append(["⬅️ Назад"])
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def account_edit_menu_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для редактирования счета"""
    return ReplyKeyboardMarkup(
        [["💰 Сумма"], ["💱 Валюта"], ["⬅️ Назад"]],
        resize_keyboard=True
    )

def currency_selection_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора валюты"""
    return ReplyKeyboardMarkup(
        [["UAH", "USD", "EUR"], ["RUB", "PLN", "GBP"], ["⬅️ Назад"]],
        resize_keyboard=True
    )

def delete_confirmation_kb() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    return ReplyKeyboardMarkup(
        [["✅ Да, удалить"], ["❌ Отмена"], ["⬅️ Назад"]],
        resize_keyboard=True
    )

# Клавиатуры для пошагового добавления дохода
def income_add_amount_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода суммы дохода"""
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"], ["❌ Отмена"]],
        resize_keyboard=True
    )

def income_add_currency_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора валюты дохода"""
    return ReplyKeyboardMarkup(
        [["UAH", "USD", "EUR"], ["RUB", "PLN", "GBP"], ["⬅️ Назад", "❌ Отмена"]],
        resize_keyboard=True
    )

def income_add_source_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода источника дохода"""
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"], ["❌ Отмена"]],
        resize_keyboard=True
    )

def income_add_category_kb(*, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора категории дохода"""
    from app.categories import get_income_categories_list, format_category_for_display
    categories = get_income_categories_list()
    
    # Создаем кнопки по 2 в ряд для экономии места
    rows = []
    for i in range(0, len(categories), 2):
        row = [format_category_for_display(categories[i])]
        if i + 1 < len(categories):
            row.append(format_category_for_display(categories[i + 1]))
        rows.append(row)
    
    # Добавляем кнопки навигации
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("❌ Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def income_add_account_kb(accounts: list, *, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора счета для зачисления дохода"""
    rows = [[acc] for acc in accounts]
    
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("❌ Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def transfer_amount_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода суммы перевода"""
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"], ["❌ Отмена"]],
        resize_keyboard=True
    )

def transfer_confirm_kb() -> ReplyKeyboardMarkup:
    """Клавиатура подтверждения перевода"""
    return ReplyKeyboardMarkup(
        [["✅ Подтвердить"], ["❌ Отмена"], ["⬅️ Назад"]],
        resize_keyboard=True
    )

def export_menu_kb() -> ReplyKeyboardMarkup:
    """Клавиатура меню экспорта"""
    return ReplyKeyboardMarkup(
        [
            ["📄 Простой CSV", "📊 По месяцам"],
            ["📅 Текущий месяц", "📆 Последние 3 месяца"],
            ["💼 Балансы", "⬅️ Назад"]
        ],
        resize_keyboard=True
    )

def export_monthly_menu_kb() -> ReplyKeyboardMarkup:
    """Клавиатура выбора месяца для экспорта"""
    from datetime import date
    today = date.today()
    
    # Создаем кнопки с месяцами
    rows = []
    
    # Текущий месяц
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    current_month = f"{month_names[today.month - 1]} {today.year}"
    rows.append([f"📅 {current_month}"])
    
    # Последние 6 месяцев
    
    recent_months = []
    for i in range(1, 7):  # Последние 6 месяцев
        month_date = today.replace(day=1) - timedelta(days=i*30)
        month_name = month_names[month_date.month - 1]
        recent_months.append(f"{month_name} {month_date.year}")
    
    # Разбиваем на строки по 2 месяца
    for i in range(0, len(recent_months), 2):
        row = recent_months[i:i+2]
        rows.append(row)
    
    # Добавляем кнопку "Назад"
    rows.append(["⬅️ Назад"])
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def export_period_menu_kb() -> ReplyKeyboardMarkup:
    """Клавиатура выбора периода для экспорта"""
    return ReplyKeyboardMarkup(
        [
            ["📅 3 месяца", "📆 6 месяцев"],
            ["📊 12 месяцев", "⬅️ Назад"]
        ],
        resize_keyboard=True
    )

# Клавиатуры для пошагового добавления расхода
def expense_add_amount_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода суммы расхода"""
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"], ["❌ Отмена"]],
        resize_keyboard=True
    )

def expense_add_currency_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для выбора валюты расхода"""
    return ReplyKeyboardMarkup(
        [["UAH", "USD", "EUR"], ["RUB", "PLN", "GBP"], ["⬅️ Назад", "❌ Отмена"]],
        resize_keyboard=True
    )

def expense_add_merchant_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для ввода магазина расхода"""
    return ReplyKeyboardMarkup(
        [["⬅️ Назад"], ["❌ Отмена"]],
        resize_keyboard=True
    )

def expense_add_category_kb(*, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора категории расхода"""
    from app.categories import get_categories_list, format_category_for_display
    categories = get_categories_list()
    
    # Создаем кнопки по 2 в ряд для экономии места
    rows = []
    for i in range(0, len(categories), 2):
        row = [format_category_for_display(categories[i])]
        if i + 1 < len(categories):
            row.append(format_category_for_display(categories[i + 1]))
        rows.append(row)
    
    # Добавляем кнопки навигации
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("❌ Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def expense_add_account_kb(accounts: list, *, include_back=False, include_cancel=False) -> ReplyKeyboardMarkup:
    """Клавиатура для выбора счета для списания расхода"""
    rows = [[acc] for acc in accounts]
    
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("❌ Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
