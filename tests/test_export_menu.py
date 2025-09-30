# tests/test_export_menu.py
"""Тесты для меню экспорта"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from app.handlers.export import (
    export_menu_entry, export_menu_router, export_monthly_menu_router,
    parse_month_selection
)


class TestExportMenu:
    """Тесты для меню экспорта"""
    
    def test_parse_month_selection_current_month(self):
        """Тест парсинга текущего месяца"""
        today = date.today()
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]
        current_month_text = f"{month_names[today.month - 1]} {today.year}"
        
        year, month = parse_month_selection(current_month_text)
        
        assert year == today.year
        assert month == today.month
    
    def test_parse_month_selection_specific_month(self):
        """Тест парсинга конкретного месяца"""
        year, month = parse_month_selection("Март 2024")
        
        assert year == 2024
        assert month == 3
    
    def test_parse_month_selection_invalid(self):
        """Тест парсинга неверного формата"""
        year, month = parse_month_selection("Неверный формат")
        
        assert year is None
        assert month is None
    
    @patch('app.handlers.export.export_csv_command')
    async def test_export_menu_router_simple_csv(self, mock_export_csv):
        """Тест выбора простого CSV экспорта"""
        # Создаем мок объекты
        update = MagicMock()
        context = MagicMock()
        
        # Настраиваем мок
        update.effective_message.text = "📄 Простой CSV"
        
        # Вызываем функцию
        result = await export_menu_router(update, context)
        
        # Проверяем, что была вызвана команда экспорта
        mock_export_csv.assert_called_once_with(update, context)
        assert result == -1  # ConversationHandler.END
    
    @patch('app.handlers.export.export_balances_command')
    async def test_export_menu_router_balances(self, mock_export_balances):
        """Тест выбора экспорта балансов"""
        # Создаем мок объекты
        update = MagicMock()
        context = MagicMock()
        
        # Настраиваем мок
        update.effective_message.text = "💼 Балансы"
        
        # Вызываем функцию
        result = await export_menu_router(update, context)
        
        # Проверяем, что была вызвана команда экспорта балансов
        mock_export_balances.assert_called_once_with(update, context)
        assert result == -1  # ConversationHandler.END
    
    @patch('app.handlers.export.export_menu_entry')
    async def test_export_menu_router_back(self, mock_export_menu):
        """Тест возврата в меню экспорта"""
        # Создаем мок объекты
        update = MagicMock()
        context = MagicMock()
        
        # Настраиваем мок
        update.effective_message.text = "⬅️ Назад"
        
        # Вызываем функцию
        result = await export_menu_router(update, context)
        
        # Проверяем, что был вызван возврат в меню
        mock_export_menu.assert_called_once_with(update, context)
        assert result == 500  # EXPORT_MENU
    
    @patch('app.handlers.export.export_specific_month')
    async def test_export_monthly_menu_router_valid_month(self, mock_export_month):
        """Тест выбора валидного месяца"""
        # Создаем мок объекты
        update = MagicMock()
        context = MagicMock()
        
        # Настраиваем мок
        update.effective_message.text = "Март 2024"
        
        # Вызываем функцию
        result = await export_monthly_menu_router(update, context)
        
        # Проверяем, что был вызван экспорт месяца
        mock_export_month.assert_called_once_with(update, context, 2024, 3)
        assert result == -1  # ConversationHandler.END
    
    @patch('app.handlers.export.export_menu_entry')
    async def test_export_monthly_menu_router_back(self, mock_export_menu):
        """Тест возврата из меню выбора месяца"""
        # Создаем мок объекты
        update = MagicMock()
        context = MagicMock()
        
        # Настраиваем мок
        update.effective_message.text = "⬅️ Назад"
        
        # Вызываем функцию
        result = await export_monthly_menu_router(update, context)
        
        # Проверяем, что был вызван возврат в меню
        mock_export_menu.assert_called_once_with(update, context)
        assert result == 500  # EXPORT_MENU


def test_export_menu_keyboard_creation():
    """Тест создания клавиатуры меню экспорта"""
    from app.keyboards import export_menu_kb
    
    keyboard = export_menu_kb()
    
    # Проверяем, что клавиатура создана
    assert keyboard is not None
    assert hasattr(keyboard, 'keyboard')
    
    # Проверяем наличие основных кнопок
    keyboard_text = str(keyboard.keyboard)
    assert "📄 Простой CSV" in keyboard_text
    assert "📊 По месяцам" in keyboard_text
    assert "📅 Текущий месяц" in keyboard_text
    assert "📆 Последние 3 месяца" in keyboard_text
    assert "💼 Балансы" in keyboard_text
    assert "⬅️ Назад" in keyboard_text


def test_export_monthly_menu_keyboard_creation():
    """Тест создания клавиатуры выбора месяца"""
    from app.keyboards import export_monthly_menu_kb
    
    keyboard = export_monthly_menu_kb()
    
    # Проверяем, что клавиатура создана
    assert keyboard is not None
    assert hasattr(keyboard, 'keyboard')
    
    # Проверяем наличие кнопки "Назад"
    keyboard_text = str(keyboard.keyboard)
    assert "⬅️ Назад" in keyboard_text
