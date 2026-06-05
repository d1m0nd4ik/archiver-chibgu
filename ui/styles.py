from urllib.parse import quote

from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from core.config_manager import get_effective_theme
from ui.ui_scale import UiScale, scale_stylesheet, scale_stylesheet_dict

def apply_dark_theme(app):
    """Применение тёмной темы"""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 17, 21))
    palette.setColor(QPalette.WindowText, QColor(238, 241, 246))
    palette.setColor(QPalette.Base, QColor(34, 40, 49))
    palette.setColor(QPalette.AlternateBase, QColor(26, 31, 40))
    palette.setColor(QPalette.ToolTipBase, QColor(22, 25, 32))
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

ACCENT = '#3a7bd5'
ACCENT_HOVER = '#2c5aa0'
ACCENT_GRADIENT_END = '#2f6fce'


def get_theme_colors(theme=None):
    """Единая палитра интерфейса (светлая / тёмная)."""
    if (theme or STYLES._theme) == 'light':
        return {
            'page_bg': '#e2e5ec',
            'content_bg': '#e8ebf1',
            'sidebar_bg': '#e0e4ec',
            'header_bg': '#f0f2f6',
            'card': '#eef0f5',
            'panel_bg': '#eef0f5',
            'input_bg': '#f6f7fa',
            'input_border': '#c5cbd8',
            'text': '#2e3440',
            'text_muted': '#5c6478',
            'separator': '#cdd3df',
            'hover_bg': '#dce1eb',
            'btn_surface': '#e4e8f0',
            'tag': '#2f6fce',
            'link': '#2f6fce',
            'accent': ACCENT,
            'accent_hover': ACCENT_HOVER,
            'on_accent': '#ffffff',
            'radius_lg': '12px',
            'radius_md': '8px',
            'radius_sm': '6px',
        }
    return {
        'page_bg': '#0f1115',
        'content_bg': '#0f1115',
        'sidebar_bg': '#161a21',
        'header_bg': '#0f1115',
        'card': '#1a1f28',
        'panel_bg': '#1a1f28',
        'input_bg': '#222831',
        'input_border': '#3a4454',
        'btn_surface': '#252c38',
        'text': '#eef1f6',
        'text_muted': '#9aa5b8',
        'separator': '#2e3644',
        'hover_bg': '#323b4a',
        'tag': '#6ea8ff',
        'link': '#6ea8ff',
        'accent': ACCENT,
        'accent_hover': ACCENT_HOVER,
        'on_accent': '#ffffff',
        'radius_lg': '12px',
        'radius_md': '8px',
        'radius_sm': '6px',
    }


def get_page_header_style(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(
        f"color: {c['text']}; font-size: 22px; font-weight: bold; padding: 10px 0;"
    )


def get_page_subtitle_style(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(
        f"color: {c['text_muted']}; font-size: 13px; padding: 0 0 8px 0;"
    )


def get_page_hint_style(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(
        f"color: {c['text_muted']}; font-size: 12px; font-style: italic;"
    )


def get_section_title_style(theme=None) -> str:
    c = get_theme_colors(theme)
    surf = c.get('btn_surface', c['card'])
    return scale_stylesheet(
        f"color: {c['text']}; font-size: 15px; font-weight: 600; "
        f"padding: 8px 10px; margin: 0; "
        f"background-color: {surf}; "
        f"border: 1px solid {c['input_border']}; "
        f"border-radius: {c['radius_sm']}; "
        f"font-family: inherit;"
    )


def get_sidebar_section_label_style(theme=None) -> str:
    c = get_theme_colors(theme)
    fs = UiScale.font_small()
    pad = UiScale.px(10)
    return (
        f"color: {c['text_muted']}; font-size: {fs}px; font-weight: bold; "
        f"padding: {pad}px {pad}px {UiScale.px(5)}px {pad}px;"
    )


def get_nav_button_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    fs = UiScale.px(14)
    pad_v = UiScale.px(12)
    pad_h = UiScale.px(20)
    r = c['radius_md']
    return scale_stylesheet(f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text']};
            border: 2px solid transparent;
            border-radius: {r};
            padding: {pad_v}px {pad_h}px;
            text-align: left;
            font-size: {fs}px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['hover_bg']};
            border: 2px solid {c['input_border']};
        }}
        QPushButton:checked {{
            background-color: {c['accent']};
            color: {c['on_accent']};
            border: 2px solid {c['accent_hover']};
        }}
    """)


def get_sidebar_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        #SidebarWidget {{
            background-color: {c['sidebar_bg']};
            border-right: 1px solid {c['separator']};
        }}
    """)


