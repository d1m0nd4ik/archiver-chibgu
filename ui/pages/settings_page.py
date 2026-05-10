from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from core.config_manager import save_env_settings
from ui.styles import STYLES

class SettingsPage(QWidget):
    """Страница настроек"""

    def __init__(self, current_theme='system', styles=None):
        super().__init__()
        self.current_theme = current_theme
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Настройки приложения")
        header.setStyleSheet(self._get_header_style())
        self.header_label = header
        layout.addWidget(header)

        settings_frame = QFrame()
        settings_frame.setStyleSheet(self.styles['frame'])
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setSpacing(20)

        # ТЕМА ПРИЛОЖЕНИЯ
        theme_section = QFrame()
        theme_section.setStyleSheet("background-color: transparent;")
        theme_layout = QGridLayout(theme_section)
        theme_layout.setSpacing(15)

        theme_label = QLabel("🎨 Тема оформления:")
        theme_label.setStyleSheet(self._get_label_style())
        theme_layout.addWidget(theme_label, 0, 0)

        # Кнопка переключения темы (вместо ComboBox)
        self.theme_toggle_btn = QPushButton("Тёмная тема")
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setMinimumHeight(45)
        self.theme_toggle_btn.clicked.connect(self.on_theme_toggle)
        self._update_theme_button_style()
        theme_layout.addWidget(self.theme_toggle_btn, 0, 1)

        self.theme_info_label = QLabel(f"→ Сейчас: {'Светлая' if self.current_theme == 'light' else 'Тёмная'} тема")
        self.theme_info_label.setStyleSheet(self._get_info_style())
        theme_layout.addWidget(self.theme_info_label, 1, 0, 1, 2)

        settings_layout.addWidget(theme_section)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #555555;" if STYLES._theme == 'dark' else "background-color: #cccccc;")
        settings_layout.addWidget(line)

        settings_layout.addStretch()

        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.setStyleSheet(self.styles['button'])
        self.save_btn.setMinimumHeight(50)
        self.save_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_btn.clicked.connect(self.on_save_clicked)
        settings_layout.addWidget(self.save_btn)

        layout.addWidget(settings_frame)

    def _get_header_style(self):
        if STYLES._theme == 'light':
            return "color: #000000; font-size: 22px; font-weight: bold; padding: 10px 0;"
        else:
            return "color: #ffffff; font-size: 22px; font-weight: bold; padding: 10px 0;"

    def _get_label_style(self):
        if STYLES._theme == 'light':
            return "color: #000000; font-size: 14px; font-weight: 600;"
        else:
            return "color: #ffffff; font-size: 14px; font-weight: 600;"

    def _get_info_style(self):
        if STYLES._theme == 'light':
            return "color: #666666; font-size: 13px; font-style: italic;"
        else:
            return "color: #aaaaaa; font-size: 13px; font-style: italic;"

    def _update_theme_button_style(self):
        if STYLES._theme == 'light':
            self.theme_toggle_btn.setText("Светлая тема")
            self.theme_toggle_btn.setChecked(True)
            self.theme_toggle_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    background-color: #ffd700;
                    color: #000000;
                    border: 2px solid #ffa500;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #ffed4e;
                    border: 2px solid #ff8c00;
                }
            """)
        else:
            self.theme_toggle_btn.setText("Тёмная тема")
            self.theme_toggle_btn.setChecked(False)
            self.theme_toggle_btn.setStyleSheet("""
                QPushButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 2px solid #555555;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 2px solid #777777;
                }
            """)

    def on_theme_toggle(self):
        new_theme = 'light' if STYLES._theme == 'dark' else 'dark'
        STYLES.set_theme(new_theme)
        
        # Динамическое применение ко всему приложению
        from ui.styles import apply_theme_dynamic
        app = QApplication.instance()
        apply_theme_dynamic(app, new_theme)
        
        self._update_theme_button_style()
        self.theme_info_label.setText(f"→ Сейчас: {'Светлая' if new_theme == 'light' else 'Тёмная'} тема")

    def on_save_clicked(self):
        """Сохранение настроек"""
        theme = 'light' if STYLES._theme == 'light' else 'dark'

        save_env_settings(theme=theme)

        QMessageBox.information(
            self,
            "Настройки сохранены",
            f"Тема: {'Светлая' if theme == 'light' else 'Тёмная'}\n\n"
            "Изменения темы применятся после перезапуска приложения!"
        )

    def get_theme(self):
        return STYLES._theme

    def update_styles(self, styles):
        self.styles = styles
        self.header_label.setStyleSheet(self._get_header_style())
        self.theme_info_label.setStyleSheet(self._get_info_style())
        self._update_theme_button_style()


