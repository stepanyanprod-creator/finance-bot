# app/categories.py
"""Стандартные категории расходов для Finance Bot"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Category:
    """Модель категории расходов"""
    id: str
    name: str
    emoji: str
    keywords: List[str]
    description: str = ""


# Стандартные категории расходов
STANDARD_CATEGORIES = {
    "nutrition": Category(
        id="nutrition",
        name="Питание",
        emoji="🍎",
        keywords=[
            "хлеб", "молоко", "мясо", "курица", "говядина", "свинина", "рыба",
            "овощи", "фрукты", "яблоки", "бананы", "апельсины", "помидоры",
            "огурцы", "картофель", "лук", "морковь", "сыр", "йогурт", "творог",
            "масло", "яйца", "колбаса", "сосиски", "консервы", "крупа", "макароны",
            "рис", "гречка", "овсянка", "мука", "сахар", "соль", "перец",
            "rewe", "lidl", "aldi", "edeka", "kaufland", "пятерочка", "магнит", "перекресток"
        ],
        description="Продукты питания и бакалея"
    ),
    
    "housing": Category(
        id="housing",
        name="Жильё",
        emoji="🏠",
        keywords=[
            "аренда", "квартплата", "коммунальные", "электричество", "газ", "вода",
            "отопление", "интернет", "телефон", "домофон", "лифт", "уборка",
            "ремонт", "мебель", "бытовая техника", "освещение", "сантехника"
        ],
        description="Расходы на жилье и коммунальные услуги"
    ),
    
    "household": Category(
        id="household",
        name="Бытовые товары",
        emoji="🧽",
        keywords=[
            "моющее средство", "стиральный порошок", "кондиционер", "туалетная бумага",
            "салфетки", "губки", "щетки", "перчатки", "посуда", "тарелки", "чашки",
            "кастрюли", "сковороды", "полотенца", "простыни", "подушки", "одеяла",
            "ковры", "пылесос", "швабра", "ведро", "тряпки"
        ],
        description="Товары для дома и быта"
    ),
    
    "transport": Category(
        id="transport",
        name="Транспорт",
        emoji="🚗",
        keywords=[
            "бензин", "дизель", "топливо", "парковка", "стоянка", "автобус",
            "метро", "такси", "поезд", "самолет", "билет", "проездной",
            "shell", "bp", "esso", "азс", "заправка", "uber", "яндекс такси"
        ],
        description="Транспортные расходы"
    ),
    
    "utilities": Category(
        id="utilities",
        name="Коммунальные и телекоммуникационные услуги",
        emoji="📱",
        keywords=[
            "интернет", "мобильная связь", "телефон", "кабельное", "спутниковое",
            "роуминг", "sms", "мобильный интернет", "wifi", "модем", "роутер"
        ],
        description="Связь и телекоммуникации"
    ),
    
    "health": Category(
        id="health",
        name="Здоровье, красота и спорт",
        emoji="💊",
        keywords=[
            "лекарство", "таблетки", "витамины", "аспирин", "парацетамол",
            "йод", "зеленка", "бинт", "пластырь", "крем", "шампунь",
            "зубная паста", "щетка", "мыло", "гель", "дезодорант",
            "косметика", "помада", "тушь", "тени", "лосьон", "духи",
            "тренажер", "гантели", "мяч", "ракетка", "лыжи", "коньки",
            "велосипед", "ролики", "спорт", "фитнес", "йога", "бассейн",
            "apotheke", "pharmacy", "аптека", "доктор", "мед"
        ],
        description="Здоровье, красота и спорт"
    ),
    
    "clothing": Category(
        id="clothing",
        name="Одежда и обувь",
        emoji="👕",
        keywords=[
            "рубашка", "блузка", "футболка", "брюки", "джинсы", "платье",
            "юбка", "куртка", "пальто", "обувь", "кроссовки", "туфли",
            "сапоги", "носки", "трусы", "лифчик", "белье", "шляпа", "перчатки",
            "h&m", "zara", "uniqlo", "adidas", "nike", "одежда"
        ],
        description="Одежда и обувь"
    ),
    
    "education": Category(
        id="education",
        name="Образование и саморазвитие",
        emoji="📚",
        keywords=[
            "книги", "учебники", "курсы", "обучение", "тренинги", "семинары",
            "конференции", "вебинары", "онлайн курсы", "языки", "программирование",
            "дизайн", "маркетинг", "бизнес", "психология", "саморазвитие"
        ],
        description="Образование и саморазвитие"
    ),
    
    "entertainment": Category(
        id="entertainment",
        name="Досуг и развлечения",
        emoji="🎬",
        keywords=[
            "кино", "театр", "концерт", "музей", "выставка", "парк",
            "аттракционы", "игры", "развлечения", "отдых", "отпуск",
            "путешествие", "отель", "билеты", "мероприятия"
        ],
        description="Досуг и развлечения"
    ),
    
    "gifts": Category(
        id="gifts",
        name="Подарки и благотворительность",
        emoji="🎁",
        keywords=[
            "подарок", "подарки", "сувенир", "цветы", "букет", "поздравление",
            "день рождения", "новый год", "рождество", "8 марта", "23 февраля",
            "благотворительность", "пожертвование", "помощь", "фонд"
        ],
        description="Подарки и благотворительность"
    ),
    
    "other": Category(
        id="other",
        name="Прочие расходы",
        emoji="📦",
        keywords=[
            "прочее", "разное", "неожиданные", "случайные", "непредвиденные"
        ],
        description="Прочие расходы"
    ),
    
    "banking": Category(
        id="banking",
        name="Банковские операции",
        emoji="🏦",
        keywords=[
            "комиссия", "обслуживание", "перевод", "конвертация", "снятие",
            "пополнение", "кредит", "займ", "проценты", "штраф", "пеня"
        ],
        description="Банковские операции и комиссии"
    ),
    
    "software": Category(
        id="software",
        name="Программное обеспечение",
        emoji="💻",
        keywords=[
            "приложение", "программа", "софт", "подписка", "лицензия",
            "app store", "google play", "steam", "netflix", "spotify",
            "youtube premium", "adobe", "microsoft", "office"
        ],
        description="Программное обеспечение и подписки"
    ),
    
    "electronics": Category(
        id="electronics",
        name="Техника",
        emoji="📱",
        keywords=[
            "телефон", "смартфон", "компьютер", "ноутбук", "планшет",
            "наушники", "колонки", "кабель", "зарядка", "адаптер",
            "мышь", "клавиатура", "монитор", "принтер", "роутер",
            "media markt", "saturn", "apple", "samsung", "электроника"
        ],
        description="Электроника и техника"
    ),
    
    "eating_out": Category(
        id="eating_out",
        name="Еда вне дома",
        emoji="🍽️",
        keywords=[
            "ресторан", "кафе", "бар", "пиццерия", "суши", "бургер",
            "mcdonalds", "kfc", "burger king", "subway", "пицца",
            "обед", "ужин", "завтрак", "кофе", "латте", "капучино",
            "доставка", "еда на вынос", "столовая", "буфет"
        ],
        description="Питание вне дома"
    )
}


# Категории доходов
INCOME_CATEGORIES = {
    "salary": Category(
        id="salary",
        name="Зарплата",
        emoji="💰",
        keywords=[
            "зарплата", "оклад", "заработная плата", "аванс", "премия", "бонус",
            "доплата", "надбавка", "тринадцатая зарплата", "отпускные", "больничные"
        ],
        description="Заработная плата и связанные выплаты"
    ),
    
    "freelance": Category(
        id="freelance",
        name="Фриланс",
        emoji="💻",
        keywords=[
            "фриланс", "проект", "заказ", "консультация", "разработка",
            "дизайн", "копирайтинг", "переводы", "репетиторство", "услуги",
            "подработка", "самозанятость"
        ],
        description="Доходы от фриланса и подработки"
    ),
    
    "business": Category(
        id="business",
        name="Бизнес",
        emoji="🏢",
        keywords=[
            "бизнес", "прибыль", "доход от бизнеса", "продажи", "выручка",
            "предпринимательство", "ип", "ооо", "торговля", "услуги"
        ],
        description="Доходы от предпринимательской деятельности"
    ),
    
    "investments": Category(
        id="investments",
        name="Инвестиции",
        emoji="📈",
        keywords=[
            "дивиденды", "проценты", "акции", "облигации", "депозит",
            "инвестиции", "доходность", "прибыль", "рента", "купоны",
            "криптовалюта", "forex", "трейдинг"
        ],
        description="Доходы от инвестиций и финансовых инструментов"
    ),
    
    "gifts": Category(
        id="gifts",
        name="Подарки",
        emoji="🎁",
        keywords=[
            "подарок", "подарки", "день рождения", "новый год", "праздник",
            "денежный подарок", "поздравление", "сувенир"
        ],
        description="Подарки и денежные поступления от близких"
    ),
    
    "refunds": Category(
        id="refunds",
        name="Возвраты",
        emoji="↩️",
        keywords=[
            "возврат", "возмещение", "компенсация", "страховка", "гарантия",
            "рефанд", "кешбэк", "cashback", "скидка", "бонусы", "возврат налогов"
        ],
        description="Возвраты, компенсации и возмещения"
    ),
    
    "rent": Category(
        id="rent",
        name="Аренда",
        emoji="🏠",
        keywords=[
            "аренда", "сдача", "арендная плата", "квартира", "недвижимость",
            "жилье", "комната", "дача", "гараж", "склад"
        ],
        description="Доходы от сдачи в аренду недвижимости"
    ),
    
    "social": Category(
        id="social",
        name="Социальные выплаты",
        emoji="🏛️",
        keywords=[
            "пенсия", "пособие", "стипендия", "алименты", "субсидия",
            "льготы", "материнский капитал", "детские", "безработица"
        ],
        description="Социальные выплаты и пособия"
    ),
    
    "other_income": Category(
        id="other_income",
        name="Прочие доходы",
        emoji="💵",
        keywords=[
            "прочее", "разное", "другое", "неожиданные", "случайные",
            "находка", "выигрыш", "приз", "лотерея"
        ],
        description="Прочие доходы"
    )
}


def get_category_by_id(category_id: str) -> Optional[Category]:
    """Получить категорию по ID"""
    return STANDARD_CATEGORIES.get(category_id)


def get_category_by_name(name: str) -> Optional[Category]:
    """Получить категорию по названию"""
    for category in STANDARD_CATEGORIES.values():
        if category.name.lower() == name.lower():
            return category
    return None


def get_all_categories() -> Dict[str, Category]:
    """Получить все категории"""
    return STANDARD_CATEGORIES.copy()


def get_categories_list() -> List[Category]:
    """Получить список всех категорий"""
    return list(STANDARD_CATEGORIES.values())


def search_categories_by_keyword(keyword: str) -> List[Category]:
    """Поиск категорий по ключевому слову"""
    keyword_lower = keyword.lower()
    matching_categories = []
    
    for category in STANDARD_CATEGORIES.values():
        # Поиск в названии
        if keyword_lower in category.name.lower():
            matching_categories.append(category)
            continue
            
        # Поиск в ключевых словах
        for cat_keyword in category.keywords:
            if keyword_lower in cat_keyword.lower():
                matching_categories.append(category)
                break
    
    return matching_categories


def get_category_keywords_dict() -> Dict[str, List[str]]:
    """Получить словарь категорий и их ключевых слов для совместимости"""
    return {category.name: category.keywords for category in STANDARD_CATEGORIES.values()}


def format_category_for_display(category: Category) -> str:
    """Форматировать категорию для отображения"""
    return f"{category.emoji} {category.name}"


def format_categories_list(categories: List[Category] = None) -> str:
    """Форматировать список категорий для отображения"""
    if categories is None:
        categories = get_categories_list()
    
    lines = ["📋 Доступные категории:"]
    for category in categories:
        lines.append(f"{category.emoji} {category.name}")
    
    return "\n".join(lines)


def is_valid_category(category_name: str) -> bool:
    """Проверить, является ли категория валидной (существует в стандартных категориях)"""
    if not category_name:
        return False
    
    # Проверяем точное совпадение по названию
    for category in STANDARD_CATEGORIES.values():
        if category.name.lower() == category_name.lower():
            return True
    
    return False


def validate_and_normalize_category(category_name: str) -> Optional[str]:
    """Валидировать и нормализовать название категории.
    Возвращает нормализованное название категории или None, если категория невалидна."""
    if not category_name:
        return None
    
    # Ищем точное совпадение по названию
    for category in STANDARD_CATEGORIES.values():
        if category.name.lower() == category_name.lower():
            return category.name
    
    return None


# Функции для работы с категориями доходов
def get_income_categories_list() -> List[Category]:
    """Получить список всех категорий доходов"""
    return list(INCOME_CATEGORIES.values())


def get_income_category_by_name(name: str) -> Optional[Category]:
    """Получить категорию доходов по названию"""
    for category in INCOME_CATEGORIES.values():
        if category.name.lower() == name.lower():
            return category
    return None


def get_income_category_by_id(category_id: str) -> Optional[Category]:
    """Получить категорию доходов по ID"""
    return INCOME_CATEGORIES.get(category_id)


def search_income_categories_by_keyword(keyword: str) -> List[Category]:
    """Поиск категорий доходов по ключевому слову"""
    keyword_lower = keyword.lower()
    matching_categories = []
    
    for category in INCOME_CATEGORIES.values():
        # Поиск в названии
        if keyword_lower in category.name.lower():
            matching_categories.append(category)
            continue
            
        # Поиск в ключевых словах
        for cat_keyword in category.keywords:
            if keyword_lower in cat_keyword.lower():
                matching_categories.append(category)
                break
    
    return matching_categories


def validate_and_normalize_income_category(category_name: str) -> Optional[str]:
    """Валидировать и нормализовать название категории доходов.
    Возвращает нормализованное название категории или None, если категория невалидна."""
    if not category_name:
        return None
    
    # Ищем точное совпадение по названию
    for category in INCOME_CATEGORIES.values():
        if category.name.lower() == category_name.lower():
            return category.name
    
    return None


def income_categories_kb(*, include_back=False, include_cancel=False) -> 'ReplyKeyboardMarkup':
    """Клавиатура для выбора категорий доходов"""
    from telegram import ReplyKeyboardMarkup
    
    categories = get_income_categories_list()
    # Создаем кнопки по 2 в ряд для экономии места
    rows = []
    for i in range(0, len(categories), 2):
        row = [format_category_for_display(categories[i])]
        if i + 1 < len(categories):
            row.append(format_category_for_display(categories[i + 1]))
        rows.append(row)
    
    # Добавляем кнопки навигации
    tail = []
    if include_back:
        tail.append("⬅️ Назад")
    if include_cancel:
        tail.append("Отмена")
    if tail:
        rows.append(tail)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
