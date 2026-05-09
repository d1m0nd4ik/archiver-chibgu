"""
Менеджер конфигурации для VK Media Archiver Pro
Использует python-dotenv для безопасного парсинга .env
"""
import os
from dotenv import load_dotenv, set_key, dotenv_values

ENV_FILE = ".env"

def ensure_env_file():
    """Создаёт .env файл если не существует"""
    if not os.path.exists(ENV_FILE):
        env_content = """# VK Media Archiver Pro - Configuration
# Скопируйте этот файл в .env и заполните своими данными

# VK Access Token (получить на vkhost.github.io)
VK_TOKEN=

# Ссылка на сообщество (например: https://vk.com/public123456 или https://vk.com/durov)
VK_GROUP_LINK=

# Количество постов для загрузки по умолчанию
DEFAULT_POST_COUNT=20

# Тема приложения (system, light, dark)
APP_THEME=system

# Язык интерфейса (ru, en)
APP_LANGUAGE=ru
"""
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"[INFO] Создан файл {ENV_FILE}")

def load_env_settings():
    """Загружает настройки из .env файла через python-dotenv"""
    # Загружаем переменные в os.environ
    load_dotenv(ENV_FILE, override=True)
    
    return {
        'token': os.getenv('VK_TOKEN', ''),
        'group_link': os.getenv('VK_GROUP_LINK', ''),
        'post_count': os.getenv('DEFAULT_POST_COUNT', '20'),
        'theme': os.getenv('APP_THEME', 'system'),
        'language': os.getenv('APP_LANGUAGE', 'ru')
    }

def save_env_settings(token='', group_link='', post_count='', theme='', language='', webp_quality='', video_crf='', folder=''):
    """Сохраняет настройки в .env файл с помощью dotenv.set_key"""
    try:
        updates = {}
        if token: updates['VK_TOKEN'] = token
        if group_link: updates['VK_GROUP_LINK'] = group_link
        if post_count: updates['DEFAULT_POST_COUNT'] = post_count
        if theme: updates['APP_THEME'] = theme
        if language: updates['APP_LANGUAGE'] = language
        if webp_quality: updates['WEBP_QUALITY'] = webp_quality
        if video_crf: updates['VIDEO_CRF'] = video_crf
        if folder: updates['SAVE_FOLDER'] = folder

        for key, value in updates.items():
            set_key(ENV_FILE, key, value)
            
        print(f"[INFO] Настройки сохранены в {ENV_FILE}")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить .env: {e}")

def get_system_theme():
    """Определяет системную тему (Windows 10/11 / macOS)"""
    try:
        import sys
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize')
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return 'light' if value == 1 else 'dark'
        elif sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
            return 'light' if result.returncode != 0 else 'dark'
        else:
            return 'dark'
    except Exception as e:
        print(f"[WARNING] Не удалось определить системную тему: {e}")
        return 'dark'

def get_effective_theme(saved_theme='system'):
    """Возвращает эффективную тему с учётом системной"""
    if saved_theme == 'system':
        return get_system_theme()
    return saved_theme