from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from core.config_manager import get_effective_theme

def apply_dark_theme(app):
    """Применение тёмной темы"""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(40, 40, 40))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ToolTipBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(58, 123, 213))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.PlaceholderText, QColor(150, 150, 150))
    palette.setColor(QPalette.Link, QColor(58, 123, 213))
    palette.setColor(QPalette.LinkVisited, QColor(58, 123, 213))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80, 80, 80))
    app.setPalette(palette)
    app.setStyle("Fusion")

def apply_light_theme(app):
    """Применение светлой темы"""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(245, 245, 245))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(58, 123, 213))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.PlaceholderText, QColor(120, 120, 120))
    palette.setColor(QPalette.Link, QColor(58, 123, 213))
    palette.setColor(QPalette.LinkVisited, QColor(58, 123, 213))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor(200, 200, 200))
    app.setPalette(palette)
    app.setStyle("Fusion")

def apply_theme(app, theme_name='system'):
    """Применяет тему к приложению"""
    effective_theme = get_effective_theme(theme_name)
    if effective_theme == 'light':
        apply_light_theme(app)
    else:
        apply_dark_theme(app)
    return effective_theme

# ============================================================================
# СТИЛИ ДЛЯ ТЁМНОЙ ТЕМЫ
# ============================================================================
DARK_STYLES = {
    'input': """
        QLineEdit {
            padding: 10px;
            border-radius: 6px;
            border: 2px solid #555555;
            background-color: #3c3c3c;
            color: #ffffff;
            font-size: 13px;
            selection-background-color: #3a7bd5;
            min-height: 40px;
        }
        QLineEdit:focus { border: 2px solid #3a7bd5; }
        QLineEdit:disabled { background-color: #2a2a2a; color: #888888; border: 2px solid #444444; }
    """,
    'button': """
        QPushButton { 
            padding: 11px 22px; 
            border-radius: 10px; 
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4b8df2, stop:1 #2f6fce); 
            color: #ffffff; 
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #2c5aa0;
        }
        QPushButton:hover { 
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5a9cff, stop:1 #3578d9); 
            border: 1px solid #3d7dd8;
        }
        QPushButton:pressed { background-color: #255cb4; }
        QPushButton:disabled { background-color: #555555; color: #888888; border: 1px solid #444444; }
    """,
    'button_secondary': """
        QPushButton { 
            padding: 11px 22px; 
            border-radius: 10px; 
            background-color: #444a57; 
            color: #ffffff; 
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #5a6170;
        }
        QPushButton:hover { background-color: #545c6d; border: 1px solid #6a7386; }
    """,
    'textedit': """
        QTextEdit { 
            background-color: #2b2b2b; 
            color: #d4d4d4; 
            font-family: 'Consolas', 'Courier New', monospace; 
            font-size: 13px; 
            border-radius: 6px; 
            border: 2px solid #555555;
            padding: 10px; 
            selection-background-color: #3a7bd5;
        }
        QTextEdit:focus { border: 2px solid #3a7bd5; }
    """,
    'frame': """
        QFrame { 
            background-color: #262a32; 
            border-radius: 14px; 
            padding: 15px;
            border: 1px solid #3f4654;
        }
    """,
    'label': "color: #ffffff; font-size: 13px; padding: 5px; ",
    'label_title': "color: #ffffff; font-size: 18px; font-weight: bold; padding: 10px; ",
    'progressbar': """
        QProgressBar {
            border: 2px solid #555555;
            border-radius: 6px;
            background-color: #2a2a2a;
            text-align: center;
            color: #ffffff;
            height: 25px;
        }
        QProgressBar::chunk { background-color: #3a7bd5; border-radius: 5px; }
    """,
    'statusbar': "background-color: #1e1e1e; color: #d4d4d4; border-top: 2px solid #444444; ",
    'navigation': """
        QPushButton {
            background-color: transparent;
            color: #d4d4d4;
            border: 2px solid transparent;
            border-radius: 8px;
            padding: 12px 20px;
            text-align: left;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #3a3a3a; border: 2px solid #555555; }
        QPushButton:checked { background-color: #3a7bd5; color: white; border: 2px solid #2c5aa0; }
    """
}

