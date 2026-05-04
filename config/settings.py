import os

# База данных
DB_NAME = "vk_archive.db"

# Папки для данных
DATA_DIR = "vk_archive_data"
PHOTOS_DIR = os.path.join(DATA_DIR, "photos_webp")
VIDEOS_DIR = os.path.join(DATA_DIR, "videos_mp4")

# Настройки качества
WEBP_QUALITY = 80  # 1-100 (80 - оптимально)
VIDEO_CRF = 23  # 18-28 (меньше = лучше качество)
VIDEO_PRESET = "medium"  # ultrafast, fast, medium, slow, veryslow

# Теги
MAX_TAGS = 5
MIN_WORD_LENGTH = 3

# VK API
VK_API_VERSION = "5.131"

# Создаем папки при импорте
for folder in [DATA_DIR, PHOTOS_DIR, VIDEOS_DIR]:
    os.makedirs(folder, exist_ok=True)