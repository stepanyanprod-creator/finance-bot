#!/usr/bin/env python3
"""
Надежная настройка git конфигурации для Render
"""

import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def setup_git_config():
    """Надежная настройка git конфигурации"""
    try:
        logger.info("Настройка git конфигурации...")
        
        # Устанавливаем переменные окружения
        os.environ['GIT_AUTHOR_NAME'] = 'Finance Bot'
        os.environ['GIT_AUTHOR_EMAIL'] = 'bot@finance.local'
        os.environ['GIT_COMMITTER_NAME'] = 'Finance Bot'
        os.environ['GIT_COMMITTER_EMAIL'] = 'bot@finance.local'
        
        # Настраиваем git конфигурацию
        commands = [
            ['git', 'config', 'user.name', 'Finance Bot'],
            ['git', 'config', 'user.email', 'bot@finance.local'],
            ['git', 'config', '--global', 'user.name', 'Finance Bot'],
            ['git', 'config', '--global', 'user.email', 'bot@finance.local'],
            ['git', 'config', 'core.autocrlf', 'false'],
            ['git', 'config', 'core.filemode', 'false'],
            ['git', 'config', 'pull.rebase', 'false'],
            ['git', 'config', 'credential.helper', 'store'],
            ['git', 'config', 'http.sslVerify', 'false']
        ]
        
        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"Выполнено: {' '.join(cmd)}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Ошибка команды {' '.join(cmd)}: {e}")
                # Продолжаем выполнение других команд
        
        # Проверяем настройки
        try:
            result = subprocess.run(['git', 'config', 'user.name'], 
                                 capture_output=True, text=True)
            if result.stdout.strip() == 'Finance Bot':
                logger.info("Git пользователь настроен успешно")
                return True
            else:
                logger.error("Git пользователь не настроен")
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки git конфигурации: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Общая ошибка настройки git: {e}")
        return False

def force_git_config():
    """Принудительная настройка git"""
    try:
        logger.info("Принудительная настройка git...")
        
        # Удаляем существующие настройки
        try:
            subprocess.run(['git', 'config', '--unset', 'user.name'], 
                         capture_output=True)
            subprocess.run(['git', 'config', '--unset', 'user.email'], 
                         capture_output=True)
            subprocess.run(['git', 'config', '--global', '--unset', 'user.name'], 
                         capture_output=True)
            subprocess.run(['git', 'config', '--global', '--unset', 'user.email'], 
                         capture_output=True)
        except:
            pass  # Игнорируем ошибки удаления
        
        # Устанавливаем переменные окружения
        os.environ['GIT_AUTHOR_NAME'] = 'Finance Bot'
        os.environ['GIT_AUTHOR_EMAIL'] = 'bot@finance.local'
        os.environ['GIT_COMMITTER_NAME'] = 'Finance Bot'
        os.environ['GIT_COMMITTER_EMAIL'] = 'bot@finance.local'
        
        # Настраиваем git
        subprocess.run(['git', 'config', 'user.name', 'Finance Bot'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'bot@finance.local'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Finance Bot'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'bot@finance.local'], check=True)
        
        logger.info("Принудительная настройка git завершена")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка принудительной настройки git: {e}")
        return False

if __name__ == "__main__":
    print("Настройка git конфигурации...")
    success = setup_git_config()
    if success:
        print("✅ Git конфигурация настроена")
    else:
        print("❌ Ошибка настройки git конфигурации")
        print("Пробуем принудительную настройку...")
        force_success = force_git_config()
        if force_success:
            print("✅ Принудительная настройка успешна")
        else:
            print("❌ Принудительная настройка не удалась")
