# app/keyboards/advanced.py
"""Продвинутые клавиатуры для Finance Bot"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from typing import List, Dict, Any


def create_inline_keyboard(buttons: List[List[Dict[str, str]]]) -> InlineKeyboardMarkup:
    """Создать inline клавиатуру из списка кнопок"""
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button in row:
            keyboard_row.append(
                InlineKeyboardButton(
                    text=button["text"],
                    callback_data=button["callback_data"]
                )
            )
        keyboard.append(keyboard_row)
    
    return InlineKeyboardMarkup(keyboard)


def analytics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для аналитики"""
    buttons = [
        [
            {"text": "📊 Тренды", "callback_data": "analytics_trends"},
            {"text": "📈 Категории", "callback_data": "analytics_categories"}
        ],
        [
            {"text": "🏪 Магазины", "callback_data": "analytics_merchants"},
            {"text": "📅 Паттерны", "callback_data": "analytics_patterns"}
        ],
        [
            {"text": "⬅️ Назад", "callback_data": "back_to_main"}
        ]
    ]
    return create_inline_keyboard(buttons)


def period_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода"""
    buttons = [
        [
            {"text": "📅 Сегодня", "callback_data": "period_today"},
            {"text": "📆 Неделя", "callback_data": "period_week"}
        ],
        [
            {"text": "📊 Месяц", "callback_data": "period_month"},
            {"text": "📈 3 месяца", "callback_data": "period_quarter"}
        ],
        [
            {"text": "📋 Год", "callback_data": "period_year"},
            {"text": "🔧 Настроить", "callback_data": "period_custom"}
        ]
    ]
    return create_inline_keyboard(buttons)


def category_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления категориями"""
    buttons = [
        [
            {"text": "➕ Добавить", "callback_data": "category_add"},
            {"text": "✏️ Редактировать", "callback_data": "category_edit"}
        ],
        [
            {"text": "🗑 Удалить", "callback_data": "category_delete"},
            {"text": "📋 Список", "callback_data": "category_list"}
        ],
        [
            {"text": "⬅️ Назад", "callback_data": "back_to_rules"}
        ]
    ]
    return create_inline_keyboard(buttons)


def account_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления счетами"""
    buttons = [
        [
            {"text": "➕ Добавить счет", "callback_data": "account_add"},
            {"text": "✏️ Редактировать", "callback_data": "account_edit"}
        ],
        [
            {"text": "💰 Пополнить", "callback_data": "account_topup"},
            {"text": "📊 Статистика", "callback_data": "account_stats"}
        ],
        [
            {"text": "⬅️ Назад", "callback_data": "back_to_balance"}
        ]
    ]
    return create_inline_keyboard(buttons)


def quick_actions_keyboard() -> ReplyKeyboardMarkup:
    """Быстрые действия"""
    return ReplyKeyboardMarkup(
        [
            ["📸 Чек", "🎙️ Голос"],
            ["💰 Баланс", "📊 Статистика"],
            ["⚙️ Настройки", "❓ Помощь"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    buttons = [
        [
            {"text": "🔔 Уведомления", "callback_data": "settings_notifications"},
            {"text": "🌍 Язык", "callback_data": "settings_language"}
        ],
        [
            {"text": "💱 Валюты", "callback_data": "settings_currencies"},
            {"text": "📱 Тема", "callback_data": "settings_theme"}
        ],
        [
            {"text": "🔒 Безопасность", "callback_data": "settings_security"},
            {"text": "📤 Экспорт", "callback_data": "settings_export"}
        ],
        [
            {"text": "⬅️ Назад", "callback_data": "back_to_main"}
        ]
    ]
    return create_inline_keyboard(buttons)


def confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    buttons = [
        [
            {"text": "✅ Да", "callback_data": f"confirm_{action}"},
            {"text": "❌ Нет", "callback_data": f"cancel_{action}"}
        ]
    ]
    return create_inline_keyboard(buttons)
