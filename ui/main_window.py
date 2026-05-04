from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QProgressBar, QStatusBar, QFrame, QMessageBox,
    QStackedWidget, QScrollArea, QSizePolicy, QApplication, QComboBox,
    QDialog, QSlider, QStackedLayout, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QFont, QPixmap, QGuiApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from .styles import STYLES, update_global_styles
from worker.download_worker import DownloadWorker
from core.database import Database
from core.config_manager import save_env_settings, get_system_theme
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
import os, datetime
import subprocess

class NavigationButton(QPushButton):
    """Кнопка навигации"""
    clicked_signal = Signal(str)

    def __init__(self, icon, text, page_name, theme='dark'):
        super().__init__()
        self.page_name = page_name
        self.setText(f"{icon} {text}")
        self.theme = theme
        self.update_style()
        self.setCheckable(True)
        self.clicked.connect(self.on_clicked)

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        if self.theme == 'light':
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #000000;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    padding: 12px 20px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border: 2px solid #999999;
                }
                QPushButton:checked {
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #d4d4d4;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    padding: 12px 20px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 2px solid #555555;
                }
                QPushButton:checked {
                    background-color: #3a7bd5;
                    color: white;
                    border: 2px solid #2c5aa0;
                }
            """)

    def on_clicked(self):
        self.clicked_signal.emit(self.page_name)


class HeaderWidget(QFrame):
    """Верхняя шапка приложения"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("HeaderWidget")
        self.setFixedHeight(70)
        self.update_style()
        self.init_ui()

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        if self.theme == 'light':
            self.setStyleSheet("""
                #HeaderWidget {
                    background-color: #ffffff;
                    border-bottom: 2px solid #3a7bd5;
                }
            """)
        else:
            self.setStyleSheet("""
                #HeaderWidget {
                    background-color: #1e1e1e;
                    border-bottom: 2px solid #3a7bd5;
                }
            """)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)

        title_layout = QHBoxLayout()
        logo_label = QLabel("🎬")
        logo_label.setStyleSheet("font-size: 32px;")

        title_label = QLabel("VK Media Archiver Pro")
        title_label.setStyleSheet(self._get_title_style())

        subtitle_label = QLabel("Профессиональный архиватор контента ВКонтакте")
        subtitle_label.setStyleSheet(self._get_subtitle_style())

        title_layout.addWidget(logo_label)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        layout.addStretch()

    def _get_title_style(self):
        if self.theme == 'light':
            return "color: #000000; font-size: 24px; font-weight: bold;"
        else:
            return "color: #ffffff; font-size: 24px; font-weight: bold;"

    def _get_subtitle_style(self):
        if self.theme == 'light':
            return "color: #888888; font-size: 12px;"
        else:
            return "color: #888888; font-size: 12px;"

    def update_theme(self, theme):
        self.update_style(theme)
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item and item.layout():
                for j in range(item.layout().count()):
                    widget = item.layout().itemAt(j).widget()
                    if isinstance(widget, QLabel):
                        if 'Pro' in widget.text():
                            widget.setStyleSheet(self._get_title_style())
                        elif 'Профессиональный' in widget.text():
                            widget.setStyleSheet(self._get_subtitle_style())


