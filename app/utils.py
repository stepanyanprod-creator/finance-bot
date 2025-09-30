# app/utils.py
from telegram import Update
from typing import Union
import re


def get_user_id(update: Update) -> int:
    """Получить ID пользователя из update"""
    return update.effective_user.id


def format_money(amount: Union[int, float, str], currency: str) -> str:
    """Форматировать денежную сумму"""
    try:
        value = float(amount or 0)
    except (ValueError, TypeError):
        value = 0.0
    return f"{value:.2f} {currency or ''}".strip()


def parse_amount(text: str) -> float:
    """Парсить сумму из текста"""
    try:
        return float(str(text).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def normalize_currency(currency: str) -> str:
    """Нормализовать валюту"""
    if not currency:
        return ""
    
    currency = currency.upper().strip()
    # Заменяем символы валют на ISO коды
    replacements = {
        "€": "EUR",
        "$": "USD", 
        "₴": "UAH",
        "£": "GBP",
        "₽": "RUB"
    }
    
    for symbol, code in replacements.items():
        if symbol in currency:
            currency = currency.replace(symbol, code)
    
    return currency


def validate_date_format(date_str: str) -> bool:
    """Проверить формат даты YYYY-MM-DD"""
    try:
        from datetime import datetime
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def clean_text(text: str) -> str:
    """Очистить текст от лишних символов"""
    if not text:
        return ""
    return text.strip()


def extract_currency_from_text(text: str) -> tuple[float, str]:
    """Извлечь сумму и валюту из текста"""
    # Паттерн для поиска суммы и валюты (включая отрицательные суммы)
    pattern = r"(-?\d+[.,]?\d*)\s*(eur|usd|uah|pln|gbp|rub|₴|€|\$|£|₽)"
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        amount = parse_amount(match.group(1))
        currency = normalize_currency(match.group(2))
        return amount, currency
    
    return 0.0, ""


def safe_int(value: Union[str, int, None]) -> int:
    """Безопасно преобразовать в int"""
    try:
        return int(value) if value is not None else 0
    except (ValueError, TypeError):
        return 0


def safe_float(value: Union[str, int, float, None]) -> float:
    """Безопасно преобразовать в float"""
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до максимальной длины"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def is_valid_account_name(name: str) -> bool:
    """Проверить валидность имени счета"""
    if not name or not name.strip():
        return False
    # Имя не должно содержать специальные символы
    return not re.search(r'[<>:"/\\|?*]', name.strip())


def generate_rule_id(existing_rules: list) -> int:
    """Генерировать новый ID для правила"""
    used_ids = {int(rule.get("id", 0)) for rule in existing_rules if rule.get("id")}
    rule_id = 1
    while rule_id in used_ids:
        rule_id += 1
    return rule_id
