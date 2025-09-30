# app/services/enhanced_exporter.py
"""Улучшенный сервис экспорта данных с поддержкой экспорта по месяцам"""

import csv
import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from app.logger import get_logger
from app.storage import read_rows, list_accounts, get_balances

logger = get_logger(__name__)


class EnhancedExporter:
    """Класс для расширенного экспорта данных пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.transactions = read_rows(user_id)
        self.accounts = list_accounts(user_id)
        self.balances = get_balances(user_id)
    
    def export_monthly_data(self, year: int, month: int, output_dir: str = None) -> Dict:
        """
        Экспортирует данные за конкретный месяц
        
        Args:
            year: Год
            month: Месяц (1-12)
            output_dir: Директория для сохранения файлов
            
        Returns:
            Dict с результатами экспорта
        """
        try:
            # Определяем период
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            # Фильтруем транзакции за период
            monthly_transactions = self._filter_transactions_by_period(start_date, end_date)
            
            if not monthly_transactions:
                return {
                    'success': False,
                    'message': f'Нет данных за {year}-{month:02d}'
                }
            
            # Определяем директорию для сохранения
            if not output_dir:
                output_dir = f"exports/{self.user_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Создаем файлы экспорта
            files_created = []
            
            # 1. Таблица доходов
            income_file = self._export_income_table(monthly_transactions, output_dir, year, month)
            if income_file:
                files_created.append(income_file)
            
            # 2. Таблица расходов
            expense_file = self._export_expense_table(monthly_transactions, output_dir, year, month)
            if expense_file:
                files_created.append(expense_file)
            
            # 3. Таблица счетов (текущие балансы) - всегда создаем
            accounts_file = self._export_accounts_table(output_dir, year, month)
            if accounts_file:
                files_created.append(accounts_file)
            
            # 4. Таблица обменов (переводы между счетами) - всегда создаем
            transfers_file = self._export_transfers_table(monthly_transactions, output_dir, year, month)
            if transfers_file:
                files_created.append(transfers_file)
            
            # 5. Сводная таблица всех транзакций - всегда создаем
            summary_file = self._export_summary_table(monthly_transactions, output_dir, year, month)
            if summary_file:
                files_created.append(summary_file)
            
            return {
                'success': True,
                'files_created': files_created,
                'period': f'{year}-{month:02d}',
                'transactions_count': len(monthly_transactions),
                'message': f'Экспорт за {year}-{month:02d} завершен. Создано файлов: {len(files_created)}'
            }
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте данных за {year}-{month}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Ошибка при экспорте: {e}'
            }
    
    def export_current_month(self, output_dir: str = None) -> Dict:
        """Экспортирует данные за текущий месяц"""
        today = date.today()
        return self.export_monthly_data(today.year, today.month, output_dir)
    
    def export_last_n_months(self, months_count: int, output_dir: str = None) -> Dict:
        """
        Экспортирует данные за последние N месяцев
        
        Args:
            months_count: Количество месяцев для экспорта
            output_dir: Директория для сохранения файлов
            
        Returns:
            Dict с результатами экспорта
        """
        try:
            if not output_dir:
                output_dir = f"exports/{self.user_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            results = []
            today = date.today()
            
            for i in range(months_count):
                # Вычисляем дату для i месяцев назад
                if today.month - i <= 0:
                    year = today.year - 1
                    month = 12 + (today.month - i)
                else:
                    year = today.year
                    month = today.month - i
                
                result = self.export_monthly_data(year, month, output_dir)
                results.append(result)
            
            successful_exports = [r for r in results if r.get('success')]
            
            return {
                'success': True,
                'results': results,
                'successful_count': len(successful_exports),
                'total_count': months_count,
                'message': f'Экспорт за {months_count} месяцев завершен. Успешно: {len(successful_exports)}'
            }
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте за {months_count} месяцев: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Ошибка при экспорте: {e}'
            }
    
    def _filter_transactions_by_period(self, start_date: date, end_date: date) -> List[Dict]:
        """Фильтрует транзакции по периоду"""
        filtered = []
        
        for transaction in self.transactions:
            try:
                transaction_date = datetime.strptime(transaction.get('date', ''), '%Y-%m-%d').date()
                if start_date <= transaction_date < end_date:
                    filtered.append(transaction)
            except (ValueError, TypeError):
                continue
        
        return filtered
    
    def _generate_notes(self, transaction: Dict) -> str:
        """Генерирует заметки для транзакции на основе доступной информации"""
        # Если в транзакции уже есть сохраненные заметки, используем их
        existing_notes = transaction.get('notes', '')
        if existing_notes:
            return existing_notes
        
        # Если заметок нет, генерируем их на основе источника
        source = transaction.get('source', '')
        merchant = transaction.get('merchant', '')
        
        # Для голосовых сообщений
        if source.startswith('voice'):
            # Пытаемся извлечь транскрипцию из поля source
            if ':' in source and len(source.split(':')) > 1:
                transcription = source.split(':', 1)[1].strip()
                if transcription:
                    return f"Голосовая запись: {transcription}"
            
            # Если транскрипция недоступна, используем название мерчанта как подсказку
            if merchant:
                return f"Голосовая запись: {merchant}"
            return "Голосовая запись"
        
        # Для фотографий
        elif source.startswith('enhanced_photo'):
            # Улучшенный парсер фотографий
            return f"Фото чека: {merchant}" if merchant else "Фото чека"
        
        elif source.startswith('photo'):
            # Обычный парсер фотографий
            return f"Фото чека: {merchant}" if merchant else "Фото чека"
        
        # Для ручных записей
        elif source.startswith('manual'):
            return "Ручная запись"
        
        # Для переводов
        elif source.startswith('transfer'):
            return "Перевод между счетами"
        
        # Если источник неизвестен или пустой
        return source if source else ""
    
    def _identify_transfers(self, transactions: List[Dict]) -> set:
        """Определяет какие транзакции являются переводами между счетами"""
        transfer_ids = set()
        transfer_candidates = defaultdict(list)
        
        for i, transaction in enumerate(transactions):
            amount = float(transaction.get('total', 0) or 0)
            if amount != 0:
                # Используем ключ: дата + валюта + абсолютная сумма
                key = (transaction.get('date', ''), transaction.get('currency', ''), abs(amount))
                transfer_candidates[key].append((i, transaction))
        
        # Находим пары транзакций с одинаковой суммой, но разными знаками
        for key, candidate_transactions in transfer_candidates.items():
            if len(candidate_transactions) >= 2:
                # Разделяем на отрицательные и положительные
                negative_transactions = [(idx, t) for idx, t in candidate_transactions if float(t.get('total', 0) or 0) < 0]
                positive_transactions = [(idx, t) for idx, t in candidate_transactions if float(t.get('total', 0) or 0) > 0]
                
                # Ищем пары: одна отрицательная, одна положительная
                for neg_idx, neg_tx in negative_transactions:
                    for pos_idx, pos_tx in positive_transactions:
                        neg_amount = abs(float(neg_tx.get('total', 0) or 0))
                        pos_amount = float(pos_tx.get('total', 0) or 0)
                        
                        # Проверяем, что суммы совпадают (с небольшой погрешностью)
                        if abs(neg_amount - pos_amount) < 0.01:
                            # Проверяем, что это разные счета
                            from_account = neg_tx.get('payment_method', '')
                            to_account = pos_tx.get('payment_method', '')
                            
                            if from_account and to_account and from_account != to_account:
                                # Добавляем обе транзакции как переводы
                                transfer_ids.add(neg_idx)
                                transfer_ids.add(pos_idx)
                                break
        
        return transfer_ids
    
    def _export_income_table(self, transactions: List[Dict], output_dir: str, year: int, month: int) -> Optional[str]:
        """Экспортирует таблицу доходов (исключая переводы между счетами)"""
        try:
            # Определяем какие транзакции являются переводами
            transfer_ids = self._identify_transfers(transactions)
            
            # Фильтруем только доходы, исключая переводы
            incomes = []
            for i, transaction in enumerate(transactions):
                if i in transfer_ids:
                    continue  # Пропускаем переводы
                
                amount = float(transaction.get('total', 0) or 0)
                source = transaction.get('source', '').lower()
                category = transaction.get('category', '').lower()
                merchant = transaction.get('merchant', '').lower()
                
                # Определяем доходы по ключевым словам и категориям
                is_income = (
                    # Категория указывает на доход
                    any(keyword in category for keyword in [
                        'зарплата', 'salary', 'фриланс', 'freelance', 'подарки', 'gifts',
                        'прочие доходы', 'other income', 'доходы', 'income'
                    ]) or
                    # Название магазина/мерчанта указывает на доход
                    any(keyword in merchant for keyword in [
                        'заработал', 'получил зарплату', 'получил подарок'
                    ])
                )
                
                if is_income:
                    incomes.append(transaction)
            
            filename = f"income_{year}_{month:02d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'source', 'amount', 'currency', 'category', 'account', 'notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                if incomes:
                    for income in incomes:
                        writer.writerow({
                            'date': income.get('date', ''),
                            'source': income.get('merchant', ''),
                            'amount': income.get('total', ''),
                            'currency': income.get('currency', ''),
                            'category': income.get('category', ''),
                            'account': income.get('payment_method', ''),
                            'notes': self._generate_notes(income)
                        })
                    
                    logger.info(f"Exported {len(incomes)} income records to {filepath}")
                else:
                    logger.info(f"Created empty income table at {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте доходов: {e}")
            return None
    
    def _export_expense_table(self, transactions: List[Dict], output_dir: str, year: int, month: int) -> Optional[str]:
        """Экспортирует таблицу расходов (исключая переводы между счетами)"""
        try:
            # Определяем какие транзакции являются переводами
            transfer_ids = self._identify_transfers(transactions)
            
            # Фильтруем только расходы, исключая переводы
            expenses = []
            for i, transaction in enumerate(transactions):
                if i in transfer_ids:
                    continue  # Пропускаем переводы
                
                amount = float(transaction.get('total', 0) or 0)
                source = transaction.get('source', '').lower()
                category = transaction.get('category', '').lower()
                merchant = transaction.get('merchant', '').lower()
                
                # Определяем расходы по ключевым словам и категориям
                is_expense = (
                    # Отрицательная сумма (для переводов)
                    amount < 0 or
                    # Расходные категории
                    any(keyword in category for keyword in [
                        'groceries', 'продукты', 'питание', 'покупки', 'purchases',
                        'программное обеспечение', 'образование и саморазвитие'
                    ]) or
                    # Расходные магазины/мерчанты
                    any(keyword in merchant for keyword in [
                        'rewe', 'aldi', 'yaz', 'supermarkt', 'adobe', 'openai',
                        'casa-idea', 'bft', 'головна частка'
                    ]) or
                    # Фото чеков (обычно расходы)
                    source.startswith('enhanced_photo') or source.startswith('photo') or
                    # Любая транзакция с нулевой суммой (обычно ошибки)
                    amount == 0
                )
                
                if is_expense:
                    expenses.append(transaction)
            
            filename = f"expenses_{year}_{month:02d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'merchant', 'amount', 'currency', 'category', 'payment_method', 'notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                if expenses:
                    for expense in expenses:
                        writer.writerow({
                            'date': expense.get('date', ''),
                            'merchant': expense.get('merchant', ''),
                            'amount': abs(float(expense.get('total', 0) or 0)),  # Положительное значение
                            'currency': expense.get('currency', ''),
                            'category': expense.get('category', ''),
                            'payment_method': expense.get('payment_method', ''),
                            'notes': self._generate_notes(expense)
                        })
                    
                    logger.info(f"Exported {len(expenses)} expense records to {filepath}")
                else:
                    logger.info(f"Created empty expenses table at {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте расходов: {e}")
            return None
    
    def _export_accounts_table(self, output_dir: str, year: int, month: int) -> Optional[str]:
        """Экспортирует таблицу счетов"""
        try:
            filename = f"accounts_{year}_{month:02d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['account_name', 'currency', 'balance', 'export_date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                if self.accounts:
                    for account_name, account_data in self.accounts.items():
                        writer.writerow({
                            'account_name': account_name,
                            'currency': account_data.get('currency', ''),
                            'balance': account_data.get('amount', 0),
                            'export_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                    
                    logger.info(f"Exported {len(self.accounts)} accounts to {filepath}")
                else:
                    logger.info(f"Created empty accounts table at {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте счетов: {e}")
            return None
    
    def _export_transfers_table(self, transactions: List[Dict], output_dir: str, year: int, month: int) -> Optional[str]:
        """Экспортирует таблицу обменов (переводов между счетами)"""
        try:
            # Определяем какие транзакции являются переводами
            transfer_ids = self._identify_transfers(transactions)
            
            # Создаем записи о переводах
            transfers = []
            transfer_candidates = defaultdict(list)
            
            # Группируем переводы по ключу (дата + валюта + сумма)
            for i, transaction in enumerate(transactions):
                if i in transfer_ids:
                    amount = float(transaction.get('total', 0) or 0)
                    key = (transaction.get('date', ''), transaction.get('currency', ''), abs(amount))
                    transfer_candidates[key].append((i, transaction))
            
            # Создаем записи о переводах
            for key, candidate_transactions in transfer_candidates.items():
                if len(candidate_transactions) >= 2:
                    # Разделяем на отрицательные и положительные
                    negative_transactions = [(idx, t) for idx, t in candidate_transactions if float(t.get('total', 0) or 0) < 0]
                    positive_transactions = [(idx, t) for idx, t in candidate_transactions if float(t.get('total', 0) or 0) > 0]
                    
                    # Создаем записи о переводах
                    for neg_idx, neg_tx in negative_transactions:
                        for pos_idx, pos_tx in positive_transactions:
                            neg_amount = abs(float(neg_tx.get('total', 0) or 0))
                            pos_amount = float(pos_tx.get('total', 0) or 0)
                            
                            # Проверяем, что суммы совпадают (с небольшой погрешностью)
                            if abs(neg_amount - pos_amount) < 0.01:
                                # Проверяем, что это разные счета
                                from_account = neg_tx.get('payment_method', '')
                                to_account = pos_tx.get('payment_method', '')
                                
                                if from_account and to_account and from_account != to_account:
                                    transfers.append({
                                        'date': neg_tx.get('date', ''),
                                        'from_account': from_account,
                                        'to_account': to_account,
                                        'amount': neg_amount,
                                        'currency': neg_tx.get('currency', ''),
                                        'notes': f"Transfer: {neg_tx.get('merchant', '')} -> {pos_tx.get('merchant', '')}"
                                    })
                                    break
            
            # Создаем файл таблицы переводов
            filename = f"transfers_{year}_{month:02d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'from_account', 'to_account', 'amount', 'currency', 'notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for transfer in transfers:
                    writer.writerow(transfer)
            
            if transfers:
                logger.info(f"Exported {len(transfers)} transfer records to {filepath}")
            else:
                logger.info(f"Created empty transfers table at {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте переводов: {e}")
            return None
    
    def _export_summary_table(self, transactions: List[Dict], output_dir: str, year: int, month: int) -> Optional[str]:
        """Экспортирует сводную таблицу всех транзакций"""
        try:
            filename = f"summary_{year}_{month:02d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['date', 'type', 'merchant', 'amount', 'currency', 'category', 'account', 'notes']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                if transactions:
                    for transaction in transactions:
                        amount = float(transaction.get('total', 0) or 0)
                        transaction_type = 'income' if amount > 0 else 'expense' if amount < 0 else 'zero'
                        
                        writer.writerow({
                            'date': transaction.get('date', ''),
                            'type': transaction_type,
                            'merchant': transaction.get('merchant', ''),
                            'amount': abs(amount),  # Всегда положительное значение
                            'currency': transaction.get('currency', ''),
                            'category': transaction.get('category', ''),
                            'account': transaction.get('payment_method', ''),
                            'notes': self._generate_notes(transaction)
                        })
                    
                    logger.info(f"Exported {len(transactions)} summary records to {filepath}")
                else:
                    logger.info(f"Created empty summary table at {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте сводной таблицы: {e}")
            return None


def export_monthly_data(user_id: int, year: int, month: int, output_dir: str = None) -> Dict:
    """
    Функция для экспорта данных за конкретный месяц
    
    Args:
        user_id: ID пользователя
        year: Год
        month: Месяц (1-12)
        output_dir: Директория для сохранения файлов
        
    Returns:
        Dict с результатами экспорта
    """
    try:
        exporter = EnhancedExporter(user_id)
        return exporter.export_monthly_data(year, month, output_dir)
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Ошибка при экспорте: {e}'
        }


def export_current_month(user_id: int, output_dir: str = None) -> Dict:
    """Экспортирует данные за текущий месяц"""
    try:
        exporter = EnhancedExporter(user_id)
        return exporter.export_current_month(output_dir)
    except Exception as e:
        logger.error(f"Ошибка при экспорте текущего месяца для пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Ошибка при экспорте: {e}'
        }


def export_last_n_months(user_id: int, months_count: int, output_dir: str = None) -> Dict:
    """Экспортирует данные за последние N месяцев"""
    try:
        exporter = EnhancedExporter(user_id)
        return exporter.export_last_n_months(months_count, output_dir)
    except Exception as e:
        logger.error(f"Ошибка при экспорте за {months_count} месяцев для пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Ошибка при экспорте: {e}'
        }


def create_export_archive(user_id: int, year: int, month: int, output_dir: str = None) -> Dict:
    """
    Создает архив с экспортированными данными
    
    Args:
        user_id: ID пользователя
        year: Год
        month: Месяц
        output_dir: Директория для сохранения архива
        
    Returns:
        Dict с результатами создания архива
    """
    try:
        import zipfile
        import tempfile
        
        # Экспортируем данные
        export_result = export_monthly_data(user_id, year, month, output_dir)
        
        if not export_result.get('success'):
            return export_result
        
        files_created = export_result.get('files_created', [])
        if not files_created:
            return {
                'success': False,
                'message': 'Нет файлов для архивирования'
            }
        
        # Создаем архив
        if not output_dir:
            output_dir = f"exports/{user_id}"
        
        archive_name = f"finance_export_{user_id}_{year}_{month:02d}.zip"
        archive_path = os.path.join(output_dir, archive_name)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_created:
                if os.path.exists(file_path):
                    # Добавляем файл в архив с относительным путем
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        
        # Удаляем отдельные файлы после архивирования
        for file_path in files_created:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        logger.info(f"Created archive {archive_path} with {len(files_created)} files")
        
        return {
            'success': True,
            'archive_path': archive_path,
            'files_count': len(files_created),
            'message': f'Архив создан: {archive_name}'
        }
        
    except Exception as e:
        logger.error(f"Ошибка при создании архива для пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f'Ошибка при создании архива: {e}'
        }
