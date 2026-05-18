from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
from ui.styles import STYLES, apply_theme_to_page

class SearchPage(QWidget):
    """Страница поиска"""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Поиск в архиве")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст или #тег для поиска...")
        self.search_input.setStyleSheet(self.styles['input'])
        self.search_input.setMinimumHeight(45)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Найти")
        self.search_btn.setStyleSheet(self.styles['button'])
        self.search_btn.setMinimumWidth(120)
        search_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.setStyleSheet(self.styles['button_secondary'])
        self.clear_btn.setMinimumWidth(120)
        search_layout.addWidget(self.clear_btn)

        layout.addLayout(search_layout)

        results_label = QLabel("Результаты поиска:")
        results_label.setStyleSheet(self.styles['label_title'])
        self.results_label = results_label
        layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(self.styles['textedit'])
        layout.addWidget(self.results_text)

        self._secondary_buttons = [self.clear_btn]

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)