def get_header_widget_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        #HeaderWidget {{
            background-color: {c['header_bg']};
            border-bottom: 2px solid {c['accent']};
        }}
    """)


def get_header_title_style(theme=None) -> str:
    c = get_theme_colors(theme)
    return f"color: {c['text']}; font-size: {UiScale.font_header_widget()}px; font-weight: bold;"


def get_tab_widget_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    r = c['radius_md']
    return scale_stylesheet(f"""
        QTabWidget::pane {{
            border: 1px solid {c['input_border']};
            border-radius: {r};
            background: {c['card']};
            top: -1px;
        }}
        QTabBar::tab {{
            background: {c['input_bg']};
            color: {c['text_muted']};
            padding: 10px 18px;
            margin-right: 4px;
            border-top-left-radius: {c['radius_sm']};
            border-top-right-radius: {c['radius_sm']};
            border: 1px solid transparent;
            font-size: {UiScale.font_small()}px;
        }}
        QTabBar::tab:selected {{
            background: {c['card']};
            color: {c['text']};
            font-weight: 600;
            border: 1px solid {c['input_border']};
            border-bottom-color: {c['card']};
        }}
        QTabBar::tab:hover:!selected {{
            background: {c['hover_bg']};
            color: {c['text']};
        }}
    """)


def get_scroll_area_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
    """) + get_scrollbar_stylesheet(theme)


def get_scrollbar_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QScrollBar:vertical {{
            background: {c['card']};
            width: 10px;
            margin: 2px 0;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['input_border']};
            min-height: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: {c['card']};
            height: 10px;
            margin: 0 2px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c['input_border']};
            min-width: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """)


def get_standard_input_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    fs = UiScale.px(13)
    h = UiScale.px(40)
    return scale_stylesheet(f"""
        QLineEdit {{
            padding: 10px 12px;
            border-radius: {c['radius_sm']};
            border: 1px solid {c['input_border']};
            background-color: {c['input_bg']};
            color: {c['text']};
            font-family: inherit;
            font-size: {fs}px;
            selection-background-color: {c['accent']};
            min-height: {h}px;
        }}
        QLineEdit:focus {{ border: 1px solid {c['accent']}; }}
        QLineEdit:disabled {{
            background-color: {c['card']};
            color: {c['text_muted']};
        }}
    """)


def get_standard_button_stylesheet(theme=None, *, primary: bool = True) -> str:
    c = get_theme_colors(theme)
    fs = UiScale.px(13)
    r = c['radius_md']
    if primary:
        return scale_stylesheet(f"""
            QPushButton {{
                padding: 11px 22px;
                border-radius: {r};
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4b8df2, stop:1 {ACCENT_GRADIENT_END});
                color: {c['on_accent']};
                font-weight: bold;
                font-size: {fs}px;
                border: 1px solid {c['accent_hover']};
            }}
            QPushButton:hover {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a9cff, stop:1 #3578d9);
            }}
            QPushButton:pressed {{ background-color: {c['accent_hover']}; }}
            QPushButton:disabled {{
                background-color: {c['card']};
                color: {c['text_muted']};
                border: 1px solid {c['separator']};
            }}
        """)
    surf = c.get('btn_surface', c['card'])
    return scale_stylesheet(f"""
        QPushButton {{
            padding: 11px 22px;
            border-radius: {r};
            background-color: {surf};
            color: {c['text']};
            font-weight: 600;
            font-size: {fs}px;
            border: 2px solid {c['input_border']};
        }}
        QPushButton:hover {{
            background-color: {c['hover_bg']};
            border-color: {c['accent']};
            color: {c['text']};
        }}
        QPushButton:pressed {{
            background-color: {c['card']};
            border-color: {c['accent_hover']};
        }}
    """)


def get_standard_frame_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QFrame {{
            background-color: {c['card']};
            border-radius: {c['radius_lg']};
            padding: 15px;
            border: 1px solid {c['input_border']};
        }}
    """)


def get_standard_textedit_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QTextEdit {{
            background-color: {c['input_bg']};
            color: {c['text']};
            font-family: Consolas, 'Courier New', monospace;
            font-size: {UiScale.font_body()}px;
            border-radius: {c['radius_sm']};
            border: 1px solid {c['input_border']};
            padding: 10px;
            selection-background-color: {c['accent']};
        }}
        QTextEdit:focus {{ border: 1px solid {c['accent']}; }}
    """)


def get_standard_progressbar_stylesheet(theme=None) -> str:
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QProgressBar {{
            border: 1px solid {c['input_border']};
            border-radius: {c['radius_sm']};
            background-color: {c['input_bg']};
            text-align: center;
            color: {c['text']};
            height: 25px;
        }}
        QProgressBar::chunk {{
            background-color: {c['accent']};
            border-radius: 5px;
        }}
    """)


