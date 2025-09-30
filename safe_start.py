#!/usr/bin/env python3
"""
Безопасный запуск Finance Bot с проверкой на дублирующиеся процессы
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
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        bot_processes = []
        for line in lines:
            if 'main.py' in line and 'python' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    bot_processes.append(pid)
        
        return bot_processes
    except Exception as e:
        print(f"Ошибка при проверке процессов: {e}")
        return []

def kill_existing_processes(pids):
    """Останавливает существующие процессы бота"""
    for pid in pids:
        try:
            print(f"Останавливаю процесс {pid}...")
            os.kill(int(pid), signal.SIGTERM)
            time.sleep(1)
            # Если процесс не остановился, принудительно завершаем
            try:
                os.kill(int(pid), 0)  # Проверяем, существует ли процесс
                print(f"Принудительно завершаю процесс {pid}...")
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                print(f"Процесс {pid} успешно остановлен")
        except Exception as e:
            print(f"Ошибка при остановке процесса {pid}: {e}")

def main():
    print("🔍 Проверяю запущенные процессы бота...")
    
    # Проверяем существующие процессы
    existing_pids = check_running_processes()
    
    if existing_pids:
        print(f"⚠️  Найдено {len(existing_pids)} запущенных процессов бота: {existing_pids}")
        print("🛑 Останавливаю существующие процессы...")
        kill_existing_processes(existing_pids)
        time.sleep(3)
        
        # Проверяем еще раз
        remaining_pids = check_running_processes()
        if remaining_pids:
            print(f"❌ Не удалось остановить процессы: {remaining_pids}")
            print("Попробуйте остановить их вручную:")
            for pid in remaining_pids:
                print(f"  kill -9 {pid}")
            return False
        else:
            print("✅ Все существующие процессы остановлены")
    else:
        print("✅ Запущенных процессов бота не найдено")
    
    print("🚀 Запускаю бота...")
    
    try:
        from main import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
