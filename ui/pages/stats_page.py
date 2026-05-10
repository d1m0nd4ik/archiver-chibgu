import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox, QDateEdit, QPushButton, QHBoxLayout, QTextEdit, QMessageBox
from PySide6.QtCore import Qt
from ui.styles import STYLES
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter

class StatsPage(QWidget):
    """Страница статистики"""

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.analyzer = StatisticsAnalyzer()
        self.exporter = StatisticsExporter()
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Статистика архива")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setSpacing(16)

        controls_layout.addWidget(QLabel("Период:"), 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems([
            "Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"
        ])
        self.period_combo.setCurrentText("День")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.period_combo, 0, 1)

        controls_layout.addWidget(QLabel("Метрика:"), 0, 2)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Лайки", "Комментарии", "Репосты", "Просмотры"])
        self.metric_combo.setCurrentText("Просмотры")
        self.metric_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.metric_combo, 0, 3)

        controls_layout.addWidget(QLabel("Дата от:"), 1, 0)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30))
        self.custom_start.setEnabled(False)
        self.custom_start.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_start, 1, 1)

        controls_layout.addWidget(QLabel("Дата до:"), 1, 2)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        self.custom_end.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_end, 1, 3)

        self.refresh_btn = QPushButton("Обновить статистику")
        self.refresh_btn.setStyleSheet(self.styles['button'])
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        controls_layout.addWidget(self.refresh_btn, 2, 0, 1, 2)

        self.export_csv_btn = QPushButton("Экспорт CSV")
        self.export_csv_btn.setStyleSheet(self.styles['button_secondary'])
        self.export_csv_btn.clicked.connect(self.export_csv)
        controls_layout.addWidget(self.export_csv_btn, 2, 2, 1, 2)

        self.export_excel_btn = QPushButton("Экспорт Excel")
        self.export_excel_btn.setStyleSheet(self.styles['button_secondary'])
        self.export_excel_btn.clicked.connect(self.export_excel)
        controls_layout.addWidget(self.export_excel_btn, 2, 4, 1, 2)

        layout.addWidget(controls_frame)

        self.top_posts_text = QTextEdit()
        self.top_posts_text.setReadOnly(True)
        self.top_posts_text.setStyleSheet(self.styles['textedit'])
        self.top_posts_text.setMinimumHeight(240)

        self.top_employees_text = QTextEdit()
        self.top_employees_text.setReadOnly(True)
        self.top_employees_text.setStyleSheet(self.styles['textedit'])
        self.top_employees_text.setMinimumHeight(240)

        results_layout = QHBoxLayout()
        posts_frame = QFrame()
        posts_frame.setStyleSheet(self.styles['frame'])
        posts_layout = QVBoxLayout(posts_frame)
        posts_layout.addWidget(QLabel("Топ постов"))
        posts_layout.addWidget(self.top_posts_text)

        employees_frame = QFrame()
        employees_frame.setStyleSheet(self.styles['frame'])
        employees_layout = QVBoxLayout(employees_frame)
        employees_layout.addWidget(QLabel("Топ преподавателей"))
        employees_layout.addWidget(self.top_employees_text)

        results_layout.addWidget(posts_frame)
        results_layout.addWidget(employees_frame)

        layout.addLayout(results_layout)
        layout.addStretch()

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0; ")
        self.setStyleSheet(f"background-color: {bg_color}; ")
        self.top_posts_text.setStyleSheet(self.styles['textedit'])
        self.top_employees_text.setStyleSheet(self.styles['textedit'])

    def on_period_changed(self, value):
        custom = value == "Свой диапазон"
        self.custom_start.setEnabled(custom)
        self.custom_end.setEnabled(custom)

    def get_period_selection(self):
        mapping = {
            "Час": "hour",
            "День": "day",
            "Неделя": "week",
            "Месяц": "month",
            "Год": "year",
            "Все время": "all_time",
            "Свой диапазон": "custom"
        }
        return mapping.get(self.period_combo.currentText(), "day")

    def get_date_range(self):
        period = self.get_period_selection()
        if period == "custom":
            start = self.custom_start.date().toPython()
            end = self.custom_end.date().toPython() + datetime.timedelta(days=1)
            return start, end
        return self.analyzer.period_calc.get_period_range(period)

    def _metric_display_to_key(self, display_name):
        mapping = {
            'Лайки': 'likes',
            'Комментарии': 'comments',
            'Репосты': 'shares',
            'Просмотры': 'views'
        }
        return mapping.get(display_name, 'views')

    def _translate_metric(self, metric_key):
        mapping = {
            'likes': 'Лайки',
            'comments': 'Комментарии',
            'shares': 'Репосты',
            'views': 'Просмотры'
        }
        return mapping.get(metric_key, metric_key)

    def refresh_statistics(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric_key = self._metric_display_to_key(self.metric_combo.currentText())

            summary = self.analyzer.get_statistics_summary(period_key, start_date, end_date)

            self.status_message = (
                f"Период: {summary.get('period')} | "
                f"Постов: {summary.get('total_posts')} | "
                f"Просмотров: {summary.get('total_views')} | "
                f"Лайков: {summary.get('total_likes')}"
            )

            top_posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric_key, limit=10)

            employees = self.analyzer.get_top_employees(period_key, start_date, end_date, metric='mention_count', 
                                                       employees_list=self.analyzer.load_employee_list(), limit=10)

            self.top_posts_text.setPlainText(self.format_posts(top_posts))
            self.top_employees_text.setPlainText(self.format_employees(employees))

        except Exception as e:
            self.top_posts_text.setPlainText(f"Ошибка загрузки статистики: {e}")
            self.top_employees_text.clear()

    def format_posts(self, posts):
        if not posts:
            return "Нет данных за выбранный период."
        lines = []
        for idx, post in enumerate(posts, start=1):
            lines.append(f"{idx}. ID поста {post.get('post_id')} | {post.get('date')}")
            lines.append(f"   Лайки: {post.get('likes')}  Комментарии: {post.get('comments')}  "
                         f"Репосты: {post.get('shares')}  Просмотры: {post.get('views')}")
            lines.append(f"   Текст: {post.get('text')}")
            lines.append("")
        return "\n".join(lines)

    def format_employees(self, employees):
        if not employees:
            return "Нет данных по преподавателям."
        lines = []
        for idx, item in enumerate(employees, start=1):
            # Нормализуем имя преподавателя
            employee_name = self.analyzer.normalize_employee_name_for_display(item.get('employee'))
            lines.append(f"{idx}. {employee_name} | Упоминаний: {item.get('mention_count')}  "
                         f"Постов: {item.get('post_count')}")
            lines.append(f"   Лайков: {item.get('total_likes')}  Просмотров: {item.get('total_views')}")
            lines.append("")
        return "\n".join(lines)

    def export_csv(self):
        period_key = self.get_period_selection()
        start_date, end_date = self.get_date_range()
        metric = self.metric_combo.currentText()
        posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric, limit=50)
        filepath = self.exporter.export_posts_to_csv(posts)
        QMessageBox.information(self, "Экспорт завершен", f"CSV файл сохранен: {filepath}")

    def export_excel(self):
        period_key = self.get_period_selection()
        start_date, end_date = self.get_date_range()
        metric = self.metric_combo.currentText()
        posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric, limit=50)
        filepath = self.exporter.export_posts_to_excel(posts)
        QMessageBox.information(self, "Экспорт завершен", f"Excel файл сохранен: {filepath}")

