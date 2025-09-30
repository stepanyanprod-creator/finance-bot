# tests/test_storage.py
import pytest
import tempfile
import os
from app.storage import (
    ensure_csv, read_rows, append_row_csv, undo_last_row,
    set_balance, get_balances, dec_balance,
    list_accounts, add_account, set_account_amount, dec_account
)


class TestCSVOperations:
    def test_ensure_csv_creates_file(self, temp_data_dir, mock_user):
        """Тест создания CSV файла"""
        user_id = mock_user.id
        ensure_csv(user_id)
        csv_path = os.path.join(temp_data_dir, str(user_id), "finance.csv")
        assert os.path.exists(csv_path)
    
    def test_append_row_csv(self, temp_data_dir, mock_user, sample_receipt_data):
        """Тест добавления записи в CSV"""
        user_id = mock_user.id
        ensure_csv(user_id)
        append_row_csv(user_id, sample_receipt_data, source="test")
        
        rows = read_rows(user_id)
        assert len(rows) == 1
        assert rows[0]["merchant"] == sample_receipt_data["merchant"]
        assert float(rows[0]["total"]) == sample_receipt_data["total"]
    
    def test_undo_last_row(self, temp_data_dir, mock_user, sample_receipt_data):
        """Тест отмены последней записи"""
        user_id = mock_user.id
        ensure_csv(user_id)
        
        # Добавляем две записи
        append_row_csv(user_id, sample_receipt_data, source="test1")
        append_row_csv(user_id, sample_receipt_data, source="test2")
        
        assert len(read_rows(user_id)) == 2
        
        # Отменяем последнюю
        result = undo_last_row(user_id)
        assert result == True
        assert len(read_rows(user_id)) == 1


class TestAccountOperations:
    def test_add_account(self, temp_data_dir, mock_user):
        """Тест добавления счета"""
        user_id = mock_user.id
        name, account = add_account(user_id, "Test Bank", "EUR", 1000.0)
        
        assert name == "Test Bank"
        assert account["currency"] == "EUR"
        assert account["amount"] == 1000.0
        
        accounts = list_accounts(user_id)
        assert "Test Bank" in accounts
    
    def test_set_account_amount(self, temp_data_dir, mock_user):
        """Тест изменения суммы счета"""
        user_id = mock_user.id
        add_account(user_id, "Test Bank", "EUR", 1000.0)
        
        name, account = set_account_amount(user_id, "Test Bank", 1500.0)
        assert account["amount"] == 1500.0
    
    def test_dec_account(self, temp_data_dir, mock_user):
        """Тест списания со счета"""
        user_id = mock_user.id
        add_account(user_id, "Test Bank", "EUR", 1000.0)
        
        dec_account(user_id, "Test Bank", 250.0)
        accounts = list_accounts(user_id)
        assert accounts["Test Bank"]["amount"] == 750.0


class TestBalanceOperations:
    def test_set_balance(self, temp_data_dir, mock_user):
        """Тест установки баланса"""
        user_id = mock_user.id
        key, amount = set_balance(user_id, 1000.0, "EUR", None)
        
        assert key == "EUR"
        assert amount == 1000.0
        
        balances = get_balances(user_id)
        assert balances["EUR"] == 1000.0
    
    def test_set_balance_with_category(self, temp_data_dir, mock_user):
        """Тест установки баланса с категорией"""
        user_id = mock_user.id
        key, amount = set_balance(user_id, 500.0, "EUR", "groceries")
        
        assert key == "groceries@EUR"
        assert amount == 500.0
    
    def test_dec_balance(self, temp_data_dir, mock_user):
        """Тест списания с баланса"""
        user_id = mock_user.id
        set_balance(user_id, 1000.0, "EUR", None)
        
        dec_balance(user_id, 250.0, "EUR", None)
        balances = get_balances(user_id)
        assert balances["EUR"] == 750.0
