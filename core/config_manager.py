"""
Менеджер конфигурации для VK Media Archiver Pro
Отвечает за загрузку и сохранение настроек в .env файл
"""
import os
import sys

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
    """Загружает настройки из .env файла"""
    settings = {
        'token': '',
        'group_link': '',
        'post_count': '20',
        'theme': 'system',
        'language': 'ru'
    }
    
    try:
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'VK_TOKEN':
                            settings['token'] = value
                        elif key == 'VK_GROUP_LINK':
                            settings['group_link'] = value
                        elif key == 'DEFAULT_POST_COUNT':
                            settings['post_count'] = value
                        elif key == 'APP_THEME':
                            settings['theme'] = value
                        elif key == 'APP_LANGUAGE':
                            settings['language'] = value
    except Exception as e:
        print(f"[WARNING] Не удалось загрузить .env: {e}")
    
    return settings


def save_env_settings(token='', group_link='', post_count='', theme='', language='', webp_quality='', video_crf='', folder=''):
    """Сохраняет настройки в .env файл"""
    try:
        lines = []
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        updated = {
            'VK_TOKEN': False, 'VK_GROUP_LINK': False, 'DEFAULT_POST_COUNT': False,
            'APP_THEME': False, 'APP_LANGUAGE': False,
            'WEBP_QUALITY': False, 'VIDEO_CRF': False, 'SAVE_FOLDER': False
        }

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('VK_TOKEN=') and token:
                lines[i] = f'VK_TOKEN={token}\n'
                updated['VK_TOKEN'] = True
            elif stripped.startswith('VK_GROUP_LINK=') and group_link:
                lines[i] = f'VK_GROUP_LINK={group_link}\n'
                updated['VK_GROUP_LINK'] = True
            elif stripped.startswith('DEFAULT_POST_COUNT=') and post_count:
                lines[i] = f'DEFAULT_POST_COUNT={post_count}\n'
                updated['DEFAULT_POST_COUNT'] = True
            elif stripped.startswith('APP_THEME=') and theme:
                lines[i] = f'APP_THEME={theme}\n'
                updated['APP_THEME'] = True
            elif stripped.startswith('APP_LANGUAGE=') and language:
                lines[i] = f'APP_LANGUAGE={language}\n'
                updated['APP_LANGUAGE'] = True
            elif stripped.startswith('WEBP_QUALITY=') and webp_quality:
                lines[i] = f'WEBP_QUALITY={webp_quality}\n'
                updated['WEBP_QUALITY'] = True
            elif stripped.startswith('VIDEO_CRF=') and video_crf:
                lines[i] = f'VIDEO_CRF={video_crf}\n'
                updated['VIDEO_CRF'] = True
            elif stripped.startswith('SAVE_FOLDER=') and folder:
                lines[i] = f'SAVE_FOLDER={folder}\n'
                updated['SAVE_FOLDER'] = True

        if token and not updated['VK_TOKEN']:
            lines.append(f'\nVK_TOKEN={token}\n')
        if group_link and not updated['VK_GROUP_LINK']:
            lines.append(f'VK_GROUP_LINK={group_link}\n')
        if post_count and not updated['DEFAULT_POST_COUNT']:
            lines.append(f'DEFAULT_POST_COUNT={post_count}\n')
        if theme and not updated['APP_THEME']:
            lines.append(f'APP_THEME={theme}\n')
        if language and not updated['APP_LANGUAGE']:
            lines.append(f'APP_LANGUAGE={language}\n')
        if webp_quality and not updated['WEBP_QUALITY']:
            lines.append(f'WEBP_QUALITY={webp_quality}\n')
        if video_crf and not updated['VIDEO_CRF']:
            lines.append(f'VIDEO_CRF={video_crf}\n')
        if folder and not updated['SAVE_FOLDER']:
            lines.append(f'SAVE_FOLDER={folder}\n')

        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"[INFO] Настройки сохранены в {ENV_FILE}")

    except Exception as e:
        print(f"[ERROR] Не удалось сохранить .env: {e}")


def get_system_theme():
    """Определяет системную тему (Windows 10/11)"""
    try:
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return 'light' if value == 1 else 'dark'
        elif sys.platform == 'darwin':
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True
            )
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