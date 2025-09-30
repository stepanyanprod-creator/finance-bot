# app/speech.py
import os
import re
import subprocess
from datetime import date, timedelta

# OpenAI (>=1.x)
from openai import OpenAI

# ── ffmpeg: .oga/.ogg → .mp3 (mono, 16 kHz)
def ffmpeg_convert_to_mp3(in_path: str) -> str:
    out_path = in_path + ".mp3"
    cmd = ["ffmpeg", "-y", "-i", in_path, "-ac", "1", "-ar", "16000", out_path]
    # если ffmpeg ещё не в PATH — вернётся осмысленная ошибка
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path

# ── OpenAI STT (Whisper)
def transcribe_openai(file_path: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не задан")

    client = OpenAI(api_key=api_key)
    with open(file_path, "rb") as f:
        res = client.audio.transcriptions.create(model="whisper-1", file=f)
    return (res.text or "").strip()

# ── Примитивный парсер текста вида:
# "вчера rewe 12,30 eur категория groceries счёт Volksbank Debit"
def parse_spoken_purchase(text: str) -> dict:
    t = (text or "").strip()
    out = {
        "date": date.today().strftime("%Y-%m-%d"),
        "merchant": "",
        "total": 0.0,
        "currency": "",
        "category": "",
        "payment_method": "",
    }
    low = t.lower()

    # дата
    if "вчера" in low:
        out["date"] = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif "сегодня" in low:
        out["date"] = date.today().strftime("%Y-%m-%d")
    else:
        # Попробуем найти дату в тексте
        date_patterns = [
            r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})",  # 15.03.2024 или 15/03/24
            r"(\d{1,2})[./-](\d{1,2})",  # 15.03 (только день и месяц)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, t)
            if match:
                try:
                    if len(match.groups()) == 3:  # Полная дата
                        day, month, year = match.groups()
                        if len(year) == 2:  # Двузначный год
                            year = "20" + year
                        parsed_date = date(int(year), int(month), int(day))
                        
                        # Проверяем разумность года
                        current_year = date.today().year
                        if parsed_date.year < 2020 or parsed_date.year > current_year + 1:
                            parsed_date = parsed_date.replace(year=current_year)
                        
                        out["date"] = parsed_date.strftime("%Y-%m-%d")
                        break
                    elif len(match.groups()) == 2:  # Только день и месяц
                        day, month = match.groups()
                        current_year = date.today().year
                        parsed_date = date(current_year, int(month), int(day))
                        out["date"] = parsed_date.strftime("%Y-%m-%d")
                        break
                except ValueError:
                    continue

    # Проверяем, это доход или расход по ключевым словам
    income_keywords = [
        "получил", "заработал", "зарплата", "доход", "прибыль", "выплата", 
        "премия", "бонус", "подарок", "возврат", "компенсация", "дивиденды",
        "проценты", "аренда", "фриланс", "проект", "заказ", "консультация"
    ]
    
    expense_keywords = [
        "потратил", "купил", "заплатил", "расход", "покупка", "оплата",
        "чек", "чеков", "магазин", "ресторан", "кафе", "бензин", "топливо"
    ]
    
    is_income = any(keyword in low for keyword in income_keywords)
    is_expense = any(keyword in low for keyword in expense_keywords)
    
    # сумма + валюта (поддержка € $ ₴ и ISO, включая отрицательные суммы)
    # Ищем сумму перед валютой (поддерживаем русские названия валют)
    m = re.search(r"(-?\d+[.,]?\d*)\s*(eur|usd|uah|pln|gbp|₴|€|\$|евро|долларов|рублей|euro|dollars|руб)", t, re.IGNORECASE)
    if m:
        amount = float(m.group(1).replace(",", "."))
        cur_raw = m.group(2).lower()
        
        # Конвертируем в стандартные коды валют
        currency_map = {
            '€': 'EUR', '$': 'USD', '₴': 'UAH',
            'евро': 'EUR', 'euro': 'EUR',
            'долларов': 'USD', 'dollars': 'USD',
            'рублей': 'UAH', 'руб': 'UAH',  # Предполагаем, что рубли = UAH для Украины
            'eur': 'EUR', 'usd': 'USD', 'uah': 'UAH'
        }
        cur = currency_map.get(cur_raw, cur_raw.upper())
        
        # Если это доход, делаем сумму положительной
        if is_income and not is_expense:
            out["total"] = abs(amount)  # Всегда положительная для доходов
        # Если это расход, делаем сумму отрицательной
        elif is_expense and not is_income:
            out["total"] = -abs(amount)  # Всегда отрицательная для расходов
        else:
            # Если неясно или есть конфликт, оставляем как есть
            out["total"] = amount
            
        out["currency"] = cur

    # Автоматическое определение категории дохода (приоритет над парсингом "на")
    if is_income:
        # Зарплата (различные формы слова)
        if any(word in low for word in ["зарплат", "оклад", "выплат", "преми", "бонус"]):
            out["category"] = "Зарплата"
        # Фриланс
        elif any(word in low for word in ["фриланс", "проект", "заказ", "консультац", "разработк"]):
            out["category"] = "Фриланс"
        # Подарки
        elif any(word in low for word in ["подарок", "подарк"]):
            out["category"] = "Подарки"
        # Возвраты
        elif any(word in low for word in ["возврат", "компенсац", "кешбэк"]):
            out["category"] = "Возвраты"
        # Аренда
        elif any(word in low for word in ["аренд", "сдач"]):
            out["category"] = "Аренда"
        # Инвестиции
        elif any(word in low for word in ["дивиденд", "процент", "инвестиц"]):
            out["category"] = "Инвестиции"
        else:
            out["category"] = "Прочие доходы"
    
    # категория: "категория XXX" или "на XXX" (только если не определена автоматически)
    m = re.search(r"(категория|на)\s+([A-Za-zА-Яа-яёЁ \-]+)", t, re.IGNORECASE)
    if m and not out["category"]:  # Только если категория еще не определена
        out["category"] = m.group(2).strip()

    # платёжный счёт/карта
    m = re.search(r"(сч[её]т|карта)\s+([^\d,.;]+)", t, re.IGNORECASE)
    if m:
        out["payment_method"] = m.group(2).strip()

    # магазин: всё до числа, если сумма распознана
    if out["total"]:
        m = re.search(r"^(.*?)(\d+[.,]?\d*)", t)
        if m:
            cand = m.group(1)
            cand = re.sub(r"\b(вчера|сегодня|категория|карта|сч[её]т)\b.*$", "", cand, flags=re.IGNORECASE)
            out["merchant"] = cand.strip(" ,.-")
    else:
        out["merchant"] = (t.split(",")[0].split()[0] if t else "")

    return out
