#!/bin/bash
"""
Скрипт для быстрого перезапуска Finance Bot
"""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Перезапуск Finance Bot${NC}"
echo "=================================="

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Ошибка: main.py не найден. Запустите скрипт из директории проекта.${NC}"
    exit 1
fi

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Ошибка: python3 не найден${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Запускаю Python скрипт перезапуска...${NC}"
echo ""

# Запускаем Python скрипт
python3 restart_bot.py

# Проверяем результат
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Перезапуск завершен успешно${NC}"
else
    echo -e "${RED}❌ Перезапуск завершен с ошибками${NC}"
    exit 1
fi
