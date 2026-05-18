import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox, 
    QDateEdit, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt
from ui.styles import STYLES, apply_theme_to_page
from core.statistics_analyzer import StatisticsAnalyzer
from core.employee_tagger import ensure_employees_loaded
from core.logging_config import logger

class TeachersPage(QWidget):
    """Страница со списком преподавателей (только ФИО и количество постов)"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.analyzer = StatisticsAnalyzer()
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Преподаватели и сотрудники")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        # --- Панель управления ---
        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setSpacing(16)

        controls_layout.addWidget(QLabel("Период: "), 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"])
        self.period_combo.setCurrentText("Все время")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles.get('combo', self.styles['input']))
        controls_layout.addWidget(self.period_combo, 0, 1)

        controls_layout.addWidget(QLabel("Дата от: "), 1, 0)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30))
        self.custom_start.setEnabled(False)
        self.custom_start.setStyleSheet(self.styles.get('date', self.styles['input']))
        controls_layout.addWidget(self.custom_start, 1, 1)

        controls_layout.addWidget(QLabel("Дата до: "), 1, 2)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        self.custom_end.setStyleSheet(self.styles.get('date', self.styles['input']))
        controls_layout.addWidget(self.custom_end, 1, 3)

        self.refresh_btn = QPushButton("Обновить список")
        self.refresh_btn.setStyleSheet(self.styles['button'])
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        controls_layout.addWidget(self.refresh_btn, 2, 0, 1, 4)

        layout.addWidget(controls_frame)

        # --- Результат ---
        self.teachers_text = QTextEdit()
        self.teachers_text.setReadOnly(True)
        self.teachers_text.setStyleSheet(self.styles['textedit'])
        self.teachers_text.setMinimumHeight(240)

        info_frame = QFrame()
        info_frame.setStyleSheet(self.styles['frame'])
        info_layout = QVBoxLayout(info_frame)
        info_layout.addWidget(QLabel("Список преподавателей"))
        info_layout.addWidget(self.teachers_text)

        layout.addWidget(info_frame)
        layout.addStretch()

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)

    def on_period_changed(self, value):
        custom = value == "Свой диапазон"
        self.custom_start.setEnabled(custom)
        self.custom_end.setEnabled(custom)

    def get_period_selection(self):
        mapping = {"Час": "hour", "День": "day", "Неделя": "week", "Месяц": "month", "Год": "year", "Все время": "all_time", "Свой диапазон": "custom"}
        return mapping.get(self.period_combo.currentText(), "day")

    def get_date_range(self):
        period = self.get_period_selection()
        if period == "custom":
            start = self.custom_start.date().toPython()
            end = self.custom_end.date().toPython() + datetime.timedelta(days=1)
            return start, end
        return self.analyzer.period_calc.get_period_range(period)

    def refresh_statistics(self):
        try:
            ensure_employees_loaded(self.analyzer.db)

            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()

            # Получаем всех преподавателей из БД (без фильтрации)
            employees = self.analyzer.get_top_employees(
                period_key, start_date, end_date, 
                metric='post_count', 
                limit=None
            ) or []

            self.teachers_text.setPlainText(self.format_teachers(employees))

        except Exception as e:
            logger.error(f"Teachers load error: {e}", exc_info=True)
            self.teachers_text.setPlainText(f"Ошибка загрузки: {e}")

    def format_teachers(self, employees):
        """Форматирование: ТОЛЬКО ФИО и количество постов"""
        if not employees:
            return "За выбранный период нет данных по преподавателям."
        
        lines = []
        for idx, item in enumerate(employees, start=1):
            name = item.get('employee', 'Неизвестно')
            count = item.get('post_count', 0)
            
            lines.append(f"{idx}. {name} | Постов: {count}")
            lines.append(" ")
        return "\n".join(lines)