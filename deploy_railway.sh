#!/bin/bash

# Скрипт для быстрого развертывания на Railway
echo "🚂 Развертывание Finance Bot на Railway..."

# Проверяем наличие git
if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен!"
    exit 1
fi

# Проверяем, что мы в git репозитории
if [ ! -d ".git" ]; then
    echo "📦 Инициализируем git репозиторий..."
    git init
    git add .
    git commit -m "Initial commit: Finance Bot ready for deployment"
fi

# Проверяем наличие Railway CLI
if ! command -v railway &> /dev/null; then
    echo "📦 Устанавливаем Railway CLI..."
    curl -fsSL https://railway.app/install.sh | sh
    export PATH="$HOME/.railway/bin:$PATH"
fi

echo "🔑 Настройка Railway..."
echo "1. Войдите в Railway: https://railway.app/"
echo "2. Создайте новый проект"
echo "3. Подключите ваш GitHub репозиторий"
echo "4. Добавьте переменные окружения:"
echo "   - BOT_TOKEN=ваш_telegram_bot_token"
echo "   - OPENAI_API_KEY=ваш_openai_api_key (опционально)"
echo "   - DATA_DIR=/app/data"
echo "   - DEBUG=false"
echo ""
echo "📋 Или используйте Railway CLI:"
echo "   railway login"
echo "   railway link"
echo "   railway up"

echo "✅ Готово! Следуйте инструкциям в RAILWAY_DEPLOY.md"