# ============================================================================
# СТИЛИ ДЛЯ СВЕТЛОЙ ТЕМЫ
# ============================================================================
LIGHT_STYLES = {
    'input': """
        QLineEdit {
            padding: 10px;
            border-radius: 6px;
            border: 2px solid #999999;
            background-color: #ffffff;
            color: #000000;
            font-size: 13px;
            selection-background-color: #3a7bd5;
            min-height: 40px;
        }
        QLineEdit:focus { border: 2px solid #3a7bd5; }
        QLineEdit:disabled { background-color: #f5f5f5; color: #999999; border: 2px solid #cccccc; }
    """,
    'button': """
        QPushButton { 
            padding: 11px 22px; 
            border-radius: 10px; 
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4b8df2, stop:1 #2f6fce); 
            color: #ffffff; 
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #2c5aa0;
        }
        QPushButton:hover { 
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #5a9cff, stop:1 #3578d9); 
            border: 1px solid #3d7dd8;
        }
        QPushButton:pressed { background-color: #255cb4; }
        QPushButton:disabled { background-color: #cccccc; color: #999999; border: 1px solid #bbbbbb; }
    """,
    'button_secondary': """
        QPushButton { 
            padding: 11px 22px; 
            border-radius: 10px; 
            background-color: #eef0f5; 
            color: #000000; 
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #c5cad6;
        }
        QPushButton:hover { background-color: #e3e7f1; border: 1px solid #b2bacb; }
    """,
    'textedit': """
        QTextEdit { 
            background-color: #ffffff; 
            color: #000000; 
            font-family: 'Consolas', 'Courier New', monospace; 
            font-size: 13px; 
            border-radius: 6px; 
            border: 2px solid #999999;
            padding: 10px; 
            selection-background-color: #3a7bd5;
        }
        QTextEdit:focus { border: 2px solid #3a7bd5; }
    """,
    'frame': """
        QFrame { 
            background-color: #ffffff; 
            border-radius: 14px; 
            padding: 15px;
            border: 1px solid #d8dce5;
        }
    """,
    'label': "color: #000000; font-size: 13px; padding: 5px; ",
    'label_title': "color: #000000; font-size: 18px; font-weight: bold; padding: 10px; ",
    'progressbar': """
        QProgressBar {
            border: 2px solid #999999;
            border-radius: 6px;
            background-color: #f0f0f0;
            text-align: center;
            color: #000000;
            height: 25px;
        }
        QProgressBar::chunk { background-color: #3a7bd5; border-radius: 5px; }
    """,
    'statusbar': "background-color: #f0f0f0; color: #000000; border-top: 2px solid #999999; ",
    'navigation': """
        QPushButton {
            background-color: transparent;
            color: #000000;
            border: 2px solid transparent;
            border-radius: 8px;
            padding: 12px 20px;
            text-align: left;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #e0e0e0; border: 2px solid #999999; }
        QPushButton:checked { background-color: #3a7bd5; color: white; border: 2px solid #2c5aa0; }
    """
}

# ============================================================================
# МЕНЕДЖЕР СТИЛЕЙ
# ============================================================================
class StyleManager:
    """Динамический менеджер стилей"""
    def __init__(self):
        self._theme = 'dark'
        self._styles = DARK_STYLES

    def set_theme(self, theme):
        """Устанавливает тему и обновляет стили"""
        self._theme = theme
        self._styles = get_styles_for_theme(theme)

    def get_styles(self):
        """Возвращает текущие стили"""
        return self._styles

    def __getitem__(self, key):
        return self._styles[key]

    def __getattr__(self, name):
        return self._styles.get(name, "")

# Глобальный экземпляр
STYLES = StyleManager()

def get_styles_for_theme(theme):
    """Возвращает словарь стилей для выбранной темы"""
    if theme == 'light':
        return LIGHT_STYLES
    else:
        return DARK_STYLES

def update_global_styles(theme):
    """Обновляет глобальные стили при смене темы"""
    STYLES.set_theme(theme)

def apply_theme_dynamic(app, theme_name='system'):
    """Применяет тему и принудительно обновляет все виджеты"""
    effective_theme = get_effective_theme(theme_name)
    if effective_theme == 'light':
        apply_light_theme(app)
    else:
        apply_dark_theme(app)

    # Форсируем перерисовку UI
    for widget in app.allWidgets():
        widget.update()
        widget.repaint()

    update_global_styles(effective_theme)
    return effective_theme