def get_theme_toggle_button_styles(theme=None, *, light_selected: bool) -> str:
    c = get_theme_colors(theme)
    r = c['radius_md']
    if light_selected:
        return scale_stylesheet(f"""
            QPushButton {{
                padding: 10px 20px;
                border-radius: {r};
                background-color: #e8b923;
                color: #1a1a1a;
                border: 1px solid #c9a01e;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #f5d547; }}
        """)
    return scale_stylesheet(f"""
        QPushButton {{
            padding: 10px 20px;
            border-radius: {r};
            background-color: {c['input_bg']};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            font-weight: bold;
            font-size: 14px;
        }}
        QPushButton:hover {{
            background-color: {c['hover_bg']};
            border-color: {c['accent']};
        }}
    """)


def _svg_data_uri(svg: str) -> str:
    """Data-URI для QSS: url в кавычках, без charset (запятая ломает парсер Qt)."""
    encoded = quote(svg, safe="")
    return f'url("data:image/svg+xml,{encoded}")'


def _qss_arrow_down(color: str, *, w: int = 10, h: int = 6) -> str:
    hex_c = color.lstrip('#')
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<path fill='#{hex_c}' d='M0 0h{w}L{w // 2} {h}Z'/>"
        f"</svg>"
    )
    return (
        f"width: {w}px; height: {h}px; border: none; image: {_svg_data_uri(svg)};"
    )


def _qss_arrow_up(color: str, *, w: int = 10, h: int = 6) -> str:
    hex_c = color.lstrip('#')
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}'>"
        f"<path fill='#{hex_c}' d='M0 {h}h{w}L{w // 2} 0Z'/>"
        f"</svg>"
    )
    return (
        f"width: {w}px; height: {h}px; border: none; image: {_svg_data_uri(svg)};"
    )


def _label_inside_panel(label, names: tuple[str, ...]) -> bool:
    widget = label.parentWidget()
    while widget is not None:
        if widget.objectName() in names:
            return True
        widget = widget.parentWidget()
    return False


def _is_calendar_popup_widget(widget) -> bool:
    """Внутренние виджеты календаря QDateEdit — не стилизуем нашим QSS."""
    name = widget.objectName() or ""
    if name.startswith("qt_calendar"):
        return True
    parent = widget.parentWidget()
    while parent is not None:
        if parent.metaObject().className() == "QCalendarWidget":
            return True
        parent = parent.parentWidget()
    return False


def _compact_field_base(theme=None) -> tuple[dict, int, int]:
    c = get_theme_colors(theme)
    fs = UiScale.font_small()
    h = UiScale.px(30)
    arrow = c['text_muted']
    return c, fs, h, arrow


def get_compact_input_stylesheet(theme=None) -> str:
    """Компактное поле ввода (без стрелки)."""
    c, fs, h, _ = _compact_field_base(theme)
    return scale_stylesheet(f"""
        QLineEdit {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            border-radius: 6px;
            font-size: {fs}px;
            padding: 3px 8px;
            min-height: {h}px;
            max-height: {h}px;
        }}
    """)


def get_combo_stylesheet(theme=None, *, compact: bool = False) -> str:
    """QComboBox со видимой кнопкой и стрелкой (Fusion не рисует её без QSS)."""
    c = get_theme_colors(theme)
    arrow = c['text_muted']
    if compact:
        fs = UiScale.font_small()
        h = UiScale.px(30)
        border_w = 1
        pad = "3px 6px 3px 8px"
    else:
        fs = UiScale.px(13)
        h = UiScale.px(36)
        border_w = 2
        pad = "8px 12px"
    dd = UiScale.px(28)
    arrow_qss = _qss_arrow_down(arrow)
    btn_bg = c.get('btn_surface', c['card'])
    return scale_stylesheet(f"""
        QComboBox {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: {border_w}px solid {c['input_border']};
            border-radius: 6px;
            font-size: {fs}px;
            padding: {pad};
            padding-right: {dd}px;
            min-height: {h}px;
        }}
        QComboBox:editable {{
            padding-right: {dd}px;
        }}
        QComboBox:editable QLineEdit {{
            background: transparent;
            color: {c['text']};
            border: none;
            padding: 0 2px;
            margin: 0;
            selection-background-color: #3a7bd5;
        }}
        QComboBox:focus {{
            border: {border_w}px solid #3a7bd5;
        }}
        QComboBox:disabled {{
            background-color: {c['card']};
            color: {c['text_muted']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: {dd}px;
            border: none;
            border-left: 1px solid {c['input_border']};
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
            background-color: {btn_bg};
        }}
        QComboBox::down-arrow {{
            {arrow_qss}
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            selection-background-color: #3a7bd5;
            font-size: {fs}px;
        }}
    """)


