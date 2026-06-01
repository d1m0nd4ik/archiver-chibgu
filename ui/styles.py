from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from core.config_manager import get_effective_theme
from ui.ui_scale import UiScale, scale_stylesheet, scale_stylesheet_dict

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
    """Применение мягкой светлой темы (без чистого белого)"""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(226, 229, 236))
    palette.setColor(QPalette.WindowText, QColor(46, 52, 64))
    palette.setColor(QPalette.Base, QColor(246, 247, 250))
    palette.setColor(QPalette.AlternateBase, QColor(238, 240, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(244, 245, 248))
    palette.setColor(QPalette.ToolTipText, QColor(46, 52, 64))
    palette.setColor(QPalette.Text, QColor(46, 52, 64))
    palette.setColor(QPalette.Button, QColor(238, 240, 245))
    palette.setColor(QPalette.ButtonText, QColor(46, 52, 64))
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

def get_theme_colors(theme=None):
    """Цвета интерфейса для страниц и карточек."""
    if (theme or STYLES._theme) == 'light':
        return {
            'page_bg': '#e2e5ec',
            'content_bg': '#e8ebf1',
            'card': '#eef0f5',
            'input_bg': '#f6f7fa',
            'input_border': '#c5cbd8',
            'text': '#2e3440',
            'text_muted': '#5c6478',
            'separator': '#cdd3df',
        }
    return {
        'page_bg': '#1e1e1e',
        'content_bg': '#1e1e1e',
        'card': '#262a32',
        'input_bg': '#3c3c3c',
        'input_border': '#555555',
        'text': '#ffffff',
        'text_muted': '#aaaaaa',
        'separator': '#555555',
    }


def get_section_title_style(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(
        f"color: {c['text']}; font-size: 15px; font-weight: 600; "
        f"padding: 0; margin: 0;"
    )


def get_panel_frame_stylesheet(theme=None) -> str:
    """Панели-карточки (кафедры / преподаватели) — цвета из активной темы."""
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QFrame#deptPanel, QFrame#teacherPanel {{
            background-color: {c['card']};
            border: 1px solid {c['input_border']};
            border-radius: 14px;
        }}
    """)


def get_table_widget_palette(theme=None) -> QPalette:
    """Палитра таблицы: без неё Qt рисует выделение цветами темы окна (белый текст на светлом фоне)."""
    c = get_theme_colors(theme)
    palette = QPalette()
    palette.setColor(QPalette.Base, QColor(c['input_bg']))
    palette.setColor(QPalette.AlternateBase, QColor(c['card']))
    palette.setColor(QPalette.Text, QColor(c['text']))
    palette.setColor(QPalette.Window, QColor(c['input_bg']))
    palette.setColor(QPalette.Highlight, QColor('#3a7bd5'))
    palette.setColor(QPalette.HighlightedText, QColor('#ffffff'))
    return palette


def get_table_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    qss = f"""
        QTableWidget {{
            background-color: {c['input_bg']};
            color: {c['text']};
            gridline-color: {c['separator']};
            border: 1px solid {c['input_border']};
            border-radius: 8px;
            font-size: 13px;
            alternate-background-color: {c['card']};
            outline: none;
        }}
        QTableWidget::item {{
            padding: 8px 6px;
            border: none;
        }}
        QTableWidget::item:selected,
        QTableWidget::item:selected:active,
        QTableWidget::item:selected:!active,
        QTableWidget::item:selected:hover {{
            background-color: #3a7bd5;
            color: #ffffff;
        }}
        QTableWidget::item:alternate {{
            background-color: {c['card']};
        }}
        QTableCornerButton {{
            background-color: {c['card']};
            border: none;
        }}
        QHeaderView {{
            background-color: transparent;
            border: none;
        }}
        QHeaderView::section {{
            background-color: {c['card']};
            color: {c['text_muted']};
            padding: 8px 6px;
            border: none;
            border-bottom: 1px solid {c['separator']};
            font-weight: 600;
            font-size: 12px;
        }}
        QScrollBar:vertical {{
            background: {c['card']};
            width: 12px;
            margin: 2px 0 2px 0;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['input_border']};
            min-height: 28px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #3a7bd5;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: none;
        }}
        QScrollBar:horizontal {{
            background: {c['card']};
            height: 12px;
            margin: 0 2px 0 2px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c['input_border']};
            min-width: 28px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #3a7bd5;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
            background: none;
        }}
    """
    return scale_stylesheet(qss)


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
    'combo': """
        QComboBox {
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid #555555;
            background-color: #3c3c3c;
            color: #ffffff;
            font-size: 13px;
            min-height: 36px;
        }
        QComboBox:focus { border: 2px solid #3a7bd5; }
        QComboBox:disabled { background-color: #2a2a2a; color: #888888; }
        QComboBox::drop-down { border: none; width: 28px; }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            color: #ffffff;
            selection-background-color: #3a7bd5;
            border: 1px solid #555555;
        }
    """,
    'date': """
        QDateEdit {
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid #555555;
            background-color: #3c3c3c;
            color: #ffffff;
            font-size: 13px;
            min-height: 36px;
        }
        QDateEdit:focus { border: 2px solid #3a7bd5; }
        QDateEdit:disabled { background-color: #2a2a2a; color: #888888; }
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
    'table': """
        QTableWidget {
            background-color: #2b2b2b;
            color: #d4d4d4;
            gridline-color: #3f4654;
            border: 2px solid #555555;
            border-radius: 8px;
            font-size: 13px;
            alternate-background-color: #32363f;
        }
        QTableWidget::item { padding: 6px; }
        QTableWidget::item:selected {
            background-color: #3a7bd5;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #4472C4;
            color: #ffffff;
            padding: 8px;
            border: none;
            font-weight: bold;
            font-size: 11px;
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
            border: 2px solid #c5cbd8;
            background-color: #f6f7fa;
            color: #2e3440;
            font-size: 13px;
            selection-background-color: #3a7bd5;
            min-height: 40px;
        }
        QLineEdit:focus { border: 2px solid #3a7bd5; }
        QLineEdit:disabled { background-color: #e8ebf1; color: #8b93a3; border: 2px solid #d5dae3; }
    """,
    'combo': """
        QComboBox {
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid #c5cbd8;
            background-color: #f6f7fa;
            color: #2e3440;
            font-size: 13px;
            min-height: 36px;
        }
        QComboBox:focus { border: 2px solid #3a7bd5; }
        QComboBox:disabled { background-color: #e8ebf1; color: #8b93a3; }
        QComboBox::drop-down { border: none; width: 28px; }
        QComboBox QAbstractItemView {
            background-color: #f0f2f6;
            color: #2e3440;
            selection-background-color: #3a7bd5;
            selection-color: #ffffff;
            border: 1px solid #c5cbd8;
        }
    """,
    'date': """
        QDateEdit {
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid #c5cbd8;
            background-color: #f6f7fa;
            color: #2e3440;
            font-size: 13px;
            min-height: 36px;
        }
        QDateEdit:focus { border: 2px solid #3a7bd5; }
        QDateEdit:disabled { background-color: #e8ebf1; color: #8b93a3; }
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
            background-color: #f6f7fa; 
            color: #2e3440; 
            font-family: 'Consolas', 'Courier New', monospace; 
            font-size: 13px; 
            border-radius: 6px; 
            border: 2px solid #c5cbd8;
            padding: 10px; 
            selection-background-color: #3a7bd5;
        }
        QTextEdit:focus { border: 2px solid #3a7bd5; }
    """,
    'frame': """
        QFrame { 
            background-color: #eef0f5; 
            border-radius: 14px; 
            padding: 15px;
            border: 1px solid #d0d5df;
        }
    """,
    'table': """
        QTableWidget {
            background-color: #f6f7fa;
            color: #2e3440;
            gridline-color: #d0d5df;
            border: 2px solid #c5cbd8;
            border-radius: 8px;
            font-size: 13px;
            alternate-background-color: #eef0f5;
        }
        QTableWidget::item { padding: 6px; }
        QTableWidget::item:selected {
            background-color: #3a7bd5;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #4472C4;
            color: #ffffff;
            padding: 8px;
            border: none;
            font-weight: bold;
            font-size: 11px;
        }
    """,
    'label': "color: #2e3440; font-size: 13px; padding: 5px; ",
    'label_title': "color: #2e3440; font-size: 18px; font-weight: bold; padding: 10px; ",
    'progressbar': """
        QProgressBar {
            border: 2px solid #c5cbd8;
            border-radius: 6px;
            background-color: #e4e7ee;
            text-align: center;
            color: #2e3440;
            height: 25px;
        }
        QProgressBar::chunk { background-color: #3a7bd5; border-radius: 5px; }
    """,
    'statusbar': "background-color: #e4e7ee; color: #2e3440; border-top: 2px solid #cdd3df; ",
    'navigation': """
        QPushButton {
            background-color: transparent;
            color: #2e3440;
            border: 2px solid transparent;
            border-radius: 8px;
            padding: 12px 20px;
            text-align: left;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #dce1eb; border: 2px solid #c5cbd8; }
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
        self._styles = scale_stylesheet_dict(get_styles_for_theme(theme))

    def get_styles(self):
        """Возвращает текущие стили"""
        return self._styles

    def refresh_scale(self):
        """Пересчитать px в QSS после смены разрешения / DPI."""
        self._styles = scale_stylesheet_dict(get_styles_for_theme(self._theme))

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


def refresh_ui_scale():
    """Пересчёт масштаба и стилей (после init_from_screen)."""
    STYLES.refresh_scale()

def apply_theme_to_page(page, styles=None):
    """Обновляет все стандартные виджеты на странице после смены темы."""
    from PySide6.QtWidgets import (
        QFrame, QLineEdit, QTextEdit, QComboBox, QDateEdit, QPushButton, QLabel, QScrollArea,
        QTableWidget,
    )

    styles = styles or STYLES.get_styles()
    colors = get_theme_colors()
    skip_frame_ids = set()
    for scroll in page.findChildren(QScrollArea):
        vp = scroll.viewport()
        if vp:
            skip_frame_ids.add(id(vp))

    page.setStyleSheet(f"background-color: {colors['page_bg']};")

    if hasattr(page, 'header_label'):
        page.header_label.setStyleSheet(
            scale_stylesheet(
                f"color: {colors['text']}; font-size: 22px; font-weight: bold; padding: 10px 0;"
            )
        )

    for frame in page.findChildren(QFrame):
        if id(frame) in skip_frame_ids:
            continue
        ss = frame.styleSheet() or ''
        if 'background-color: transparent' in ss:
            continue
        frame.setStyleSheet(styles['frame'])

    combo_style = styles.get('combo', styles['input'])
    date_style = styles.get('date', styles['input'])
    for combo in page.findChildren(QComboBox):
        combo.setStyleSheet(combo_style)
    for date_edit in page.findChildren(QDateEdit):
        date_edit.setStyleSheet(date_style)
    for line_edit in page.findChildren(QLineEdit):
        line_edit.setStyleSheet(styles['input'])
    for text_edit in page.findChildren(QTextEdit):
        text_edit.setStyleSheet(styles['textedit'])
    if hasattr(page, 'progress_bar'):
        page.progress_bar.setStyleSheet(styles['progressbar'])
    if hasattr(page, 'progress'):
        page.progress.setStyleSheet(styles['progressbar'])

    table_style = get_table_stylesheet()
    for table in page.findChildren(QTableWidget):
        table.setStyleSheet(table_style)

    secondary = set(getattr(page, '_secondary_buttons', []) or [])
    for btn in page.findChildren(QPushButton):
        if hasattr(page, 'theme_toggle_btn') and btn is page.theme_toggle_btn:
            continue
        if btn in secondary:
            btn.setStyleSheet(styles['button_secondary'])
        else:
            btn.setStyleSheet(styles['button'])

    skip_labels = set(getattr(page, '_theme_custom_labels', []) or [])
    if hasattr(page, 'header_label'):
        skip_labels.add(page.header_label)
    if hasattr(page, 'theme_info_label'):
        skip_labels.add(page.theme_info_label)

    for label in page.findChildren(QLabel):
        if label in skip_labels:
            continue
        if label is getattr(page, 'results_label', None):
            label.setStyleSheet(styles.get('label_title', styles.get('label', '')))
        elif isinstance(label.parent(), QFrame):
            label.setStyleSheet(styles.get('label', ''))


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