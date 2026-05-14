import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QComboBox,
    QDateEdit, QPushButton, QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from ui.styles import STYLES
from core.database import Database
from core.period_calculator import PeriodCalculator
from core.statistics_exporter import StatisticsExporter
from core.logging_config import logger

class MediaStatsPage(QWidget):
    """Страница статистики медиа (стиль идентичен StatsPage)"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.db = Database()
        self.exporter = StatisticsExporter()
        self.period_calc = PeriodCalculator()
        self.init_ui()
        self.refresh_statistics()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Заголовок
        header = QLabel("📊 Статистика медиа")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.header_label = header
        layout.addWidget(header)

        # Панель управления
        controls_frame = QFrame()
        controls_frame.setStyleSheet(self.styles['frame'])
        controls_layout = QGridLayout(controls_frame)
        controls_layout.setSpacing(16)

        controls_layout.addWidget(QLabel("Период:"), 0, 0)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Час", "День", "Неделя", "Месяц", "Год", "Все время", "Свой диапазон"])
        self.period_combo.setCurrentText("День")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        self.period_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.period_combo, 0, 1)

        controls_layout.addWidget(QLabel("Тип медиа:"), 0, 2)
        self.media_type_combo = QComboBox()
        self.media_type_combo.addItems(["Все", "Фото", "Видео", "Клипы"])
        self.media_type_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.media_type_combo, 0, 3)

        controls_layout.addWidget(QLabel("Метрика:"), 1, 0)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Лайки", "Комментарии", "Репосты"])
        self.metric_combo.setCurrentText("Лайки")
        self.metric_combo.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.metric_combo, 1, 1)

        controls_layout.addWidget(QLabel("Дата от:"), 1, 2)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=7))
        self.custom_start.setEnabled(False)
        self.custom_start.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_start, 1, 3)

        controls_layout.addWidget(QLabel("Дата до:"), 2, 0)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        self.custom_end.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_end, 2, 1)

        self.refresh_btn = QPushButton("🔄 Обновить статистику")
        self.refresh_btn.setStyleSheet(self.styles['button'])
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        controls_layout.addWidget(self.refresh_btn, 2, 2, 1, 2)

        self.export_csv_btn = QPushButton("Экспорт CSV")
        self.export_csv_btn.setStyleSheet(self.styles['button_secondary'])
        self.export_csv_btn.clicked.connect(self.export_csv)
        controls_layout.addWidget(self.export_csv_btn, 3, 0, 1, 2)

        self.export_excel_btn = QPushButton("Экспорт Excel")
        self.export_excel_btn.setStyleSheet(self.styles['button_secondary'])
        self.export_excel_btn.clicked.connect(self.export_excel)
        controls_layout.addWidget(self.export_excel_btn, 3, 2, 1, 2)

        layout.addWidget(controls_frame)

        # Блок результатов
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(self.styles['textedit'])
        self.results_text.setMinimumHeight(300)

        results_frame = QFrame()
        results_frame.setStyleSheet(self.styles['frame'])
        results_layout = QVBoxLayout(results_frame)
        results_layout.addWidget(QLabel(" Топ медиафайлов"))
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_frame)
        layout.addStretch()

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'
        
        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg_color};")
        self.results_text.setStyleSheet(self.styles['textedit'])

    def on_period_changed(self, value):
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
        return self.period_calc.get_period_range(period)

    def _metric_display_to_key(self, display_name):
        mapping = {'Лайки': 'likes', 'Комментарии': 'comments', 'Репосты': 'shares'}
        return mapping.get(display_name, 'likes')

    def _media_type_display_to_key(self, display_name):
        mapping = {'Все': 'all', 'Фото': 'photo', 'Видео': 'video', 'Клипы': 'clip'}
        return mapping.get(display_name, 'all')

    def refresh_statistics(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric_key = self._metric_display_to_key(self.metric_combo.currentText())
            media_type_key = self._media_type_display_to_key(self.media_type_combo.currentText())

            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            summary = self.db.get_media_stats_summary(start_str, end_str, media_type_key)
            
            # Формируем строку статуса
            self.status_message = (
                f"Период: {start_str} - {end_str} | "
                f"Тип: {self.media_type_combo.currentText()} | "
                f"Медиа: {summary['total_media']} | "
                f"Лайков: {summary['total_likes']} | "
                f"Комментариев: {summary['total_comments']}"
            )

            top_media = self.db.get_media_statistics_by_period(
                start_str, end_str, media_type_key, metric_key, limit=20
            )

            self.results_text.setPlainText(self.format_media(top_media, metric_key))

        except Exception as e:
            logger.error(f"Media Stats refresh error: {e}", exc_info=True)
            self.results_text.setPlainText(f"❌ Ошибка загрузки статистики:\n{e}")

    def format_media(self, media_list, metric_key):
        if not media_list:
            return "Нет данных за выбранный период."
        
        lines = []
        lines.append(f" Показано топ-{len(media_list)} по метрике: {self.metric_combo.currentText()}\n")
        lines.append("=" * 70 + "\n")
        
        for idx, (post_id, media_key, media_type, likes, comments, shares, date) in enumerate(media_list, 1):
            type_emoji = {"photo": "📷", "video": "🎬", "clip": "🎥"}.get(media_type, "")
            lines.append(f"{idx}. {type_emoji} {media_key} (Пост #{post_id})")
            lines.append(f"   Тип: {media_type} | Дата: {date}")
            lines.append(f"   ❤️ Лайки: {likes} |  Комментарии: {comments} | 🔄 Репосты: {shares}")
            lines.append("")
            
        return "\n".join(lines)

    def export_csv(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric_key = self._metric_display_to_key(self.metric_combo.currentText())
            media_type_key = self._media_type_display_to_key(self.media_type_combo.currentText())
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            media_list = self.db.get_media_statistics_by_period(
                start_str, end_str, media_type_key, metric_key, limit=200
            )
            
            # Преобразуем в список словарей для экспортера
            export_data = []
            for post_id, media_key, media_type, likes, comments, shares, date in media_list:
                export_data.append({
                    'post_id': post_id,
                    'media_key': media_key,
                    'media_type': media_type,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'date': date
                })
            
            filepath = self.exporter.export_media_to_csv(export_data)
            if filepath:
                QMessageBox.information(self, "Экспорт завершен", f"CSV файл сохранен:\n{filepath}")
            else:
                QMessageBox.warning(self, "Ошибка экспорта", "Не удалось сохранить CSV файл.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать данные:\n{e}")

    def export_excel(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric_key = self._metric_display_to_key(self.metric_combo.currentText())
            media_type_key = self._media_type_display_to_key(self.media_type_combo.currentText())
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            media_list = self.db.get_media_statistics_by_period(
                start_str, end_str, media_type_key, metric_key, limit=200
            )
            
            export_data = []
            for post_id, media_key, media_type, likes, comments, shares, date in media_list:
                export_data.append({
                    'post_id': post_id,
                    'media_key': media_key,
                    'media_type': media_type,
                    'likes': likes,
                    'comments': comments,
                    'shares': shares,
                    'date': date
                })
            
            filepath = self.exporter.export_media_to_excel(export_data)
            if filepath:
                QMessageBox.information(self, "Экспорт завершен", f"Excel файл сохранен:\n{filepath}")
            else:
                QMessageBox.warning(self, "Ошибка экспорта", "Не удалось сохранить Excel файл.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать данные:\n{e}")