def get_compact_combo_stylesheet(theme=None) -> str:
    """Компактный выпадающий список со стрелкой."""
    return get_combo_stylesheet(theme, compact=True)


def get_date_stylesheet(theme=None, *, compact: bool = False) -> str:
    """QDateEdit со стрелкой календаря."""
    c = get_theme_colors(theme)
    arrow = c['text_muted']
    if compact:
        fs = UiScale.font_small()
        h = UiScale.px(30)
        border_w = 1
        pad = "3px 6px 3px 8px"
    else:
        fs = UiScale.px(13)
        h = UiScale.px(36)
        border_w = 2
        pad = "8px 12px"
    dd = UiScale.px(28)
    arrow_qss = _qss_arrow_down(arrow)
    btn_bg = c.get('btn_surface', c['card'])
    return scale_stylesheet(f"""
        QDateEdit {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: {border_w}px solid {c['input_border']};
            border-radius: 6px;
            font-size: {fs}px;
            padding: {pad};
            padding-right: {dd}px;
            min-height: {h}px;
        }}
        QDateEdit:focus {{
            border: {border_w}px solid #3a7bd5;
        }}
        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: {dd}px;
            border: none;
            border-left: 1px solid {c['input_border']};
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
            background-color: {btn_bg};
        }}
        QDateEdit::down-arrow {{
            {arrow_qss}
        }}
    """)


def get_compact_date_stylesheet(theme=None) -> str:
    """Компактный выбор даты со стрелкой календаря."""
    return get_date_stylesheet(theme, compact=True)


def get_datetime_stylesheet(theme=None, *, compact: bool = False) -> str:
    """QDateTimeEdit — дата и время в едином стиле с полями."""
    c = get_theme_colors(theme)
    arrow = c['text']
    if compact:
        fs = UiScale.font_small()
        h = UiScale.px(30)
        border_w = 1
        pad = "3px 6px 3px 8px"
    else:
        fs = UiScale.px(13)
        h = UiScale.px(40)
        border_w = 1
        pad = "8px 12px"
    dd = UiScale.px(30)
    arrow_qss = _qss_arrow_down(arrow)
    btn_bg = c.get('btn_surface', c['card'])
    return scale_stylesheet(f"""
        QDateTimeEdit {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: {border_w}px solid {c['input_border']};
            border-radius: {c['radius_sm']};
            font-size: {fs}px;
            font-weight: 500;
            padding: {pad};
            padding-right: {dd}px;
            min-height: {h}px;
        }}
        QDateTimeEdit:focus {{
            border: {border_w}px solid {c['accent']};
        }}
        QDateTimeEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: {dd}px;
            border: none;
            border-left: 1px solid {c['input_border']};
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
            background-color: {btn_bg};
        }}
        QDateTimeEdit::down-arrow {{
            {arrow_qss}
        }}
    """)


def get_spinbox_stylesheet(theme=None) -> str:
    """QSpinBox / QDoubleSpinBox — без чёрного фона и стрелок."""
    c = get_theme_colors(theme)
    fs = UiScale.px(13)
    h = UiScale.px(36)
    btn = c.get('btn_surface', c['card'])
    up_arrow = _qss_arrow_up(c['text'])
    down_arrow = _qss_arrow_down(c['text'])
    return scale_stylesheet(f"""
        QAbstractSpinBox {{
            background-color: {c['input_bg']};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            border-radius: {c['radius_sm']};
            font-size: {fs}px;
            font-weight: 500;
            padding: 4px 8px;
            min-height: {h}px;
        }}
        QAbstractSpinBox:focus {{
            border: 1px solid {c['accent']};
        }}
        QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
            subcontrol-origin: border;
            width: 22px;
            background: {btn};
            border-left: 1px solid {c['input_border']};
        }}
        QAbstractSpinBox::up-button {{
            subcontrol-position: top right;
            border-top-right-radius: 5px;
        }}
        QAbstractSpinBox::down-button {{
            subcontrol-position: bottom right;
            border-bottom-right-radius: 5px;
        }}
        QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{
            background: {c['hover_bg']};
        }}
        QAbstractSpinBox::up-arrow {{
            {up_arrow}
        }}
        QAbstractSpinBox::down-arrow {{
            {down_arrow}
        }}
    """)


def get_stat_card_styles(theme=None) -> dict[str, str]:
    """Карточки сводки на дашборде."""
    c = get_theme_colors(theme)
    surf = c.get('btn_surface', c['card'])
    return {
        'frame': (
            f"QFrame#StatCard {{ background-color: {surf}; "
            f"border: 1px solid {c['input_border']}; border-radius: 10px; padding: 14px; }}"
        ),
        'title': (
            f"color: {c['text_muted']}; font-size: 12px; font-weight: 600; "
            f"background: transparent; padding: 0;"
        ),
        'value': (
            f"color: {c['text']}; font-size: 20px; font-weight: 700; "
            f"background: transparent; padding: 4px 0 0 0;"
        ),
    }


