# tests/test_enhanced_receipt_parser.py
import pytest
import tempfile
from unittest.mock import Mock, patch
from app.services.enhanced_receipt_parser import EnhancedReceiptParser, ReceiptType, ParsingResult
from app.models import ReceiptData, ReceiptItem
from app.exceptions import ReceiptParsingError


class TestEnhancedReceiptParser:
    def test_parser_initialization(self):
        """Тест инициализации парсера"""
        parser = EnhancedReceiptParser()
        assert parser is not None
    
    @patch('app.services.enhanced_receipt_parser.client')
    def test_parse_receipt_success(self, mock_client):
        """Тест успешного парсинга чека"""
        # Мокаем ответ OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.tool_calls = [Mock()]
        mock_response.choices[0].message.tool_calls[0].function = Mock()
        mock_response.choices[0].message.tool_calls[0].function.name = "submit_receipt"
        mock_response.choices[0].message.tool_calls[0].function.arguments = '{"date": "2024-01-15", "merchant": "Test Store", "total": 25.50, "currency": "EUR", "items": [{"name": "Bread", "quantity": 1, "price": 2.50}]}'
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = EnhancedReceiptParser()
        
        # Создаем временный файл изображения
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"fake image data")
            tmp_path = tmp.name
        
        try:
            result = parser.parse_receipt(tmp_path)
            
            assert result.success is True
            assert result.data is not None
            assert result.data.merchant == "Test Store"
            assert result.data.total == 25.50
            assert result.data.currency == "EUR"
            assert len(result.data.items) == 1
            assert result.data.items[0].name == "Bread"
            
        finally:
            import os
            os.unlink(tmp_path)
    
    def test_parse_receipt_no_openai(self):
        """Тест парсинга без OpenAI"""
        parser = EnhancedReceiptParser()
        parser.client = None  # Отключаем OpenAI
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"fake image data")
            tmp_path = tmp.name
        
        try:
            result = parser.parse_receipt(tmp_path)
            
            assert result.success is True
            assert result.data is not None
            assert result.data.merchant == "Неизвестный магазин"
            assert result.data.total == 0.0
            
        finally:
            import os
            os.unlink(tmp_path)
    
    def test_validate_and_enhance(self):
        """Тест валидации и улучшения данных"""
        parser = EnhancedReceiptParser()
        
        raw_data = {
            "date": "2024-01-15",
            "merchant": "Test Store",
            "total": "25.50",  # Строка вместо числа
            "currency": "eur",  # Строчные буквы
            "items": [
                {"name": "Bread", "quantity": 1, "price": 2.50},
                {"name": "", "quantity": 0, "price": 0}  # Пустой товар
            ]
        }
        
        result = parser._validate_and_enhance(raw_data, ReceiptType.GROCERY)
        
        assert isinstance(result, ReceiptData)
        assert result.date == "2024-01-15"
        assert result.merchant == "Test Store"
        assert result.total == 25.50  # Преобразовано в float
        assert result.currency == "EUR"  # Преобразовано в верхний регистр
        assert len(result.items) == 1  # Пустой товар отфильтрован
        assert result.items[0].name == "Bread"
    
    def test_suggest_category(self):
        """Тест предложения категории"""
        parser = EnhancedReceiptParser()
        
        # Тест с продуктами
        receipt_data = ReceiptData(
            date="2024-01-15",
            merchant="REWE",
            total=25.50,
            currency="EUR",
            items=[
                ReceiptItem(name="Bread", qty=1, price=2.50),
                ReceiptItem(name="Milk", qty=2, price=1.50)
            ]
        )
        
        category = parser._suggest_category(receipt_data, ReceiptType.GROCERY)
        assert category == "Продукты"
        
        # Тест с напитками
        receipt_data.items = [ReceiptItem(name="Coffee", qty=1, price=3.50)]
        category = parser._suggest_category(receipt_data, ReceiptType.RESTAURANT)
        assert category == "Напитки"
    
    def test_calculate_confidence(self):
        """Тест расчета уверенности"""
        parser = EnhancedReceiptParser()
        
        # Полные данные
        receipt_data = ReceiptData(
            date="2024-01-15",
            merchant="Test Store",
            total=25.50,
            currency="EUR",
            items=[ReceiptItem(name="Bread", qty=1, price=2.50)]
        )
        
        confidence = parser._calculate_confidence(receipt_data)
        assert confidence > 0.5
        
        # Неполные данные
        receipt_data.merchant = ""
        receipt_data.items = []
        confidence = parser._calculate_confidence(receipt_data)
        assert confidence < 0.5
    
    def test_parse_amount(self):
        """Тест парсинга суммы"""
        parser = EnhancedReceiptParser()
        
        assert parser._parse_amount("25.50") == 25.50
        assert parser._parse_amount("25,50") == 25.50
        assert parser._parse_amount(25.50) == 25.50
        assert parser._parse_amount("invalid") == 0.0
        assert parser._parse_amount(None) == 0.0
    
    def test_normalize_currency(self):
        """Тест нормализации валюты"""
        parser = EnhancedReceiptParser()
        
        assert parser._normalize_currency("€") == "EUR"
        assert parser._normalize_currency("$") == "USD"
        assert parser._normalize_currency("eur") == "EUR"
        assert parser._normalize_currency("") == "EUR"
        assert parser._normalize_currency("unknown") == "EUR"
    
    def test_is_valid_date(self):
        """Тест валидации даты"""
        parser = EnhancedReceiptParser()
        
        assert parser._is_valid_date("2024-01-15") is True
        assert parser._is_valid_date("2024-13-01") is False
        assert parser._is_valid_date("invalid") is False
        assert parser._is_valid_date("") is False


class TestReceiptType:
    def test_receipt_type_enum(self):
        """Тест enum типов чеков"""
        assert ReceiptType.GROCERY.value == "grocery"
        assert ReceiptType.RESTAURANT.value == "restaurant"
        assert ReceiptType.PHARMACY.value == "pharmacy"
        assert ReceiptType.UNKNOWN.value == "unknown"


class TestParsingResult:
    def test_parsing_result_initialization(self):
        """Тест инициализации результата парсинга"""
        result = ParsingResult(success=True)
        assert result.success is True
        assert result.data is None
        assert result.confidence == 0.0
        assert result.receipt_type == ReceiptType.UNKNOWN
        assert result.errors == []
