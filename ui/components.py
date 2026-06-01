from PySide6.QtWidgets import QPushButton, QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from ui.styles import STYLES
from ui.ui_scale import UiScale, scale_stylesheet
from core.app_icon import get_logo_pixmap


class NavigationButton(QPushButton):
    """Кнопка навигации"""

    clicked_signal = Signal(str)

    def __init__(self, icon, text, page_name, theme='dark'):
        super().__init__()
        self.page_name = page_name
        self.setText(f"{icon} {text}")
        self.theme = theme
        self.update_style()
        self.setCheckable(True)
        self.clicked.connect(self.on_clicked)

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        fs = UiScale.px(14)
        pad_v = UiScale.px(12)
        pad_h = UiScale.px(20)
        radius = UiScale.px(8)

        if self.theme == 'light':
            qss = f"""
                QPushButton {{
                    background-color: transparent;
                    color: #000000;
                    border: 2px solid transparent;
                    border-radius: {radius}px;
                    padding: {pad_v}px {pad_h}px;
                    text-align: left;
                    font-size: {fs}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #e0e0e0;
                    border: 2px solid #999999;
                }}
                QPushButton:checked {{
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }}
            """
        else:
            qss = f"""
                QPushButton {{
                    background-color: transparent;
                    color: #d4d4d4;
                    border: 2px solid transparent;
                    border-radius: {radius}px;
                    padding: {pad_v}px {pad_h}px;
                    text-align: left;
                    font-size: {fs}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #3a3a3a;
                    border: 2px solid #555555;
                }}
                QPushButton:checked {{
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }}
            """
        self.setStyleSheet(qss)

    def on_clicked(self):
        self.clicked_signal.emit(self.page_name)


class HeaderWidget(QFrame):
    """Верхняя шапка приложения"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("HeaderWidget")
        self.title_label = None
        self.subtitle_label = None
        self.apply_scale()
        self.update_style()
        self.init_ui()

    def apply_scale(self):
        self.setFixedHeight(UiScale.header_height())

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        if self.theme == 'light':
            self.setStyleSheet("""
                #HeaderWidget {
                    background-color: #ffffff;
                    border-bottom: 2px solid #3a7bd5;
                }
            """)
        else:
            self.setStyleSheet("""
                #HeaderWidget {
                    background-color: #1e1e1e;
                    border-bottom: 2px solid #3a7bd5;
                }
            """)
        if self.title_label:
            self.title_label.setStyleSheet(self._get_title_style())

    def init_ui(self):
        layout = QHBoxLayout(self)
        m = UiScale.px(20)
        layout.setContentsMargins(m, UiScale.px(10), m, UiScale.px(10))

        title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        logo = UiScale.logo_size()
        self.logo_label.setFixedSize(logo, logo)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_logo_pixmap()

        self.title_label = QLabel("VK Archiver CHIBGU")
        self.title_label.setStyleSheet(self._get_title_style())

        title_layout.addWidget(self.logo_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addStretch()

    def _get_title_style(self):
        fs = UiScale.font_header_widget()
        color = '#000000' if self.theme == 'light' else '#ffffff'
        return f"color: {color}; font-size: {fs}px; font-weight: bold;"

    def _set_logo_pixmap(self):
        size = UiScale.logo_size()
        pixmap = get_logo_pixmap(size, self.theme)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setText("")

    def update_theme(self, theme):
        self.apply_scale()
        self.update_style(theme)
        self._set_logo_pixmap()
        if self.title_label:
            self.title_label.setStyleSheet(self._get_title_style())


class SidebarWidget(QFrame):
    """Боковая панель навигации"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("SidebarWidget")
        self._section_labels = []
        self._version_label = None
        self.apply_scale()
        self.update_style()
        self.init_ui()

    def apply_scale(self):
        self.setFixedWidth(UiScale.sidebar_width())

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        if self.theme == 'light':
            self.setStyleSheet("""
                #SidebarWidget {
                    background-color: #f5f5f5;
                    border-right: 2px solid #dddddd;
                }
            """)
        else:
            self.setStyleSheet("""
                #SidebarWidget {
                    background-color: #252525;
                    border-right: 2px solid #333333;
                }
            """)
        for label in self._section_labels:
            label.setStyleSheet(self._get_section_label_style())
        if self._version_label:
            self._version_label.setStyleSheet(self._get_version_label_style())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(UiScale.px(10), UiScale.px(20), UiScale.px(10), UiScale.px(20))
        layout.setSpacing(UiScale.px(5))

        main_label = QLabel("ОСНОВНОЕ")
        main_label.setStyleSheet(self._get_section_label_style())
        self._section_labels.append(main_label)
        layout.addWidget(main_label)

        self.buttons = {}
        self.buttons['download'] = NavigationButton("", "Загрузка контента", "download", self.theme)
        self.buttons['search'] = NavigationButton("", "Поиск в архиве", "search", self.theme)
        self.buttons['stats'] = NavigationButton("", "Статистика постов", "stats", self.theme)
        self.buttons['storage'] = NavigationButton("", "Хранилище постов", "storage", self.theme)
        self.buttons['teachers'] = NavigationButton("", "Преподаватели в постах", "teachers", self.theme)

        for key in ('download', 'search', 'stats', 'storage', 'teachers'):
            layout.addWidget(self.buttons[key])

        layout.addSpacing(UiScale.px(20))

        settings_label = QLabel("НАСТРОЙКИ")
        settings_label.setStyleSheet(self._get_section_label_style())
        self._section_labels.append(settings_label)
        layout.addWidget(settings_label)

        self.buttons['departments'] = NavigationButton("", "Кафедры и преподаватели", "departments", self.theme)
        self.buttons['settings'] = NavigationButton("", "Настройки приложения", "settings", self.theme)
        self.buttons['about'] = NavigationButton("", "О программе", "about", self.theme)

        for key in ('departments', 'settings', 'about'):
            layout.addWidget(self.buttons[key])

        layout.addStretch()

        self._version_label = QLabel("v1.0.0")
        self._version_label.setStyleSheet(self._get_version_label_style())
        layout.addWidget(self._version_label)

    def _get_section_label_style(self):
        fs = UiScale.font_small()
        pad = UiScale.px(10)
        return (
            f"color: #888888; font-size: {fs}px; font-weight: bold; "
            f"padding: {pad}px {pad}px {UiScale.px(5)}px {pad}px; text-transform: uppercase;"
        )

    def _get_version_label_style(self):
        fs = UiScale.font_small()
        pad = UiScale.px(10)
        color = '#999999' if self.theme == 'light' else '#555555'
        return f"color: {color}; font-size: {fs}px; padding: {pad}px;"

    def update_theme(self, theme):
        self.apply_scale()
        self.update_style(theme)
        for btn in self.buttons.values():
            btn.update_style(theme)
