from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QProgressBar, QStatusBar, QFrame, QMessageBox,
    QStackedWidget, QScrollArea, QSizePolicy, QApplication, QComboBox,
    QDialog, QSlider, QStackedLayout, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from core.app_icon import get_app_icon
from PySide6.QtGui import QFont, QPixmap, QGuiApplication, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from ui.styles import STYLES, update_global_styles, apply_theme_dynamic, get_theme_colors
from worker.download_worker import DownloadWorker
from core.database import Database
from core.config_manager import save_env_settings, get_system_theme
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
import os, datetime
import subprocess
from core.logging_config import logger
from config.settings import DATA_DIR

from .components import HeaderWidget, SidebarWidget
from .pages.download_page import DownloadPage
from .pages.search_page import SearchPage
from .pages.stats_page import StatsPage
from .pages.storage_page import StoragePage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage
from .pages.teachers_page import TeachersPage
from .pages.departments_page import DepartmentsPage

class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, saved_token=None, saved_group_link=None, saved_post_count=None, saved_theme='system'):
        super().__init__()
        self.setWindowTitle("VK Archiver CHIBGU")
        self.setWindowIcon(get_app_icon())
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

        self.content_frame = QFrame()
        c = get_theme_colors(self.current_theme)
        self.content_frame.setStyleSheet(f"background-color: {c['content_bg']};")
        content_layout_main = QVBoxLayout(self.content_frame)
        content_layout_main.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()

        # Порядок важен! Индексы должны соответствовать словарю pages ниже
        self.download_page = DownloadPage(self.styles)       # 0
        self.search_page = SearchPage(self.styles)           # 1
        self.stats_page = StatsPage(self.styles)             # 2
        self.storage_page = StoragePage(self.styles)        # 3    
        self.teachers_page = TeachersPage(self.styles)       # 4
        self.departments_page = DepartmentsPage(self.styles)  # 5
        self.settings_page = SettingsPage(
            self.current_theme, self.saved_token, self.saved_group_link, self.styles
        )  # 5
        self.about_page = AboutPage(self.styles)             # 6

        self.stacked_widget.addWidget(self.download_page)
        self.stacked_widget.addWidget(self.search_page)
        self.stacked_widget.addWidget(self.stats_page)
        self.stacked_widget.addWidget(self.storage_page)
        self.stacked_widget.addWidget(self.teachers_page)
        # wrap settings/about/departments pages into scroll areas for vertical scrolling
        def _wrap_with_scroll(widget):
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setWidget(widget)
            return sa

        self.stacked_widget.addWidget(self.departments_page)
        self.stacked_widget.addWidget(_wrap_with_scroll(self.settings_page))
        self.stacked_widget.addWidget(_wrap_with_scroll(self.about_page))

        content_layout_main.addWidget(self.stacked_widget)
        content_layout.addWidget(self.content_frame)
        main_layout.addWidget(content_container)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(self.styles['statusbar'])
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        self.sidebar.buttons['download'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['search'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['stats'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['storage'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['teachers'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['departments'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['settings'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['about'].clicked_signal.connect(self.switch_page)
        

        self.download_page.download_btn.clicked.connect(self.start_download)
        self.search_page.search_btn.clicked.connect(self.search_posts)
        self.search_page.clear_btn.clicked.connect(self.clear_results)
        self.search_page.search_input.returnPressed.connect(self.search_posts)

    def switch_page(self, page_name):
        for btn in self.sidebar.buttons.values():
            btn.setChecked(False)
        if page_name in self.sidebar.buttons:
            self.sidebar.buttons[page_name].setChecked(True)
            
        pages = {
        'download': 0, 
        'search': 1, 
        'stats': 2, 
        'storage': 3, 
        'teachers' : 4,
        'departments': 5,
        'settings': 6, 
        'about': 7
    }
        if page_name in pages:
            self.stacked_widget.setCurrentIndex(pages[page_name])
            if page_name == 'storage':
                self.load_storage_posts()
            elif page_name == 'stats':
                self.stats_page.refresh_statistics()

    def closeEvent(self, event):
        """Безопасное завершение работы"""
        self.timer.stop()
        
        if hasattr(self, 'syncer') and self.syncer:
            self.syncer.stop_automatic_sync()
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.is_running = False
            self.worker.wait(3000)
        if hasattr(self, 'storage_page'):
            self.storage_page.cleanup_players()
            
        self.save_settings()
        logger.info("Приложение закрыто пользователем")
        event.accept()

    def apply_theme(self, theme):
        """Применяет тему ко всему окну (вызывается после сохранения настроек)."""
        app = QApplication.instance()
        effective = apply_theme_dynamic(app, theme)
        self.current_theme = effective
        self.saved_theme = effective
        self.styles = STYLES.get_styles()

        self.header.update_theme(effective)
        self.sidebar.update_theme(effective)
        c = get_theme_colors(effective)
        self.content_frame.setStyleSheet(f"background-color: {c['content_bg']};")
        self.status_bar.setStyleSheet(self.styles['statusbar'])

        for page in (
            self.download_page,
            self.search_page,
            self.stats_page,
            self.storage_page,
            self.teachers_page,
            self.departments_page,
            self.settings_page,
            self.about_page,
        ):
            if hasattr(page, 'update_styles'):
                page.update_styles(self.styles)

        self.settings_page.selected_theme = effective
        if self.stacked_widget.currentWidget() == self.storage_page and self.storage_page._last_posts:
            self.storage_page.load_posts(self.storage_page._last_posts, clear=True)
        self.update()

    def save_settings(self):
        token = self.settings_page.token_input.text().strip()
        group_link = self.settings_page.group_input.text().strip()
        if token or group_link or self.current_theme:
            save_env_settings(token, group_link, '', self.current_theme)

    def update_stats(self):
        """Безопасное обновление статуса"""
        try:
            sw = getattr(self.storage_page, "stats_worker", None)
            if sw is not None and sw.isRunning():
                return
            if getattr(self, "worker", None) is not None and self.worker.isRunning():
                return
            db = Database()
            stats = db.get_stats()
            db.close()
            self.status_bar.showMessage(
                f"Всего постов: {stats['total']} | Фото: {stats['photos']} | "
                f"Видео: {stats['videos']} | Клипы: {stats['clips']} | "
                f"Папка: {os.path.abspath(DATA_DIR)}"
            )
        except Exception as e:
            logger.error("Ошибка обновления статуса: %s", e, exc_info=True)

    def log(self, message):
        self.status_bar.showMessage(message)

    def start_download(self):
        token = self.settings_page.token_input.text().strip()
        group_input = self.settings_page.group_input.text().strip()

        self.save_settings()

        if not token:
            QMessageBox.warning(
                self, "Ошибка",
                "Не указан токен VK.\n\nОткройте «Настройки» и введите токен доступа.",
            )
            self.switch_page('settings')
            return
        if not group_input:
            QMessageBox.warning(
                self, "Ошибка",
                "Не указано сообщество.\n\nОткройте «Настройки» и укажите ссылку или ID группы.",
            )
            self.switch_page('settings')
            return

        self.download_page.reset_progress()
        self.download_page.download_btn.setEnabled(False)
        self.log("🔄 Загрузка началась...")

        # count больше не нужен, используем фиксированный размер порции 100 для API
        self.worker = DownloadWorker(token, group_input, count=100)
        self.worker.signals.progress.connect(self.log)
        self.worker.signals.progress_value.connect(self.download_page.set_progress)
        self.worker.signals.finished.connect(self.download_finished)
        self.worker.signals.error.connect(self.download_error)
        self.worker.start()

    def download_finished(self):
        self.download_page.set_progress(100)
        self.download_page.download_btn.setEnabled(True)
        self.log("Загрузка завершена")
        self.update_stats()
        self.storage_page.update_storage_stats()
        QMessageBox.information(
            self,
            "Готово",
            "Архив успешно обновлен!\n\nФайлы сохранены в папку vk_archive_data/\n\nНастройки сохранены в .env"
        )

    def download_error(self, error_msg):
        self.download_page.reset_progress()
        self.download_page.download_btn.setEnabled(True)
        self.log(f"Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n\n{error_msg}")

    def search_posts(self):
        query = self.search_page.search_input.text().strip()
        self.search_page.results_text.clear()
        
        if not query:
            self.search_page.results_text.append("Введите запрос для поиска.\n")
            return
        
        db = Database()
        results = db.search(query)
        db.close()
        
        if not results:
            self.search_page.results_text.append("Ничего не найдено.\n")
            self.log("Ничего не найдено")
            return
        
        self.search_page.results_text.append(f"Найдено постов: {len(results)}\n")
        self.search_page.results_text.append("=" * 60 + "\n\n")
        
        for i, row in enumerate(results, 1):
            original_post_id, _, date, text, tags, media_types, media_paths, file_sizes = row
            preview = text[:150] + "..." if len(text) > 150 else text
            
            # Разделяем множественные медиа
            types_list = media_types.split(',') if media_types else []
            paths_list = media_paths.split(',') if media_paths else []
            sizes_list = file_sizes.split(',') if file_sizes else []
            
            self.search_page.results_text.append(f"Пост #{i}\n")
            self.search_page.results_text.append(f"Дата: {date}\n")
            self.search_page.results_text.append(f"ID поста: {original_post_id}\n")
            self.search_page.results_text.append(f"Теги: {tags if tags else 'Нет'}\n")
            
            # Показываем все медиа поста
            self.search_page.results_text.append(
                f"Медиа (фото/видео/клипы): {len(types_list)}")
            for j, (mtype, mpath, msize) in enumerate(zip(types_list, paths_list, sizes_list), 1):
                type_label = {
                    'photo': 'Фото',
                    'video': 'Видео',
                    'clip': 'Клип'
                }.get(mtype.strip().lower(), mtype)
                self.search_page.results_text.append(f"\n   {j}. {type_label} ({msize}) → {mpath}")
            
            self.search_page.results_text.append(f"\nТекст: {preview}\n")
            self.search_page.results_text.append("=" * 60 + "\n\n")
        
        self.log(f"Найдено: {len(results)} постов")

    def clear_results(self):
        self.search_page.results_text.clear()
        self.search_page.search_input.clear()
        self.log("Результаты очищены")

    def load_storage_posts(self):
        """Загрузка постов в хранилище"""
        try:
            db = Database()
            posts = db.get_all_posts(limit=100)
            db.close()
            
            logger.info(f"[Storage] Загружено {len(posts)} постов из БД")
            for i, post in enumerate(posts[:3]):  # Первые 3 для отладки
                logger.info(f"  Post {i}: ID={post[0]}, date={post[2]}, media_types={post[5]}, media_paths={post[6]}")
            
            self.storage_page.load_posts(posts)
            self.storage_page.update_storage_stats()
        except Exception as e:
            logger.error(f"[Storage] Error loading posts: {e}")
            import traceback
            traceback.print_exc()
