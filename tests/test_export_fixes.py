# tests/test_export_fixes.py
"""Тесты для исправлений в экспорте"""

import os
import tempfile
import csv
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from app.services.enhanced_exporter import EnhancedExporter


class TestExportFixes:
    """Тесты для исправлений в экспорте"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.user_id = 12345
        self.temp_dir = tempfile.mkdtemp()
        
        # Мокаем данные пользователя с переводами
        self.mock_transactions_with_transfers = [
            {
                'date': '2024-03-15',
                'merchant': 'Перевод с основного',
                'total': '-1000.00',
                'currency': 'UAH',
                'category': 'Перевод',
                'payment_method': 'Основной счет',
                'source': 'manual'
            },
            {
                'date': '2024-03-15',
                'merchant': 'Перевод на сберегательный',
                'total': '1000.00',
                'currency': 'UAH',
                'category': 'Перевод',
                'payment_method': 'Сберегательный счет',
                'source': 'manual'
            },
            {
                'date': '2024-03-16',
                'merchant': 'Зарплата',
                'total': '5000.00',
                'currency': 'UAH',
                'category': 'Зарплата',
                'payment_method': 'Основной счет',
                'source': 'manual'
            }
        ]
        
        self.mock_accounts = {
            'Основной счет': {'currency': 'UAH', 'amount': 4000.00},
            'Сберегательный счет': {'currency': 'UAH', 'amount': 1000.00}
        }
        
        self.mock_balances = {
            'UAH': 5000.00
        }
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_transfers_table_always_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица переводов всегда создается"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions_with_transfers
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
            assert rows[0]['amount'] == '1000.0'
            assert rows[0]['currency'] == 'UAH'
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_transfers_table_empty_but_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица переводов создается даже если переводов нет"""
        # Настраиваем моки без переводов
        mock_transactions.return_value = [
            {
                'date': '2024-03-16',
                'merchant': 'Зарплата',
                'total': '5000.00',
                'currency': 'UAH',
                'category': 'Зарплата',
                'payment_method': 'Основной счет',
                'source': 'manual'
            }
        ]
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
        
        # Проверяем, что файл содержит только заголовки
        with open(transfers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должны быть только заголовки, без данных
            assert len(rows) == 0
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_summary_table_always_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что сводная таблица всегда создается"""
        # Настраиваем моки
        mock_transactions.return_value = self.mock_transactions_with_transfers
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Экспортируем сводную таблицу
        summary_file = exporter._export_summary_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert summary_file is not None
        assert os.path.exists(summary_file)
        
        # Проверяем содержимое файла
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должно быть 3 записи
            assert len(rows) == 3
            
            # Проверяем типы транзакций
            types = [row['type'] for row in rows]
            assert 'expense' in types  # Перевод с основного счета
            assert 'income' in types   # Перевод на сберегательный счет и зарплата
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_summary_table_empty_but_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что сводная таблица создается даже если транзакций нет"""
        # Настраиваем моки без транзакций
        mock_transactions.return_value = []
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Экспортируем сводную таблицу
        summary_file = exporter._export_summary_table(
            [], self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert summary_file is not None
        assert os.path.exists(summary_file)
        
        # Проверяем, что файл содержит только заголовки
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должны быть только заголовки, без данных
            assert len(rows) == 0
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_accounts_table_always_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица счетов всегда создается"""
        # Настраиваем моки
        mock_transactions.return_value = []
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
            
            # Проверяем счета
            account_names = [row['account_name'] for row in rows]
            assert 'Основной счет' in account_names
            assert 'Сберегательный счет' in account_names
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_accounts_table_empty_but_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица счетов создается даже если счетов нет"""
        # Настраиваем моки без счетов
        mock_transactions.return_value = []
        mock_accounts.return_value = {}
        mock_balances.return_value = {}
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Экспортируем таблицу счетов
        accounts_file = exporter._export_accounts_table(self.temp_dir, 2024, 3)
        
        # Проверяем, что файл создан
        assert accounts_file is not None
        assert os.path.exists(accounts_file)
        
        # Проверяем, что файл содержит только заголовки
        with open(accounts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должны быть только заголовки, без данных
            assert len(rows) == 0
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_expenses_table_empty_but_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица расходов создается даже если расходов нет"""
        # Настраиваем моки только с доходами
        mock_transactions.return_value = [
            {
                'date': '2024-03-16',
                'merchant': 'Зарплата',
                'total': '5000.00',
                'currency': 'UAH',
                'category': 'Зарплата',
                'payment_method': 'Основной счет',
                'source': 'manual'
            }
        ]
        mock_accounts.return_value = self.mock_accounts
        mock_balances.return_value = self.mock_balances
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Экспортируем таблицу расходов
        expenses_file = exporter._export_expense_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        # Проверяем, что файл создан
        assert expenses_file is not None
        assert os.path.exists(expenses_file)
        
        # Проверяем, что файл содержит только заголовки
        with open(expenses_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должны быть только заголовки, без данных
            assert len(rows) == 0
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_transfer_exclusion_logic(self, mock_balances, mock_accounts, mock_transactions):
        """Тест правильного исключения переводов из таблиц доходов и расходов"""
        # Настраиваем моки с переводами и обычными транзакциями
        mock_transactions.return_value = [
            # Обычный расход (положительная сумма, но расходная категория)
            {
                'date': '2024-03-16',
                'merchant': 'REWE',
                'total': '150.50',
                'currency': 'EUR',
                'category': 'groceries',
                'payment_method': 'Основной счет',
                'source': 'photo'
            },
            # Обычный доход
            {
                'date': '2024-03-17',
                'merchant': 'Получил зарплату',
                'total': '5000.00',
                'currency': 'EUR',
                'category': 'Зарплата',
                'payment_method': 'Основной счет',
                'source': 'voice'
            },
            # Перевод (списание)
            {
                'date': '2024-03-18',
                'merchant': 'Перевод на сберегательный',
                'total': '-1000.00',
                'currency': 'EUR',
                'category': 'Банковские операции',
                'payment_method': 'Основной счет',
                'source': 'transfer'
            },
            # Перевод (зачисление)
            {
                'date': '2024-03-18',
                'merchant': 'Перевод с основного',
                'total': '1000.00',
                'currency': 'EUR',
                'category': 'Банковские операции',
                'payment_method': 'Сберегательный счет',
                'source': 'transfer'
            }
        ]
        mock_accounts.return_value = {
            'Основной счет': {'currency': 'EUR', 'amount': 4850.00},
            'Сберегательный счет': {'currency': 'EUR', 'amount': 1000.00}
        }
        mock_balances.return_value = {'EUR': 5850.00}
        
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Фильтруем транзакции за март 2024
        monthly_transactions = exporter._filter_transactions_by_period(
            date(2024, 3, 1), date(2024, 4, 1)
        )
        
        # Тестируем таблицу расходов
        expenses_file = exporter._export_expense_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        assert expenses_file is not None
        with open(expenses_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            expense_rows = list(reader)
        
        # В таблице расходов должна быть только 1 запись (не перевод)
        assert len(expense_rows) == 1
        assert 'rewe' in expense_rows[0]['merchant'].lower()
        # Проверяем, что заметки содержат информацию о типе источника
        assert 'фото чека' in expense_rows[0]['notes'].lower()
        
        # Тестируем таблицу доходов
        income_file = exporter._export_income_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        assert income_file is not None
        with open(income_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            income_rows = list(reader)
        
        # В таблице доходов должна быть только 1 запись (не перевод)
        assert len(income_rows) == 1
        assert 'получил зарплату' in income_rows[0]['source'].lower()
        # Проверяем, что заметки содержат информацию о типе источника
        assert 'голосовая запись' in income_rows[0]['notes'].lower()
        
        # Тестируем таблицу переводов
        transfers_file = exporter._export_transfers_table(
            monthly_transactions, self.temp_dir, 2024, 3
        )
        
        assert transfers_file is not None
        with open(transfers_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            transfer_rows = list(reader)
        
        # В таблице переводов должна быть 1 запись о переводе
        assert len(transfer_rows) == 1
        assert 'основной счет' in transfer_rows[0]['from_account'].lower()
        assert 'сберегательный счет' in transfer_rows[0]['to_account'].lower()
    
    def test_notes_generation(self):
        """Тест генерации заметок для разных типов транзакций"""
        # Создаем экспортер
        exporter = EnhancedExporter(self.user_id)
        
        # Тестируем разные типы источников
        test_cases = [
            # Тест с сохраненными заметками (приоритет)
            {
                'transaction': {'source': 'voice:', 'merchant': 'Заработал', 'notes': 'Голосовая запись: вчера заработал 5000 евро'},
                'expected': 'Голосовая запись: вчера заработал 5000 евро'
            },
            {
                'transaction': {'source': 'enhanced_photo:file_id', 'merchant': 'REWE', 'notes': 'Фото чека: REWE | Товары: Хлеб (2x1.50); Молоко (1x2.00)'},
                'expected': 'Фото чека: REWE | Товары: Хлеб (2x1.50); Молоко (1x2.00)'
            },
            # Тест без сохраненных заметок (fallback)
            {
                'transaction': {'source': 'voice:', 'merchant': 'Заработал'},
                'expected': 'Голосовая запись: Заработал'
            },
            {
                'transaction': {'source': 'enhanced_photo:file_id', 'merchant': 'REWE'},
                'expected': 'Фото чека: REWE'
            },
            {
                'transaction': {'source': 'photo:file_id', 'merchant': 'ALDI SÜD'},
                'expected': 'Фото чека: ALDI SÜD'
            },
            {
                'transaction': {'source': 'manual_income', 'merchant': 'Зарплата'},
                'expected': 'Ручная запись'
            },
            {
                'transaction': {'source': 'transfer', 'merchant': 'Перевод'},
                'expected': 'Перевод между счетами'
            },
            {
                'transaction': {'source': '', 'merchant': 'Неизвестно'},
                'expected': ''
            }
        ]
        
        for case in test_cases:
            result = exporter._generate_notes(case['transaction'])
            assert result == case['expected'], f"Expected '{case['expected']}', got '{result}' for source '{case['transaction']['source']}'"
    
    @patch('app.services.enhanced_exporter.read_rows')
    @patch('app.services.enhanced_exporter.list_accounts')
    @patch('app.services.enhanced_exporter.get_balances')
    def test_income_table_empty_but_created(self, mock_balances, mock_accounts, mock_transactions):
        """Тест что таблица доходов создается даже если доходов нет"""
        # Настраиваем моки только с расходами
        mock_transactions.return_value = [
            {
                'date': '2024-03-16',
                'merchant': 'Магазин',
                'total': '-150.50',
                'currency': 'UAH',
                'category': 'Питание',
                'payment_method': 'Основной счет',
                'source': 'photo'
            }
        ]
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
        
        # Проверяем, что файл содержит только заголовки
        with open(income_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Должны быть только заголовки, без данных
            assert len(rows) == 0
