#!/usr/bin/env python3
"""
Скрипт для управления Finance Bot

Использование:
  python3 restart_bot.py           - перезапустить бота (по умолчанию)
  python3 restart_bot.py start     - запустить бота
  python3 restart_bot.py stop      - остановить бота
  python3 restart_bot.py restart   - перезапустить бота
  python3 restart_bot.py status    - показать статус бота
  python3 restart_bot.py monitor   - мониторить бота

Скрипт может работать даже когда бот активен.
"""
import sys
import os
import subprocess
import time
import signal

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_running_processes():
    """Проверяет, запущены ли уже процессы бота"""
    try:
        # Используем pgrep для более надежного поиска процессов
        result = subprocess.run(['pgrep', '-f', 'main.py'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            return pids
        return []
    except Exception as e:
        print(f"❌ Ошибка при проверке процессов: {e}")
        return []

def stop_bot_processes():
    """Останавливает все процессы бота"""
    print("🔍 Ищу запущенные процессы бота...")
    
    existing_pids = check_running_processes()
    
    if not existing_pids:
        print("✅ Запущенных процессов бота не найдено")
        return True
    
    print(f"⚠️  Найдено {len(existing_pids)} процессов: {existing_pids}")
    
    # Останавливаем процессы
    for pid in existing_pids:
        try:
            print(f"🛑 Останавливаю процесс {pid}...")
            
            # Сначала пытаемся мягко остановить процесс
            try:
                subprocess.run(['kill', '-TERM', pid], check=True, timeout=5)
            except subprocess.TimeoutExpired:
                print(f"⚠️  Процесс {pid} не отвечает на SIGTERM")
            except subprocess.CalledProcessError:
                print(f"⚠️  Не удалось отправить SIGTERM процессу {pid}")
            
            # Ждем немного
            time.sleep(2)
            
            # Проверяем, остановился ли процесс
            try:
                check_result = subprocess.run(['ps', '-p', pid], capture_output=True, timeout=5)
                if check_result.returncode == 0:
                    print(f"⚡ Принудительно завершаю процесс {pid}...")
                    subprocess.run(['kill', '-KILL', pid], check=True, timeout=5)
                    time.sleep(1)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                print(f"⚠️  Не удалось принудительно завершить процесс {pid}")
            
            print(f"✅ Процесс {pid} остановлен")
            
        except Exception as e:
            print(f"❌ Ошибка при остановке процесса {pid}: {e}")
            continue
    
    # Финальная проверка
    time.sleep(3)
    remaining_pids = check_running_processes()
    
    if remaining_pids:
        print(f"⚠️  Остались процессы: {remaining_pids}")
        return False
    else:
        print("✅ Все процессы бота успешно остановлены")
        return True

def start_bot():
    """Запускает бота"""
    print("🚀 Запускаю бота...")
    
    try:
        # Запускаем бота как отдельный процесс в фоновом режиме
        process = subprocess.Popen([sys.executable, 'main.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT, 
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Даем боту время на запуск
        time.sleep(3)
        
        # Проверяем, что процесс запустился
        if process.poll() is None:
            print("✅ Бот успешно запущен в фоновом режиме")
            print(f"📋 PID процесса: {process.pid}")
            print("💡 Для остановки бота используйте Ctrl+C или команду kill")
            return True
        else:
            print(f"❌ Бот завершился с кодом ошибки: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        return False

def monitor_bot():
    """Мониторит работу бота"""
    print("👀 Мониторинг бота...")
    print("💡 Нажмите Ctrl+C для остановки мониторинга")
    
    try:
        while True:
            pids = check_running_processes()
            if pids:
                print(f"✅ Бот работает (PID: {', '.join(pids)})")
            else:
                print("❌ Бот не запущен")
            
            time.sleep(10)  # Проверяем каждые 10 секунд
            
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен")

def restart_bot():
    """Перезапускает бота"""
    print("🔄 Перезапуск Finance Bot...")
    print("=" * 50)
    
    # Шаг 1: Останавливаем существующие процессы
    print("📋 Шаг 1: Остановка существующих процессов")
    if not stop_bot_processes():
        print("❌ Не удалось остановить все процессы. Перезапуск прерван.")
        return False
    
    print()
    
    # Шаг 2: Небольшая пауза для завершения всех операций
    print("📋 Шаг 2: Ожидание завершения операций...")
    time.sleep(3)
    
    print()
    
    # Шаг 3: Запускаем бота
    print("📋 Шаг 3: Запуск нового процесса")
    return start_bot()

def main():
    """Главная функция"""
    # Настраиваем обработку сигналов
    def signal_handler(signum, frame):
        print(f"\n👋 Получен сигнал {signum}. Завершение работы...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Обрабатываем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            print("🚀 Запуск бота...")
            return start_bot()
        elif command == "stop":
            print("🛑 Остановка бота...")
            return stop_bot_processes()
        elif command == "restart":
            print("🔄 Перезапуск бота...")
            return restart_bot()
        elif command == "status":
            print("📊 Статус бота:")
            pids = check_running_processes()
            if pids:
                print(f"✅ Бот работает (PID: {', '.join(pids)})")
            else:
                print("❌ Бот не запущен")
            return True
        elif command == "monitor":
            monitor_bot()
            return True
        else:
            print("❌ Неизвестная команда. Доступные команды:")
            print("  start    - запустить бота")
            print("  stop     - остановить бота")
            print("  restart  - перезапустить бота")
            print("  status   - показать статус бота")
            print("  monitor  - мониторить бота")
            return False
    
    # По умолчанию - перезапуск
    try:
        success = restart_bot()
        if success:
            print("\n✅ Перезапуск завершен успешно")
        else:
            print("\n❌ Перезапуск завершен с ошибками")
        return success
    except KeyboardInterrupt:
        print("\n👋 Перезапуск прерван пользователем")
        return False
    except Exception as e:
        print(f"\n❌ Критическая ошибка при перезапуске: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
