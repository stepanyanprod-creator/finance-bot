# app/services/smart_categorization.py
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import statistics

from app.logger import get_logger
from app.models import ReceiptData, ReceiptItem
from app.rules import load_rules, apply_category_rules
from app.categories import get_category_keywords_dict, get_category_by_name

logger = get_logger(__name__)


@dataclass
class CategorySuggestion:
    """Предложение категории с уверенностью"""
    category: str
    confidence: float
    reason: str
    source: str  # "rules", "ml", "keywords", "merchant"


class SmartCategorizationService:
    """Умная система категоризации с множественными стратегиями"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.rules = load_rules(user_id)
        
        # Базовые категории и их ключевые слова
        self.category_keywords = self._load_category_keywords()
        
        # Паттерны для распознавания категорий
        self.category_patterns = self._load_category_patterns()
        
        # Статистика пользователя для обучения
        self.user_stats = self._load_user_statistics()
    
    def categorize_receipt(self, receipt_data: ReceiptData) -> CategorySuggestion:
        """Основной метод категоризации чека"""
        
        suggestions = []
        
        # 1. Применение пользовательских правил
        rule_category = apply_category_rules(receipt_data.__dict__, self.rules)
        if rule_category:
            suggestions.append(CategorySuggestion(
                category=rule_category,
                confidence=0.9,
                reason="Пользовательское правило",
                source="rules"
            ))
        
        # 2. Анализ по ключевым словам в товарах
        keyword_suggestion = self._categorize_by_keywords(receipt_data)
        if keyword_suggestion:
            suggestions.append(keyword_suggestion)
        
        # 3. Анализ по названию магазина
        merchant_suggestion = self._categorize_by_merchant(receipt_data)
        if merchant_suggestion:
            suggestions.append(merchant_suggestion)
        
        # 4. Анализ по сумме и паттернам
        pattern_suggestion = self._categorize_by_patterns(receipt_data)
        if pattern_suggestion:
            suggestions.append(pattern_suggestion)
        
        # 5. ML-анализ на основе истории пользователя
        ml_suggestion = self._categorize_by_ml(receipt_data)
        if ml_suggestion:
            suggestions.append(ml_suggestion)
        
        # Выбираем лучшее предложение
        if suggestions:
            best_suggestion = max(suggestions, key=lambda x: x.confidence)
            
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category(best_suggestion.category)
            
            if validated_cat:
                best_suggestion.category = validated_cat
                logger.info(f"Best category suggestion: {best_suggestion.category} (confidence: {best_suggestion.confidence})")
                return best_suggestion
            else:
                logger.warning(f"Invalid category suggested: {best_suggestion.category}, skipping")
        
        # Если ничего не найдено или все предложения невалидны, возвращаем None
        return CategorySuggestion(
            category="",
            confidence=0.0,
            reason="Не удалось определить валидную категорию",
            source="default"
        )
    
    def _categorize_by_keywords(self, receipt_data: ReceiptData) -> Optional[CategorySuggestion]:
        """Категоризация по ключевым словам в товарах"""
        if not receipt_data.items:
            return None
        
        # Собираем все названия товаров
        item_text = " ".join(item.name.lower() for item in receipt_data.items)
        
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword.lower() in item_text:
                    # Вес ключевого слова зависит от его специфичности
                    weight = self._get_keyword_weight(keyword)
                    score += weight
                    matched_keywords.append(keyword)
            
            if score > 0:
                category_scores[category] = {
                    'score': score,
                    'keywords': matched_keywords
                }
        
        if category_scores:
            best_category = max(category_scores.keys(), key=lambda x: category_scores[x]['score'])
            
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category(best_category)
            
            if validated_cat:
                confidence = min(category_scores[best_category]['score'] / 10.0, 0.8)  # Нормализуем до 0.8
                
                return CategorySuggestion(
                    category=validated_cat,
                    confidence=confidence,
                    reason=f"Ключевые слова: {', '.join(category_scores[best_category]['keywords'][:3])}",
                    source="keywords"
                )
        
        return None
    
    def _categorize_by_merchant(self, receipt_data: ReceiptData) -> Optional[CategorySuggestion]:
        """Категоризация по названию магазина"""
        if not receipt_data.merchant:
            return None
        
        merchant_lower = receipt_data.merchant.lower()
        
        # Специфичные магазины и их категории
        merchant_categories = {
            "продукты": ["rewe", "lidl", "aldi", "edeka", "kaufland", "пятерочка", "магнит", "перекресток"],
            "рестораны": ["mcdonalds", "kfc", "burger king", "subway", "пицца", "ресторан", "кафе"],
            "аптеки": ["apotheke", "pharmacy", "аптека", "доктор", "мед"],
            "транспорт": ["shell", "bp", "esso", "азс", "заправка", "парковка"],
            "одежда": ["h&m", "zara", "uniqlo", "adidas", "nike", "одежда", "обувь"],
            "электроника": ["media markt", "saturn", "apple", "samsung", "электроника", "техника"],
            "здоровье": ["fitness", "спорт", "тренажер", "йога", "бассейн"]
        }
        
        for category, merchants in merchant_categories.items():
            for merchant in merchants:
                if merchant in merchant_lower:
                    # Валидируем, что категория существует в стандартных категориях
                    from app.categories import validate_and_normalize_category
                    validated_cat = validate_and_normalize_category(category.title())
                    
                    if validated_cat:
                        return CategorySuggestion(
                            category=validated_cat,
                            confidence=0.7,
                            reason=f"Магазин: {receipt_data.merchant}",
                            source="merchant"
                        )
        
        return None
    
    def _categorize_by_patterns(self, receipt_data: ReceiptData) -> Optional[CategorySuggestion]:
        """Категоризация по паттернам (сумма, время, частота)"""
        
        # Анализ суммы
        total = receipt_data.total
        
        # Малые суммы часто связаны с продуктами
        if total < 20:
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category("Питание")
            
            if validated_cat:
                return CategorySuggestion(
                    category=validated_cat,
                    confidence=0.3,
                    reason=f"Малая сумма: {total}",
                    source="patterns"
                )
        
        # Большие суммы могут быть электроникой или одеждой
        if total > 200:
            # Валидируем, что категория существует в стандартных категориях
            from app.categories import validate_and_normalize_category
            validated_cat = validate_and_normalize_category("Прочие расходы")
            
            if validated_cat:
                return CategorySuggestion(
                    category=validated_cat,
                    confidence=0.4,
                    reason=f"Большая сумма: {total}",
                    source="patterns"
                )
        
        # Анализ количества товаров
        if receipt_data.items:
            item_count = len(receipt_data.items)
            
            # Много товаров = продукты
            if item_count > 10:
                # Валидируем, что категория существует в стандартных категориях
                from app.categories import validate_and_normalize_category
                validated_cat = validate_and_normalize_category("Питание")
                
                if validated_cat:
                    return CategorySuggestion(
                        category=validated_cat,
                        confidence=0.5,
                        reason=f"Много товаров: {item_count}",
                        source="patterns"
                    )
            
            # Один дорогой товар = электроника/одежда
            if item_count == 1 and total > 50:
                # Валидируем, что категория существует в стандартных категориях
                from app.categories import validate_and_normalize_category
                validated_cat = validate_and_normalize_category("Прочие расходы")
                
                if validated_cat:
                    return CategorySuggestion(
                        category=validated_cat,
                        confidence=0.4,
                        reason="Один дорогой товар",
                        source="patterns"
                    )
        
        return None
    
    def _categorize_by_ml(self, receipt_data: ReceiptData) -> Optional[CategorySuggestion]:
        """ML-категоризация на основе истории пользователя"""
        if not self.user_stats:
            return None
        
        # Простая реализация на основе частоты категорий для похожих покупок
        similar_purchases = self._find_similar_purchases(receipt_data)
        
        if similar_purchases:
            # Находим наиболее частую категорию среди похожих покупок
            categories = [purchase.get('category') for purchase in similar_purchases if purchase.get('category')]
            if categories:
                most_common = Counter(categories).most_common(1)[0]
                confidence = min(most_common[1] / len(similar_purchases), 0.6)
                
                return CategorySuggestion(
                    category=most_common[0],
                    confidence=confidence,
                    reason=f"Похожие покупки ({most_common[1]} из {len(similar_purchases)})",
                    source="ml"
                )
        
        return None
    
    def _find_similar_purchases(self, receipt_data: ReceiptData) -> List[Dict]:
        """Поиск похожих покупок в истории пользователя"""
        similar = []
        
        for purchase in self.user_stats.get('purchases', []):
            similarity_score = 0
            
            # Сравнение по магазину
            if purchase.get('merchant', '').lower() == receipt_data.merchant.lower():
                similarity_score += 3
            
            # Сравнение по сумме (в пределах 20%)
            purchase_total = purchase.get('total', 0)
            if purchase_total > 0:
                diff_percent = abs(receipt_data.total - purchase_total) / purchase_total
                if diff_percent < 0.2:
                    similarity_score += 2
            
            # Сравнение по товарам
            if receipt_data.items and purchase.get('items'):
                common_items = 0
                receipt_item_names = {item.name.lower() for item in receipt_data.items}
                purchase_item_names = {item.get('name', '').lower() for item in purchase.get('items', [])}
                
                common_items = len(receipt_item_names.intersection(purchase_item_names))
                similarity_score += common_items
            
            if similarity_score >= 2:
                similar.append(purchase)
        
        return similar[:10]  # Возвращаем топ-10 похожих покупок
    
    def _get_keyword_weight(self, keyword: str) -> float:
        """Получение веса ключевого слова"""
        # Более специфичные слова имеют больший вес
        if len(keyword) > 8:
            return 2.0
        elif len(keyword) > 5:
            return 1.5
        else:
            return 1.0
    
    def _load_category_keywords(self) -> Dict[str, List[str]]:
        """Загрузка ключевых слов для категорий"""
        return get_category_keywords_dict()
    
    def _load_category_patterns(self) -> Dict[str, Any]:
        """Загрузка паттернов для категоризации"""
        return {
            "time_patterns": {
                "Продукты": ["утром", "вечером", "выходные"],
                "Рестораны": ["обед", "ужин", "выходные"]
            },
            "amount_patterns": {
                "Продукты": {"min": 5, "max": 100, "typical": 30},
                "Электроника": {"min": 50, "max": 2000, "typical": 300},
                "Одежда": {"min": 20, "max": 500, "typical": 80}
            }
        }
    
    def _load_user_statistics(self) -> Dict[str, Any]:
        """Загрузка статистики пользователя"""
        # Здесь можно загрузить историю покупок пользователя
        # Пока возвращаем пустую статистику
        return {
            "purchases": [],
            "categories": {},
            "merchants": {},
            "patterns": {}
        }
    
    def learn_from_feedback(self, receipt_data: ReceiptData, correct_category: str):
        """Обучение на основе обратной связи пользователя"""
        # Добавляем покупку в статистику
        purchase_data = {
            "merchant": receipt_data.merchant,
            "total": receipt_data.total,
            "category": correct_category,
            "items": [{"name": item.name} for item in receipt_data.items],
            "date": receipt_data.date
        }
        
        if "purchases" not in self.user_stats:
            self.user_stats["purchases"] = []
        
        self.user_stats["purchases"].append(purchase_data)
        
        # Обновляем статистику категорий
        if "categories" not in self.user_stats:
            self.user_stats["categories"] = {}
        
        self.user_stats["categories"][correct_category] = self.user_stats["categories"].get(correct_category, 0) + 1
        
        logger.info(f"Learned from feedback: {receipt_data.merchant} -> {correct_category}")
    
    def get_category_suggestions(self, receipt_data: ReceiptData, limit: int = 3) -> List[CategorySuggestion]:
        """Получение нескольких предложений категорий"""
        suggestions = []
        
        # Собираем все возможные предложения
        rule_category = apply_category_rules(receipt_data.__dict__, self.rules)
        if rule_category:
            suggestions.append(CategorySuggestion(
                category=rule_category,
                confidence=0.9,
                reason="Пользовательское правило",
                source="rules"
            ))
        
        keyword_suggestion = self._categorize_by_keywords(receipt_data)
        if keyword_suggestion:
            suggestions.append(keyword_suggestion)
        
        merchant_suggestion = self._categorize_by_merchant(receipt_data)
        if merchant_suggestion:
            suggestions.append(merchant_suggestion)
        
        # Убираем дубликаты и сортируем по уверенности
        unique_suggestions = {}
        for suggestion in suggestions:
            if suggestion.category not in unique_suggestions or suggestion.confidence > unique_suggestions[suggestion.category].confidence:
                unique_suggestions[suggestion.category] = suggestion
        
        # Возвращаем топ предложения
        sorted_suggestions = sorted(unique_suggestions.values(), key=lambda x: x.confidence, reverse=True)
        return sorted_suggestions[:limit]
