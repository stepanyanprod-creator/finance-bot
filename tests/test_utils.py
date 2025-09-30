# tests/test_utils.py
import pytest
from app.utils import (
    format_money, parse_amount, normalize_currency,
    validate_date_format, clean_text, extract_currency_from_text,
    safe_int, safe_float, truncate_text, is_valid_account_name,
    generate_rule_id
)


class TestFormatMoney:
    def test_format_money_basic(self):
        assert format_money(25.50, "EUR") == "25.50 EUR"
        assert format_money(0, "USD") == "0.00 USD"
        assert format_money("100", "UAH") == "100.00 UAH"
    
    def test_format_money_empty_currency(self):
        assert format_money(25.50, "") == "25.50"
        assert format_money(25.50, None) == "25.50"


class TestParseAmount:
    def test_parse_amount_valid(self):
        assert parse_amount("25.50") == 25.50
        assert parse_amount("25,50") == 25.50
        assert parse_amount("100") == 100.0
        assert parse_amount(25.50) == 25.50
    
    def test_parse_amount_invalid(self):
        assert parse_amount("invalid") == 0.0
        assert parse_amount("") == 0.0
        assert parse_amount(None) == 0.0


class TestNormalizeCurrency:
    def test_normalize_currency_symbols(self):
        assert normalize_currency("€") == "EUR"
        assert normalize_currency("$") == "USD"
        assert normalize_currency("₴") == "UAH"
        assert normalize_currency("£") == "GBP"
    
    def test_normalize_currency_codes(self):
        assert normalize_currency("eur") == "EUR"
        assert normalize_currency("USD") == "USD"
        assert normalize_currency("uah") == "UAH"
    
    def test_normalize_currency_empty(self):
        assert normalize_currency("") == ""
        assert normalize_currency(None) == ""


class TestValidateDateFormat:
    def test_validate_date_format_valid(self):
        assert validate_date_format("2024-01-15") == True
        assert validate_date_format("2023-12-31") == True
    
    def test_validate_date_format_invalid(self):
        assert validate_date_format("15-01-2024") == False
        assert validate_date_format("2024/01/15") == False
        assert validate_date_format("invalid") == False
        assert validate_date_format("") == False


class TestCleanText:
    def test_clean_text_basic(self):
        assert clean_text("  hello world  ") == "hello world"
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestExtractCurrencyFromText:
    def test_extract_currency_basic(self):
        amount, currency = extract_currency_from_text("25.50 EUR")
        assert amount == 25.50
        assert currency == "EUR"
        
        amount, currency = extract_currency_from_text("100 USD")
        assert amount == 100.0
        assert currency == "USD"
    
    def test_extract_currency_with_comma(self):
        amount, currency = extract_currency_from_text("25,50 €")
        assert amount == 25.50
        assert currency == "EUR"
    
    def test_extract_currency_no_match(self):
        amount, currency = extract_currency_from_text("just text")
        assert amount == 0.0
        assert currency == ""


class TestSafeConversions:
    def test_safe_int(self):
        assert safe_int("123") == 123
        assert safe_int(123) == 123
        assert safe_int("invalid") == 0
        assert safe_int(None) == 0
    
    def test_safe_float(self):
        assert safe_float("123.45") == 123.45
        assert safe_float(123.45) == 123.45
        assert safe_float("invalid") == 0.0
        assert safe_float(None) == 0.0


class TestTruncateText:
    def test_truncate_text_short(self):
        assert truncate_text("short text") == "short text"
    
    def test_truncate_text_long(self):
        long_text = "a" * 150
        result = truncate_text(long_text, 100)
        assert len(result) == 100
        assert result.endswith("...")


class TestIsValidAccountName:
    def test_valid_account_names(self):
        assert is_valid_account_name("Test Account") == True
        assert is_valid_account_name("Monobank") == True
        assert is_valid_account_name("Card 123") == True
    
    def test_invalid_account_names(self):
        assert is_valid_account_name("") == False
        assert is_valid_account_name("   ") == False
        assert is_valid_account_name("Test<Account") == False
        assert is_valid_account_name("Test:Account") == False


class TestGenerateRuleId:
    def test_generate_rule_id_empty(self):
        assert generate_rule_id([]) == 1
    
    def test_generate_rule_id_with_existing(self):
        rules = [{"id": 1}, {"id": 3}]
        assert generate_rule_id(rules) == 2
    
    def test_generate_rule_id_sequential(self):
        rules = [{"id": 1}, {"id": 2}, {"id": 3}]
        assert generate_rule_id(rules) == 4
