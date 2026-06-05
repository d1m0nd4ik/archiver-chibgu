import os

# Корень проекта (папка выше config/), чтобы Archive.db не зависел от текущей директории процесса
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# База данных (абсолютный путь — одна и та же БД из UI, воркеров и отладчика)
DB_NAME = os.path.join(_PROJECT_ROOT, "Archive.db")

# Папки для данных
DATA_DIR = os.path.join(_PROJECT_ROOT, "Exports_data")

# Теги: словарь «Тэги» без лимита; самодельные (из текста) — только слова, не более MAX_CUSTOM_TAGS
MAX_TAGS = 15
MAX_CUSTOM_TAGS = 15
MIN_WORD_LENGTH = 3

# VK API
VK_API_VERSION = "5.131"