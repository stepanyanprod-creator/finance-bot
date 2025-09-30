# storage.py — multi-user файловое хранилище
import os
import csv
import json
from datetime import datetime
from collections import OrderedDict

DATA_DIR = os.getenv("DATA_DIR", "data")

# ──────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНОЕ
# ──────────────────────────────────────────────────────────────────────────────
def _user_dir(user_id: int) -> str:
    d = os.path.join(DATA_DIR, str(user_id))
    os.makedirs(d, exist_ok=True)
    return d

def _csv_path(user_id: int) -> str:
    return os.path.join(_user_dir(user_id), "finance.csv")

def _balances_path(user_id: int) -> str:
    return os.path.join(_user_dir(user_id), "balances.json")

def _accounts_path(user_id: int) -> str:
    return os.path.join(_user_dir(user_id), "accounts.json")

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def _write_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

from app.utils import format_money as fmt_money

# ──────────────────────────────────────────────────────────────────────────────
# CSV
# ──────────────────────────────────────────────────────────────────────────────
CSV_FIELDS = ["date", "merchant", "total", "currency", "category", "payment_method", "source", "notes"]

def ensure_csv(user_id: int):
    path = _csv_path(user_id)
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()

def read_rows(user_id: int):
    path = _csv_path(user_id)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def append_row_csv(user_id: int, data: dict, source: str = ""):
    ensure_csv(user_id)
    row = OrderedDict()
    row["date"] = (data.get("date") or datetime.now().strftime("%Y-%m-%d"))
    row["merchant"] = data.get("merchant") or ""
    row["total"] = float(data.get("total") or 0)
    row["currency"] = (data.get("currency") or "").upper()
    row["category"] = data.get("category") or ""
    row["payment_method"] = data.get("payment_method") or ""
    row["source"] = source or ""
    row["notes"] = data.get("notes") or ""
    with open(_csv_path(user_id), "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writerow(row)

def undo_last_row(user_id: int):
    rows = read_rows(user_id)
    if not rows:
        return False
    rows = rows[:-1]
    ensure_csv(user_id)
    with open(_csv_path(user_id), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return True

def _rewrite_rows(user_id: int, rows):
    ensure_csv(user_id)
    with open(_csv_path(user_id), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def update_last_row(user_id: int, **changes):
    rows = read_rows(user_id)
    if not rows:
        raise ValueError("Нет записей")
    old = dict(rows[-1])
    new = dict(old)
    for k, v in changes.items():
        if k == "total":
            v = float(str(v).replace(",", "."))
        if k == "currency":
            v = (v or "").upper()
        new[k] = v
    rows[-1] = new
    _rewrite_rows(user_id, rows)
    return old, new

def update_row_from_end(user_id: int, n: int, **changes):
    rows = read_rows(user_id)
    if n <= 0 or n > len(rows):
        raise ValueError("Неверный индекс")
    idx = len(rows) - n
    old = dict(rows[idx])
    new = dict(old)
    for k, v in changes.items():
        if k == "total":
            v = float(str(v).replace(",", "."))
        if k == "currency":
            v = (v or "").upper()
        new[k] = v
    rows[idx] = new
    _rewrite_rows(user_id, rows)
    return old, new

# ──────────────────────────────────────────────────────────────────────────────
# БАЛАНСЫ (валюта/категория — старый функционал)
# ──────────────────────────────────────────────────────────────────────────────
def _load_balances(user_id: int):
    return _read_json(_balances_path(user_id), {})

def _save_balances(user_id: int, data: dict):
    _write_json(_balances_path(user_id), data)

def set_balance(user_id: int, data, currency: str = None, category: str = None):
    """Установить баланс. Может принимать словарь балансов или отдельные параметры."""
    if isinstance(data, dict):
        # Если передан словарь балансов, сохраняем его целиком
        _save_balances(user_id, data)
        return data
    else:
        # Старый формат для совместимости
        amount = data
        bal = _load_balances(user_id)
        key = f"{currency.upper()}" if not category else f"{category}@{currency.upper()}"
        bal[key] = float(amount)
        _save_balances(user_id, bal)
        return key, bal[key]

def get_balances(user_id: int):
    return _load_balances(user_id)

def dec_balance(user_id: int, amount: float, currency: str | None, category: str | None):
    bal = _load_balances(user_id)
    if not currency:
        return
    key1 = currency.upper()
    key2 = f"{(category or '')}@{currency.upper()}"
    # Если сумма отрицательная, то это расход, и мы уменьшаем баланс
    # Если сумма положительная, то это доход, и мы увеличиваем баланс
    for k in (key1, key2):
        if k in bal:
            bal[k] = float(bal[k]) - float(amount or 0)
    _save_balances(user_id, bal)

def rebalance_on_edit(user_id: int, old_row: dict, new_row: dict):
    def _num(x):
        try:
            return float(x)
        except:
            return 0.0
    old_cur = (old_row.get("currency") or "").upper()
    new_cur = (new_row.get("currency") or "").upper()
    old_cat = old_row.get("category") or None
    new_cat = new_row.get("category") or None
    old_total = _num(old_row.get("total", 0))
    new_total = _num(new_row.get("total", 0))

    # вернуть старую сумму (отменить предыдущее изменение)
    if old_cur:
        bal = _load_balances(user_id)
        for k in (old_cur, f"{(old_cat or '')}@{old_cur}"):
            if k in bal:
                bal[k] = float(bal[k]) + old_total
        _save_balances(user_id, bal)

    # применить новую сумму (отрицательная = расход, положительная = доход)
    if new_cur:
        bal = _load_balances(user_id)
        for k in (new_cur, f"{(new_cat or '')}@{new_cur}"):
            if k in bal:
                bal[k] = float(bal[k]) - new_total
        _save_balances(user_id, bal)

# ──────────────────────────────────────────────────────────────────────────────
# СЧЕТА (банковские/кошельки)
# ──────────────────────────────────────────────────────────────────────────────
def list_accounts(user_id: int) -> dict:
    return _read_json(_accounts_path(user_id), {})

def add_account(user_id: int, name: str, currency: str, amount: float = 0.0):
    name = name.strip()
    currency = (currency or "").upper()
    if not name or not currency:
        raise ValueError("name/currency пустые")
    acc = list_accounts(user_id)
    if name in acc:
        raise ValueError("Счёт с таким именем уже существует")
    acc[name] = {"currency": currency, "amount": float(amount)}
    _write_json(_accounts_path(user_id), acc)
    return name, acc[name]

def set_account_amount(user_id: int, name: str, amount: float):
    acc = list_accounts(user_id)
    if name not in acc:
        raise ValueError("Нет такого счёта")
    acc[name]["amount"] = float(amount)
    _write_json(_accounts_path(user_id), acc)
    return name, acc[name]

def dec_account(user_id: int, name: str, amount: float):
    acc = list_accounts(user_id)
    if name not in acc:
        raise ValueError("Нет такого счёта")
    # Если сумма отрицательная, то это расход, и мы уменьшаем баланс счета
    # Если сумма положительная, то это доход, и мы увеличиваем баланс счета
    acc[name]["amount"] = float(acc[name]["amount"]) - float(amount or 0)
    _write_json(_accounts_path(user_id), acc)

def inc_account(user_id: int, name: str, amount: float):
    """Увеличить баланс счёта (для доходов)"""
    acc = list_accounts(user_id)
    if name not in acc:
        raise ValueError("Нет такого счёта")
    acc[name]["amount"] = float(acc[name]["amount"]) + float(amount or 0)
    _write_json(_accounts_path(user_id), acc)

def delete_account(user_id: int, name: str):
    """Удалить счёт"""
    acc = list_accounts(user_id)
    if name not in acc:
        raise ValueError("Нет такого счёта")
    del acc[name]
    _write_json(_accounts_path(user_id), acc)
    return name

def update_account_currency(user_id: int, name: str, currency: str):
    """Обновить валюту счёта"""
    acc = list_accounts(user_id)
    if name not in acc:
        raise ValueError("Нет такого счёта")
    acc[name]["currency"] = (currency or "").upper()
    _write_json(_accounts_path(user_id), acc)
    return name, acc[name]

def find_accounts_by_currency(user_id: int, currency: str) -> list[str]:
    currency = (currency or "").upper()
    acc = list_accounts(user_id)
    return [n for n, v in acc.items() if (v.get("currency") or "").upper() == currency]

def format_accounts(user_id: int) -> str:
    acc = list_accounts(user_id)
    if not acc:
        return "📊 Счетов пока нет.\n\n💡 Добавьте первый счёт, чтобы начать отслеживать баланс!"
    
    lines = ["💼 <b>Ваши счета:</b>\n"]
    total_amounts = {}
    
    for name, v in acc.items():
        amount = float(v.get('amount', 0))
        currency = v.get('currency', '')
        
        # Группируем по валютам для подсчета общего баланса
        if currency not in total_amounts:
            total_amounts[currency] = 0
        total_amounts[currency] += amount
        
        # Красивое форматирование счета
        if amount >= 0:
            emoji = "💰"
        else:
            emoji = "💸"
            
        lines.append(f"{emoji} <b>{name}</b>\n   {amount:,.2f} {currency}\n")
    
    # Добавляем общий баланс по валютам
    if total_amounts:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("📈 <b>Общий баланс:</b>")
        for currency, total in total_amounts.items():
            if total >= 0:
                emoji = "💚"
            else:
                emoji = "❤️"
            lines.append(f"{emoji} {total:,.2f} {currency}")
    
    return "\n".join(lines)

def transfer_between_accounts(user_id: int, from_account: str, to_account: str, amount: float, second_amount: float = None):
    """Перевод денег между счетами"""
    acc = list_accounts(user_id)
    
    if from_account not in acc:
        raise ValueError(f"Счет-источник «{from_account}» не найден")
    if to_account not in acc:
        raise ValueError(f"Счет-получатель «{to_account}» не найден")
    if from_account == to_account:
        raise ValueError("Нельзя переводить на тот же счет")
    
    from_acc = acc[from_account]
    to_acc = acc[to_account]
    
    # Проверяем достаточность средств
    if float(from_acc["amount"]) < amount:
        raise ValueError(f"Недостаточно средств на счете «{from_account}». Доступно: {from_acc['amount']:.2f} {from_acc['currency']}")
    
    # Определяем валюты
    from_currency = from_acc["currency"]
    to_currency = to_acc["currency"]
    
    # Если валюты одинаковые, используем одну сумму
    if from_currency == to_currency:
        transfer_amount = amount
    else:
        # Если валюты разные, используем вторую сумму
        if second_amount is None:
            raise ValueError("Для разных валют необходимо указать сумму для счета-получателя")
        transfer_amount = second_amount
    
    # Выполняем перевод
    acc[from_account]["amount"] = float(acc[from_account]["amount"]) - amount
    acc[to_account]["amount"] = float(acc[to_account]["amount"]) + transfer_amount
    
    _write_json(_accounts_path(user_id), acc)
    
    # Записываем переводы в CSV для отображения в экспорте
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Запись списания с исходного счета
    from_transaction = {
        "date": current_date,
        "merchant": f"Перевод на {to_account}",
        "total": -amount,  # Отрицательная сумма для расхода
        "currency": from_currency,
        "category": "Банковские операции",
        "payment_method": from_account,
        "source": "transfer"
    }
    append_row_csv(user_id, from_transaction, source="transfer")
    
    # Запись зачисления на целевой счет
    to_transaction = {
        "date": current_date,
        "merchant": f"Перевод с {from_account}",
        "total": transfer_amount,  # Положительная сумма для дохода
        "currency": to_currency,
        "category": "Банковские операции",
        "payment_method": to_account,
        "source": "transfer"
    }
    append_row_csv(user_id, to_transaction, source="transfer")
    
    return {
        "from_account": from_account,
        "to_account": to_account,
        "from_amount": amount,
        "to_amount": transfer_amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "date": current_date
    }
