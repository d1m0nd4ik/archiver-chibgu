from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel
from ui.styles import STYLES

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

        name_label = QLabel("VK Media Archiver Pro")
        name_label.setStyleSheet(f"color: {text_color}; font-size: 24px; font-weight: bold;")
        info_layout.addWidget(name_label)

        version_label = QLabel("Версия: 1.0.0")
        version_label.setStyleSheet("color: #888888; font-size: 14px;")
        info_layout.addWidget(version_label)

        desc_label = QLabel("""
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
        desc_label.setStyleSheet(f"color: {desc_color}; font-size: 13px; line-height: 1.6;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        info_layout.addStretch()

        layout.addWidget(info_frame)
        layout.addStretch()

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg_color};")

