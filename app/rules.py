# app/rules.py
import os
import json
from typing import List, Dict, Any, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Путь к rules.json для конкретного пользователя
# ──────────────────────────────────────────────────────────────────────────────
def _rules_path(user_id: int) -> str:
    # файлы лежат в data/<user_id>/rules.json
    base = os.path.join("data", str(user_id))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "rules.json")

# ──────────────────────────────────────────────────────────────────────────────
# Загрузка / сохранение правил
# ──────────────────────────────────────────────────────────────────────────────
def load_rules(user_id: int) -> List[Dict[str, Any]]:
    """Загрузить правила пользователя. Если файла ещё нет — вернуть [].
    Как мягкий fallback: если у пользователя нет своего файла, а в корне
    лежит общий rules.json — вернём его содержимое (не записывая)."""
    p = _rules_path(user_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    # fallback на общий rules.json в корне проекта (необязательный)
    if os.path.exists("rules.json"):
        try:
            with open("rules.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_rules(user_id: int, rules: List[Dict[str, Any]]) -> None:
    """Сохранить правила пользователя в data/<uid>/rules.json."""
    p = _rules_path(user_id)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rules or [], f, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────────────────────────────────────────
# Сопоставление транзакции правилам
# ──────────────────────────────────────────────────────────────────────────────
def _str(x: Any) -> str:
    return (x or "").strip()

def _num(x: Any) -> float:
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0

def _contains_any(haystack: str, needles: List[str]) -> bool:
    low = haystack.lower()
    return any(n.strip().lower() in low for n in needles if str(n).strip())

def _match_rule(rule: Dict[str, Any], tx: Dict[str, Any]) -> bool:
    """Проверяем, подходит ли транзакция под правило."""
    match = rule.get("match", {}) or {}

    merchant = _str(tx.get("merchant"))
    item_text = ""
    # Если парсер чеков кладёт позиции в items (list[dict]), соберём текст
    items = tx.get("items")
    if isinstance(items, list):
        parts = []
        for it in items:
            # попробуем 'name'/'title'/'desc'
            for k in ("name", "title", "desc", "description"):
                if it and isinstance(it, dict) and it.get(k):
                    parts.append(str(it.get(k)))
                    break
        item_text = " ".join(parts)

    currency = _str(tx.get("currency")).upper()
    payment = _str(tx.get("payment_method"))
    total = _num(tx.get("total"))

    # merchant_contains: [..]
    merch_needles = match.get("merchant_contains")
    if merch_needles:
        if not _contains_any(merchant, merch_needles):
            return False

    # item_contains: [..]
    item_needles = match.get("item_contains")
    if item_needles:
        if not _contains_any(item_text, item_needles):
            return False

    # currency_is: "EUR"
    cur_is = match.get("currency_is")
    if cur_is:
        if currency != str(cur_is).strip().upper():
            return False

    # payment_is: "Revolut"
    pay_is = match.get("payment_is")
    if pay_is:
        # точное совпадение по названию счёта/способу
        if payment.lower() != str(pay_is).strip().lower():
            return False

    # total_min / total_max
    tmin = match.get("total_min")
    if tmin is not None and total < _num(tmin):
        return False
    tmax = match.get("total_max")
    if tmax is not None and total > _num(tmax):
        return False

    return True

def apply_category_rules(
    tx: Dict[str, Any],
    rules: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """Возвращает категорию первой подходящей записи из rules.
    Если rules не переданы — пробуем fallback на общий rules.json (в корне).
    Валидирует, что возвращаемая категория существует в стандартных категориях."""
    from app.categories import validate_and_normalize_category
    
    rules_list: List[Dict[str, Any]] = rules if isinstance(rules, list) else []
    if not rules_list and os.path.exists("rules.json"):
        try:
            with open("rules.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    rules_list = data
        except Exception:
            pass

    for r in rules_list:
        if _match_rule(r, tx):
            cat = _str(r.get("category"))
            if cat:
                # Валидируем и нормализуем категорию
                validated_cat = validate_and_normalize_category(cat)
                if validated_cat:
                    return validated_cat
    return None