class SidebarWidget(QFrame):
    """Боковая панель навигации"""

    def __init__(self, theme='dark'):
        super().__init__()
        self.theme = theme
        self.setObjectName("SidebarWidget")
        self.setFixedWidth(280)
        self.update_style()
        self.init_ui()

    def update_style(self, theme=None):
        if theme:
            self.theme = theme

        if self.theme == 'light':
            self.setStyleSheet("""
                #SidebarWidget {
                    background-color: #f5f5f5;
                    border-right: 2px solid #dddddd;
                }
            """)
        else:
            self.setStyleSheet("""
                #SidebarWidget {
                    background-color: #252525;
                    border-right: 2px solid #333333;
                }
            """)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)

        main_label = QLabel("📋 ОСНОВНОЕ")
        main_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(main_label)

        self.buttons = {}
        self.buttons['download'] = NavigationButton("📥", "Загрузка контента", "download", self.theme)
        self.buttons['search'] = NavigationButton("🔍", "Поиск в архиве", "search", self.theme)
        self.buttons['stats'] = NavigationButton("📊", "Статистика", "stats", self.theme)
        self.buttons['storage'] = NavigationButton("📚", "Хранилище", "storage", self.theme)

        for btn in self.buttons.values():
            layout.addWidget(btn)

        layout.addSpacing(20)

        settings_label = QLabel("⚙️ НАСТРОЙКИ")
        settings_label.setStyleSheet(self._get_section_label_style())
        layout.addWidget(settings_label)

        self.buttons['settings'] = NavigationButton("🔧", "Настройки приложения", "settings", self.theme)
        self.buttons['about'] = NavigationButton("ℹ️", "О программе", "about", self.theme)

        for btn in self.buttons.values():
            if btn not in list(self.buttons.values())[:4]:
                layout.addWidget(btn)

        layout.addStretch()

        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet(self._get_version_label_style())
        layout.addWidget(version_label)

    def _get_section_label_style(self):
        return "color: #888888; font-size: 11px; font-weight: bold; padding: 10px 10px 5px 10px; text-transform: uppercase;"

    def _get_version_label_style(self):
        if self.theme == 'light':
            return "color: #999999; font-size: 11px; padding: 10px;"
        else:
            return "color: #555555; font-size: 11px; padding: 10px;"

    def update_theme(self, theme):
        self.update_style(theme)
        for btn in self.buttons.values():
            btn.update_style(theme)
        for i in range(self.layout().count()):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, QLabel):
                if 'ОСНОВНОЕ' in widget.text() or 'НАСТРОЙКИ' in widget.text():
                    widget.setStyleSheet(self._get_section_label_style())
                elif 'v1.0' in widget.text():
                    widget.setStyleSheet(self._get_version_label_style())


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

        header = QLabel("📥 Загрузка контента из ВКонтакте")
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        header.setStyleSheet(f"font-size: 22px; font-weight: bold; padding: 10px 0; color: {text_color};")
        self.header_label = header
        layout.addWidget(header)

        form_frame = QFrame()
        form_frame.setStyleSheet(self.styles['frame'])
        form_layout = QGridLayout(form_frame)
        form_layout.setSpacing(15)

        form_layout.addWidget(QLabel("🔑 Access Token:"), 0, 0)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте токен из vkhost.github.io")
        self.token_input.setStyleSheet(self.styles['input'])
        form_layout.addWidget(self.token_input, 0, 1)

        form_layout.addWidget(QLabel("🔗 Ссылка на сообщество:"), 1, 0)
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("https://vk.com/public123456 или https://vk.com/durov")
        self.group_input.setStyleSheet(self.styles['input'])
        form_layout.addWidget(self.group_input, 1, 1)

        # ДАТЫ (в том же стиле!)
        form_layout.addWidget(QLabel("📅 Дата начала:"), 2, 0)
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(datetime.datetime.now() - datetime.timedelta(days=7))
        self.date_start.setStyleSheet(self.styles['input'])
        self.date_start.setMinimumHeight(40)
        form_layout.addWidget(self.date_start, 2, 1)

        form_layout.addWidget(QLabel("📅 Дата окончания:"), 3, 0)
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(datetime.datetime.now())
        self.date_end.setStyleSheet(self.styles['input'])
        self.date_end.setMinimumHeight(40)
        form_layout.addWidget(self.date_end, 3, 1)

        layout.addWidget(form_frame)

        self.download_btn = QPushButton("🚀 Начать загрузку")
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

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"font-size: 22px; font-weight: bold; padding: 10px 0; color: {text_color};")
        self.setStyleSheet(f"background-color: {bg_color};")


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

        header = QLabel("🔍 Поиск в архиве")
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

        results_label = QLabel("📋 Результаты поиска:")
        results_label.setStyleSheet(self.styles['label_title'])
        self.results_label = results_label
        layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setStyleSheet(self.styles['textedit'])
        layout.addWidget(self.results_text)

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg_color};")


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

        header = QLabel("📊 Статистика архива")
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
            "Час", "Пол дня", "День", "Неделя", "Месяц", "Пол года", "Год", "Все время", "Свой диапазон"
        ])
        self.period_combo.setCurrentText("День")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        controls_layout.addWidget(self.period_combo, 0, 1)

        controls_layout.addWidget(QLabel("Метрика:"), 0, 2)
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["likes", "comments", "shares", "views", "engagement"])
        self.metric_combo.setCurrentText("views")
        controls_layout.addWidget(self.metric_combo, 0, 3)

        controls_layout.addWidget(QLabel("Тип медиа:"), 1, 0)
        self.media_combo = QComboBox()
        self.media_combo.addItems(["all", "photo", "video"])
        self.media_combo.setCurrentText("all")
        controls_layout.addWidget(self.media_combo, 1, 1)

        controls_layout.addWidget(QLabel("Дата от:"), 1, 2)
        self.custom_start = QDateEdit()
        self.custom_start.setCalendarPopup(True)
        self.custom_start.setDate(datetime.datetime.now() - datetime.timedelta(days=30))
        self.custom_start.setEnabled(False)
        self.custom_start.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_start, 1, 3)

        controls_layout.addWidget(QLabel("Дата до:"), 1, 4)
        self.custom_end = QDateEdit()
        self.custom_end.setCalendarPopup(True)
        self.custom_end.setDate(datetime.datetime.now())
        self.custom_end.setEnabled(False)
        self.custom_end.setStyleSheet(self.styles['input'])
        controls_layout.addWidget(self.custom_end, 1, 5)

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

        self.top_media_text = QTextEdit()
        self.top_media_text.setReadOnly(True)
        self.top_media_text.setStyleSheet(self.styles['textedit'])
        self.top_media_text.setMinimumHeight(240)

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

        media_frame = QFrame()
        media_frame.setStyleSheet(self.styles['frame'])
        media_layout = QVBoxLayout(media_frame)
        media_layout.addWidget(QLabel("Топ медиа"))
        media_layout.addWidget(self.top_media_text)

        employees_frame = QFrame()
        employees_frame.setStyleSheet(self.styles['frame'])
        employees_layout = QVBoxLayout(employees_frame)
        employees_layout.addWidget(QLabel("Топ преподавателей"))
        employees_layout.addWidget(self.top_employees_text)

        results_layout.addWidget(posts_frame)
        results_layout.addWidget(media_frame)
        results_layout.addWidget(employees_frame)

        layout.addLayout(results_layout)
        layout.addStretch()

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'

        self.header_label.setStyleSheet(f"color: {text_color}; font-size: 22px; font-weight: bold; padding: 10px 0;")
        self.setStyleSheet(f"background-color: {bg_color};")
        self.top_posts_text.setStyleSheet(self.styles['textedit'])
        self.top_media_text.setStyleSheet(self.styles['textedit'])
        self.top_employees_text.setStyleSheet(self.styles['textedit'])

    def on_period_changed(self, value):
        custom = value == "Свой диапазон"
        self.custom_start.setEnabled(custom)
        self.custom_end.setEnabled(custom)

    def get_period_selection(self):
        mapping = {
            "Час": "hour",
            "Пол дня": "half_day",
            "День": "day",
            "Неделя": "week",
            "Месяц": "month",
            "Пол года": "half_year",
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

    def refresh_statistics(self):
        try:
            period_key = self.get_period_selection()
            start_date, end_date = self.get_date_range()
            metric = self.metric_combo.currentText()
            media_type = self.media_combo.currentText()

            summary = self.analyzer.get_statistics_summary(period_key, start_date, end_date)

            self.status_message = (
                f"Период: {summary.get('period')} | "
                f"Постов: {summary.get('total_posts')} | "
                f"Просмотров: {summary.get('total_views')} | "
                f"Лайков: {summary.get('total_likes')}"
            )

            top_posts = self.analyzer.get_top_posts(period_key, start_date, end_date, metric, limit=10)
            media_items = []
            if media_type == 'all':
                media_items.extend(self.analyzer.get_top_media('photo', period_key, start_date, end_date, metric, limit=5))
                media_items.extend(self.analyzer.get_top_media('video', period_key, start_date, end_date, metric, limit=5))
            else:
                media_items = self.analyzer.get_top_media(media_type, period_key, start_date, end_date, metric, limit=10)

            employees = self.analyzer.get_top_employees(period_key, start_date, end_date, metric='mention_count', 
                                                       employees_list=self.analyzer.load_employee_list(), limit=10)

            self.top_posts_text.setPlainText(self.format_posts(top_posts))
            self.top_media_text.setPlainText(self.format_media(media_items))
            self.top_employees_text.setPlainText(self.format_employees(employees))

        except Exception as e:
            self.top_posts_text.setPlainText(f"Ошибка загрузки статистики: {e}")
            self.top_media_text.clear()
            self.top_employees_text.clear()

    def format_posts(self, posts):
        if not posts:
            return "Нет данных за выбранный период."
        lines = []
        for idx, post in enumerate(posts, start=1):
            lines.append(f"{idx}. Пост ID {post.get('post_id')} | {post.get('date')}")
            lines.append(f"   Лайки: {post.get('likes')}  Комментарии: {post.get('comments')}  "
                         f"Поделиться: {post.get('shares')}  Просмотры: {post.get('views')}")
            lines.append(f"   Текст: {post.get('text')}")
            lines.append("")
        return "\n".join(lines)

    def format_media(self, media_list):
        if not media_list:
            return "Нет медиа-данных за выбранный период."
        lines = []
        for idx, item in enumerate(media_list, start=1):
            lines.append(f"{idx}. {item.get('type', '').title()} {item.get('media_key')} | {item.get('date')}")
            lines.append(f"   {self.metric_combo.currentText().title()}: {item.get('metric_value')}")
            lines.append("")
        return "\n".join(lines)

    def format_employees(self, employees):
        if not employees:
            return "Нет данных по преподавателям."
        lines = []
        for idx, item in enumerate(employees, start=1):
            lines.append(f"{idx}. {item.get('employee')} | Упоминаний: {item.get('mention_count')}  "
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

class StoragePage(QWidget):
    """Страница хранилища постов (исправленная версия)"""
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.loaded_count = 0
        self.limit = 20
        self.active_players = {}
        self._last_posts = []
        self.init_ui()

    def _theme_colors(self):
        if STYLES._theme == 'light':
            return {
                'title': '#111827',
                'muted': '#6b7280',
                'text': '#111827',
                'tag': '#2f6fce',
                'card_bg': '#ffffff',
                'card_border': '#d8dce5',
                'separator': '#e5e7eb',
                'media_bg': '#f3f4f6',
                'empty': '#9ca3af'
            }
        return {
            'title': '#f3f4f6',
            'muted': '#9aa4b2',
            'text': '#e5e7eb',
            'tag': '#6ea8ff',
            'card_bg': '#262a32',
            'card_border': '#3f4654',
            'separator': '#3f4654',
            'media_bg': '#16191f',
            'empty': '#7b8594'
        }

    def _post_card_style(self):
        c = self._theme_colors()
        return f"""
            QFrame {{
                background-color: {c['card_bg']};
                border: 1px solid {c['card_border']};
                border-radius: 14px;
                padding: 16px;
            }}
        """

    def _build_cover_pixmap(self, source_path, target_w, target_h):
        """Рисует превью в режиме cover (как в соцсетях), чтобы не было пустых полей."""
        pixmap = QPixmap(source_path)
        if pixmap.isNull():
            return QPixmap()

        scaled = pixmap.scaled(
            target_w,
            target_h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        x = max(0, (scaled.width() - target_w) // 2)
        y = max(0, (scaled.height() - target_h) // 2)
        return scaled.copy(x, y, target_w, target_h)

    def _content_width(self):
        """Текущая ширина рабочей области хранилища (без сайдбара/полос)."""
        viewport = self.scroll_area.viewport()
        width = viewport.width() if viewport else self.width()
        return max(320, min(width - 28, 1320))

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15) 
        
        header = QLabel("📚 Хранилище постов")
        colors = self._theme_colors()
        header.setStyleSheet(f"font-size: 24px; font-weight: 700; padding: 8px 2px 12px 2px; color: {colors['title']};")
        self.header_label = header
        layout.addWidget(header)
        
        # === ИНФОРМАЦИОННАЯ СТРОКА СТАТИСТИКИ ===
        stats_label = QLabel()
        colors = self._theme_colors()
        stats_label.setStyleSheet(f"color: {colors['text']}; font-size: 14px; padding: 10px; font-weight: 500;")
        self.storage_stats_label = stats_label
        layout.addWidget(self.storage_stats_label)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.posts_container = QWidget()
        self.posts_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.posts_layout = QVBoxLayout(self.posts_container)
        self.posts_layout.setSpacing(15)
        self.posts_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.posts_container)
        layout.addWidget(self.scroll_area)
        
        self.load_more_btn = QPushButton("📥 Загрузить ещё посты")
        self.load_more_btn.setStyleSheet(self.styles['button'])
        self.load_more_btn.setMinimumHeight(45)
        self.load_more_btn.clicked.connect(self.load_more_posts)
        self.load_more_btn.setVisible(False)
        layout.addWidget(self.load_more_btn)
        
        # Обновляем статистику при инициализации
        self.update_storage_stats()

    def update_storage_stats(self):
        """Обновляет статистику в хранилище"""
        try:
            db = Database()
            stats = db.get_stats()
            db.close()
            
            total = stats.get('total', 0)
            photos = stats.get('photos', 0)
            videos = stats.get('videos', 0)
            
            stats_text = f"📌 Всего: {total}  |  📷 Фото: {photos}  |  🎬 Видео: {videos}"
            self.storage_stats_label.setText(stats_text)
        except Exception as e:
            print(f"Error updating storage stats: {e}")

    def load_posts(self, posts, clear=True):
        if clear:
            self._last_posts = list(posts)

        if clear:
            while self.posts_layout.count():
                child = self.posts_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.loaded_count = 0
        
        if not posts:
            if clear:
                no_posts_label = QLabel("📭 Постов пока нет")
                colors = self._theme_colors()
                no_posts_label.setStyleSheet(f"color: {colors['muted']}; font-size: 16px; padding: 50px;")
                no_posts_label.setAlignment(Qt.AlignCenter)
                self.posts_layout.addWidget(no_posts_label)
            self.load_more_btn.setVisible(False)
            return
        
        sorted_posts = sorted(posts, key=lambda x: x[2] if len(x) > 2 else '', reverse=True)
        posts_to_show = sorted_posts[self.loaded_count:self.loaded_count + self.limit]
        
        for post in posts_to_show:
            post_widget = self.create_post_widget(post)
            self.posts_layout.addWidget(post_widget)
        
        self.loaded_count += len(posts_to_show)
        self.load_more_btn.setVisible(self.loaded_count < len(sorted_posts))
        self.posts_layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        # При первом показе вкладки пересчитываем layout под фактическую ширину.
        if self._last_posts:
            self.load_posts(self._last_posts, clear=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # При изменении размеров окна держим медиа в границах контейнера.
        if self.isVisible() and self._last_posts:
            self.load_posts(self._last_posts, clear=True)

    def load_more_posts(self):
        try:
            db = Database()
            all_posts = db.get_all_posts(limit=500)
            db.close()
            remaining_posts = all_posts[self.loaded_count:]
            self.load_posts(remaining_posts, clear=False)
        except Exception as e:
            print(f"Error loading more posts: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить посты:\n{e}")

    def create_post_widget(self, post):
        post_id = str(post[1]) if len(post) > 1 and post[1] is not None else "Unknown"
        date = str(post[2]) if len(post) > 2 and post[2] is not None else " "
        text = str(post[3]) if len(post) > 3 and post[3] is not None else " "
        tags = str(post[4]) if len(post) > 4 and post[4] is not None else " "
        media_type = str(post[5]) if len(post) > 5 and post[5] is not None else " "
        media_path = str(post[6]) if len(post) > 6 and post[6] is not None else " "

        post_frame = QFrame()
        post_frame.setStyleSheet(self._post_card_style())
        post_layout = QVBoxLayout(post_frame)
        post_layout.setSpacing(12)
        colors = self._theme_colors()

        if date:
            date_label = QLabel(date)
            date_label.setStyleSheet(f"color: {colors['muted']}; font-size: 12px; font-weight: 500;")
            post_layout.addWidget(date_label)

        if text:
            text_label = QLabel(text)
            text_label.setStyleSheet(f"color: {colors['text']}; font-size: 14px; line-height: 1.6;")
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            post_layout.addWidget(text_label)

        if tags:
            tags_label = QLabel(tags)
            tags_label.setStyleSheet(f"color: {colors['tag']}; font-size: 13px; font-weight: 600;")
            tags_label.setWordWrap(True)
            post_layout.addWidget(tags_label)

        if media_path and media_type:
            paths_list = [p.strip() for p in media_path.split(',') if p and p.strip() and p.strip() != "None"]
            types_list = [t.strip() for t in media_type.split(',')] if media_type else []
            normalized_media = []
            for idx, m_path in enumerate(paths_list):
                m_type = types_list[idx] if idx < len(types_list) and types_list[idx] else "photo"
                normalized_media.append((m_path, m_type))

            # Видео всегда показываем первыми, затем фото (как просили).
            normalized_media.sort(key=lambda item: 0 if str(item[1]).lower() == "video" else 1)

            if normalized_media:
                media_block = self._create_media_collection_widget(normalized_media, post_id)
                post_layout.addWidget(media_block)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {colors['separator']}; min-height: 1px; border: none;")
        post_layout.addWidget(line)

        return post_frame

    def _create_media_widget(self, media_path, media_type, post_id, target_w=None, target_h=None):
        if media_type.lower() == 'photo':
            return self._create_photo_widget(media_path, target_w=target_w, target_h=target_h)
        elif media_type.lower() == 'video':
            return self._create_video_widget(media_path, post_id, target_w=target_w, target_h=target_h)
        return None

    def _create_media_collection_widget(self, media_items, post_id):
        """VK-подобный блок медиа: только сетка (без карусели)."""
        colors = self._theme_colors()
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{background-color: transparent; border: none;}}"
        )
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 4, 0, 0)
        wrapper_layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        media_count = len(media_items)
        count_label = QLabel(f"Медиа: {media_count}")
        count_label.setStyleSheet(f"color: {colors['muted']}; font-size: 12px; font-weight: 600;")
        top_row.addWidget(count_label)
        top_row.addStretch()
        wrapper_layout.addLayout(top_row)

        grid_page = QWidget()
        grid_layout = QGridLayout(grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        content_w = self._content_width()
        cols = 3 if content_w >= 1080 else 2
        cell_w = max(220, min(380, (content_w - ((cols - 1) * 10)) // cols))
        cell_h = 260 if cols == 3 else 300

        row = 0
        col = 0
        for idx, (path, media_type) in enumerate(media_items):
            is_video = str(media_type).lower() == "video"
            span = 2 if is_video and cols > 1 else 1

            if is_video and col != 0:
                row += 1
                col = 0

            tile_w = (cell_w * span) + (10 * (span - 1))
            media_h = cell_h + (120 if is_video else 0)
            media_widget = self._create_media_widget(
                path,
                media_type,
                f"{post_id}_{idx}_grid",
                target_w=tile_w,
                target_h=media_h
            )
            if media_widget:
                media_widget.setFixedWidth(tile_w)
                media_widget.setMinimumHeight(media_h)
                media_widget.setMaximumHeight(media_h + 20)
                grid_layout.addWidget(media_widget, row, col, 1, span)

            if is_video:
                row += 1
                col = 0
            else:
                col += 1
                if col >= cols:
                    row += 1
                    col = 0

        wrapper_layout.addWidget(grid_page)
        return wrapper

    def _create_photo_widget(self, media_path, target_w=None, target_h=None):
        colors = self._theme_colors()
        target_w = target_w or min(680, self._content_width())
        target_h = target_h or 320
        photo_label = QLabel()
        photo_label.setAlignment(Qt.AlignCenter)
        photo_label.setMinimumHeight(target_h)
        photo_label.setMaximumHeight(target_h)
        photo_label.setStyleSheet(f"background-color: {colors['media_bg']}; border-radius: 12px;")
        
        if os.path.exists(media_path):
            pixmap = QPixmap(media_path)
            fit_pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            photo_label.setPixmap(fit_pixmap)
        else:
            photo_label.setText("📷 Фото не найдено")
            photo_label.setStyleSheet(f"color: {colors['empty']}; font-size: 14px;")
        return photo_label

    def _create_video_widget(self, video_path, post_id, target_w=None, target_h=None):
        # Создаем QStackedWidget вместо QStackedLayout
        colors = self._theme_colors()
        target_h = target_h or 320
        stack = QStackedWidget()
        stack.setMinimumHeight(target_h)
        stack.setMaximumHeight(target_h + 20)
        stack.setStyleSheet(f"background-color: {colors['media_bg']}; border-radius: 12px;")

        # Страница 0: Превью
        thumb_page = QWidget()
        thumb_layout = QVBoxLayout(thumb_page)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        thumb_label = QLabel()
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setCursor(Qt.PointingHandCursor)
        
        thumbnail = self._generate_thumbnail(video_path)
        if thumbnail and os.path.exists(thumbnail):
            frame_h = max(220, target_h - 70)
            cover = self._build_cover_pixmap(thumbnail, target_w or self._content_width(), frame_h)
            thumb_label.setPixmap(cover)
        else:
            thumb_label.setText("🎬")
            thumb_label.setStyleSheet(f"color: {colors['empty']}; font-size: 60px; background-color: {colors['media_bg']};")
            
        thumb_layout.addWidget(thumb_label)
        
        # Иконка поверх
        icon_overlay = QLabel("▶")
        icon_overlay.setAlignment(Qt.AlignCenter)
        icon_overlay.setStyleSheet("""
            QLabel { background-color: rgba(0,0,0,0.6); color: white; border: 2px solid white;
                    border-radius: 25px; font-size: 30px; padding: 10px 18px; }
        """)
        
        overlay_stack = QStackedLayout(thumb_page)
        overlay_stack.setStackingMode(QStackedLayout.StackAll)
        overlay_stack.addWidget(thumb_label)
        overlay_stack.addWidget(icon_overlay)
        
        stack.addWidget(thumb_page)
        
        # Страница 1: Контейнер плеера
        player_page = QWidget()
        player_page.setStyleSheet(f"background-color: {colors['media_bg']};")
        player_layout = QVBoxLayout(player_page)
        player_layout.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(player_page)
        
        def click_handler(event, path=video_path, pid=post_id, s=stack, pl=player_layout):
            self._play_video(path, pid, s, pl)
            
        thumb_page.mousePressEvent = click_handler
        
        return stack

    def _play_video(self, video_path, post_id, stack, player_layout):
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "Ошибка", "Видео файл не найден!")
            return

        if post_id in self.active_players:
            stack.setCurrentIndex(1)
            return

        while player_layout.count():
            player_layout.takeAt(0).widget().deleteLater()

        player = QMediaPlayer()
        video_widget = QVideoWidget()
        video_widget.setMinimumHeight(max(260, stack.minimumHeight() - 70))
        video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        player.setVideoOutput(video_widget)
        
        audio = QAudioOutput()
        audio.setVolume(1.0)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(video_path))
        
        # Создаем контролы и получаем ссылки
        controls, play_btn, timeline, time_label = self._create_video_controls(post_id)
        
        player_layout.addWidget(video_widget)
        player_layout.addWidget(controls)
        
        # Сохраняем ВСЕ ссылки в словаре
        self.active_players[post_id] = {
            'player': player,
            'stack': stack,
            'controls': controls,
            'video_widget': video_widget,
            'play_pause_btn': play_btn,
            'timeline': timeline,
            'time_label': time_label,
            'seeking': False
        }
        
        player.positionChanged.connect(lambda pos, pid=post_id: self._update_timeline(pid, pos))
        player.durationChanged.connect(lambda dur, pid=post_id: self._update_duration(pid, dur))
        player.playbackStateChanged.connect(lambda state, pid=post_id: self._on_playback_changed(pid, state))
        
        stack.setCurrentIndex(1)
        player.play()
        controls.setVisible(True)

    def _create_video_controls(self, post_id):
        controls_widget = QWidget()
        controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 18, 25, 0.92);
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        controls_widget.setFocusPolicy(Qt.NoFocus)
        
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(10)
        
        play_pause_btn = QPushButton("⏸")
        play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #2f6fce;
                color: white;
                border: none;
                font-size: 16px;
                padding: 4px 8px;
                min-width: 36px;
                min-height: 30px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #3a7bd5; }
        """)
        play_pause_btn.setFocusPolicy(Qt.NoFocus)
        play_pause_btn.clicked.connect(lambda checked, pid=post_id: self._toggle_play_pause(pid))
        controls_layout.addWidget(play_pause_btn)
        
        timeline = QSlider(Qt.Horizontal)
        timeline.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3a7bd5;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #3a7bd5;
                border-radius: 3px;
            }
        """)
        timeline.setFocusPolicy(Qt.NoFocus)
        timeline.sliderPressed.connect(lambda pid=post_id: self._on_slider_pressed(pid))
        timeline.sliderReleased.connect(lambda pid=post_id: self._on_slider_released(pid))
        timeline.setFixedHeight(20)
        controls_layout.addWidget(timeline)
        
        time_label = QLabel("0:00 / 0:00")
        time_label.setStyleSheet("color: white; font-size: 13px; min-width: 100px;")
        time_label.setAlignment(Qt.AlignRight)
        controls_layout.addWidget(time_label)
        
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 12px;
                min-height: 30px;
            }
        """)
        close_btn.setFocusPolicy(Qt.NoFocus)
        close_btn.clicked.connect(lambda checked, pid=post_id: self._stop_video(pid))
        controls_layout.addWidget(close_btn)
        
        controls_widget.setVisible(False)
        
        # Возвращаем все необходимые виджеты
        return controls_widget, play_pause_btn, timeline, time_label

    def _toggle_play_pause(self, post_id):
        data = self.active_players.get(post_id)
        if not data: 
            return
        try:
            player = data['player']
            btn = data.get('play_pause_btn')
            if player.isPlaying(): 
                player.pause()
                if btn: btn.setText("▶")
            else: 
                player.play()
                if btn: btn.setText("⏸")
        except RuntimeError: 
            pass

    def _seek_video(self, post_id):
        data = self.active_players.get(post_id)
        if not data: 
            return
        try:
            timeline = data.get('timeline')
            player = data['player']
            if timeline and player: 
                player.setPosition(timeline.value())
        except RuntimeError: 
            pass

    def _on_slider_pressed(self, post_id):
        """Пользователь начал тянуть ползунок"""
        data = self.active_players.get(post_id)
        if data:
            data['seeking'] = True

    def _on_slider_released(self, post_id):
        """Пользователь отпустил ползунок -> применяем перемотку"""
        data = self.active_players.get(post_id)
        if not data: return
        try:
            slider = data['controls'].findChild(QSlider)
            player = data['player']
            if slider and player:
                player.setPosition(slider.value())
            data['seeking'] = False
        except RuntimeError: pass

    def _update_timeline(self, post_id, pos):
        """Обновление таймлайна и времени"""
        data = self.active_players.get(post_id)
        if not data: return
        try:
            # ⛔ ГЛАВНОЕ ИСПРАВЛЕНИЕ: не двигаем ползунок, если пользователь его тянет
            if data.get('seeking', False):
                return
                
            slider = data['controls'].findChild(QSlider)
            lbl = data['controls'].findChild(QLabel)
            dur = data['player'].duration()
            
            if slider: slider.setValue(pos)
            if lbl: lbl.setText(f"{self._fmt(pos)} / {self._fmt(dur)}")
        except RuntimeError: pass

    def _update_duration(self, post_id, dur):
        data = self.active_players.get(post_id)
        if not data: 
            return
        try:
            timeline = data.get('timeline')
            time_label = data.get('time_label')
            if timeline: 
                timeline.setMaximum(dur)
            if time_label: 
                time_label.setText(f"0:00 / {self._fmt(dur)}")
        except RuntimeError: 
            pass

    def _on_playback_changed(self, post_id, state):
        from PySide6.QtMultimedia import QMediaPlayer
        data = self.active_players.get(post_id)
        if not data: 
            return
        try:
            btn = data.get('play_pause_btn')
            if btn:
                if state == QMediaPlayer.PlayingState:
                    btn.setText("⏸")
                elif state == QMediaPlayer.PausedState:
                    btn.setText("▶")
            if state == QMediaPlayer.StoppedState:
                self._stop_video(post_id)
        except RuntimeError: 
            pass

    def _stop_video(self, post_id):
        data = self.active_players.pop(post_id, None)
        if not data: 
            return
        try:
            player = data['player']
            stack = data['stack']
            
            player.blockSignals(True)
            player.stop()
            
            if stack: 
                stack.setCurrentIndex(0)
            
            player.deleteLater()
        except RuntimeError: 
            pass

    def _fmt(self, ms):
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"

    def _generate_thumbnail(self, video_path):
        try:
            if not os.path.exists(video_path): 
                return None
            d = os.path.join(os.path.dirname(video_path), "thumbnails")
            os.makedirs(d, exist_ok=True)
            tp = os.path.join(d, os.path.basename(video_path) + ".thumb.jpg")
            if os.path.exists(tp): 
                return tp
            import subprocess
            subprocess.run(['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', '-vf', 'scale=800:-1', '-y', tp],
                           capture_output=True, timeout=15)
            return tp if os.path.exists(tp) else None
        except: 
            return None

    def update_styles(self, styles):
        self.styles = styles
        text_color = '#000000' if STYLES._theme == 'light' else '#ffffff'
        bg_color = '#f5f5f5' if STYLES._theme == 'light' else '#1e1e1e'
        self.header_label.setStyleSheet(f"font-size: 24px; font-weight: 700; padding: 8px 2px 12px 2px; color: {text_color};")
        self.setStyleSheet(f"background-color: {bg_color};")
        self.load_more_btn.setStyleSheet(self.styles['button'])

class VideoPlayerWidget(QWidget):
    """Виджет видеоплеера с миниатюрой и управлением как в VK"""
    
    def __init__(self, video_path, styles):
        super().__init__()
        self.video_path = video_path
        self.styles = styles
        self.player = None
        self.is_playing = False
        self.thumbnail_label = None
        self.video_widget = None
        self.controls_widget = None
        self.play_overlay = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Контейнер для видео/миниатюры
        self.media_container = QWidget()
        self.media_container.setStyleSheet("background-color: #000000;")
        self.media_container.setMinimumHeight(250)
        self.media_container.setMaximumHeight(500)
        
        # Используем QStackedLayout для наложения элементов
        self.media_layout = QStackedLayout(self.media_container)
        self.media_layout.setContentsMargins(0, 0, 0, 0)
        
        # Страница 1: Миниатюра с кнопкой Play
        thumbnail_widget = QWidget()
        thumbnail_layout = QVBoxLayout(thumbnail_widget)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("background-color: #000000;")
        self.thumbnail_label.setMinimumHeight(250)
        
        # Генерируем миниатюру
        thumbnail = self.generate_thumbnail()
        if thumbnail and os.path.exists(thumbnail):
            pixmap = QPixmap(thumbnail)
            scaled_pixmap = pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            self.thumbnail_label.setText("🎬")
            self.thumbnail_label.setStyleSheet("color: #888888; font-size: 64px; background-color: #1e1e1e;")
        
        thumbnail_layout.addWidget(self.thumbnail_label)
        
        # Кнопка Play ПОВЕРХ миниатюры
        self.play_overlay = QPushButton("▶")
        self.play_overlay.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.6);
                color: white;
                border: 3px solid white;
                border-radius: 35px;
                font-size: 36px;
                width: 70px;
                height: 70px;
            }
            QPushButton:hover {
                background-color: rgba(58, 123, 213, 0.9);
                border-color: #3a7bd5;
            }
        """)
        self.play_overlay.setCursor(Qt.PointingHandCursor)
        self.play_overlay.clicked.connect(self.toggle_play)
        
        # Центрируем кнопку поверх миниатюры
        overlay_container = QWidget()
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.play_overlay)
        overlay_container.setStyleSheet("background-color: transparent;")
        overlay_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        thumbnail_layout.addWidget(overlay_container)
        
        self.media_layout.addWidget(thumbnail_widget)
        
        # Страница 2: Видеоплеер (добавляется при воспроизведении)
        self.video_page_widget = None
        
        layout.addWidget(self.media_container)
        
        # Контролы (скрыты по умолчанию, показываются при наведении)
        self.controls_widget = QWidget()
        self.controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.85);
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        self.controls_widget.setVisible(False)
        
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(10)
        
        # Кнопка Play/Pause
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 20px;
                padding: 5px 10px;
                min-width: 40px;
            }
            QPushButton:hover {
                color: #3a7bd5;
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_pause_btn)
        
        # Таймлайн
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 5px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3a7bd5;
                width: 15px;
                height: 15px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #3a7bd5;
                border-radius: 3px;
            }
        """)
        self.timeline.sliderMoved.connect(self.seek_video)
        self.timeline.setFixedHeight(20)
        controls_layout.addWidget(self.timeline)
        
        # Время
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: white; font-size: 13px; min-width: 100px;")
        self.time_label.setAlignment(Qt.AlignRight)
        controls_layout.addWidget(self.time_label)
        
        # Громкость
        self.volume_btn = QPushButton("🔊")
        self.volume_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 18px;
                padding: 5px;
                min-width: 30px;
            }
        """)
        controls_layout.addWidget(self.volume_btn)
        
        layout.addWidget(self.controls_widget)
        
        # Показываем контролы при наведении
        self.setMouseTracking(True)
        self.media_container.setMouseTracking(True)
        
        # Предотвращаем скролл при фокусе
        self.setFocusPolicy(Qt.NoFocus)
        if self.play_overlay:
            self.play_overlay.setFocusPolicy(Qt.NoFocus)
    
    def enterEvent(self, event):
        """Показ контролов при наведении"""
        if self.is_playing:
            self.controls_widget.setVisible(True)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Скрытие контролов при уходе мыши"""
        self.controls_widget.setVisible(False)
        super().leaveEvent(event)
    
    def generate_thumbnail(self):
        """Генерация миниатюры видео"""
        try:
            if not os.path.exists(self.video_path):
                return None
            
            thumb_dir = os.path.join(os.path.dirname(self.video_path), "thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)
            thumb_path = os.path.join(thumb_dir, os.path.basename(self.video_path) + ".thumb.jpg")
            
            if os.path.exists(thumb_path):
                return thumb_path
            
            import subprocess
            subprocess.run([
                'ffmpeg',
                '-i', self.video_path,
                '-ss', '00:00:01',
                '-vframes', '1',
                '-vf', 'scale=500:-1',
                '-y',
                thumb_path
            ], capture_output=True, timeout=30)
            
            return thumb_path if os.path.exists(thumb_path) else None
        except Exception as e:
            print(f"[Thumbnail] Error: {e}")
            return None
    
    def toggle_play(self):
        """Воспроизведение/пауза видео"""
        if self.is_playing:
            self.pause_video()
        else:
            self.play_video()
    
    def play_video(self):
        """Начало воспроизведения"""
        if not os.path.exists(self.video_path):
            return
        
        # Создаём видеоплеер
        self.player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.video_widget.setMinimumHeight(250)
        
        self.player.setVideoOutput(self.video_widget)
        audio_output = QAudioOutput()
        audio_output.setVolume(1.0)
        self.player.setAudioOutput(audio_output)
        self.player.setSource(QUrl.fromLocalFile(self.video_path))
        
        # Создаём страницу для видео
        self.video_page_widget = QWidget()
        video_page_layout = QVBoxLayout(self.video_page_widget)
        video_page_layout.setContentsMargins(0, 0, 0, 0)
        video_page_layout.addWidget(self.video_widget)
        
        # Переключаемся на страницу с видео
        self.media_layout.addWidget(self.video_page_widget)
        self.media_layout.setCurrentWidget(self.video_page_widget)
        
        # Скрываем кнопку Play
        if self.play_overlay:
            self.play_overlay.setVisible(False)
        
        # Подключаем сигналы
        self.player.positionChanged.connect(self.update_timeline)
        self.player.durationChanged.connect(self.update_duration)
        self.player.playbackStateChanged.connect(self.on_playback_changed)
        
        # Предотвращаем скролл
        self.video_widget.setFocusPolicy(Qt.NoFocus)
        self.player.play()
        
        self.is_playing = True
        self.play_pause_btn.setText("⏸")
        self.controls_widget.setVisible(True)
    
    def pause_video(self):
        """Пауза видео"""
        if self.player:
            self.player.pause()
            self.is_playing = False
            self.play_pause_btn.setText("▶")
    
    def seek_video(self, position):
        """Перемотка видео"""
        if self.player:
            self.player.setPosition(position)
    
    def update_timeline(self, position):
        """Обновление таймлайна"""
        self.timeline.setValue(position)
        self.time_label.setText(f"{self._format_time(position)} / {self._format_time(self.player.duration())}")
    
    def update_duration(self, duration):
        """Установка максимальной длительности"""
        self.timeline.setMaximum(duration)
    
    def on_playback_changed(self, state):
        """Обработка изменения состояния воспроизведения"""
        if state == QMediaPlayer.StoppedState:
            self.stop_video()
    
    def stop_video(self):
        """Остановка и возврат к миниатюре"""
        if self.player:
            self.player.stop()
            self.player = None
        
        if self.video_page_widget:
            # Переключаемся обратно на миниатюру
            self.media_layout.setCurrentIndex(0)
            self.video_page_widget.deleteLater()
            self.video_page_widget = None
            self.video_widget = None
            
            # Показываем кнопку Play
            if self.play_overlay:
                self.play_overlay.setVisible(True)
        
        self.is_playing = False
        self.play_pause_btn.setText("▶")
        self.controls_widget.setVisible(False)
    
    def _format_time(self, ms):
        """Форматирование времени"""
        if ms <= 0:
            return "0:00"
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

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

        header = QLabel("⚙️ Настройки приложения")
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
        self.theme_toggle_btn = QPushButton("🌓 Тёмная тема")
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

        # КАЧЕСТВО WEBP
        webp_layout = QGridLayout()
        webp_layout.setSpacing(15)
        webp_label = QLabel("🖼️ Качество WebP (1-100):")
        webp_label.setStyleSheet(self._get_label_style())
        webp_layout.addWidget(webp_label, 0, 0)
        self.webp_quality = QLineEdit("80")
        self.webp_quality.setStyleSheet(self.styles['input'])
        self.webp_quality.setMinimumHeight(40)
        webp_layout.addWidget(self.webp_quality, 0, 1)
        settings_layout.addLayout(webp_layout)

        # КАЧЕСТВО ВИДЕО
        video_layout = QGridLayout()
        video_layout.setSpacing(15)
        video_label = QLabel("🎥 Качество видео CRF (18-28):")
        video_label.setStyleSheet(self._get_label_style())
        video_layout.addWidget(video_label, 0, 0)
        self.video_crf = QLineEdit("23")
        self.video_crf.setStyleSheet(self.styles['input'])
        self.video_crf.setMinimumHeight(40)
        video_layout.addWidget(self.video_crf, 0, 1)
        settings_layout.addLayout(video_layout)

        # ПАПКА СОХРАНЕНИЯ
        folder_layout = QGridLayout()
        folder_layout.setSpacing(15)
        folder_label = QLabel("📁 Папка для сохранения:")
        folder_label.setStyleSheet(self._get_label_style())
        folder_layout.addWidget(folder_label, 0, 0)
        folder_input_layout = QHBoxLayout()
        self.folder_input = QLineEdit("vk_archive_data")
        self.folder_input.setStyleSheet(self.styles['input'])
        self.folder_input.setMinimumHeight(40)
        folder_input_layout.addWidget(self.folder_input)
        self.folder_btn = QPushButton("Обзор...")
        self.folder_btn.setStyleSheet(self.styles['button_secondary'])
        self.folder_btn.setMinimumWidth(100)
        folder_input_layout.addWidget(self.folder_btn)
        folder_layout.addLayout(folder_input_layout, 0, 1)
        settings_layout.addLayout(folder_layout)

        settings_layout.addStretch()

        self.save_btn = QPushButton("💾 Сохранить настройки")
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
            self.theme_toggle_btn.setText("☀️ Светлая тема")
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
            self.theme_toggle_btn.setText("🌓 Тёмная тема")
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
        """Переключение темы"""
        if STYLES._theme == 'dark':
            STYLES.set_theme('light')
        else:
            STYLES.set_theme('dark')

        self._update_theme_button_style()
        self.theme_info_label.setText(f"→ Сейчас: {'Светлая' if STYLES._theme == 'light' else 'Тёмная'} тема")
        self.theme_info_label.setStyleSheet(self._get_info_style())

    def on_save_clicked(self):
        """Сохранение настроек"""
        theme = 'light' if STYLES._theme == 'light' else 'dark'

        save_env_settings(
            theme=theme,
            webp_quality=self.webp_quality.text(),
            video_crf=self.video_crf.text(),
            folder=self.folder_input.text()
        )

        QMessageBox.information(
            self,
            "Настройки сохранены",
            f"✅ Тема: {'Светлая' if theme == 'light' else 'Тёмная'}\n\n"
            f"🖼️ WebP качество: {self.webp_quality.text()}\n"
            f"🎥 Видео CRF: {self.video_crf.text()}\n"
            f"📁 Папка: {self.folder_input.text()}\n\n"
            "⚠️ Изменения темы применятся после перезапуска приложения!"
        )

    def get_theme(self):
        return STYLES._theme

    def update_styles(self, styles):
        self.styles = styles
        self.header_label.setStyleSheet(self._get_header_style())
        self.theme_info_label.setStyleSheet(self._get_info_style())
        self._update_theme_button_style()


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

        header = QLabel("ℹ️ О программе")
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
            • 📥 Загрузка фото и видео из групп
            • 🖼️ Конвертация фото в WebP
            • 🎥 Обработка видео с улучшением качества
            • 🏷️ Авто-тегирование контента
            • 🔍 Быстрый поиск по архиву
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

class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, saved_token=None, saved_group_link=None, saved_post_count=None, saved_theme='system'):
        super().__init__()
        self.setWindowTitle("VK Media Archiver Pro")
        self.setMinimumSize(1024, 700)

        self.worker = None
        self.timer = QTimer()

        self.saved_token = saved_token or ''
        self.saved_group_link = saved_group_link or ''
        self.saved_post_count = saved_post_count or '20'
        self.saved_theme = saved_theme or 'system'

        from core.config_manager import get_effective_theme
        self.current_theme = get_effective_theme(self.saved_theme)

        update_global_styles(self.current_theme)
        self.styles = STYLES.get_styles()

        self.init_ui()
        self._fit_to_screen()
        self.update_stats()

        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)

    def _fit_to_screen(self):
        """Подгоняет размер окна под монитор пользователя."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.resize(1280, 800)
            return

        available = screen.availableGeometry()
        target_w = max(1024, int(available.width() * 0.92))
        target_h = max(700, int(available.height() * 0.90))
        self.resize(target_w, target_h)
        self.move(
            available.x() + (available.width() - target_w) // 2,
            available.y() + (available.height() - target_h) // 2
        )

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.header = HeaderWidget(self.current_theme)
        main_layout.addWidget(self.header)

        content_container = QWidget()
        content_layout = QHBoxLayout(content_container)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = SidebarWidget(self.current_theme)
        content_layout.addWidget(self.sidebar)

        content_frame = QFrame()
        content_frame.setStyleSheet(f"background-color: {'#f5f5f5' if self.current_theme == 'light' else '#1e1e1e'};")
        content_layout_main = QVBoxLayout(content_frame)
        content_layout_main.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
    
        # Порядок ВАЖЕН! Должен соответствовать словарю в switch_page
        self.download_page = DownloadPage(self.styles)      # 0
        self.search_page = SearchPage(self.styles)          # 1
        self.stats_page = StatsPage(self.styles)            # 2
        self.storage_page = StoragePage(self.styles)        # 3
        self.settings_page = SettingsPage(self.saved_theme, self.styles)  # 4
        self.about_page = AboutPage(self.styles)            # 5
        
        self.stacked_widget.addWidget(self.download_page)   # индекс 0
        self.stacked_widget.addWidget(self.search_page)     # индекс 1
        self.stacked_widget.addWidget(self.stats_page)      # индекс 2
        self.stacked_widget.addWidget(self.storage_page)    # индекс 3
        self.stacked_widget.addWidget(self.settings_page)   # индекс 4
        self.stacked_widget.addWidget(self.about_page)      # индекс 5

        content_layout_main.addWidget(self.stacked_widget)
        content_layout.addWidget(content_frame)
        main_layout.addWidget(content_container)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(self.styles['statusbar'])
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ Готов к работе")

        self.sidebar.buttons['download'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['search'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['stats'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['storage'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['settings'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['about'].clicked_signal.connect(self.switch_page)
        

        self.download_page.download_btn.clicked.connect(self.start_download)
        self.search_page.search_btn.clicked.connect(self.search_posts)
        self.search_page.clear_btn.clicked.connect(self.clear_results)
        self.search_page.search_input.returnPressed.connect(self.search_posts)

        self.download_page.token_input.setText(self.saved_token)
        self.download_page.group_input.setText(self.saved_group_link)
       
    def switch_page(self, page_name):
        for btn in self.sidebar.buttons.values():
            btn.setChecked(False)
        if page_name in self.sidebar.buttons:
            self.sidebar.buttons[page_name].setChecked(True)
        
        # Порядок должен соответствовать порядку добавления в stacked_widget!
        pages = {
            'download': 0,
            'search': 1,
            'stats': 2,
            'storage': 3,
            'settings': 4,
            'about': 5
        }
        
        if page_name in pages:
            self.stacked_widget.setCurrentIndex(pages[page_name])
            
            # Загружаем посты при переходе в хранилище
            if page_name == 'storage':
                self.load_storage_posts()
            elif page_name == 'stats':
                self.stats_page.refresh_statistics()

    def save_settings(self):
        token = self.download_page.token_input.text().strip()
        group_link = self.download_page.group_input.text().strip()
        theme = self.settings_page.get_theme()
        
        # Третий параметр (count) передаем пустым, так как скачивание теперь по датам
        if token or group_link or theme:
            save_env_settings(token, group_link, '', theme)

    def update_stats(self):
        try:
            db = Database()
            stats = db.get_stats()
            db.close()
            self.status_bar.showMessage(
                f"📊 Всего: {stats['total']} | "
                f"📷 Фото: {stats['photos']} | "
                f"🎬 Видео: {stats['videos']} | "
                f"📁 Папка: vk_archive_data/"
            )
            self.stats_page.total_value.setText(str(stats['total']))
            self.stats_page.photo_value.setText(str(stats['photos']))
            self.stats_page.video_value.setText(str(stats['videos']))
        except Exception:
            pass

    def log(self, message):
        self.status_bar.showMessage(message)

    def start_download(self):
        token = self.download_page.token_input.text().strip()
        group_input = self.download_page.group_input.text().strip()

        self.save_settings()

        if not token:
            QMessageBox.warning(self, "Ошибка", "Введите Access Token!")
            return
        if not group_input:
            QMessageBox.warning(self, "Ошибка", "Введите ссылку на сообщество!")
            return

        self.download_page.progress_bar.setVisible(True)
        self.download_page.download_btn.setEnabled(False)
        self.log("🔄 Загрузка началась...")

        # count больше не нужен, используем фиксированный размер порции 100 для API
        self.worker = DownloadWorker(token, group_input, count=100)
        self.worker.signals.progress.connect(self.log)
        self.worker.signals.finished.connect(self.download_finished)
        self.worker.signals.error.connect(self.download_error)
        self.worker.start()

    def download_finished(self):
        self.download_page.progress_bar.setVisible(False)
        self.download_page.download_btn.setEnabled(True)
        self.log("✅ Загрузка завершена!")
        self.update_stats()
        self.storage_page.update_storage_stats()
        QMessageBox.information(
            self,
            "Готово",
            "Архив успешно обновлен!\n\nФайлы сохранены в папку vk_archive_data/\n\nНастройки сохранены в .env"
        )

    def download_error(self, error_msg):
        self.download_page.progress_bar.setVisible(False)
        self.download_page.download_btn.setEnabled(True)
        self.log(f"❌ Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{error_msg}")

    def search_posts(self):
        query = self.search_page.search_input.text().strip()
        self.search_page.results_text.clear()
        
        if not query:
            self.search_page.results_text.append("⚠️ Введите запрос для поиска.\n")
            return
        
        db = Database()
        results = db.search(query)
        db.close()
        
        if not results:
            self.search_page.results_text.append("❌ Ничего не найдено.\n")
            self.log("📭 Ничего не найдено")
            return
        
        self.search_page.results_text.append(f"✅ Найдено постов: {len(results)}\n")
        self.search_page.results_text.append("=" * 60 + "\n\n")
        
        for i, row in enumerate(results, 1):
            original_post_id, _, date, text, tags, media_types, media_paths, file_sizes = row
            preview = text[:150] + "..." if len(text) > 150 else text
            
            # Разделяем множественные медиа
            types_list = media_types.split(',') if media_types else []
            paths_list = media_paths.split(',') if media_paths else []
            sizes_list = file_sizes.split(',') if file_sizes else []
            
            self.search_page.results_text.append(f"📌 Пост #{i}\n")
            self.search_page.results_text.append(f"📅 Дата: {date}\n")
            self.search_page.results_text.append(f"🆔 Post ID: {original_post_id}\n")
            self.search_page.results_text.append(f"🏷 Теги: {tags if tags else 'Нет'}\n")
            
            # Показываем все медиа поста
            self.search_page.results_text.append(f"📎 Медиа ({len(types_list)}):")
            for j, (mtype, mpath, msize) in enumerate(zip(types_list, paths_list, sizes_list), 1):
                self.search_page.results_text.append(f"\n   {j}. {mtype.upper()} ({msize}) → {mpath}")
            
            self.search_page.results_text.append(f"\n📝 Текст: {preview}\n")
            self.search_page.results_text.append("=" * 60 + "\n\n")
        
        self.log(f"✅ Найдено: {len(results)} постов")

    def clear_results(self):
        self.search_page.results_text.clear()
        self.search_page.search_input.clear()
        self.log("🗑 Результаты очищены")

    def load_storage_posts(self):
        """Загрузка постов в хранилище"""
        try:
            db = Database()
            posts = db.get_all_posts(limit=100)  # Получаем последние 100 постов
            db.close()
            self.storage_page.load_posts(posts)
            self.storage_page.update_storage_stats()
        except Exception as e:
            print(f"Error loading storage: {e}")

    def switch_page(self, page_name):
        for btn in self.sidebar.buttons.values():
            btn.setChecked(False)
        if page_name in self.sidebar.buttons:
            self.sidebar.buttons[page_name].setChecked(True)
        pages = {'download': 0, 'search': 1, 'stats': 2, 'storage': 3, 'settings': 4, 'about': 5}
        if page_name in pages:
            self.stacked_widget.setCurrentIndex(pages[page_name])
            
            # Загружаем посты при переходе в хранилище
            if page_name == 'storage':
                self.load_storage_posts()

    def closeEvent(self, event):
        self.timer.stop()
        self.save_settings()
        event.accept()