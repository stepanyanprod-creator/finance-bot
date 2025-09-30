# app/services/ml_categorizer.py
import json
import pickle
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass
import os

from app.logger import get_logger
from app.models import ReceiptData
from app.storage import read_rows

logger = get_logger(__name__)


@dataclass
class MLPrediction:
    """Предсказание ML модели"""
    category: str
    confidence: float
    features_used: List[str]


class SimpleMLCategorizer:
    """Простая ML модель для категоризации на основе правил и статистики"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.model_path = f"data/{user_id}/ml_model.pkl"
        self.feature_weights = self._initialize_feature_weights()
        self.category_stats = self._load_category_statistics()
        
    def _initialize_feature_weights(self) -> Dict[str, float]:
        """Инициализация весов признаков"""
        return {
            "merchant_keywords": 0.4,
            "item_keywords": 0.3,
            "amount_range": 0.1,
            "time_pattern": 0.1,
            "frequency": 0.1
        }
    
    def _load_category_statistics(self) -> Dict[str, Any]:
        """Загрузка статистики категорий пользователя"""
        try:
            stats_path = f"data/{self.user_id}/category_stats.json"
            if os.path.exists(stats_path):
                with open(stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading category stats: {e}")
        
        return {
            "categories": {},
            "merchants": {},
            "amount_ranges": {},
            "time_patterns": {},
            "item_keywords": {}
        }
    
    def _save_category_statistics(self):
        """Сохранение статистики категорий"""
        try:
            stats_path = f"data/{self.user_id}/category_stats.json"
            os.makedirs(os.path.dirname(stats_path), exist_ok=True)
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.category_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving category stats: {e}")
    
    def predict_category(self, receipt_data: ReceiptData) -> MLPrediction:
        """Предсказание категории с помощью ML"""
        
        # Извлекаем признаки
        features = self._extract_features(receipt_data)
        
        # Вычисляем скоринг для каждой категории
        category_scores = {}
        
        for category in self._get_known_categories():
            score = self._calculate_category_score(category, features)
            category_scores[category] = score
        
        # Выбираем лучшую категорию
        if category_scores:
            best_category = max(category_scores.keys(), key=lambda x: category_scores[x])
            confidence = min(category_scores[best_category], 1.0)
            
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category(best_category)
            
            if validated_cat:
                return MLPrediction(
                    category=validated_cat,
                    confidence=confidence,
                    features_used=list(features.keys())
                )
        
        # Если нет данных, возвращаем дефолтную категорию
        from app.categories import validate_and_normalize_category
        validated_cat = validate_and_normalize_category("Прочие расходы")
        
        return MLPrediction(
            category=validated_cat or "",
            confidence=0.1,
            features_used=[]
        )
    
    def _extract_features(self, receipt_data: ReceiptData) -> Dict[str, Any]:
        """Извлечение признаков из данных чека"""
        features = {}
        
        # Признаки магазина
        if receipt_data.merchant:
            features["merchant"] = receipt_data.merchant.lower()
            features["merchant_keywords"] = self._extract_merchant_keywords(receipt_data.merchant)
        
        # Признаки товаров
        if receipt_data.items:
            features["item_keywords"] = self._extract_item_keywords(receipt_data.items)
            features["item_count"] = len(receipt_data.items)
            features["avg_item_price"] = sum(item.price for item in receipt_data.items) / len(receipt_data.items)
        
        # Признаки суммы
        features["amount"] = receipt_data.total
        features["amount_range"] = self._get_amount_range(receipt_data.total)
        
        # Признаки времени
        features["time_pattern"] = self._extract_time_pattern(receipt_data.date)
        
        return features
    
    def _extract_merchant_keywords(self, merchant: str) -> List[str]:
        """Извлечение ключевых слов из названия магазина"""
        merchant_lower = merchant.lower()
        keywords = []
        
        # Специфичные слова для категорий
        keyword_mapping = {
            "продукты": ["rewe", "lidl", "aldi", "edeka", "kaufland", "пятерочка", "магнит"],
            "рестораны": ["mcdonalds", "kfc", "burger", "пицца", "ресторан", "кафе"],
            "аптеки": ["apotheke", "pharmacy", "аптека", "мед"],
            "транспорт": ["shell", "bp", "esso", "азс", "заправка"],
            "одежда": ["h&m", "zara", "uniqlo", "adidas", "nike"],
            "электроника": ["media markt", "saturn", "apple", "samsung"]
        }
        
        for category, words in keyword_mapping.items():
            for word in words:
                if word in merchant_lower:
                    keywords.append(category)
        
        return keywords
    
    def _extract_item_keywords(self, items: List) -> List[str]:
        """Извлечение ключевых слов из товаров"""
        all_text = " ".join(item.name.lower() for item in items)
        keywords = []
        
        # Ключевые слова для категорий
        category_keywords = {
            "продукты": ["хлеб", "молоко", "мясо", "овощи", "фрукты", "сыр", "йогурт"],
            "напитки": ["вода", "сок", "кофе", "чай", "пиво", "вино"],
            "сладости": ["шоколад", "конфеты", "печенье", "торт", "мороженое"],
            "здоровье": ["лекарство", "таблетки", "витамины", "крем", "шампунь"],
            "транспорт": ["бензин", "дизель", "топливо", "парковка"],
            "одежда": ["рубашка", "брюки", "платье", "обувь", "куртка"],
            "электроника": ["телефон", "компьютер", "наушники", "кабель"]
        }
        
        for category, words in category_keywords.items():
            for word in words:
                if word in all_text:
                    keywords.append(category)
        
        return keywords
    
    def _get_amount_range(self, amount: float) -> str:
        """Определение диапазона суммы"""
        if amount < 10:
            return "small"
        elif amount < 50:
            return "medium"
        elif amount < 200:
            return "large"
        else:
            return "very_large"
    
    def _extract_time_pattern(self, date_str: str) -> str:
        """Извлечение паттерна времени"""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            weekday = date_obj.weekday()
            
            if weekday < 5:  # Понедельник-пятница
                return "weekday"
            else:  # Суббота-воскресенье
                return "weekend"
        except:
            return "unknown"
    
    def _get_known_categories(self) -> List[str]:
        """Получение списка известных категорий"""
        categories = set(self.category_stats.get("categories", {}).keys())
        
        # Добавляем базовые категории
        base_categories = [
            "Продукты", "Напитки", "Сладости", "Здоровье", "Транспорт",
            "Одежда", "Электроника", "Дом", "Красота", "Спорт", "Рестораны"
        ]
        categories.update(base_categories)
        
        return list(categories)
    
    def _calculate_category_score(self, category: str, features: Dict[str, Any]) -> float:
        """Вычисление скора для категории"""
        score = 0.0
        
        # Скор на основе статистики пользователя
        user_stats = self.category_stats.get("categories", {}).get(category, {})
        if user_stats:
            frequency = user_stats.get("count", 0)
            if frequency > 0:
                score += self.feature_weights["frequency"] * min(frequency / 100, 1.0)
        
        # Скор на основе ключевых слов магазина
        merchant_keywords = features.get("merchant_keywords", [])
        if category.lower() in merchant_keywords:
            score += self.feature_weights["merchant_keywords"]
        
        # Скор на основе ключевых слов товаров
        item_keywords = features.get("item_keywords", [])
        if category.lower() in item_keywords:
            score += self.feature_weights["item_keywords"]
        
        # Скор на основе диапазона суммы
        amount_range = features.get("amount_range", "")
        category_amount_stats = self.category_stats.get("amount_ranges", {}).get(category, {})
        if amount_range in category_amount_stats:
            score += self.feature_weights["amount_range"] * 0.5
        
        # Скор на основе времени
        time_pattern = features.get("time_pattern", "")
        category_time_stats = self.category_stats.get("time_patterns", {}).get(category, {})
        if time_pattern in category_time_stats:
            score += self.feature_weights["time_pattern"] * 0.5
        
        return score
    
    def train(self, training_data: List[Dict[str, Any]]):
        """Обучение модели на исторических данных"""
        logger.info(f"Training ML model for user {self.user_id} with {len(training_data)} samples")
        
        for transaction in training_data:
            category = transaction.get("category", "")
            if not category:
                continue
            
            # Обновляем статистику категорий
            if "categories" not in self.category_stats:
                self.category_stats["categories"] = {}
            
            if category not in self.category_stats["categories"]:
                self.category_stats["categories"][category] = {"count": 0, "total_amount": 0}
            
            self.category_stats["categories"][category]["count"] += 1
            self.category_stats["categories"][category]["total_amount"] += transaction.get("total", 0)
            
            # Обновляем статистику магазинов
            merchant = transaction.get("merchant", "").lower()
            if merchant:
                if "merchants" not in self.category_stats:
                    self.category_stats["merchants"] = {}
                
                if merchant not in self.category_stats["merchants"]:
                    self.category_stats["merchants"][merchant] = {}
                
                if category not in self.category_stats["merchants"][merchant]:
                    self.category_stats["merchants"][merchant][category] = 0
                
                self.category_stats["merchants"][merchant][category] += 1
            
            # Обновляем статистику диапазонов сумм
            amount = transaction.get("total", 0)
            amount_range = self._get_amount_range(amount)
            
            if "amount_ranges" not in self.category_stats:
                self.category_stats["amount_ranges"] = {}
            
            if category not in self.category_stats["amount_ranges"]:
                self.category_stats["amount_ranges"][category] = {}
            
            if amount_range not in self.category_stats["amount_ranges"][category]:
                self.category_stats["amount_ranges"][category][amount_range] = 0
            
            self.category_stats["amount_ranges"][category][amount_range] += 1
        
        # Сохраняем обновленную статистику
        self._save_category_statistics()
        
        logger.info(f"ML model training completed for user {self.user_id}")
    
    def update_with_feedback(self, receipt_data: ReceiptData, correct_category: str):
        """Обновление модели на основе обратной связи"""
        # Создаем транзакцию для обучения
        transaction = {
            "merchant": receipt_data.merchant,
            "total": receipt_data.total,
            "category": correct_category,
            "date": receipt_data.date,
            "items": [{"name": item.name} for item in receipt_data.items]
        }
        
        # Обучаем на одном примере
        self.train([transaction])
        
        logger.info(f"Updated ML model with feedback: {receipt_data.merchant} -> {correct_category}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получение информации о модели"""
        total_categories = len(self.category_stats.get("categories", {}))
        total_merchants = len(self.category_stats.get("merchants", {}))
        total_transactions = sum(
            cat_stats.get("count", 0) 
            for cat_stats in self.category_stats.get("categories", {}).values()
        )
        
        return {
            "total_categories": total_categories,
            "total_merchants": total_merchants,
            "total_transactions": total_transactions,
            "feature_weights": self.feature_weights,
            "last_updated": "now"  # Можно добавить timestamp
        }