def get_compact_field_stylesheet(theme=None) -> str:
    """Обратная совместимость: общий стиль для всех полей."""
    return get_compact_input_stylesheet(theme)


def get_compact_button_stylesheet(primary: bool, theme=None) -> str:
    c = get_theme_colors(theme)
    fs = UiScale.font_small()
    h = UiScale.px(32)
    if primary:
        return scale_stylesheet(f"""
            QPushButton {{
                background-color: #3a7bd5;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: {fs}px;
                font-weight: 600;
                padding: 4px 14px;
                min-height: {h}px;
                max-height: {h}px;
            }}
            QPushButton:hover {{ background-color: #2c5aa0; }}
        """)
    surf = c.get('btn_surface', c['card'])
    return scale_stylesheet(f"""
        QPushButton {{
            background-color: {surf};
            color: {c['text']};
            border: 2px solid {c['input_border']};
            border-radius: 6px;
            font-size: {fs}px;
            font-weight: 600;
            padding: 4px 12px;
            min-height: {h}px;
            max-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: {c['hover_bg']};
            border-color: {c['accent']};
        }}
        QPushButton:pressed {{
            background-color: {c['card']};
        }}
    """)


def get_task_queue_styles(theme=None) -> dict[str, str]:
    """Стили панели фоновых задач — контрастные кнопки на тёмной теме."""
    c = get_theme_colors(theme)
    fs = UiScale.font_small()
    h = UiScale.px(34)
    base_btn = scale_stylesheet(f"""
        QPushButton {{
            border-radius: 6px;
            font-size: {fs}px;
            font-weight: 600;
            padding: 5px 16px;
            min-height: {h}px;
            max-height: {h}px;
        }}
    """)
    return {
        'clear': base_btn + scale_stylesheet(f"""
            QPushButton {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
            }}
            QPushButton:hover {{
                background-color: {c['card']};
                border-color: #3a7bd5;
                color: {c['text']};
            }}
        """),
        'cancel': base_btn + scale_stylesheet("""
            QPushButton {
                background-color: #c2410c;
                color: #ffffff;
                border: 1px solid #ea580c;
            }
            QPushButton:hover {
                background-color: #ea580c;
            }
        """),
        'cancel_disabled': base_btn + scale_stylesheet(f"""
            QPushButton {{
                background-color: {c['card']};
                color: {c['text_muted']};
                border: 1px solid {c['separator']};
            }}
        """),
        'status_ready': (
            f"color: {c['text_muted']}; font-size: {fs}px; "
            f"padding: 4px 10px; background: {c['card']}; "
            f"border-radius: 6px; border: 1px solid {c['separator']};"
        ),
        'status_busy': (
            f"color: #ffffff; font-size: {fs}px; font-weight: 600; "
            f"padding: 4px 10px; background: #3a7bd5; border-radius: 6px;"
        ),
        'progress': scale_stylesheet(f"""
            QProgressBar {{
                border: 1px solid {c['input_border']};
                border-radius: 6px;
                background: {c['input_bg']};
                color: {c['text']};
                font-size: {fs}px;
                text-align: center;
                min-height: {UiScale.px(22)}px;
                max-height: {UiScale.px(22)}px;
            }}
            QProgressBar::chunk {{
                background-color: #3a7bd5;
                border-radius: 5px;
            }}
        """),
        'log': scale_stylesheet(f"""
            QTextEdit {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 8px;
                font-size: {UiScale.font_body()}px;
                padding: 8px;
            }}
        """),
        'panel': scale_stylesheet(f"""
            QFrame#TaskQueuePanel {{
                background-color: {c['card']};
                border: 1px solid {c['input_border']};
                border-radius: 10px;
            }}
        """),
    }


def _transparent_label_qss(extra: str) -> str:
    """QLabel на фоне карточки — без отдельной «плашки» (светлая и тёмная тема)."""
    return (
        f"background-color: transparent; background: none; border: none; "
        f"{extra}"
    )


def apply_panel_label_style(label, qss: str) -> None:
    """Подпись внутри панели: прозрачный фон, не перекрывается палитрой Qt."""
    from PySide6.QtWidgets import QLabel
    if isinstance(label, QLabel):
        label.setAutoFillBackground(False)
        label.setStyleSheet(qss)


