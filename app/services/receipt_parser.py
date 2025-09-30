# receipt_parser.py
import os, io, base64, json, datetime
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# --- JSON-схема результата через function calling ---
TOOLS = [{
    "type": "function",
    "function": {
        "name": "submit_receipt",
        "description": "Нормализованные поля чека",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "merchant": {"type": "string"},
                "total": {"type": "number"},
                "currency": {"type": "string"},
                "category": {"type": "string"},
                "payment_method": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "qty": {"type": "number"},
                            "price": {"type": "number"}
                        },
                        "required": ["name","qty","price"]
                    }
                },
                "notes": {"type": "string"}
            },
            "required": ["date","merchant","total","currency","items"]
        }
    }
}]

SYSTEM = (
    "Ты парсер кассовых чеков. Проанализируй изображение чека и ВЫЗОВИ функцию "
    "`submit_receipt` с аргументами, соответствующими схеме. Никакого обычного текста, "
    "только вызов функции."
)

current_year = datetime.date.today().year
USER_INSTRUCTION = (
    f"Извлеки поля: date (YYYY-MM-DD), merchant, total, currency, category, "
    f"payment_method и items (name, qty, price). Если чего-то нет — ставь пустую строку или 0. "
    f"ВАЖНО для даты: если год не указан или неправильный (не {current_year-1}, {current_year} или {current_year+1}), "
    f"используй текущий год {current_year}. Если видишь только день и месяц, добавляй год {current_year}. "
    f"Верни результат ИСКЛЮЧИТЕЛЬНО через вызов функции submit_receipt."
)

def _jpeg_base64(path: str, max_side: int = 2000, quality: int = 85) -> str:
    """Открыть, при необходимости ужать и вернуть data-url JPEG base64."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        im = im.resize((int(w*scale), int(h*scale)))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

def _call_model(data_url: str):
    # Первый вызов: просим модель сразу сделать tool call
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        tools=TOOLS,
        tool_choice={"type": "function", "function": {"name": "submit_receipt"}},
        messages=[  # system + user (text+image)
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": USER_INSTRUCTION},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
            ]}
        ],
    )
    return resp

def parse_receipt(image_path: str) -> dict:
    data_url = _jpeg_base64(image_path)

    # 1) Пытаемся получить tool_call
    resp = _call_model(data_url)
    msg = resp.choices[0].message

    # Если почему-то пришёл обычный текст — делаем повтор с ещё более строгой инструкцией
    if not getattr(msg, "tool_calls", None):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            tools=TOOLS,
            tool_choice={"type": "function", "function": {"name": "submit_receipt"}},
            messages=[
                {"role": "system", "content": SYSTEM + " ВАЖНО: нельзя отвечать текстом, только function call."},
                {"role": "user", "content": [
                    {"type": "text", "text": USER_INSTRUCTION + " Повтори строго как function call."},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
                ]}
            ],
        )
        msg = resp.choices[0].message

    if not getattr(msg, "tool_calls", None):
        raise ValueError("Модель не вернула вызов функции (tool_call).")

    tool_call = msg.tool_calls[0]
    if tool_call.function.name != "submit_receipt":
        raise ValueError(f"Неожиданная функция: {tool_call.function.name}")

    # Аргументы функции — это СТРОГО JSON-строка. Её безопасно json.loads.
    try:
        data = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        raise ValueError("Модель вернула невалидные arguments для function call.")

    # Подстраховки, чтобы строка точно записалась в CSV
    data.setdefault("date", datetime.date.today().isoformat())
    
    # Нормализуем дату с улучшенной обработкой года
    if data.get("date"):
        data["date"] = _normalize_date(data["date"])
    
    data.setdefault("merchant", "")
    data.setdefault("total", 0)
    data.setdefault("currency", "EUR")
    data.setdefault("category", "")
    data.setdefault("payment_method", "")
    data.setdefault("items", [])
    data.setdefault("notes", "")

    # Типы
    if not isinstance(data.get("items"), list):
        data["items"] = []
    if not isinstance(data.get("total"), (int, float)):
        # иногда модель может прислать строку — аккуратно привести
        try:
            data["total"] = float(str(data["total"]).replace(",", "."))
        except Exception:
            data["total"] = 0.0

    return data

def _normalize_date(date_str: str) -> str:
    """Нормализация даты в формат YYYY-MM-DD с улучшенной обработкой года"""
    if not date_str:
        return datetime.date.today().isoformat()
    
    date_str = str(date_str).strip()
    current_year = datetime.date.today().year
    
    # Попробуем различные форматы дат
    date_formats = [
        "%Y-%m-%d",      # 2024-01-15
        "%d.%m.%Y",      # 15.01.2024
        "%d/%m/%Y",      # 15/01/2024
        "%d-%m-%Y",      # 15-01-2024
        "%Y.%m.%d",      # 2024.01.15
        "%Y/%m/%d",      # 2024/01/15
        "%d.%m.%y",      # 15.01.24
        "%d/%m/%y",      # 15/01/24
        "%d.%m.%Y",      # 15.1.2024 (без ведущих нулей)
        "%d/%m/%Y",      # 15/1/2024
        "%d-%m-%Y",      # 15-1-2024
        "%Y-%m-%d",      # 2024-1-15
        "%d.%m",         # 15.03 (только день и месяц)
        "%d/%m",         # 15/03
        "%d-%m",         # 15-03
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.datetime.strptime(date_str, fmt).date()
            
            # Если формат не содержит год (только день и месяц)
            if fmt in ["%d.%m", "%d/%m", "%d-%m"]:
                parsed_date = parsed_date.replace(year=current_year)
            
            # Проверяем разумность года
            if parsed_date.year < 2020 or parsed_date.year > current_year + 1:
                # Если год неправильный, заменяем на текущий
                parsed_date = parsed_date.replace(year=current_year)
            
            return parsed_date.isoformat()
        except ValueError:
            continue
    
    # Если не удалось распарсить, возвращаем сегодняшнюю дату
    return datetime.date.today().isoformat()
