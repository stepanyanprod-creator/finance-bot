#!/bin/bash

# Скрипт развертывания Finance Bot
set -e

echo "🚀 Развертывание Finance Bot..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📋 Скопируйте env.example в .env и заполните переменные:"
    echo "   cp env.example .env"
    echo "   nano .env"
    exit 1
fi

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo "📦 Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    echo "📦 Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Останавливаем существующие контейнеры
echo "🛑 Останавливаем существующие контейнеры..."
docker-compose down || true

# Создаем необходимые директории
echo "📁 Создаем директории..."
mkdir -p data exports logs

# Собираем и запускаем контейнеры
echo "🔨 Собираем Docker образ..."
docker-compose build

echo "🚀 Запускаем бота..."
docker-compose up -d

# Проверяем статус
echo "📊 Проверяем статус..."
sleep 5
docker-compose ps

echo "✅ Бот развернут!"
echo "📋 Полезные команды:"
echo "   docker-compose logs -f finance-bot    # Просмотр логов"
echo "   docker-compose restart finance-bot    # Перезапуск бота"
echo "   docker-compose down                   # Остановка"
echo "   docker-compose exec finance-bot bash  # Вход в контейнер"
