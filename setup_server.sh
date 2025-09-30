#!/bin/bash

# Скрипт настройки сервера для Finance Bot
set -e

echo "🚀 Настройка сервера для Finance Bot..."

# Проверяем, что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт от root: sudo ./setup_server.sh"
    exit 1
fi

# Обновляем систему
echo "📦 Обновляем систему..."
apt update && apt upgrade -y

# Устанавливаем необходимые пакеты
echo "🔧 Устанавливаем зависимости..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    unzip \
    htop \
    nano \
    ufw \
    fail2ban \
    logrotate

# Устанавливаем Docker (опционально)
read -p "🐳 Установить Docker? (y/n): " install_docker
if [ "$install_docker" = "y" ]; then
    echo "🐳 Устанавливаем Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    systemctl enable docker
    systemctl start docker
    
    # Устанавливаем Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Создаем пользователя для бота
echo "👤 Создаем пользователя finance-bot..."
useradd -r -s /bin/bash -d /opt/finance-bot -m finance-bot || true

# Создаем директории
echo "📁 Создаем директории..."
mkdir -p /opt/finance-bot/{data,exports,logs}
chown -R finance-bot:finance-bot /opt/finance-bot

# Настраиваем firewall
echo "🔥 Настраиваем firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
# Не открываем порты для бота - он работает через webhook

# Настраиваем fail2ban
echo "🛡️ Настраиваем fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Настраиваем logrotate
echo "📋 Настраиваем logrotate..."
cat > /etc/logrotate.d/finance-bot << EOF
/opt/finance-bot/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 finance-bot finance-bot
    postrotate
        systemctl reload finance-bot || true
    endscript
}
EOF

# Создаем systemd сервис
echo "⚙️ Настраиваем systemd сервис..."
cp finance-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable finance-bot

echo "✅ Настройка сервера завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Скопируйте код бота в /opt/finance-bot/"
echo "2. Создайте файл .env с настройками"
echo "3. Установите зависимости: pip3 install -r requirements.txt"
echo "4. Запустите бота: systemctl start finance-bot"
echo ""
echo "🔧 Полезные команды:"
echo "   systemctl status finance-bot    # Статус бота"
echo "   systemctl logs -f finance-bot   # Просмотр логов"
echo "   systemctl restart finance-bot   # Перезапуск"
echo "   systemctl stop finance-bot      # Остановка"
