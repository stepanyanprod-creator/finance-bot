# 🚀 Руководство по развертыванию Finance Bot

## 📋 Варианты развертывания

### 1. 🐳 Docker (Рекомендуется)
Самый простой способ для быстрого развертывания.

### 2. 🐧 Linux Server (VPS/Dedicated)
Для постоянного использования на собственном сервере.

### 3. ☁️ Cloud Platforms
Развертывание на облачных платформах.

---

## 🐳 Развертывание с Docker

### Требования
- Docker
- Docker Compose
- 1GB RAM
- 10GB дискового пространства

### Шаги развертывания

1. **Клонируйте репозиторий:**
```bash
git clone <your-repo-url>
cd finance-bot
```

2. **Настройте переменные окружения:**
```bash
cp env.example .env
nano .env
```

Заполните обязательные поля:
```env
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

3. **Запустите бота:**
```bash
./deploy.sh
```

4. **Проверьте статус:**
```bash
docker-compose ps
docker-compose logs -f finance-bot
```

### Управление Docker контейнером

```bash
# Просмотр логов
docker-compose logs -f finance-bot

# Перезапуск
docker-compose restart finance-bot

# Остановка
docker-compose down

# Обновление
docker-compose pull
docker-compose up -d
```

---

## 🐧 Развертывание на Linux сервере

### Требования
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- 1GB RAM
- 10GB дискового пространства
- Python 3.11+

### Автоматическая настройка

1. **Загрузите код на сервер:**
```bash
scp -r finance-bot/ user@your-server:/tmp/
```

2. **Подключитесь к серверу:**
```bash
ssh user@your-server
```

3. **Запустите скрипт настройки:**
```bash
cd /tmp/finance-bot
sudo ./setup_server.sh
```

4. **Скопируйте код в рабочую директорию:**
```bash
sudo cp -r /tmp/finance-bot/* /opt/finance-bot/
sudo chown -R finance-bot:finance-bot /opt/finance-bot
```

5. **Настройте переменные окружения:**
```bash
sudo -u finance-bot cp /opt/finance-bot/env.example /opt/finance-bot/.env
sudo -u finance-bot nano /opt/finance-bot/.env
```

6. **Установите зависимости:**
```bash
sudo -u finance-bot python3 -m pip install --user -r /opt/finance-bot/requirements.txt
```

7. **Запустите бота:**
```bash
sudo systemctl start finance-bot
sudo systemctl status finance-bot
```

### Ручная настройка

Если автоматическая настройка не подходит:

1. **Установите Python и зависимости:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

2. **Создайте виртуальное окружение:**
```bash
python3 -m venv /opt/finance-bot/venv
source /opt/finance-bot/venv/bin/activate
pip install -r requirements.txt
```

3. **Настройте systemd сервис:**
```bash
sudo cp finance-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable finance-bot
sudo systemctl start finance-bot
```

### Управление сервисом

```bash
# Статус
sudo systemctl status finance-bot

# Логи
sudo journalctl -u finance-bot -f

# Перезапуск
sudo systemctl restart finance-bot

# Остановка
sudo systemctl stop finance-bot
```

---

## ☁️ Развертывание на облачных платформах

### Heroku

1. **Создайте Procfile:**
```
worker: python main_production.py
```

2. **Настройте переменные окружения в Heroku Dashboard**

3. **Деплой:**
```bash
git push heroku main
```

### DigitalOcean App Platform

1. **Создайте app.yaml:**
```yaml
name: finance-bot
services:
- name: bot
  source_dir: /
  github:
    repo: your-username/finance-bot
    branch: main
  run_command: python main_production.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: BOT_TOKEN
    value: your_bot_token
  - key: OPENAI_API_KEY
    value: your_openai_key
```

### AWS EC2

1. **Запустите EC2 инстанс (t3.micro)**
2. **Подключитесь и выполните настройку Linux сервера**

### Google Cloud Run

1. **Создайте Dockerfile (уже готов)**
2. **Соберите и загрузите образ:**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/finance-bot
gcloud run deploy --image gcr.io/PROJECT-ID/finance-bot --platform managed
```

---

## 🔧 Настройка переменных окружения

### Обязательные переменные

```env
BOT_TOKEN=your_telegram_bot_token_here
```

### Опциональные переменные

```env
OPENAI_API_KEY=your_openai_api_key_here  # Для голосовых команд
DATA_DIR=data                            # Директория данных
DEBUG=false                              # Режим отладки
LOG_LEVEL=INFO                          # Уровень логирования
```

### Получение BOT_TOKEN

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

### Получение OPENAI_API_KEY

1. Зарегистрируйтесь на https://platform.openai.com/
2. Перейдите в API Keys
3. Создайте новый ключ
4. Скопируйте ключ

---

## 📊 Мониторинг и логирование

### Просмотр логов

**Docker:**
```bash
docker-compose logs -f finance-bot
```

**Systemd:**
```bash
sudo journalctl -u finance-bot -f
```

### Мониторинг ресурсов

```bash
# CPU и память
htop

# Дисковое пространство
df -h

# Сетевые соединения
netstat -tulpn
```

### Ротация логов

Логи автоматически ротируются через logrotate (Linux) или Docker logging driver.

---

## 🔒 Безопасность

### Рекомендации

1. **Используйте сильные пароли**
2. **Настройте firewall (UFW)**
3. **Включите fail2ban**
4. **Регулярно обновляйте систему**
5. **Не храните токены в коде**

### Backup данных

```bash
# Создание backup
tar -czf finance-bot-backup-$(date +%Y%m%d).tar.gz data/ exports/

# Восстановление
tar -xzf finance-bot-backup-YYYYMMDD.tar.gz
```

---

## 🆘 Устранение проблем

### Бот не запускается

1. **Проверьте логи:**
```bash
docker-compose logs finance-bot
# или
sudo journalctl -u finance-bot
```

2. **Проверьте переменные окружения:**
```bash
docker-compose config
```

3. **Проверьте токен бота:**
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"
```

### Ошибки подключения

1. **Проверьте интернет соединение**
2. **Проверьте firewall настройки**
3. **Проверьте DNS резолюцию**

### Проблемы с памятью

1. **Увеличьте лимиты в docker-compose.yml**
2. **Оптимизируйте код**
3. **Добавьте swap файл**

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи
2. Изучите документацию
3. Создайте issue в репозитории
4. Обратитесь к сообществу

---

**🎉 Удачного развертывания!**
