import logging
import sys
import os
from datetime import datetime

def setup_logging(log_level=logging.INFO):
    """Настраивает логирование для приложения"""
    
    # Создаем директорию для логов, если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Формат логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Имя файла логов с текущей датой
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"bot_{today}.log")
    
    # Настройка обработчика файлов
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Настройка обработчика консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Отключаем логи сторонних библиотек, которые нам не нужны
    for logger_name in ["aiohttp", "aiogram"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
    
    return root_logger 