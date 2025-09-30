# app/services/csv_importer.py
"""Сервис для импорта данных из CSV файлов"""

import csv
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from decimal import Decimal, InvalidOperation

from app.logger import get_logger

logger = get_logger(__name__)


class CSVBalanceImporter:
    """Класс для импорта балансов из CSV файла"""
    
    def __init__(self):
        self.accounts = {}
        self.monthly_data = {}
        self.currencies = set()
        
    def parse_csv_file(self, file_path: str) -> Dict:
        """
        Парсит CSV файл с балансами
        
        Args:
            file_path: Путь к CSV файлу
            
        Returns:
            Dict с данными: accounts, monthly_data, currencies
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
            
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("CSV файл пуст")
        if file_size > 10 * 1024 * 1024:  # 10MB лимит
            raise ValueError("CSV файл слишком большой (максимум 10MB)")
            
        logger.info(f"Начинаем парсинг файла: {file_path} (размер: {file_size} байт)")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # Определяем разделитель
                sample = file.read(1024)
                file.seek(0)
                
                # Пробуем разные разделители
                delimiter = ','
                if ';' in sample and sample.count(';') > sample.count(','):
                    delimiter = ';'
                elif '\t' in sample:
                    delimiter = '\t'
                    
                reader = csv.reader(file, delimiter=delimiter)
                rows = list(reader)
                
        except UnicodeDecodeError:
            # Пробуем другие кодировки
            try:
                with open(file_path, 'r', encoding='cp1251') as file:
                    sample = file.read(1024)
                    file.seek(0)
                    
                    delimiter = ','
                    if ';' in sample and sample.count(';') > sample.count(','):
                        delimiter = ';'
                    elif '\t' in sample:
                        delimiter = '\t'
                        
                    reader = csv.reader(file, delimiter=delimiter)
                    rows = list(reader)
            except UnicodeDecodeError:
                raise ValueError("Не удалось прочитать файл. Поддерживаются кодировки UTF-8 и CP1251")
            
        if not rows:
            raise ValueError("CSV файл пуст")
            
        if len(rows) < 2:
            raise ValueError("CSV файл должен содержать как минимум заголовок и одну строку данных")
            
        # Парсим заголовки (первая строка)
        headers = [col.strip() for col in rows[0]]
        logger.info(f"Найдены колонки: {headers}")
        
        # Валидация заголовков
        if not headers or all(not h for h in headers):
            raise ValueError("Заголовки CSV файла пусты")
            
        # Находим колонку с названиями счетов
        account_col = None
        for i, header in enumerate(headers):
            if any(keyword in header.lower() for keyword in ['bilanzen', 'balance', 'счет', 'account', 'название']):
                account_col = i
                break
                
        if account_col is None:
            raise ValueError("Не найдена колонка с названиями счетов. Ищите колонки с названиями: 'Bilanzen', 'Balance', 'Счет', 'Account'")
            
        # Парсим данные
        parsed_accounts = 0
        skipped_rows = 0
        
        for row_num, row in enumerate(rows[1:], start=2):
            if not row or len(row) <= account_col:
                skipped_rows += 1
                continue
                
            account_name = row[account_col].strip()
            if not account_name or account_name.lower() in ['summe', 'total', 'итого', '']:
                skipped_rows += 1
                continue
                
            # Валидация названия счета
            if len(account_name) > 100:
                logger.warning(f"Строка {row_num}: название счета слишком длинное, обрезаем: {account_name[:100]}")
                account_name = account_name[:100]
                
            # Парсим значения по месяцам
            monthly_values = {}
            for col_idx, header in enumerate(headers):
                if col_idx == account_col:
                    continue
                    
                if col_idx >= len(row):
                    continue
                    
                value_str = row[col_idx].strip()
                if not value_str:
                    continue
                    
                # Парсим значение и валюту
                value, currency = self._parse_value_and_currency(value_str)
                if value is not None:
                    monthly_values[header] = {
                        'value': value,
                        'currency': currency
                    }
                    self.currencies.add(currency)
                    
            if monthly_values:
                self.accounts[account_name] = monthly_values
                parsed_accounts += 1
            else:
                skipped_rows += 1
                
        if parsed_accounts == 0:
            raise ValueError("Не найдено ни одного счета с валидными данными")
            
        logger.info(f"Найдено счетов: {parsed_accounts}, пропущено строк: {skipped_rows}")
        logger.info(f"Найдены валюты: {self.currencies}")
        
        return {
            'accounts': self.accounts,
            'currencies': list(self.currencies),
            'headers': headers,
            'parsed_accounts': parsed_accounts,
            'skipped_rows': skipped_rows
        }
    
    def _parse_value_and_currency(self, value_str: str) -> Tuple[Optional[float], str]:
        """
        Парсит значение и валюту из строки
        
        Args:
            value_str: Строка вида "123.45 €" или "123,45 UAH"
            
        Returns:
            Tuple (значение, валюта)
        """
        if not value_str:
            return None, ''
            
        # Убираем лишние пробелы
        value_str = value_str.strip()
        
        # Определяем валюту
        currency = ''
        if '€' in value_str or 'EUR' in value_str.upper():
            currency = 'EUR'
        elif 'UAH' in value_str.upper() or '₴' in value_str:
            currency = 'UAH'
        elif 'USD' in value_str.upper() or '$' in value_str:
            currency = 'USD'
        elif 'RUB' in value_str.upper() or '₽' in value_str:
            currency = 'RUB'
        else:
            # Пробуем найти валюту в конце строки
            match = re.search(r'([A-Z]{3})$', value_str)
            if match:
                currency = match.group(1)
            else:
                currency = 'EUR'  # По умолчанию
                
        # Извлекаем числовое значение
        # Убираем все символы валют
        clean_value = re.sub(r'[€$₴₽]', '', value_str)
        clean_value = re.sub(r'[A-Z]{3}', '', clean_value)
        clean_value = clean_value.strip()
        
        # Заменяем запятую на точку
        clean_value = clean_value.replace(',', '.')
        
        # Убираем все нечисловые символы кроме точки и минуса
        clean_value = re.sub(r'[^\d.-]', '', clean_value)
        
        # Валидация: проверяем, что осталось что-то похожее на число
        if not clean_value or clean_value in ['.', '-', '-.']:
            logger.warning(f"Пустое значение после очистки: {value_str}")
            return None, currency
            
        # Проверяем на слишком большие числа
        try:
            value = float(clean_value)
            if abs(value) > 1e12:  # 1 триллион
                logger.warning(f"Слишком большое значение: {value}")
                return None, currency
            return value, currency
        except (ValueError, InvalidOperation):
            logger.warning(f"Не удалось распарсить значение: {value_str}")
            return None, currency
    
    def get_latest_balances(self) -> Dict[str, Dict[str, any]]:
        """
        Возвращает последние доступные балансы для каждого счета
        
        Returns:
            Dict с последними балансами
        """
        latest_balances = {}
        
        for account_name, monthly_data in self.accounts.items():
            if not monthly_data:
                continue
                
            # Находим последний месяц с данными
            latest_month = None
            latest_value = None
            latest_currency = None
            
            for month, data in monthly_data.items():
                if data['value'] is not None:
                    latest_month = month
                    latest_value = data['value']
                    latest_currency = data['currency']
                    
            if latest_month and latest_value is not None:
                latest_balances[account_name] = {
                    'amount': latest_value,
                    'currency': latest_currency,
                    'last_month': latest_month
                }
                
        return latest_balances
    
    def get_accounts_for_import(self) -> List[Dict[str, any]]:
        """
        Возвращает список счетов готовых для импорта в бот
        
        Returns:
            List с данными счетов
        """
        latest_balances = self.get_latest_balances()
        accounts_for_import = []
        
        for account_name, data in latest_balances.items():
            accounts_for_import.append({
                'name': account_name,
                'amount': data['amount'],
                'currency': data['currency'],
                'last_month': data['last_month']
            })
            
        return accounts_for_import


def import_csv_balances(file_path: str) -> Dict:
    """
    Функция для импорта балансов из CSV файла
    
    Args:
        file_path: Путь к CSV файлу
        
    Returns:
        Dict с результатами импорта
    """
    try:
        importer = CSVBalanceImporter()
        result = importer.parse_csv_file(file_path)
        
        # Добавляем готовые для импорта счета
        result['accounts_for_import'] = importer.get_accounts_for_import()
        
        return {
            'success': True,
            'data': result,
            'message': f"Успешно импортировано {len(result['accounts'])} счетов"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при импорте CSV: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"Ошибка при импорте: {e}"
        }


def auto_create_accounts_from_csv(user_id: int, csv_data: Dict, overwrite_existing: bool = False) -> Dict:
    """
    Автоматически создает счета из CSV данных
    
    Args:
        user_id: ID пользователя
        csv_data: Данные из CSV файла
        overwrite_existing: Перезаписывать ли существующие счета
        
    Returns:
        Dict с результатами создания счетов
    """
    from app.storage import add_account, list_accounts
    
    try:
        existing_accounts = list_accounts(user_id)
        accounts_for_import = csv_data.get('accounts_for_import', [])
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        for account in accounts_for_import:
            account_name = account['name']
            account_amount = account['amount']
            account_currency = account['currency']
            
            try:
                # Проверяем, существует ли счет
                if account_name in existing_accounts:
                    if overwrite_existing:
                        # Обновляем существующий счет
                        from app.storage import set_account_amount
                        set_account_amount(user_id, account_name, account_amount)
                        updated_count += 1
                        logger.info(f"Updated account {account_name} for user {user_id}")
                    else:
                        skipped_count += 1
                        logger.info(f"Skipped existing account {account_name} for user {user_id}")
                else:
                    # Создаем новый счет
                    add_account(user_id, account_name, account_currency, account_amount)
                    created_count += 1
                    logger.info(f"Created account {account_name} for user {user_id}")
                    
            except Exception as e:
                error_msg = f"Ошибка при создании счета '{account_name}': {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'success': True,
            'created': created_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors,
            'message': f"Создано: {created_count}, обновлено: {updated_count}, пропущено: {skipped_count}"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при автоматическом создании счетов для пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"Ошибка при создании счетов: {e}"
        }


def export_balances_to_csv(user_id: int, output_path: str = None) -> Dict:
    """
    Экспортирует текущие балансы пользователя в CSV формат
    
    Args:
        user_id: ID пользователя
        output_path: Путь для сохранения файла (опционально)
        
    Returns:
        Dict с результатами экспорта
    """
    from app.storage import list_accounts
    from datetime import datetime
    import csv
    
    try:
        accounts = list_accounts(user_id)
        
        if not accounts:
            return {
                'success': False,
                'message': 'У пользователя нет счетов для экспорта'
            }
        
        # Определяем путь для файла
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"balances_export_{user_id}_{timestamp}.csv"
        
        # Группируем счета по валютам
        currencies = {}
        for account_name, account_data in accounts.items():
            currency = account_data.get('currency', 'EUR')
            if currency not in currencies:
                currencies[currency] = []
            currencies[currency].append({
                'name': account_name,
                'amount': account_data.get('amount', 0.0)
            })
        
        # Создаем CSV файл
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            
            # Заголовки
            headers = ['Счет', 'Валюта', 'Баланс', 'Дата экспорта']
            writer.writerow(headers)
            
            # Данные
            export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for currency, accounts_list in currencies.items():
                for account in accounts_list:
                    writer.writerow([
                        account['name'],
                        currency,
                        f"{account['amount']:.2f}",
                        export_date
                    ])
        
        logger.info(f"Exported {len(accounts)} accounts for user {user_id} to {output_path}")
        
        return {
            'success': True,
            'file_path': output_path,
            'accounts_count': len(accounts),
            'currencies_count': len(currencies),
            'message': f"Экспортировано {len(accounts)} счетов в {len(currencies)} валютах"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте балансов для пользователя {user_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"Ошибка при экспорте: {e}"
        }
