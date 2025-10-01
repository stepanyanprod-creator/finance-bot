# app/services/google_sheets_sync.py
"""
Сервис для синхронизации данных с Google Sheets
"""
import os
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from app.database.service import get_database_service
from app.logger import get_logger

logger = get_logger(__name__)

class GoogleSheetsSync:
    """Сервис синхронизации с Google Sheets"""
    
    def __init__(self):
        self.credentials = None
        self.client = None
        self._setup_credentials()
    
    def _setup_credentials(self):
        """Настройка учетных данных Google"""
        try:
            # Получаем путь к файлу учетных данных
            creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
            
            if not os.path.exists(creds_path):
                logger.warning(f"Файл учетных данных не найден: {creds_path}")
                return False
            
            # Настраиваем область доступа
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Загружаем учетные данные
            self.credentials = Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            
            # Создаем клиент
            self.client = gspread.authorize(self.credentials)
            
            logger.info("Google Sheets API настроен успешно")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка настройки Google Sheets API: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Проверить, настроен ли сервис"""
        return self.client is not None
    
    def create_spreadsheet(self, title: str = "Finance Bot Data") -> Optional[str]:
        """Создать новую таблицу"""
        if not self.is_configured():
            return None
        
        try:
            spreadsheet = self.client.create(title)
            logger.info(f"Создана таблица: {spreadsheet.id}")
            return spreadsheet.id
        except Exception as e:
            logger.error(f"Ошибка создания таблицы: {e}")
            return None
    
    def sync_user_data(self, user_id: int, spreadsheet_id: str) -> bool:
        """Синхронизировать данные пользователя с таблицей"""
        if not self.is_configured():
            return False
        
        try:
            db_service = get_database_service()
            spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            # Получаем данные пользователя
            user = db_service.get_user(user_id)
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return False
            
            # Создаем листы
            self._create_transactions_sheet(spreadsheet, user_id, db_service)
            self._create_accounts_sheet(spreadsheet, user_id, db_service)
            self._create_rules_sheet(spreadsheet, user_id, db_service)
            self._create_summary_sheet(spreadsheet, user_id, db_service)
            
            logger.info(f"Данные пользователя {user_id} синхронизированы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации данных пользователя {user_id}: {e}")
            return False
    
    def _create_transactions_sheet(self, spreadsheet, user_id: int, db_service):
        """Создать лист с транзакциями"""
        try:
            # Удаляем старый лист если есть
            try:
                worksheet = spreadsheet.worksheet("Транзакции")
                spreadsheet.del_worksheet(worksheet)
            except:
                pass
            
            # Создаем новый лист
            worksheet = spreadsheet.add_worksheet(title="Транзакции", rows=1000, cols=10)
            
            # Заголовки
            headers = [
                "ID", "Дата", "Тип", "Сумма", "Валюта", "Категория", 
                "Магазин", "Способ оплаты", "Источник", "Заметки"
            ]
            worksheet.append_row(headers)
            
            # Получаем транзакции
            transactions = db_service.get_transactions(user_id, limit=500)
            
            for t in transactions:
                row = [
                    t.id,
                    t.date.strftime('%Y-%m-%d %H:%M:%S'),
                    t.transaction_type,
                    t.total,
                    t.currency,
                    t.category or '',
                    t.merchant or '',
                    t.payment_method or '',
                    t.source or '',
                    t.notes or ''
                ]
                worksheet.append_row(row)
            
            # Форматируем заголовки
            worksheet.format('A1:J1', {
                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.8},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
        except Exception as e:
            logger.error(f"Ошибка создания листа транзакций: {e}")
    
    def _create_accounts_sheet(self, spreadsheet, user_id: int, db_service):
        """Создать лист со счетами"""
        try:
            # Удаляем старый лист если есть
            try:
                worksheet = spreadsheet.worksheet("Счета")
                spreadsheet.del_worksheet(worksheet)
            except:
                pass
            
            # Создаем новый лист
            worksheet = spreadsheet.add_worksheet(title="Счета", rows=100, cols=5)
            
            # Заголовки
            headers = ["ID", "Название", "Валюта", "Баланс", "Активен"]
            worksheet.append_row(headers)
            
            # Получаем счета
            accounts = db_service.get_accounts(user_id)
            
            for a in accounts:
                row = [
                    a.id,
                    a.name,
                    a.currency,
                    a.balance,
                    "Да" if a.is_active else "Нет"
                ]
                worksheet.append_row(row)
            
            # Форматируем заголовки
            worksheet.format('A1:E1', {
                'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
        except Exception as e:
            logger.error(f"Ошибка создания листа счетов: {e}")
    
    def _create_rules_sheet(self, spreadsheet, user_id: int, db_service):
        """Создать лист с правилами"""
        try:
            # Удаляем старый лист если есть
            try:
                worksheet = spreadsheet.worksheet("Правила")
                spreadsheet.del_worksheet(worksheet)
            except:
                pass
            
            # Создаем новый лист
            worksheet = spreadsheet.add_worksheet(title="Правила", rows=100, cols=4)
            
            # Заголовки
            headers = ["ID", "Категория", "Условия", "Активно"]
            worksheet.append_row(headers)
            
            # Получаем правила
            rules = db_service.get_rules(user_id)
            
            for r in rules:
                conditions = json.loads(r.match_conditions)
                row = [
                    r.id,
                    r.category,
                    json.dumps(conditions, ensure_ascii=False),
                    "Да" if r.is_active else "Нет"
                ]
                worksheet.append_row(row)
            
            # Форматируем заголовки
            worksheet.format('A1:D1', {
                'backgroundColor': {'red': 0.8, 'green': 0.2, 'blue': 0.8},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
        except Exception as e:
            logger.error(f"Ошибка создания листа правил: {e}")
    
    def _create_summary_sheet(self, spreadsheet, user_id: int, db_service):
        """Создать сводный лист"""
        try:
            # Удаляем старый лист если есть
            try:
                worksheet = spreadsheet.worksheet("Сводка")
                spreadsheet.del_worksheet(worksheet)
            except:
                pass
            
            # Создаем новый лист
            worksheet = spreadsheet.add_worksheet(title="Сводка", rows=50, cols=3)
            
            # Заголовок
            worksheet.append_row(["СВОДКА ДАННЫХ"])
            worksheet.append_row([])
            
            # Статистика
            stats = db_service.get_user_stats(user_id)
            worksheet.append_row(["Показатель", "Значение"])
            worksheet.append_row(["Всего счетов", stats['accounts_count']])
            worksheet.append_row(["Всего транзакций", stats['transactions_count']])
            worksheet.append_row(["Всего правил", stats['rules_count']])
            worksheet.append_row([])
            
            # Статистика по категориям
            category_stats = db_service.get_category_stats(user_id)
            if category_stats:
                worksheet.append_row(["СТАТИСТИКА ПО КАТЕГОРИЯМ"])
                worksheet.append_row(["Категория", "Сумма"])
                
                for category, amount in category_stats.items():
                    worksheet.append_row([category, amount])
            
            # Форматируем заголовок
            worksheet.format('A1', {
                'backgroundColor': {'red': 0.1, 'green': 0.1, 'blue': 0.1},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
            })
            
        except Exception as e:
            logger.error(f"Ошибка создания сводного листа: {e}")
    
    def get_spreadsheet_url(self, spreadsheet_id: str) -> str:
        """Получить URL таблицы"""
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


# Глобальный экземпляр сервиса
google_sheets_sync = GoogleSheetsSync()


def sync_to_google_sheets(user_id: int, spreadsheet_id: str = None) -> Dict[str, Any]:
    """Синхронизировать данные пользователя с Google Sheets"""
    if not google_sheets_sync.is_configured():
        return {
            'success': False,
            'message': 'Google Sheets API не настроен. Добавьте файл google_credentials.json'
        }
    
    # Если ID таблицы не указан, создаем новую
    if not spreadsheet_id:
        spreadsheet_id = google_sheets_sync.create_spreadsheet(f"Finance Bot - User {user_id}")
        if not spreadsheet_id:
            return {
                'success': False,
                'message': 'Не удалось создать таблицу'
            }
    
    # Синхронизируем данные
    success = google_sheets_sync.sync_user_data(user_id, spreadsheet_id)
    
    if success:
        url = google_sheets_sync.get_spreadsheet_url(spreadsheet_id)
        return {
            'success': True,
            'spreadsheet_id': spreadsheet_id,
            'url': url,
            'message': 'Данные успешно синхронизированы с Google Sheets'
        }
    else:
        return {
            'success': False,
            'message': 'Ошибка синхронизации данных'
        }
