import logging
import sys
from pathlib import Path

def setup_logger(name="VKArchiver", level=logging.INFO):
    """Создаёт и настраивает логгер с консольным выводом"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        fmt = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s')
        
        # Консольный вывод
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        
    return logger

# Глобальный экземпляр
logger = setup_logger()