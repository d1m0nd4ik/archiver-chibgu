import os

from dotenv import load_dotenv, set_key

from config.paths import get_data_root
from core.logging_config import logger


ENV_FILE = os.fspath(get_data_root() / ".env")


def ensure_env_file():
    """Создаёт .env файл если не существует."""
    if not os.path.exists(ENV_FILE):
        env_content = """
# Скопируйте этот файл в .env и заполните своими данными

# VK Access Token (получить на vkhost.github.io)
VK_TOKEN=

# ID сообщества (например: 123456)
VK_GROUP_LINK=

# Количество постов на запрос (по умолчанию 20)
POST_COUNT=20

# Тема приложения (light, dark, system)
APP_THEME=dark

# Файл cookies для yt-dlp (необязательно): cookies.txt
# VK_COOKIES_FILE=cookies.txt

# Браузеры для авто-чтения cookies: edge,chrome,firefox
# VK_COOKIES_BROWSER=edge,chrome,firefox

"""
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write(env_content)
        logger.info(f"[INFO] Создан файл {ENV_FILE}")


def load_env_settings():
    """Загружает настройки из .env файла через python-dotenv."""
    load_dotenv(ENV_FILE, override=True)

    return {
        'token': os.getenv('VK_TOKEN', ''),
        'group_link': os.getenv('VK_GROUP_LINK', ''),
        'post_count': os.getenv('POST_COUNT', '20'),
        'theme': os.getenv('APP_THEME', 'system'),
        'cookies_file': os.getenv('VK_COOKIES_FILE', ''),
        'cookies_browser': os.getenv('VK_COOKIES_BROWSER', 'edge,chrome,firefox'),
    }


def save_env_settings(
    token='',
    group_link='',
    post_count='',
    theme='',
    cookies_file=None,
    cookies_browser=None,
):
    """Сохраняет настройки в .env файл с помощью dotenv.set_key."""
    try:
        updates = {}
        if token:
            updates['VK_TOKEN'] = token
        if group_link:
            updates['VK_GROUP_LINK'] = group_link
        if post_count:
            updates['POST_COUNT'] = post_count
        if theme:
            updates['APP_THEME'] = theme
        if cookies_file is not None:
            updates['VK_COOKIES_FILE'] = cookies_file
        if cookies_browser is not None:
            updates['VK_COOKIES_BROWSER'] = cookies_browser

        for key, value in updates.items():
            set_key(ENV_FILE, key, value or '')

        load_dotenv(ENV_FILE, override=True)
        logger.info(f"Настройки сохранены в {ENV_FILE}")
    except Exception as e:
        logger.error(f"Не удалось сохранить .env: {e}")


def get_system_theme():
    """Определяет системную тему (Windows 10/11 / macOS)."""
    try:
        import sys
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize',
            )
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return 'light' if value == 1 else 'dark'
        elif sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True,
            )
            return 'light' if result.returncode != 0 else 'dark'
        else:
            return 'dark'
    except Exception as e:
        logger.warning(f"Не удалось определить системную тему: {e}")
        return 'dark'


def get_effective_theme(saved_theme='system'):
    """Возвращает эффективную тему с учётом системной."""
    if saved_theme == 'system':
        return get_system_theme()
    return saved_theme
