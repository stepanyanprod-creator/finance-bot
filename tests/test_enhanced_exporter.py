# tests/test_enhanced_exporter.py
"""Тесты для улучшенного экспорта данных"""

import os
import tempfile
import csv
from datetime import date, datetime
from unittest.mock import patch, MagicMock

import pytest

from app.services.enhanced_exporter import EnhancedExporter, export_monthly_data


class TestEnhancedExporter:
    """Тесты для класса EnhancedExporter"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.user_id = 12345
        self.temp_dir = tempfile.mkdtemp()
        
        # Мокаем данные пользователя
        self.mock_transactions = [
            {
                'date': '2024-03-15',
                'merchant': 'Зарплата',
                'total': '5000.00',
                'currency': 'UAH',
                'category': 'Зарплата',
                'payment_method': 'Основной счет',
                'source': 'manual'
            },
            {
                'date': '2024-03-16',
                'merchant': 'Магазин',
                'total': '-150.50',
                'currency': 'UAH',
                'category': 'Питание',
                'payment_method': 'Основной счет',
                'source': 'photo'
            },
            {
                'date': '2024-03-17',
                'merchant': 'Перевод',
                'total': '-1000.00',
                'currency': 'UAH',
                'category': 'Перевод',
                'payment_method': 'Основной счет',
                'source': 'manual'
            },
            {
                'date': '2024-03-17',
                'merchant': 'Перевод',
                'total': '1000.00',
                'currency': 'UAH',
                'category': 'Перевод',
                'payment_method': 'Сберегательный счет',
                'source': 'manual'
            }
        ]
        
        self.mock_accounts = {
            'Основной счет': {'currency': 'UAH', 'amount': 3500.00},
            'Сберегательный счет': {'currency': 'UAH', 'amount': 1000.00}
        }
        
        self.mock_balances = {
            'UAH': 4500.00,
            'Зарплата@UAH': 5000.00
        }
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_export_monthly_data_success(self, mock_balances, mock_accounts, mock_transactions):
        """Тест успешного экспорта данных за месяц"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Экспортируем данные за март 2024
        result = exporter.export_monthly_data(2024, 3, self.temp_dir)
        
        # Проверяем результат
        assert result['success'] is True
        assert result['period'] == '2024-03'
        assert result['transactions_count'] == 4
        assert len(result['files_created']) == 5  # 5 таблиц
        
        # Проверяем, что файлы созданы
        files = result['files_created']
        assert any('income_2024_03.csv' in f for f in files)
        assert any('expenses_2024_03.csv' in f for f in files)
        assert any('accounts_2024_03.csv' in f for f in files)
        assert any('transfers_2024_03.csv' in f for f in files)
        assert any('summary_2024_03.csv' in f for f in files)
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_export_monthly_data_no_data(self, mock_balances, mock_accounts, mock_transactions):
        """Тест экспорта когда нет данных за период"""
        # Настраиваем моки - пустые данные
        mock_transactions.return_value = []
        mock_accounts.return_value = {}
        mock_balances.return_value = {}
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Экспортируем данные за март 2024
        result = exporter.export_monthly_data(2024, 3, self.temp_dir)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'Нет данных за 2024-03' in result['message']
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_income_table_export(self, mock_balances, mock_accounts, mock_transactions):
        """Тест экспорта таблицы доходов"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Экспортируем таблицу доходов
        income_file = exporter._export_income_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert income_file is not None
        assert os.path.exists(income_file)
        
        # Проверяем содержимое файла
        with open(income_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должна быть одна запись о доходе
            assert len(rows) == 1
            assert rows[0]['source'] == 'Зарплата'
            assert rows[0]['amount'] == '5000.00'
            assert rows[0]['currency'] == 'UAH'
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_expense_table_export(self, mock_balances, mock_accounts, mock_transactions):
        """Тест экспорта таблицы расходов"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Экспортируем таблицу расходов
        expense_file = exporter._export_expense_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert expense_file is not None
        assert os.path.exists(expense_file)
        
        # Проверяем содержимое файла
        with open(expense_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должна быть одна запись о расходе
            assert len(rows) == 1
            assert rows[0]['merchant'] == 'Магазин'
            assert rows[0]['amount'] == '150.50'  # Положительное значение
            assert rows[0]['currency'] == 'UAH'
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_transfers_table_export(self, mock_balances, mock_accounts, mock_transactions):
        """Тест экспорта таблицы переводов"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Экспортируем таблицу переводов
        transfers_file = exporter._export_transfers_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert transfers_file is not None
        assert os.path.exists(transfers_file)
        
        # Проверяем содержимое файла
        with open(transfers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должна быть одна запись о переводе
            assert len(rows) == 1
            assert rows[0]['from_account'] == 'Основной счет'
            assert rows[0]['to_account'] == 'Сберегательный счет'
            assert rows[0]['amount'] == '1000.00'
            assert rows[0]['currency'] == 'UAH'
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_accounts_table_export(self, mock_balances, mock_accounts, mock_transactions):
        """Тест экспорта таблицы счетов"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Экспортируем таблицу счетов
        accounts_file = exporter._export_accounts_table(self.temp_dir, 2024, 3)
        
        # Проверяем, что файл создан
        assert accounts_file is not None
        assert os.path.exists(accounts_file)
        
        # Проверяем содержимое файла
        with open(accounts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должно быть 2 счета
            assert len(rows) == 2
            
            # Проверяем первый счет
            account_names = [row['account_name'] for row in rows]
            assert 'Основной счет' in account_names
            assert 'Сберегательный счет' in account_names
            
            # Проверяем балансы
            for row in rows:
                if row['account_name'] == 'Основной счет':
                    assert row['balance'] == '3500.0'
                elif row['account_name'] == 'Сберегательный счет':
                    assert row['balance'] == '1000.0'


def test_export_monthly_data_function():
    """Тест функции export_monthly_data"""
    with patch('app.services.enhanced_exporter.EnhancedExporter') as mock_exporter_class:
        # Настраиваем мок
        mock_exporter = MagicMock()
        mock_exporter.export_monthly_data.return_value = {
            'success': True,
            'files_created': ['test_file.csv'],
            'period': '2024-03',
            'transactions_count': 4
        }
        mock_exporter_class.return_value = mock_exporter
        
        # Вызываем функцию
        result = export_monthly_data(12345, 2024, 3)
        
        # Проверяем результат
        assert result['success'] is True
        assert result['period'] == '2024-03'
        assert result['transactions_count'] == 4
        
        # Проверяем, что экспортер был создан и вызван
        mock_exporter_class.assert_called_once_with(12345)
        mock_exporter.export_monthly_data.assert_called_once_with(2024, 3, None)
