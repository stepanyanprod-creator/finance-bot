#!/usr/bin/env python3
"""
Простой веб-сервер для Render Web Service
"""
from flask import Flask, jsonify
import os
import threading
import time

app = Flask(__name__)

@app.route('/')
def health_check():
    """Health check endpoint для Render"""
    return jsonify({
        "status": "ok",
        "service": "Finance Bot",
        "version": "2.0.0"
    })

@app.route('/health')
def health():
    """Health endpoint"""
    return jsonify({"status": "healthy"})

def run_bot():
    """Запуск бота в отдельном потоке"""
    import main_production
    main_production.main()

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