def get_storage_summary_styles(theme=None) -> dict[str, str]:
    c = get_theme_colors(theme)
    fs = UiScale.font_body()
    sm = UiScale.font_small()
    return {
        'frame': scale_stylesheet(f"""
            QFrame#storageSummary {{
                background-color: {c['card']};
                border: 1px solid {c['input_border']};
                border-radius: 10px;
            }}
        """),
        'stats': _transparent_label_qss(
            f"color: {c['text']}; font-size: {fs}px; font-weight: 500; padding: 2px 0;"
        ),
        'stat_muted': _transparent_label_qss(
            f"color: {c['text_muted']}; font-size: {sm}px; padding: 0;"
        ),
        'folder': _transparent_label_qss(
            f"color: {c['tag']}; font-size: {sm}px; font-weight: 600; padding: 0;"
        ),
        'folder_path': _transparent_label_qss(
            f"color: {c['text_muted']}; font-size: {sm}px; padding: 0;"
        ),
        'sep': f"background-color: {c['separator']}; max-height: 1px; border: none;",
    }


def get_panel_filter_label_style(theme=None) -> str:
    """Подпись фильтра на карточке (поиск и т.п.) — без отдельной плашки."""
    c = get_theme_colors(theme)
    fs = UiScale.font_small()
    return scale_stylesheet(
        _transparent_label_qss(
            f"color: {c['text']}; font-size: {fs}px; font-weight: 600; "
            f"padding: 0 8px 0 0; margin: 0;"
        )
    )


def get_filter_label_style(theme=None) -> str:
    """Подпись поля вне карточки — с лёгкой плашкой для контраста."""
    c = get_theme_colors(theme)
    surf = c.get('btn_surface', c['card'])
    fs = UiScale.font_small()
    r = c['radius_sm']
    return scale_stylesheet(
        f"color: {c['text']}; font-size: {fs}px; font-weight: 600; "
        f"padding: 6px 10px; background-color: {surf}; "
        f"border: 1px solid {c['input_border']}; border-radius: {r};"
    )


def get_form_label_style(theme=None) -> str:
    """Подпись в сетке формы на карточке — прозрачный фон."""
    return get_panel_filter_label_style(theme)


def get_panel_frame_stylesheet(theme=None) -> str:
    """Панели-карточки (кафедры / преподаватели) — цвета из активной темы."""
    c = get_theme_colors(theme)
    return scale_stylesheet(f"""
        QFrame#deptPanel, QFrame#teacherPanel, QFrame#tagsPanel {{
            background-color: {c['card']};
            border: 1px solid {c['input_border']};
            border-radius: 14px;
        }}
    """)


def get_table_widget_palette(theme=None) -> QPalette:
    """Палитра таблицы: без неё Qt рисует выделение цветами темы окна (белый текст на светлом фоне)."""
    c = get_theme_colors(theme)
    surf = c.get('btn_surface', c['card'])
    palette = QPalette()
    palette.setColor(QPalette.Base, QColor(c['input_bg']))
    palette.setColor(QPalette.AlternateBase, QColor(c['card']))
    palette.setColor(QPalette.Text, QColor(c['text']))
    palette.setColor(QPalette.Window, QColor(c['input_bg']))
    palette.setColor(QPalette.Button, QColor(surf))
    palette.setColor(QPalette.ButtonText, QColor(c['text']))
    palette.setColor(QPalette.Highlight, QColor('#3a7bd5'))
    palette.setColor(QPalette.HighlightedText, QColor('#ffffff'))
    return palette


def get_table_header_palette(theme=None) -> QPalette:
    """Палитра шапки таблицы (отдельно от тела — иначе в светлой теме текст пропадает)."""
    c = get_theme_colors(theme)
    t = theme or STYLES._theme
    if t == 'light':
        bg, fg = '#c5ccd9', '#1a2233'
    else:
        bg = c.get('btn_surface', c['card'])
        fg = c['text']
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(bg))
    palette.setColor(QPalette.WindowText, QColor(fg))
    palette.setColor(QPalette.Text, QColor(fg))
    palette.setColor(QPalette.Button, QColor(bg))
    palette.setColor(QPalette.ButtonText, QColor(fg))
    return palette


def get_table_header_stylesheet(theme=None, *, compact: bool = False) -> str:
    c = get_theme_colors(theme)
    t = theme or STYLES._theme
    header_fs = 11 if compact else 12
    header_pad = "5px 6px" if compact else "8px 6px"
    if t == 'light':
        bg, fg = '#c5ccd9', '#1a2233'
    else:
        bg = c.get('btn_surface', c['card'])
        fg = c['text']
    return scale_stylesheet(f"""
        QHeaderView::section {{
            background-color: {bg};
            color: {fg};
            padding: {header_pad};
            border: none;
            border-bottom: 2px solid {c['accent']};
            font-weight: 700;
            font-size: {header_fs}px;
        }}
    """)


