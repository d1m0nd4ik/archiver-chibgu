import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox,
    QDateEdit, QPushButton, QTextEdit, QMessageBox,
)
from ui.styles import STYLES, apply_theme_to_page, get_page_header_style
from ui.form_layout import FormGrid
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
from core.database import Database
from core.period_calculator import PeriodCalculator
from core.logging_config import logger


class TeachersPage(QWidget):
    """Список преподавателей и экспорт их постов в Word."""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.analyzer = StatisticsAnalyzer()
        self.exporter = StatisticsExporter()
        self.period_calc = PeriodCalculator()
        self._form_labels: list[QLabel] = []
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Преподаватели в постах")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        self._controls_layout = QGridLayout(controls_frame)
        controls_layout = self._controls_layout
        FormGrid.setup_quad_column(controls_layout)

        period_lbl = FormGrid.make_label("Период:")
        self._form_labels.append(period_lbl)
        controls_layout.addWidget(period_lbl, 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"])
        self.period_combo.setCurrentText("Все время")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles.get('combo', self.styles['input']))
        controls_layout.addWidget(self.period_combo, 0, 1)

        dfrom_lbl = FormGrid.make_label("Дата от:")
        self._form_labels.append(dfrom_lbl)
        controls_layout.addWidget(dfrom_lbl, 1, 0)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30))
        self.custom_start.setEnabled(False)
        self.custom_start.setStyleSheet(self.styles.get('date', self.styles['input']))
        controls_layout.addWidget(self.custom_start, 1, 1)

        dto_lbl = FormGrid.make_label("Дата до:")
        self._form_labels.append(dto_lbl)
        controls_layout.addWidget(dto_lbl, 1, 2)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        self.custom_end.setStyleSheet(self.styles.get('date', self.styles['input']))
        controls_layout.addWidget(self.custom_end, 1, 3)

        for w in (self.period_combo, self.custom_start, self.custom_end):
            FormGrid.fix_field(w)
        FormGrid.sync_grid(controls_layout, labels=self._form_labels)

        self.refresh_btn = QPushButton("Обновить список")
        self.refresh_btn.setStyleSheet(self.styles['button'])
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        controls_layout.addWidget(self.refresh_btn, 2, 0, 1, 2)

        self.export_word_btn = QPushButton("Экспорт в Word")
        self.export_word_btn.setStyleSheet(self.styles['button_secondary'])
        self.export_word_btn.clicked.connect(self.export_word)
        controls_layout.addWidget(self.export_word_btn, 2, 2, 1, 2)

        layout.addWidget(controls_frame)

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

        self._primary_buttons = [self.refresh_btn]
        self._secondary_buttons = [self.export_word_btn]

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        for w in (self.period_combo, self.custom_start, self.custom_end):
            FormGrid.fix_field(w)
        if hasattr(self, '_controls_layout'):
            FormGrid.sync_grid(self._controls_layout, labels=self._form_labels)
        self.refresh_statistics()

    def on_period_changed(self, value):
        custom = value == "Свой диапазон"
        self.custom_start.setEnabled(custom)
        self.custom_end.setEnabled(custom)

    def get_period_selection(self):
        mapping = {
            "Час": "hour", "День": "day", "Неделя": "week", "Месяц": "month",
            "Год": "year", "Все время": "all_time", "Свой диапазон": "custom",
        }
        return mapping.get(self.period_combo.currentText(), "day")

    def get_date_range(self):
        period = self.get_period_selection()
        if period == "custom":
            start = self.custom_start.date().toPython()
            end = self.custom_end.date().toPython() + datetime.timedelta(days=1)
            return start, end
        return self.analyzer.period_calc.get_period_range(period)

    def get_period_strings(self):
        start_date, end_date = self.get_date_range()
        start_str = self.period_calc.format_date(start_date)
        end_str = self.period_calc.format_date(end_date)
        period_key = self.get_period_selection()
        label = self.period_calc.get_period_label(period_key, start_date, end_date)
        return start_str, end_str, label

    def refresh_statistics(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()

            employees = self.analyzer.get_top_employees(
                period_key, start_date, end_date,
                metric='post_count',
                limit=None,
            ) or []

            self.teachers_text.setPlainText(self.format_teachers(employees))

        except Exception as e:
            logger.error(f"Teachers load error: {e}", exc_info=True)
            self.teachers_text.setPlainText(f"Ошибка загрузки: {e}")

    def format_teachers(self, employees):
        if not employees:
            return "За выбранный период нет данных по преподавателям."

        lines = []
        for idx, item in enumerate(employees, start=1):
            name = item.get('employee', 'Неизвестно')
            count = item.get('post_count', 0)
            lines.append(f"{idx}. {name} | Постов: {count}")
            lines.append("")
        return "\n".join(lines)

    def export_word(self):
        try:
            start_str, end_str, period_label = self.get_period_strings()
            db = Database()
            rows = db.get_posts_for_teachers_export(start_str, end_str)
            db.close()

            for row in rows:
                row['author_name'] = self.analyzer._resolve_author_fio(
                    row.get('author_name', ''),
                    row.get('teacher_hashtag', ''),
                    row.get('teacher_hashtag', ''),
                )

            filepath = self.exporter.export_teachers_posts_to_word(
                rows, period_label=f'Период: {period_label}',
            )
            if filepath:
                QMessageBox.information(
                    self, "Экспорт завершен",
                    f"Документ Word сохранён:\n{filepath}\n\n"
                    f"Преподавателей: {len({self.exporter._format_teacher_name(r) for r in rows})}\n"
                    f"Постов в таблице: {len(rows)}",
                )
            else:
                QMessageBox.warning(
                    self, "Ошибка экспорта",
                    "Не удалось сохранить Word.\nУстановите пакет: pip install python-docx",
                )
        except Exception as e:
            logger.error("Teachers Word export error: %s", e, exc_info=True)
            QMessageBox.warning(self, "Ошибка экспорта", f"Не удалось экспортировать:\n{e}")
