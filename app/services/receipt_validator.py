# app/services/receipt_validator.py
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date

from app.logger import get_logger
from app.models import ReceiptData, ReceiptItem
from app.exceptions import ValidationError

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    confidence_score: float


class ReceiptValidator:
    """Валидатор для данных чеков"""
    
    def __init__(self):
        self.currency_symbols = {"€", "$", "₴", "£", "₽", "¥"}
        self.currency_codes = {"EUR", "USD", "UAH", "GBP", "RUB", "JPY", "PLN", "CZK"}
        
        # Паттерны для валидации
        self.date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        # Добавлены немецкие символы: ä, ö, ü, ß, Ä, Ö, Ü
        self.merchant_pattern = re.compile(r'^[a-zA-Zа-яА-ЯäöüßÄÖÜ0-9\s\-\.&]+$', re.IGNORECASE)
        self.amount_pattern = re.compile(r'^\d+(\.\d{1,2})?$')
    
    def validate_receipt(self, receipt_data: ReceiptData) -> ValidationResult:
        """Полная валидация данных чека"""
        errors = []
        warnings = []
        suggestions = []
        
        # Валидация основных полей
        self._validate_date(receipt_data.date, errors, warnings)
        self._validate_merchant(receipt_data.merchant, errors, warnings)
        self._validate_total(receipt_data.total, errors, warnings)
        self._validate_currency(receipt_data.currency, errors, warnings)
        self._validate_items(receipt_data.items, errors, warnings)
        
        # Валидация логических связей
        self._validate_logical_consistency(receipt_data, errors, warnings, suggestions)
        
        # Расчет уверенности
        confidence_score = self._calculate_confidence(receipt_data, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            confidence_score=confidence_score
        )
    
    def _validate_date(self, date_str: str, errors: List[str], warnings: List[str]):
        """Валидация даты"""
        if not date_str:
            errors.append("Дата не указана")
            return
        
        if not self.date_pattern.match(date_str):
            errors.append(f"Неверный формат даты: {date_str}")
            return
        
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            
            # Проверка на будущую дату
            if parsed_date > today:
                errors.append(f"Дата в будущем: {date_str}")
            
            # Проверка на слишком старую дату
            if (today - parsed_date).days > 365:
                warnings.append(f"Очень старая дата: {date_str}")
            
            # Проверка на сегодняшнюю дату
            if parsed_date == today:
                warnings.append("Дата покупки - сегодня")
                
        except ValueError:
            errors.append(f"Некорректная дата: {date_str}")
    
    def _validate_merchant(self, merchant: str, errors: List[str], warnings: List[str]):
        """Валидация названия магазина"""
        if not merchant or not merchant.strip():
            errors.append("Название магазина не указано")
            return
        
        merchant = merchant.strip()
        
        if len(merchant) < 2:
            errors.append("Название магазина слишком короткое")
        
        if len(merchant) > 100:
            warnings.append("Название магазина очень длинное")
        
        if not self.merchant_pattern.match(merchant):
            warnings.append(f"Название магазина содержит необычные символы: {merchant}")
        
        # Проверка на подозрительные названия
        suspicious_names = ["тест", "test", "неизвестно", "unknown", "магазин", "store", "geschäft", "laden"]
        if merchant.lower() in suspicious_names:
            warnings.append(f"Подозрительное название магазина: {merchant}")
    
    def _validate_total(self, total: float, errors: List[str], warnings: List[str]):
        """Валидация общей суммы"""
        if total is None:
            errors.append("Сумма не указана")
            return
        
        if not isinstance(total, (int, float)):
            errors.append(f"Сумма должна быть числом: {total}")
            return
        
        if total < 0:
            errors.append(f"Отрицательная сумма: {total}")
        
        if total == 0:
            warnings.append("Сумма равна нулю")
        
        if total > 10000:
            warnings.append(f"Очень большая сумма: {total}")
        
        # Проверка на разумность суммы
        if 0 < total < 0.01:
            warnings.append(f"Очень маленькая сумма: {total}")
    
    def _validate_currency(self, currency: str, errors: List[str], warnings: List[str]):
        """Валидация валюты"""
        if not currency or not currency.strip():
            errors.append("Валюта не указана")
            return
        
        currency = currency.strip().upper()
        
        if currency not in self.currency_codes:
            warnings.append(f"Неизвестная валюта: {currency}")
        
        # Проверка на смешанные символы
        if any(symbol in currency for symbol in self.currency_symbols):
            if len(currency) > 3:
                warnings.append(f"Валюта содержит символы и код: {currency}")
    
    def _validate_items(self, items: List[ReceiptItem], errors: List[str], warnings: List[str]):
        """Валидация товаров"""
        if not items:
            warnings.append("Список товаров пуст")
            return
        
        if len(items) > 100:
            warnings.append(f"Слишком много товаров: {len(items)}")
        
        for i, item in enumerate(items):
            self._validate_single_item(item, i, errors, warnings)
    
    def _validate_single_item(self, item: ReceiptItem, index: int, errors: List[str], warnings: List[str]):
        """Валидация отдельного товара"""
        if not item.name or not item.name.strip():
            errors.append(f"Товар #{index + 1}: название не указано")
        
        if item.qty is None or item.qty <= 0:
            errors.append(f"Товар #{index + 1}: некорректное количество: {item.qty}")
        
        if item.price is None or item.price < 0:
            errors.append(f"Товар #{index + 1}: некорректная цена: {item.price}")
        
        # Проверка на разумность цен
        if item.price and item.price > 1000:
            warnings.append(f"Товар #{index + 1}: очень высокая цена: {item.price}")
        
        # Проверка на дубликаты
        if len(item.name) < 3:
            warnings.append(f"Товар #{index + 1}: очень короткое название: {item.name}")
    
    def _validate_logical_consistency(self, receipt_data: ReceiptData, errors: List[str], warnings: List[str], suggestions: List[str]):
        """Валидация логической согласованности данных"""
        
        # Проверка суммы товаров убрана - часто не совпадает из-за скидок, налогов и т.д.
        
        # Проверка дубликатов товаров убрана - повторение товаров в чеке нормально
        
        # Проверка на подозрительные паттерны
        self._check_suspicious_patterns(receipt_data, warnings, suggestions)
    
    def _check_suspicious_patterns(self, receipt_data: ReceiptData, warnings: List[str], suggestions: List[str]):
        """Проверка на подозрительные паттерны"""
        
        # Проверка на тестовые данные
        if receipt_data.merchant.lower() in ["test", "тест", "example", "пример"]:
            warnings.append("Возможные тестовые данные")
        
        # Проверка на одинаковые цены товаров
        if receipt_data.items and len(receipt_data.items) > 1:
            prices = [item.price for item in receipt_data.items if item.price]
            if len(set(prices)) == 1 and len(prices) > 2:
                warnings.append("Все товары имеют одинаковую цену")
        
        # Проверка на круглые суммы
        if receipt_data.total > 0 and receipt_data.total % 10 == 0:
            suggestions.append("Сумма является круглым числом - проверьте корректность")
        
        # Проверка на необычно большое количество одного товара
        if receipt_data.items:
            for item in receipt_data.items:
                if item.qty and item.qty > 50:
                    warnings.append(f"Необычно большое количество товара '{item.name}': {item.qty}")
    
    def _calculate_confidence(self, receipt_data: ReceiptData, errors: List[str], warnings: List[str]) -> float:
        """Расчет уверенности в корректности данных"""
        confidence = 1.0
        
        # Штрафы за ошибки
        confidence -= len(errors) * 0.3
        
        # Штрафы за предупреждения
        confidence -= len(warnings) * 0.1
        
        # Бонусы за качественные данные
        if receipt_data.merchant and len(receipt_data.merchant) > 3:
            confidence += 0.1
        
        if receipt_data.items and len(receipt_data.items) > 0:
            confidence += 0.1
        
        if receipt_data.total > 0:
            confidence += 0.1
        
        # Проверка на логическую согласованность
        if receipt_data.items:
            calculated_total = sum(item.qty * item.price for item in receipt_data.items)
            if abs(receipt_data.total - calculated_total) < 0.01:
                confidence += 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def suggest_corrections(self, receipt_data: ReceiptData) -> Dict[str, Any]:
        """Предложения по исправлению данных"""
        suggestions = {}
        
        # Исправление даты
        if not receipt_data.date:
            suggestions["date"] = date.today().isoformat()
        
        # Исправление валюты
        if not receipt_data.currency:
            suggestions["currency"] = "EUR"
        
        # Исправление названия магазина
        if not receipt_data.merchant or receipt_data.merchant.strip() == "":
            suggestions["merchant"] = "Неизвестный магазин"
        
        # Исправление суммы на основе товаров
        if receipt_data.items and receipt_data.total == 0:
            calculated_total = sum(item.qty * item.price for item in receipt_data.items)
            if calculated_total > 0:
                suggestions["total"] = calculated_total
        
        return suggestions
    
    def validate_merchant_name(self, merchant: str) -> Tuple[bool, str]:
        """Валидация названия магазина с предложением исправления"""
        if not merchant or not merchant.strip():
            return False, "Название магазина не может быть пустым"
        
        merchant = merchant.strip()
        
        # Удаление лишних пробелов
        merchant = re.sub(r'\s+', ' ', merchant)
        
        # Удаление специальных символов в начале и конце
        merchant = merchant.strip('.,-&')
        
        # Проверка на минимальную длину
        if len(merchant) < 2:
            return False, "Название магазина слишком короткое"
        
        # Проверка на максимальную длину
        if len(merchant) > 100:
            merchant = merchant[:100]
            return True, f"Название обрезано до 100 символов: {merchant}"
        
        return True, merchant
    
    def validate_amount(self, amount: Any) -> Tuple[bool, float]:
        """Валидация и нормализация суммы (включая отрицательные значения)"""
        if amount is None:
            return False, 0.0
        
        try:
            if isinstance(amount, str):
                # Удаляем все кроме цифр, точек, запятых и знака минус
                cleaned = re.sub(r'[^\d.,-]', '', amount)
                cleaned = cleaned.replace(',', '.')
                amount = float(cleaned)
            else:
                amount = float(amount)
            
            # Округляем до 2 знаков после запятой
            amount = round(amount, 2)
            
            # Теперь разрешаем отрицательные суммы (они означают расходы)
            return True, amount
            
        except (ValueError, TypeError):
            return False, 0.0