def apply_table_theme(table, theme=None, *, compact: bool = False) -> None:
    """Единое оформление таблицы: QSS + палитра viewport и заголовка."""
    from PySide6.QtWidgets import QTableWidget
    from PySide6.QtCore import Qt
    if not isinstance(table, QTableWidget):
        return
    t = theme or STYLES._theme
    table_style = get_table_stylesheet(t, compact=compact)
    table_palette = get_table_widget_palette(t)
    header_palette = get_table_header_palette(t)
    header_style = get_table_header_stylesheet(t, compact=compact)
    table.setStyleSheet(table_style)
    table.setPalette(table_palette)
    table.viewport().setPalette(table_palette)
    hdr = table.horizontalHeader()
    if hdr:
        hdr.setPalette(header_palette)
        hdr.setStyleSheet(header_style)
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hdr.setMinimumHeight(UiScale.px(26 if compact else 30))
        hdr.setVisible(True)
    vhdr = table.verticalHeader()
    if vhdr:
        vhdr.setPalette(table_palette)


def get_table_stylesheet(theme=None, *, compact: bool = False) -> str:
    c = get_theme_colors(theme)
    body_fs = 12 if compact else 13
    header_fs = 11 if compact else 12
    cell_pad = "4px 5px" if compact else "8px 6px"
    header_pad = "5px 5px" if compact else "8px 6px"
    qss = f"""
        QTableWidget {{
            background-color: {c['input_bg']};
            color: {c['text']};
            gridline-color: {c['separator']};
            border: 1px solid {c['input_border']};
            border-radius: 8px;
            font-size: {body_fs}px;
            alternate-background-color: {c['card']};
            outline: none;
        }}
        QTableWidget::item {{
            padding: {cell_pad};
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
            background-color: {c.get('btn_surface', c['card'])};
            color: {c['text']};
            padding: {header_pad};
            border: none;
            border-bottom: 2px solid {c['accent']};
            font-weight: 600;
            font-size: {header_fs}px;
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
    """Возвращает словарь стилей для выбранной темы (единая палитра)."""
    c = get_theme_colors(theme)
    return {
        'input': get_standard_input_stylesheet(theme),
        'combo': get_combo_stylesheet(theme, compact=False),
        'date': get_date_stylesheet(theme, compact=False),
        'datetime': get_datetime_stylesheet(theme, compact=False),
        'spinbox': get_spinbox_stylesheet(theme),
        'button': get_standard_button_stylesheet(theme, primary=True),
        'button_secondary': get_standard_button_stylesheet(theme, primary=False),
        'textedit': get_standard_textedit_stylesheet(theme),
        'frame': get_standard_frame_stylesheet(theme),
        'table': get_table_stylesheet(theme),
        'label': scale_stylesheet(
            f"color: {c['text']}; font-size: {UiScale.font_body()}px; "
            f"padding: 2px 4px; background-color: transparent; border: none;"
        ),
        'label_title': get_section_title_style(theme),
        'progressbar': get_standard_progressbar_stylesheet(theme),
        'statusbar': (
            f"background-color: {c['sidebar_bg']}; color: {c['text']}; "
            f"border-top: 1px solid {c['separator']};"
        ),
        'navigation': get_nav_button_stylesheet(theme),
        'tab_widget': get_tab_widget_stylesheet(theme),
        'scroll_area': get_scroll_area_stylesheet(theme),
    }

def update_global_styles(theme):
    """Обновляет глобальные стили при смене темы"""
    STYLES.set_theme(theme)


def refresh_ui_scale():
    """Пересчёт масштаба и стилей (после init_from_screen)."""
    STYLES.refresh_scale()

def apply_theme_to_page(page, styles=None):
    """Обновляет все стандартные виджеты на странице после смены темы."""
    from PySide6.QtWidgets import (
        QFrame, QLineEdit, QTextEdit, QComboBox, QDateEdit, QDateTimeEdit,
        QPushButton, QLabel, QScrollArea, QTableWidget, QTabWidget, QListWidget,
        QProgressBar, QAbstractSpinBox, QCheckBox,
    )

    styles = styles or STYLES.get_styles()
    theme = getattr(STYLES, '_theme', None)
    colors = get_theme_colors(theme)
    skip_frame_ids = set()
    for scroll in page.findChildren(QScrollArea):
        scroll.setStyleSheet(styles.get('scroll_area', get_scroll_area_stylesheet(theme)))
        vp = scroll.viewport()
        if vp:
            skip_frame_ids.add(id(vp))
            vp.setStyleSheet(f"background-color: {colors['page_bg']};")

    page.setStyleSheet(f"background-color: {colors['page_bg']};")

    if hasattr(page, 'header_label'):
        page.header_label.setStyleSheet(get_page_header_style(theme))

    for tab in page.findChildren(QTabWidget):
        tab.setStyleSheet(styles.get('tab_widget', get_tab_widget_stylesheet(theme)))

    for frame in page.findChildren(QFrame):
        if id(frame) in skip_frame_ids:
            continue
        oid = frame.objectName() or ''
        ss = frame.styleSheet() or ''
        if 'background-color: transparent' in ss:
            continue
        if oid in ('deptPanel', 'teacherPanel', 'tagsPanel', 'storageSummary', 'StatCard'):
            continue
        frame.setStyleSheet(styles['frame'])

    combo_style = get_combo_stylesheet(theme, compact=False)
    date_style = get_date_stylesheet(theme, compact=False)
    for combo in page.findChildren(QComboBox):
        if _is_calendar_popup_widget(combo):
            continue
        combo.setStyleSheet(combo_style)
    for date_edit in page.findChildren(QDateEdit):
        if _is_calendar_popup_widget(date_edit):
            continue
        date_edit.setStyleSheet(date_style)
    dt_style = styles.get('datetime', get_datetime_stylesheet(theme))
    for dt_edit in page.findChildren(QDateTimeEdit):
        if _is_calendar_popup_widget(dt_edit):
            continue
        dt_edit.setStyleSheet(dt_style)
    for line_edit in page.findChildren(QLineEdit):
        line_edit.setStyleSheet(styles['input'])
    for text_edit in page.findChildren(QTextEdit):
        if hasattr(page, 'errors_view') and text_edit is page.errors_view:
            text_edit.setStyleSheet(get_standard_textedit_stylesheet(theme))
        else:
            text_edit.setStyleSheet(styles['textedit'])
    for lst in page.findChildren(QListWidget):
        lst.setStyleSheet(styles['textedit'])
    spin_style = styles.get('spinbox', get_spinbox_stylesheet(theme))
    for spin in page.findChildren(QAbstractSpinBox):
        if _is_calendar_popup_widget(spin):
            continue
        spin.setStyleSheet(spin_style)
    chk_style = scale_stylesheet(f"""
        QCheckBox {{ color: {colors['text']}; font-size: {UiScale.font_small()}px; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px;
            border: 1px solid {colors['input_border']};
            border-radius: 4px;
            background: {colors['input_bg']};
        }}
        QCheckBox::indicator:checked {{
            background: {colors['accent']};
            border-color: {colors['accent_hover']};
        }}
    """)
    for cb in page.findChildren(QCheckBox):
        cb.setStyleSheet(chk_style)
    for bar in page.findChildren(QProgressBar):
        bar.setStyleSheet(styles['progressbar'])
    if hasattr(page, 'progress_bar'):
        page.progress_bar.setStyleSheet(styles['progressbar'])
    if hasattr(page, 'progress'):
        page.progress.setStyleSheet(styles['progressbar'])

    for table in page.findChildren(QTableWidget):
        apply_table_theme(table, theme)

    secondary = set(getattr(page, '_secondary_buttons', []) or [])
    for btn in page.findChildren(QPushButton):
        if hasattr(page, 'theme_toggle_btn') and btn is page.theme_toggle_btn:
            continue
        if btn in secondary:
            btn.setStyleSheet(styles['button_secondary'])
        else:
            btn.setStyleSheet(styles['button'])

    skip_labels = set(getattr(page, '_theme_custom_labels', []) or [])
    for attr in (
        'header_label', 'theme_info_label', 'summary_label', 'hint_label',
        'scheduler_info', 'journal_hint', 'subtitle_label', 'vk_title', 'theme_label',
    ):
        if hasattr(page, attr):
            skip_labels.add(getattr(page, attr))

    for label in page.findChildren(QLabel):
        if label in skip_labels:
            continue
        role = label.property('uiRole')
        if role == 'subtitle':
            label.setStyleSheet(get_page_subtitle_style(theme))
        elif role == 'hint':
            label.setStyleSheet(get_page_hint_style(theme))
        elif role == 'section':
            label.setStyleSheet(get_section_title_style(theme))
        elif role == 'field':
            label.setStyleSheet(get_form_label_style(theme))
        elif label is getattr(page, 'results_label', None):
            label.setStyleSheet(styles.get('label_title', styles.get('label', '')))
        elif _label_inside_panel(label, (
            'HeaderWidget', 'SidebarWidget', 'StatCard', 'storageSummary',
            'searchFilters', 'TaskQueuePanel', 'deptPanel', 'teacherPanel', 'tagsPanel',
        )):
            continue
        elif label.property('formLabel'):
            apply_panel_label_style(label, get_panel_filter_label_style(theme))
            continue
        else:
            label.setAutoFillBackground(False)
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