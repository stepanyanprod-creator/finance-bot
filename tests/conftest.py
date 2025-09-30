# tests/conftest.py
import pytest
import tempfile
import os
from unittest.mock import Mock
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes

from app.config import config


@pytest.fixture
def temp_data_dir():
    """Временная директория для тестов"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_user():
    """Мок пользователя"""
    return User(
        id=12345,
        is_bot=False,
        first_name="Test",
        username="testuser"
    )


@pytest.fixture
def mock_chat():
    """Мок чата"""
    return Chat(
        id=12345,
        type="private"
    )


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Мок сообщения"""
    return Message(
        message_id=1,
        from_user=mock_user,
        date=None,
        chat=mock_chat,
        content_type="text",
        text="test message"
    )


@pytest.fixture
def mock_update(mock_message):
    """Мок update"""
    update = Mock(spec=Update)
    update.effective_message = mock_message
    update.effective_user = mock_message.from_user
    update.effective_chat = mock_message.chat
    return update


@pytest.fixture
def mock_context():
    """Мок контекста"""
    context = Mock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.args = []
    return context


@pytest.fixture
def sample_receipt_data():
    """Пример данных чека"""
    return {
        "date": "2024-01-15",
        "merchant": "Test Store",
        "total": 25.50,
        "currency": "EUR",
        "category": "groceries",
        "payment_method": "Test Card",
        "items": [
            {"name": "Bread", "qty": 1, "price": 2.50},
            {"name": "Milk", "qty": 2, "price": 1.50}
        ],
        "notes": "Test receipt"
    }


@pytest.fixture
def sample_accounts():
    """Пример счетов"""
    return {
        "Test Card": {"currency": "EUR", "amount": 1000.0},
        "Cash": {"currency": "EUR", "amount": 50.0}
    }


@pytest.fixture
def sample_rules():
    """Пример правил"""
    return [
        {
            "id": 1,
            "category": "groceries",
            "match": {
                "merchant_contains": ["store", "market"],
                "total_max": 100.0
            }
        }
    ]
