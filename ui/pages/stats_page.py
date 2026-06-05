import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox, 
    QDateEdit, QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtWidgets import QSpinBox
from PySide6.QtCore import Qt
import html
import os
from ui.styles import (
    STYLES, apply_theme_to_page, get_page_header_style, get_theme_colors,
    get_compact_combo_stylesheet, get_compact_date_stylesheet, get_spinbox_stylesheet,
)
from ui.form_layout import FormGrid
from ui.button_effects import mark_compact_toolbar_button
from ui.styles import get_compact_button_stylesheet
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
from core.logging_config import logger

class StatsPage(QWidget):
    """Страница статистики постов"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.analyzer = StatisticsAnalyzer()
        self.exporter = StatisticsExporter()
        self._form_labels: list[QLabel] = []
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Заголовок
        header = QLabel("Статистика постов")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        # Панель управления
        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        self._controls_layout = QGridLayout(controls_frame)
        controls_layout = self._controls_layout
        FormGrid.setup_multi_field_grid(controls_layout)

        period_lbl = FormGrid.make_label("Период:")
        self._form_labels.append(period_lbl)
        controls_layout.addWidget(period_lbl, 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"])
        self.period_combo.setCurrentText("День")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        controls_layout.addWidget(self.period_combo, 0, 1)

        metric_lbl = FormGrid.make_label("Метрика:")
        self._form_labels.append(metric_lbl)
        controls_layout.addWidget(metric_lbl, 0, 2)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Лайки", "Комментарии", "Репосты", "Популярность"])
        self.metric_combo.setCurrentText("Лайки")
        controls_layout.addWidget(self.metric_combo, 0, 3)

        top_lbl = FormGrid.make_label("Показывать топ:")
        self._form_labels.append(top_lbl)
        controls_layout.addWidget(top_lbl, 0, 4)
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 200)
        self.top_n_spin.setValue(10)
        controls_layout.addWidget(self.top_n_spin, 0, 5)

        dfrom_lbl = FormGrid.make_label("Дата от:")
        self._form_labels.append(dfrom_lbl)
        controls_layout.addWidget(dfrom_lbl, 1, 0)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30))
        self.custom_start.setEnabled(False)
        controls_layout.addWidget(self.custom_start, 1, 1)

        dto_lbl = FormGrid.make_label("Дата до:")
        self._form_labels.append(dto_lbl)
        controls_layout.addWidget(dto_lbl, 1, 2)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        controls_layout.addWidget(self.custom_end, 1, 3)

        self._compact_form_widgets = [
            self.period_combo, self.metric_combo, self.top_n_spin,
            self.custom_start, self.custom_end,
        ]
        self._apply_field_styles()
        for w in self._compact_form_widgets:
            FormGrid.fix_field(w)
        FormGrid.sync_grid(controls_layout, labels=self._form_labels)

        self.refresh_btn = QPushButton("Обновить статистику")
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        controls_layout.addWidget(self.refresh_btn, 2, 0, 1, 2)

        self.export_csv_btn = QPushButton("Экспорт CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        controls_layout.addWidget(self.export_csv_btn, 2, 2, 1, 2)

        self.export_excel_btn = QPushButton("Экспорт Excel")
        self.export_excel_btn.clicked.connect(self.export_excel)
        controls_layout.addWidget(self.export_excel_btn, 2, 4, 1, 2)

        layout.addWidget(controls_frame)

        # Блок результатов (только посты)
        self.top_posts_text = QTextEdit()
        self.top_posts_text.setReadOnly(True)
        self.top_posts_text.setStyleSheet(self.styles['textedit'])
        # уменьшим высоту, чтобы окно не было чрезмерно большим
        self.top_posts_text.setMinimumHeight(300)

        results_frame = QFrame()
        results_frame.setStyleSheet(self.styles['frame'])
        results_layout = QVBoxLayout(results_frame)
        results_layout.addWidget(QLabel("Топ постов"))
        results_layout.addWidget(self.top_posts_text)

        layout.addWidget(results_frame)
        layout.addStretch()

        self._primary_buttons = [self.refresh_btn]
        self._secondary_buttons = [self.export_csv_btn, self.export_excel_btn]
        self._apply_button_styles()

    def _apply_button_styles(self):
        theme = getattr(STYLES, '_theme', None)
        self._compact_toolbar_buttons = [
            self.refresh_btn, self.export_csv_btn, self.export_excel_btn,
        ]
        mark_compact_toolbar_button(self.refresh_btn, primary=True)
        self.refresh_btn.setStyleSheet(get_compact_button_stylesheet(True, theme))
        for btn in (self.export_csv_btn, self.export_excel_btn):
            mark_compact_toolbar_button(btn, primary=False)
            btn.setStyleSheet(get_compact_button_stylesheet(False, theme))

    def _apply_field_styles(self):
        theme = getattr(STYLES, '_theme', None)
        combo_style = get_compact_combo_stylesheet(theme)
        date_style = get_compact_date_stylesheet(theme)
        spin_style = get_spinbox_stylesheet(theme, compact=True)
        for w in (self.period_combo, self.metric_combo):
            w.setStyleSheet(combo_style)
        from ui.date_field_effects import refresh_date_field

        for w in (self.custom_start, self.custom_end):
            w.setStyleSheet(date_style)
            FormGrid.fix_field(w)
            refresh_date_field(w)
        self.top_n_spin.setStyleSheet(spin_style)

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)

    def on_period_changed(self, value):
        """Активирует/деактивирует поля кастомных дат"""
        custom = value == "Свой диапазон"
        self.custom_start.setEnabled(custom)
        self.custom_end.setEnabled(custom)

    def get_period_selection(self):
        mapping = {
            "Час": "hour", "День": "day", "Неделя": "week", 
            "Месяц": "month", "Год": "year", "Все время": "all_time", 
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
        mapping = {'Лайки': 'likes', 'Комментарии': 'comments', 'Репосты': 'shares', 'Популярность': 'popularity'}
        return mapping.get(display_name, 'likes')

    def refresh_statistics(self):
        """Безопасное обновление данных с обработкой ошибок"""
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric_key = self._metric_display_to_key(self.metric_combo.currentText())

            summary = self.analyzer.get_statistics_summary(period_key, start_date, end_date)

            self.status_message = (
                f"Период: {summary.get('period')} |  "
                f"Постов: {summary.get('total_posts')} |  "
                f"Лайков: {summary.get('total_likes')} |  "
                f"Репостов: {summary.get('total_shares')}"
            )

            top_posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric_key, limit=self.top_n_spin.value()) or []

            # Use HTML so we can include thumbnails and larger text
            self.top_posts_text.setHtml(self.format_posts(top_posts))

        except Exception as e:
            logger.error(f"Stats refresh error: {e}", exc_info=True)
            self.top_posts_text.setPlainText(f"❌ Ошибка загрузки статистики:\n{e}")

    def format_posts(self, posts):
        if not posts:
            return "<i>Нет данных за выбранный период.</i>"

        text_color = get_theme_colors()['text']
        parts = [f'<div style="font-family: sans-serif; color: {text_color};">']
        for idx, post in enumerate(posts, start=1):
            date = html.escape(str(post.get('date') or ''))
            likes = int(post.get('likes') or 0)
            comments = int(post.get('comments') or 0)
            shares = int(post.get('shares') or 0)
            popularity = int(post.get('popularity') or (likes + comments + shares))
            text = html.escape(str(post.get('text') or '')).replace('\n', ' ')

            parts.append(f'<div style="margin-bottom:6px; padding:4px 6px; border-bottom:1px solid rgba(255,255,255,0.04);">')
            parts.append(f'<b style="font-size:13px;">{idx}. {date}</b>')
            author_name = html.escape(str(post.get('author_name') or '—'))
            teacher_hashtag = html.escape(str(post.get('teacher_hashtag') or '—'))
            department_hashtag = html.escape(str(post.get('department_hashtag') or '—'))

            parts.append(f'<div style="margin-top:4px; color: #9aa0a6; font-size:12px;">')
            parts.append(
                f'Автор: <b>{author_name}</b> &nbsp;&nbsp; '
                f'Хэштег преподавателя: {teacher_hashtag} &nbsp;&nbsp; '
                f'Хэштег кафедры: {department_hashtag}'
            )
            parts.append('</div>')
            parts.append('<div style="margin-top:4px; color: #9aa0a6; font-size:12px;">')
            parts.append(f'Лайки: {likes} &nbsp;&nbsp; Комментарии: {comments} &nbsp;&nbsp; Репосты: {shares} &nbsp;&nbsp; <b>Популярность: {popularity}</b>')
            parts.append('</div>')

            parts.append(f'<div style="margin-top:6px; font-size:13px; line-height:1.25;">Текст: {text}</div>')

            # thumbnails (if any)
            media_paths = post.get('media_paths') or []
            if media_paths:
                parts.append('<div style="margin-top:8px; display:flex; gap:6px; align-items:center;">')
                for p in media_paths[:6]:
                    if not p:
                        continue
                    # convert to absolute file URL if path exists on disk
                    file_url = p
                    if os.path.exists(p):
                        file_url = 'file:///' + p.replace('\\', '/')
                    else:
                        # try to treat as already a url or path
                        file_url = p
                    parts.append(f'<img src="{html.escape(file_url)}" style="max-width:120px; max-height:90px; border-radius:4px; object-fit:cover;"/>')
                parts.append('</div>')

            parts.append('</div>')

        parts.append('</div>')
        return '\n'.join(parts)

    def export_csv(self):
        period_key = self.get_period_selection()
        start_date, end_date = self.get_date_range()
        metric_key = self._metric_display_to_key(self.metric_combo.currentText())
        posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric_key, limit=self.top_n_spin.value())
        filepath = self.exporter.export_posts_to_csv(posts)
        if filepath:
            QMessageBox.information(self, "Экспорт завершен", f"CSV файл сохранен:\n{filepath}")
        else:
            QMessageBox.warning(self, "Ошибка экспорта", "Не удалось сохранить CSV файл.")

    def export_excel(self):
        period_key = self.get_period_selection()
        start_date, end_date = self.get_date_range()
        metric_key = self._metric_display_to_key(self.metric_combo.currentText())
        posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric_key, limit=self.top_n_spin.value())
        filepath = self.exporter.export_posts_to_excel(posts)
        if filepath:
            QMessageBox.information(self, "Экспорт завершен", f"Excel файл сохранен:\n{filepath}")
        else:
            QMessageBox.warning(self, "Ошибка экспорта", "Не удалось сохранить Excel файл.")