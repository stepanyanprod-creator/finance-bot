# app/services/analytics.py
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from collections import defaultdict
import statistics

from app.storage import read_rows
from app.models import StatsData, StatsPeriod
from app.utils import get_user_id, format_money


class AnalyticsService:
    """Сервис для аналитики финансовых данных"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def get_monthly_trends(self, months: int = 6) -> Dict[str, Any]:
        """Получить тренды за последние месяцы"""
        rows = read_rows(self.user_id)
        if not rows:
            return {"error": "Нет данных"}
        
        # Группируем по месяцам
        monthly_data = defaultdict(lambda: {"total": 0, "count": 0, "categories": defaultdict(float)})
        
        for row in rows:
            try:
                row_date = date.fromisoformat(row.get("date", ""))
                month_key = f"{row_date.year}-{row_date.month:02d}"
                
                amount = float(row.get("total", 0))
                category = row.get("category", "Без категории")
                
                monthly_data[month_key]["total"] += amount
                monthly_data[month_key]["count"] += 1
                monthly_data[month_key]["categories"][category] += amount
                
            except (ValueError, TypeError):
                continue
        
        # Сортируем по месяцам
        sorted_months = sorted(monthly_data.keys())
        recent_months = sorted_months[-months:] if len(sorted_months) > months else sorted_months
        
        return {
            "months": recent_months,
            "data": {month: monthly_data[month] for month in recent_months},
            "trend": self._calculate_trend([monthly_data[month]["total"] for month in recent_months])
        }
    
    def get_category_analysis(self, period_days: int = 30) -> Dict[str, Any]:
        """Анализ по категориям за период"""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        rows = read_rows(self.user_id)
        filtered_rows = self._filter_by_period(rows, start_date, end_date)
        
        if not filtered_rows:
            return {"error": "Нет данных за период"}
        
        category_stats = defaultdict(lambda: {"total": 0, "count": 0, "avg": 0})
        
        for row in filtered_rows:
            category = row.get("category", "Без категории")
            amount = float(row.get("total", 0))
            
            category_stats[category]["total"] += amount
            category_stats[category]["count"] += 1
        
        # Вычисляем средние значения
        for category, stats in category_stats.items():
            stats["avg"] = stats["total"] / stats["count"] if stats["count"] > 0 else 0
        
        # Сортируем по общей сумме
        sorted_categories = sorted(category_stats.items(), key=lambda x: x[1]["total"], reverse=True)
        
        return {
            "period": f"{start_date} - {end_date}",
            "categories": dict(sorted_categories),
            "total_spent": sum(stats["total"] for stats in category_stats.values()),
            "total_transactions": sum(stats["count"] for stats in category_stats.values())
        }
    
    def get_merchant_analysis(self, period_days: int = 30) -> Dict[str, Any]:
        """Анализ по торговым точкам"""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        rows = read_rows(self.user_id)
        filtered_rows = self._filter_by_period(rows, start_date, end_date)
        
        if not filtered_rows:
            return {"error": "Нет данных за период"}
        
        merchant_stats = defaultdict(lambda: {"total": 0, "count": 0, "last_visit": None})
        
        for row in filtered_rows:
            merchant = row.get("merchant", "Неизвестно")
            amount = float(row.get("total", 0))
            row_date = date.fromisoformat(row.get("date", ""))
            
            merchant_stats[merchant]["total"] += amount
            merchant_stats[merchant]["count"] += 1
            
            if (merchant_stats[merchant]["last_visit"] is None or 
                row_date > merchant_stats[merchant]["last_visit"]):
                merchant_stats[merchant]["last_visit"] = row_date
        
        # Сортируем по общей сумме
        sorted_merchants = sorted(merchant_stats.items(), key=lambda x: x[1]["total"], reverse=True)
        
        return {
            "period": f"{start_date} - {end_date}",
            "merchants": dict(sorted_merchants[:10]),  # Топ 10
            "total_merchants": len(merchant_stats)
        }
    
    def get_spending_patterns(self) -> Dict[str, Any]:
        """Анализ паттернов трат"""
        rows = read_rows(self.user_id)
        if not rows:
            return {"error": "Нет данных"}
        
        # Анализ по дням недели
        weekday_spending = defaultdict(float)
        # Анализ по времени месяца
        monthly_spending = defaultdict(float)
        
        for row in rows:
            try:
                row_date = date.fromisoformat(row.get("date", ""))
                amount = float(row.get("total", 0))
                
                # День недели (0 = понедельник, 6 = воскресенье)
                weekday_spending[row_date.weekday()] += amount
                # День месяца
                monthly_spending[row_date.day] += amount
                
            except (ValueError, TypeError):
                continue
        
        weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        
        return {
            "weekday_pattern": {
                weekday_names[day]: amount for day, amount in weekday_spending.items()
            },
            "monthly_pattern": dict(monthly_spending),
            "most_expensive_day": weekday_names[max(weekday_spending.keys(), key=lambda k: weekday_spending[k])] if weekday_spending else None
        }
    
    def _filter_by_period(self, rows: List[Dict], start_date: date, end_date: date) -> List[Dict]:
        """Фильтрация записей по периоду"""
        filtered = []
        for row in rows:
            try:
                row_date = date.fromisoformat(row.get("date", ""))
                if start_date <= row_date <= end_date:
                    filtered.append(row)
            except (ValueError, TypeError):
                continue
        return filtered
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Вычисление тренда (рост/падение/стабильно)"""
        if len(values) < 2:
            return "недостаточно данных"
        
        # Простой анализ тренда
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half) if first_half else 0
        second_avg = statistics.mean(second_half) if second_half else 0
        
        if second_avg > first_avg * 1.1:
            return "рост"
        elif second_avg < first_avg * 0.9:
            return "падение"
        else:
            return "стабильно"
