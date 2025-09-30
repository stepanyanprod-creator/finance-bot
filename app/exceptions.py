# app/exceptions.py
"""Пользовательские исключения для Finance Bot"""


class FinanceBotError(Exception):
    """Базовое исключение для Finance Bot"""
    pass


class StorageError(FinanceBotError):
    """Ошибки работы с хранилищем данных"""
    pass


class ValidationError(FinanceBotError):
    """Ошибки валидации данных"""
    pass


class ReceiptParsingError(FinanceBotError):
    """Ошибки парсинга чеков"""
    pass


class VoiceProcessingError(FinanceBotError):
    """Ошибки обработки голосовых сообщений"""
    pass


class AccountError(FinanceBotError):
    """Ошибки работы со счетами"""
    pass


class RuleError(FinanceBotError):
    """Ошибки работы с правилами"""
    pass


class ConfigurationError(FinanceBotError):
    """Ошибки конфигурации"""
    pass
