from PySide6.QtWidgets import QPushButton, QFrame, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Signal, Qt
from ui.styles import STYLES
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

        if self.theme == 'light':
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #000000;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    padding: 12px 20px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border: 2px solid #999999;
                }
                QPushButton:checked {
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #d4d4d4;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    padding: 12px 20px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 2px solid #555555;
                }
                QPushButton:checked {
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }
            """)

    def on_clicked(self):
        self.clicked_signal.emit(self.page_name)


class HeaderWidget(QFrame):
    """Верхняя шапка приложения"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("HeaderWidget")
        self.setFixedHeight(70)
        self.update_style()
        self.init_ui()

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

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(48, 48)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_logo_pixmap()

        title_label = QLabel("VK Media Archiver Pro")
        title_label.setStyleSheet(self._get_title_style())

        subtitle_label = QLabel("Профессиональный архиватор контента ВКонтакте")
        subtitle_label.setStyleSheet(self._get_subtitle_style())

        title_layout.addWidget(self.logo_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addStretch()

    def _get_title_style(self):
        if self.theme == 'light':
            return "color: #000000; font-size: 24px; font-weight: bold;"
        else:
            return "color: #ffffff; font-size: 24px; font-weight: bold;"

    def _get_subtitle_style(self):
        if self.theme == 'light':
            return "color: #888888; font-size: 12px;"
        else:
            return "color: #888888; font-size: 12px;"

    def _set_logo_pixmap(self):
        pixmap = get_logo_pixmap(48, self.theme)
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap)
            self.logo_label.setText("")

    def update_theme(self, theme):
        self.update_style(theme)
        self._set_logo_pixmap()
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QLabel):
                        if 'Pro' in widget.text():
                            widget.setStyleSheet(self._get_title_style())
                        elif 'Профессиональный' in widget.text():
                            widget.setStyleSheet(self._get_subtitle_style())


class SidebarWidget(QFrame):
    """Боковая панель навигации"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("SidebarWidget")
        self.setFixedWidth(280)
        self.update_style()
        self.init_ui()

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

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)

        main_label = QLabel("ОСНОВНОЕ")
        main_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(main_label)

        self.buttons = {}
        self.buttons['download'] = NavigationButton("", "Загрузка контента", "download", self.theme)
        self.buttons['search'] = NavigationButton("", "Поиск в архиве", "search", self.theme)
        self.buttons['stats'] = NavigationButton("", "Статистика постов", "stats", self.theme)
        self.buttons['storage'] = NavigationButton("", "Хранилище постов", "storage", self.theme)
        self.buttons['teachers'] = NavigationButton("", "Преподаватели в постах", "teachers", self.theme)

        for btn in self.buttons.values():
            layout.addWidget(btn)

        layout.addSpacing(20)
        
        settings_label = QLabel("НАСТРОЙКИ")
        settings_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(settings_label)

        self.buttons['settings'] = NavigationButton("", "Настройки приложения", "settings", self.theme)
        self.buttons['about'] = NavigationButton("", "О программе", "about", self.theme)

        for btn in self.buttons.values():
            if btn not in list(self.buttons.values())[:5]:
                layout.addWidget(btn)

        layout.addStretch()

        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(self._get_version_label_style())
        layout.addWidget(version_label)

    def _get_section_label_style(self):
        return "color: #888888; font-size: 11px; font-weight: bold; padding: 10px 10px 5px 10px; text-transform: uppercase;"

    def _get_version_label_style(self):
        if self.theme == 'light':
            return "color: #999999; font-size: 11px; padding: 10px;"
        else:
            return "color: #555555; font-size: 11px; padding: 10px;"

    def update_theme(self, theme):
        self.update_style(theme)
        for btn in self.buttons.values():
            btn.update_style(theme)
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QLabel):
                if 'ОСНОВНОЕ' in widget.text() or 'НАСТРОЙКИ' in widget.text():
                    widget.setStyleSheet(self._get_section_label_style())
                elif 'v1.0' in widget.text():
                    widget.setStyleSheet(self._get_version_label_style())


