#!/usr/bin/env python3
"""
Скрипт для остановки всех процессов Finance Bot
"""
import subprocess
import sys
import time

def stop_all_bot_processes():
    """Останавливает все процессы бота"""
    print("🔍 Ищу запущенные процессы бота...")
    
    try:
        # Ищем процессы с main.py
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        bot_processes = []
        for line in lines:
            if 'main.py' in line and 'python' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    bot_processes.append(pid)
        
        if not bot_processes:
            print("✅ Запущенных процессов бота не найдено")
            return True
        
        print(f"⚠️  Найдено {len(bot_processes)} процессов: {bot_processes}")
        
        # Останавливаем процессы
        for pid in bot_processes:
            try:
                print(f"🛑 Останавливаю процесс {pid}...")
                subprocess.run(['kill', '-TERM', pid], check=True)
                time.sleep(1)
                
                # Проверяем, остановился ли процесс
                check_result = subprocess.run(['ps', '-p', pid], capture_output=True)
                if check_result.returncode == 0:
                    print(f"⚡ Принудительно завершаю процесс {pid}...")
                    subprocess.run(['kill', '-KILL', pid], check=True)
                
                print(f"✅ Процесс {pid} остановлен")
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Ошибка при остановке процесса {pid}: {e}")
                return False
        
        # Финальная проверка
        time.sleep(2)
        final_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        remaining = [line for line in final_result.stdout.split('\n') 
                    if 'main.py' in line and 'python' in line and 'grep' not in line]
        
        if remaining:
            print(f"⚠️  Остались процессы: {remaining}")
            return False
        else:
            print("✅ Все процессы бота успешно остановлены")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = stop_all_bot_processes()
    sys.exit(0 if success else 1)
