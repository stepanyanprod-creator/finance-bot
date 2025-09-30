#!/bin/bash
"""
Скрипт для настройки git в Render для синхронизации данных
"""

echo "🔧 Настройка git для синхронизации данных..."

# Настройка git пользователя
git config --global user.name "Finance Bot"
git config --global user.email "bot@finance.local"

# Настройка git для работы с HTTPS
git config --global credential.helper store

# Создание файла с токеном (если нужно)
if [ ! -z "$GITHUB_TOKEN" ]; then
    echo "https://github.com:$GITHUB_TOKEN@github.com" > ~/.git-credentials
    chmod 600 ~/.git-credentials
fi

# Настройка безопасного режима для git
git config --global init.defaultBranch main
git config --global pull.rebase false

echo "✅ Git настроен для синхронизации данных"
echo "📁 Текущая директория: $(pwd)"
echo "🔍 Статус git:"
git status --short

echo "🎉 Настройка завершена!"
