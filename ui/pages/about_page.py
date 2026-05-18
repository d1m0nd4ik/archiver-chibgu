from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel
from ui.styles import STYLES, apply_theme_to_page, get_theme_colors

class AboutPage(QWidget):
    """Страница о программе"""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("О программе")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        info_frame = QFrame()
        info_frame.setStyleSheet(self.styles['frame'])
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(15)

        self.name_label = QLabel("VK Media Archiver Pro")
        self.name_label.setStyleSheet(f"color: {text_color}; font-size: 24px; font-weight: bold;")
        info_layout.addWidget(self.name_label)

        self.version_label = QLabel("Версия: 1.0.0")
        self.version_label.setStyleSheet("color: #888888; font-size: 14px;")
        info_layout.addWidget(self.version_label)

        self.desc_label = QLabel("""
            Профессиональное приложение для автоматического скачивания,
            оптимизации и индексации контента из ВКонтакте.

            Возможности:
            • Загрузка фото и видео из групп
            • Конвертация фото в WebP
            • Обработка видео с улучшением качества
            • Авто-тегирование контента
            • Быстрый поиск по архиву
        """)
        desc_color = '#666666' if STYLES._theme == 'light' else '#d4d4d4'
        self.desc_label.setStyleSheet(f"color: {desc_color}; font-size: 13px; line-height: 1.6;")
        self.desc_label.setWordWrap(True)
        info_layout.addWidget(self.desc_label)
        info_layout.addStretch()

        layout.addWidget(info_frame)
        layout.addStretch()

        self._theme_custom_labels = [self.name_label, self.version_label, self.desc_label]

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        c = get_theme_colors()
        self.name_label.setStyleSheet(
            f"color: {c['text']}; font-size: 24px; font-weight: bold;"
        )
        self.version_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 14px;")
        self.desc_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 13px; line-height: 1.6;"
        )

