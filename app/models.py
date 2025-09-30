# app/models.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import date


@dataclass
class ReceiptItem:
    """Элемент чека"""
    name: str
    qty: float
    price: float


@dataclass
class ReceiptData:
    """Данные чека"""
    date: str
    merchant: str
    total: float
    currency: str
    category: str = ""
    payment_method: str = ""
    items: List[ReceiptItem] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


@dataclass
class Account:
    """Банковский счет/кошелек"""
    name: str
    currency: str
    amount: float


@dataclass
class Balance:
    """Баланс по валюте/категории"""
    key: str  # например "EUR" или "groceries@EUR"
    amount: float


@dataclass
class CategoryRule:
    """Правило категоризации"""
    id: int
    category: str
    match: Dict[str, Any]


@dataclass
class Transaction:
    """Транзакция"""
    date: str
    merchant: str
    total: float
    currency: str
    category: str
    payment_method: str
    source: str = ""


@dataclass
class VoiceData:
    """Данные голосового сообщения"""
    text: str
    file_id: str
    parsed_data: Optional[ReceiptData] = None


@dataclass
class PendingReceipt:
    """Ожидающий обработки чек"""
    data: ReceiptData
    photo_id: str = ""
    voice_id: str = ""


@dataclass
class StatsPeriod:
    """Период для статистики"""
    start: date
    end: date


@dataclass
class StatsData:
    """Данные статистики"""
    period: StatsPeriod
    total_sum: float
    currency: str
    by_category: Dict[str, float]
    by_merchant: Dict[str, float]
