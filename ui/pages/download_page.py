import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QLineEdit, QGridLayout, QPushButton, QProgressBar, QDateEdit, QComboBox
from PySide6.QtGui import QFont
from ui.styles import STYLES

class DownloadPage(QWidget):
    """Страница загрузки контента"""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Загрузка контента из ВКонтакте")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; padding: 10px 0; color: {text_color};")
        self.header_label = header
        layout.addWidget(header)

        form_frame = QFrame()
        form_frame.setStyleSheet(self.styles['frame'])
        form_layout = QGridLayout(form_frame)
        form_layout.setSpacing(15)

        form_layout.addWidget(QLabel("Токен доступа:"), 0, 0)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте токен из vkhost.github.io")
        self.token_input.setStyleSheet(self.styles['input'])
        form_layout.addWidget(self.token_input, 0, 1)

        form_layout.addWidget(QLabel("Ссылка на сообщество:"), 1, 0)
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("https://vk.com/public123456 или https://vk.com/durov")
        self.group_input.setStyleSheet(self.styles['input'])
        form_layout.addWidget(self.group_input, 1, 1)

        # Период загрузки
        form_layout.addWidget(QLabel("Период загрузки:"), 2, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"
        ])
        self.period_combo.setCurrentText("Все время")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles['input'])
        form_layout.addWidget(self.period_combo, 2, 1)

        # ДАТЫ (в том же стиле!)
        form_layout.addWidget(QLabel("Дата начала:"), 3, 0)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(datetime.datetime.now() - datetime.timedelta(days=7))
        self.date_start.setStyleSheet(self.styles['input'])
        self.date_start.setMinimumHeight(40)
        self.date_start.setEnabled(False)
        form_layout.addWidget(self.date_start, 3, 1)

        form_layout.addWidget(QLabel("Дата окончания:"), 4, 0)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(datetime.datetime.now())
        self.date_end.setStyleSheet(self.styles['input'])
        self.date_end.setMinimumHeight(40)
        self.date_end.setEnabled(False)
        form_layout.addWidget(self.date_end, 4, 1)

        layout.addWidget(form_frame)

        self.download_btn = QPushButton("Начать загрузку")
        self.download_btn.setStyleSheet(self.styles['button'])
        self.download_btn.setMinimumHeight(50)
        self.download_btn.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.download_btn)

        self.progress_frame = QFrame()
        self.progress_frame.setStyleSheet(self.styles['frame'])
        progress_layout = QVBoxLayout(self.progress_frame)

        self.progress_label = QLabel("Прогресс:")
        self.progress_label.setStyleSheet(self.styles['label'])
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setStyleSheet(self.styles['progressbar'])
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_frame)
        layout.addStretch()

    def on_period_changed(self, value):
        """Активирует/деактивирует поля дат в зависимости от выбранного периода"""
        custom = value == "Свой диапазон"
        self.date_start.setEnabled(custom)
        self.date_end.setEnabled(custom)

    def get_date_range(self):
        """Возвращает диапазон дат в зависимости от выбранного периода"""
        period = self.period_combo.currentText()
        now = datetime.datetime.now()

        if period == "Свой диапазон":
            start = self.date_start.date().toPython()
            end = self.date_end.date().toPython() + datetime.timedelta(days=1)
            return start, end
        elif period == "Час":
            return now - datetime.timedelta(hours=1), now
        elif period == "День":
            return now - datetime.timedelta(days=1), now
        elif period == "Неделя":
            return now - datetime.timedelta(days=7), now
        elif period == "Месяц":
            return now - datetime.timedelta(days=30), now
        elif period == "Год":
            return now - datetime.timedelta(days=365), now
        else:  # "Все время"
            return datetime.datetime(2000, 1, 1), now

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"font-size: 22px; font-weight: bold; padding: 10px 0; color: {text_color};")
        self.setStyleSheet(f"background-color: {bg_color};")


