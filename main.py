"""
VK Media Archiver Pro
Приложение для скачивания и индексации контента из ВКонтакте
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from core.logging_config import logger

# === ВАЖНО: Добавляем корневую папку в путь поиска модулей ===
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Теперь импорты будут работать
from ui.main_window import MainWindow
from ui.styles import apply_theme, STYLES, update_global_styles
from core.config_manager import ensure_env_file, load_env_settings
from core.app_icon import get_app_icon, ensure_app_icons

def main():
    """Точка входа в приложение"""
    ensure_env_file()
    settings = load_env_settings()

    ensure_app_icons()
    app = QApplication(sys.argv)
    app.setApplicationName("VK Archiver CHIBGU")
    app.setOrganizationName("VK Archiver")
    app.setWindowIcon(get_app_icon())

    saved_theme = settings.get('theme', 'system')
    effective_theme = apply_theme(app, saved_theme)
    update_global_styles(effective_theme)

    logger.info("Тема приложения: %s (сохранено: %s)", effective_theme, saved_theme)

    window = MainWindow(
        saved_token=settings.get('token', ''),
        saved_group_link=settings.get('group_link', ''),
        saved_post_count=settings.get('post_count', '20'),
        saved_theme=saved_theme
    )
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()