from PySide6.QtWidgets import QPushButton, QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from ui.styles import (
    STYLES,
    get_nav_button_stylesheet,
    get_sidebar_stylesheet,
    get_header_widget_stylesheet,
    get_header_title_style,
    get_sidebar_section_label_style,
    get_theme_colors,
)
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
        self.setStyleSheet(get_nav_button_stylesheet(self.theme))

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
        self.setStyleSheet(get_header_widget_stylesheet(self.theme))
        if self.title_label:
            self.title_label.setStyleSheet(get_header_title_style(self.theme))

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
        self.title_label.setStyleSheet(get_header_title_style(self.theme))

        title_layout.addWidget(self.logo_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addStretch()

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
            self.title_label.setStyleSheet(get_header_title_style(self.theme))


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
        self.setStyleSheet(get_sidebar_stylesheet(self.theme))
        for label in self._section_labels:
            label.setStyleSheet(get_sidebar_section_label_style(self.theme))
        if self._version_label:
            c = get_theme_colors(self.theme)
            fs = UiScale.font_small()
            pad = UiScale.px(10)
            self._version_label.setStyleSheet(
                f"color: {c['text_muted']}; font-size: {fs}px; padding: {pad}px;"
            )

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(UiScale.px(10), UiScale.px(20), UiScale.px(10), UiScale.px(20))
        layout.setSpacing(UiScale.px(5))

        main_label = QLabel("ОСНОВНОЕ")
        main_label.setStyleSheet(get_sidebar_section_label_style(self.theme))
        self._section_labels.append(main_label)
        layout.addWidget(main_label)

        self.buttons = {}
        self.buttons['dashboard'] = NavigationButton("", "Сводка", "dashboard", self.theme)
        self.buttons['download'] = NavigationButton("", "Загрузка контента", "download", self.theme)
        self.buttons['search'] = NavigationButton("", "Поиск в архиве", "search", self.theme)
        self.buttons['stats'] = NavigationButton("", "Статистика постов", "stats", self.theme)
        self.buttons['storage'] = NavigationButton("", "Хранилище постов", "storage", self.theme)
        self.buttons['teachers'] = NavigationButton("", "Преподаватели в постах", "teachers", self.theme)

        for key in ('dashboard', 'download', 'search', 'stats', 'storage', 'teachers'):
            layout.addWidget(self.buttons[key])

        layout.addSpacing(UiScale.px(20))

        ref_label = QLabel("СПРАВОЧНИКИ")
        ref_label.setStyleSheet(get_sidebar_section_label_style(self.theme))
        self._section_labels.append(ref_label)
        layout.addWidget(ref_label)

        self.buttons['departments'] = NavigationButton("", "Кафедры и преподаватели", "departments", self.theme)
        self.buttons['tags'] = NavigationButton("", "Тэги", "tags", self.theme)
        self.buttons['posts_manage'] = NavigationButton("", "Управление постами", "posts_manage", self.theme)

        for key in ('departments', 'tags', 'posts_manage'):
            layout.addWidget(self.buttons[key])

        layout.addSpacing(UiScale.px(20))

        settings_label = QLabel("НАСТРОЙКИ")
        settings_label.setStyleSheet(get_sidebar_section_label_style(self.theme))
        self._section_labels.append(settings_label)
        layout.addWidget(settings_label)

        self.buttons['settings'] = NavigationButton("", "Настройки приложения", "settings", self.theme)
        self.buttons['about'] = NavigationButton("", "О программе", "about", self.theme)

        for key in ('settings', 'about'):
            layout.addWidget(self.buttons[key])

        layout.addStretch()

        self._version_label = QLabel("v1.0.0")
        c = get_theme_colors(self.theme)
        self._version_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: {UiScale.font_small()}px; "
            f"padding: {UiScale.px(10)}px;"
        )
        layout.addWidget(self._version_label)

    def update_theme(self, theme):
        self.apply_scale()
        self.update_style(theme)
        for btn in self.buttons.values():
            btn.update_style(theme)
