# app/services/enhanced_receipt_parser.py
import os
import io
import base64
import json
import datetime
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, ImageEnhance, ImageFilter

from app.logger import get_logger
from app.exceptions import ReceiptParsingError
from app.models import ReceiptData, ReceiptItem

load_dotenv()
logger = get_logger(__name__)

# Инициализация OpenAI клиента
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) if os.environ.get("OPENAI_API_KEY") else None


class ReceiptType(Enum):
    """Типы чеков"""
    GROCERY = "grocery"
    RESTAURANT = "restaurant"
    PHARMACY = "pharmacy"
    GAS_STATION = "gas_station"
    RETAIL = "retail"
    UNKNOWN = "unknown"


@dataclass
class ParsingResult:
    """Результат парсинга чека"""
    success: bool
    data: Optional[ReceiptData] = None
    confidence: float = 0.0
    receipt_type: ReceiptType = ReceiptType.UNKNOWN
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class EnhancedReceiptParser:
    """Улучшенный парсер чеков с множественными стратегиями"""
    
    def __init__(self):
        self.client = client
        if not self.client:
            logger.warning("OpenAI API key not found. Receipt parsing will be limited.")
    
    def parse_receipt(self, image_path: str, user_id: int = None) -> ParsingResult:
        """Основной метод парсинга чека"""
        try:
            # Предобработка изображения
            processed_image = self._preprocess_image(image_path)
            
            # Определение типа чека
            receipt_type = self._detect_receipt_type(processed_image)
            
            # Парсинг с помощью OpenAI
            if self.client:
                parsed_data = self._parse_with_openai(processed_image, receipt_type)
            else:
                parsed_data = self._parse_with_ocr_fallback(processed_image)
            
            # Валидация и улучшение данных
            validated_data = self._validate_and_enhance(parsed_data, receipt_type)
            
            # Определение категории на основе содержимого
            category = self._suggest_category(validated_data, receipt_type)
            validated_data.category = category
            
            return ParsingResult(
                success=True,
                data=validated_data,
                confidence=self._calculate_confidence(validated_data),
                receipt_type=receipt_type
            )
            
        except Exception as e:
            logger.error(f"Error parsing receipt: {e}")
            return ParsingResult(
                success=False,
                errors=[str(e)]
            )
    
    def _preprocess_image(self, image_path: str) -> str:
        """Предобработка изображения для лучшего распознавания"""
        try:
            # Открываем изображение
            image = Image.open(image_path).convert("RGB")
            
            # Улучшаем контраст
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Улучшаем резкость
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Применяем фильтр для удаления шума
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Изменяем размер если нужно
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Конвертируем в base64
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=95, optimize=True)
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            # Возвращаем оригинальное изображение в base64
            with open(image_path, "rb") as f:
                return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    
    def _detect_receipt_type(self, image_base64: str) -> ReceiptType:
        """Определение типа чека по изображению"""
        if not self.client:
            return ReceiptType.UNKNOWN
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": "Определи тип чека по изображению. Выбери один из: grocery, restaurant, pharmacy, gas_station, retail, unknown"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Какой это тип чека?"},
                            {"type": "image_url", "image_url": {"url": image_base64, "detail": "low"}}
                        ]
                    }
                ],
                max_tokens=50
            )
            
            result = response.choices[0].message.content.lower().strip()
            
            # Маппинг результатов
            type_mapping = {
                "grocery": ReceiptType.GROCERY,
                "restaurant": ReceiptType.RESTAURANT,
                "pharmacy": ReceiptType.PHARMACY,
                "gas_station": ReceiptType.GAS_STATION,
                "retail": ReceiptType.RETAIL,
            }
            
            for key, receipt_type in type_mapping.items():
                if key in result:
                    return receipt_type
            
            return ReceiptType.UNKNOWN
            
        except Exception as e:
            logger.error(f"Error detecting receipt type: {e}")
            return ReceiptType.UNKNOWN
    
    def _parse_with_openai(self, image_base64: str, receipt_type: ReceiptType) -> Dict[str, Any]:
        """Парсинг с помощью OpenAI GPT-4 Vision"""
        
        # Улучшенная схема для function calling
        tools = [{
            "type": "function",
            "function": {
                "name": "submit_receipt",
                "description": "Извлеченные данные с чека",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Дата покупки в формате YYYY-MM-DD"
                        },
                        "merchant": {
                            "type": "string",
                            "description": "Название магазина или торговой точки"
                        },
                        "total": {
                            "type": "number",
                            "description": "Общая сумма покупки"
                        },
                        "currency": {
                            "type": "string",
                            "description": "Валюта (EUR, USD, UAH, etc.)"
                        },
                        "items": {
                            "type": "array",
                            "description": "Список товаров",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Название товара"},
                                    "quantity": {"type": "number", "description": "Количество"},
                                    "price": {"type": "number", "description": "Цена за единицу"},
                                    "total": {"type": "number", "description": "Общая стоимость позиции"}
                                },
                                "required": ["name", "quantity", "price"]
                            }
                        },
                        "payment_method": {
                            "type": "string",
                            "description": "Способ оплаты (наличные, карта, etc.)"
                        },
                        "tax_amount": {
                            "type": "number",
                            "description": "Сумма налога"
                        },
                        "discount_amount": {
                            "type": "number",
                            "description": "Сумма скидки"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Дополнительные заметки"
                        }
                    },
                    "required": ["date", "merchant", "total", "currency", "items"]
                }
            }
        }]
        
        # Контекстная инструкция в зависимости от типа чека
        context_instructions = {
            ReceiptType.GROCERY: "Это чек из продуктового магазина. Обрати особое внимание на товары и их категории.",
            ReceiptType.RESTAURANT: "Это чек из ресторана или кафе. Обрати внимание на блюда и напитки.",
            ReceiptType.PHARMACY: "Это чек из аптеки. Обрати внимание на лекарства и медицинские товары.",
            ReceiptType.GAS_STATION: "Это чек с заправки. Обрати внимание на количество топлива и цену за литр.",
            ReceiptType.RETAIL: "Это чек из розничного магазина. Обрати внимание на товары и их описания.",
            ReceiptType.UNKNOWN: "Это чек неизвестного типа. Извлеки все доступные данные."
        }
        
        current_year = datetime.date.today().year
        system_prompt = f"""
        Ты эксперт по анализу кассовых чеков. {context_instructions.get(receipt_type, "")}
        
        ВАЖНО:
        1. Извлекай ТОЛЬКО данные, которые четко видны на чеке
        2. ДАТА: Внимательно ищи дату на чеке. Обычно она в формате ДД.ММ.ГГГГ, ДД/ММ/ГГГГ или ГГГГ-ММ-ДД. 
           КРИТИЧЕСКИ ВАЖНО: 
           - Если год не указан или указан неправильно (не {current_year-1}, {current_year} или {current_year+1}), используй текущий год {current_year}
           - Если видишь только день и месяц (например, 15.03), добавляй год {current_year}
           - Если дата не найдена - используй сегодняшнюю дату в формате ГГГГ-ММ-ДД
        3. Если валюта не указана, попробуй определить по символам (€, $, ₴)
        4. Для товаров указывай точные названия
        5. ВАЖНО: отвечай ТОЛЬКО через вызов функции submit_receipt
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "submit_receipt"}},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Проанализируй этот чек и извлеки все данные."},
                        {"type": "image_url", "image_url": {"url": image_base64, "detail": "high"}}
                    ]}
                ]
            )
            
            message = response.choices[0].message
            
            if not message.tool_calls:
                raise ReceiptParsingError("Модель не вернула вызов функции")
            
            tool_call = message.tool_calls[0]
            if tool_call.function.name != "submit_receipt":
                raise ReceiptParsingError(f"Неожиданная функция: {tool_call.function.name}")
            
            data = json.loads(tool_call.function.arguments or "{}")
            return data
            
        except Exception as e:
            logger.error(f"Error in OpenAI parsing: {e}")
            raise ReceiptParsingError(f"Ошибка парсинга с OpenAI: {e}")
    
    def _parse_with_ocr_fallback(self, image_base64: str) -> Dict[str, Any]:
        """Fallback парсинг без OpenAI (базовая реализация)"""
        # Здесь можно добавить OCR библиотеку типа Tesseract
        # Пока возвращаем базовую структуру
        return {
            "date": datetime.date.today().isoformat(),
            "merchant": "Неизвестный магазин",
            "total": 0.0,
            "currency": "EUR",
            "items": [],
            "payment_method": "",
            "notes": "Парсинг без OpenAI - данные не извлечены"
        }
    
    def _validate_and_enhance(self, data: Dict[str, Any], receipt_type: ReceiptType) -> ReceiptData:
        """Валидация и улучшение извлеченных данных"""
        
        # Валидация даты - улучшенная обработка
        date_str = data.get("date", "")
        if not date_str:
            date_str = datetime.date.today().isoformat()
        else:
            # Попробуем исправить дату если она в неправильном формате
            date_str = self._normalize_date(date_str)
            if not self._is_valid_date(date_str):
                date_str = datetime.date.today().isoformat()
        
        # Валидация суммы
        total = self._parse_amount(data.get("total", 0))
        
        # Валидация валюты
        currency = self._normalize_currency(data.get("currency", "EUR"))
        
        # Обработка товаров
        items = []
        for item_data in data.get("items", []):
            try:
                item = ReceiptItem(
                    name=str(item_data.get("name", "")).strip(),
                    qty=float(item_data.get("quantity", 1)),
                    price=float(item_data.get("price", 0))
                )
                if item.name:  # Добавляем только товары с названием
                    items.append(item)
            except (ValueError, TypeError):
                continue
        
        # Проверка математики убрана - часто не совпадает из-за скидок, налогов и т.д.
        
        return ReceiptData(
            date=date_str,
            merchant=str(data.get("merchant", "")).strip(),
            total=total,
            currency=currency,
            category="",  # Будет определена позже
            payment_method=str(data.get("payment_method", "")).strip(),
            items=items,
            notes=str(data.get("notes", "")).strip()
        )
    
    def _suggest_category(self, receipt_data: ReceiptData, receipt_type: ReceiptType) -> str:
        """Предложение категории на основе содержимого чека"""
        
        # Базовые категории по типу чека
        type_categories = {
            ReceiptType.GROCERY: "Продукты",
            ReceiptType.RESTAURANT: "Рестораны",
            ReceiptType.PHARMACY: "Здоровье",
            ReceiptType.GAS_STATION: "Транспорт",
            ReceiptType.RETAIL: "Расходы"
        }
        
        base_category = type_categories.get(receipt_type, "Расходы")
        
        # Анализ товаров для более точной категоризации
        if receipt_data.items:
            item_names = " ".join(item.name.lower() for item in receipt_data.items)
            
            # Ключевые слова для категорий
            category_keywords = {
                "Продукты": ["хлеб", "молоко", "мясо", "овощи", "фрукты", "сыр", "йогурт"],
                "Напитки": ["вода", "сок", "кофе", "чай", "пиво", "вино", "напиток"],
                "Сладости": ["шоколад", "конфеты", "печенье", "торт", "мороженое"],
                "Здоровье": ["лекарство", "витамины", "таблетки", "крем", "шампунь"],
                "Транспорт": ["бензин", "дизель", "топливо", "парковка"],
                "Одежда": ["рубашка", "брюки", "платье", "обувь", "куртка"],
                "Электроника": ["телефон", "компьютер", "наушники", "кабель"]
            }
            
            for category, keywords in category_keywords.items():
                if any(keyword in item_names for keyword in keywords):
                    return category
        
        return base_category
    
    def _calculate_confidence(self, receipt_data: ReceiptData) -> float:
        """Расчет уверенности в правильности парсинга"""
        confidence = 0.0
        
        # Базовая уверенность
        if receipt_data.merchant:
            confidence += 0.3
        if receipt_data.total > 0:
            confidence += 0.3
        if receipt_data.items:
            confidence += 0.2
        if receipt_data.date:
            confidence += 0.1
        if receipt_data.currency:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _normalize_date(self, date_str: str) -> str:
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
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Проверка валидности даты"""
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def _parse_amount(self, amount: Any) -> float:
        """Парсинг суммы (включая отрицательные значения)"""
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            if isinstance(amount, str):
                # Удаляем все кроме цифр, точек, запятых и знака минус
                cleaned = re.sub(r'[^\d.,-]', '', amount)
                cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _normalize_currency(self, currency: str) -> str:
        """Нормализация валюты"""
        if not currency:
            return "EUR"
        
        currency = currency.upper().strip()
        
        # Маппинг символов валют
        symbol_mapping = {
            "€": "EUR",
            "$": "USD",
            "₴": "UAH",
            "£": "GBP",
            "₽": "RUB"
        }
        
        for symbol, code in symbol_mapping.items():
            if symbol in currency:
                return code
        
        # Проверка на известные коды валют
        known_currencies = ["EUR", "USD", "UAH", "GBP", "RUB", "PLN", "CZK"]
        if currency in known_currencies:
            return currency
        
        return "EUR"  # По умолчанию


# Функция для обратной совместимости
def parse_receipt(image_path: str) -> dict:
    """Функция для обратной совместимости со старым API"""
    parser = EnhancedReceiptParser()
    result = parser.parse_receipt(image_path)
    
    if result.success and result.data:
        # Конвертируем ReceiptData в старый формат
        return {
            "date": result.data.date,
            "merchant": result.data.merchant,
            "total": result.data.total,
            "currency": result.data.currency,
            "category": result.data.category,
            "payment_method": result.data.payment_method,
            "items": [
                {
                    "name": item.name,
                    "qty": item.qty,
                    "price": item.price
                }
                for item in result.data.items
            ],
            "notes": result.data.notes
        }
    else:
        raise ReceiptParsingError(f"Ошибка парсинга: {', '.join(result.errors)}")
