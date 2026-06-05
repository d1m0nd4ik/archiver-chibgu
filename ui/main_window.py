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
from ui.styles import STYLES, update_global_styles, apply_theme_dynamic, get_theme_colors, refresh_ui_scale
from ui.button_effects import attach_press_animation_all
from ui.combo_effects import setup_all_combos
from ui.date_field_effects import setup_all_date_fields
from ui.ui_scale import UiScale
from core.task_queue import AppTaskQueue
from core.database import Database
from core.manual_import import ManualImportService
from core.config_manager import save_env_settings, get_system_theme
from core.statistics_analyzer import StatisticsAnalyzer
from core.statistics_exporter import StatisticsExporter
import os, datetime
import subprocess
from core.logging_config import logger, rotate_sync_log
from core.duplicate_check import find_similar_posts
from core.app_scheduler import mark_ran
from core.scheduler_prefs import load_scheduler_prefs
from core.scheduler_pipeline import build_scheduler_cycle
from core.archive_prerequisites import ensure_tag_dictionary
from core.backup_service import create_archive_backup
from config.settings import DATA_DIR

from .components import HeaderWidget, SidebarWidget
from .pages.dashboard_page import DashboardPage
from .pages.download_page import DownloadPage
from .pages.search_page import SearchPage
from .pages.stats_page import StatsPage
from .pages.storage_page import StoragePage
from .pages.settings_page import SettingsPage
from .pages.about_page import AboutPage
from .pages.teachers_page import TeachersPage
from .pages.departments_page import DepartmentsPage
from .pages.tags_page import TagsPage
from .pages.posts_manage_page import PostsManagePage

class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, saved_token=None, saved_group_link=None, saved_post_count=None, saved_theme='system'):
        super().__init__()
        self.setWindowTitle("VK Archiver CHIBGU")
        self.setWindowIcon(get_app_icon())
        min_size = UiScale.minimum_window_size()
        self.setMinimumSize(min_size)

        self.worker = None
        self.task_queue = AppTaskQueue.instance()
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
        rotate_sync_log()
        self._on_posts_archive_changed()
        self._check_scheduler(manual=False)

        self.timer.timeout.connect(self.update_stats)
        self.timer.start(5000)
        self._scheduler_timer = QTimer()
        self._scheduler_timer.timeout.connect(lambda: self._check_scheduler(manual=False))
        self._scheduler_timer.start(60 * 60 * 1000)

    def _fit_to_screen(self):
        """Подгоняет размер окна под монитор пользователя."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            self.resize(UiScale.px(1280), UiScale.px(800))
            return

        available = screen.availableGeometry()
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        target_w = max(min_w, int(available.width() * 0.96))
        target_h = max(min_h, int(available.height() * 0.92))
        self.resize(target_w, target_h)
        self.move(
            available.x() + (available.width() - target_w) // 2,
            available.y() + (available.height() - target_h) // 2,
        )

    def _wrap_with_scroll(self, widget):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sa.setWidget(widget)
        return sa

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
        self.dashboard_page = DashboardPage(self.styles, on_navigate=self.switch_page)
        self.download_page = DownloadPage(self.styles)
        self.search_page = SearchPage(
            self.styles,
            on_archive_changed=self._on_posts_archive_changed,
            on_open_in_storage=self._open_post_in_storage,
        )
        self.stats_page = StatsPage(self.styles)
        self.storage_page = StoragePage(self.styles)
        self.teachers_page = TeachersPage(self.styles)
        self.departments_page = DepartmentsPage(self.styles)
        self.tags_page = TagsPage(self.styles)
        self.posts_manage_page = PostsManagePage(
            self.styles, on_changed=self._on_posts_archive_changed
        )
        self.settings_page = SettingsPage(
            self.current_theme, self.saved_token, self.saved_group_link, self.styles
        )
        self.about_page = AboutPage(self.styles)

        self.stacked_widget.addWidget(self.dashboard_page)
        self.stacked_widget.addWidget(self.download_page)
        self.stacked_widget.addWidget(self.search_page)
        self.stacked_widget.addWidget(self.stats_page)
        self.stacked_widget.addWidget(self.storage_page)
        self.stacked_widget.addWidget(self.teachers_page)
        self.stacked_widget.addWidget(self._wrap_with_scroll(self.departments_page))
        self.stacked_widget.addWidget(self._wrap_with_scroll(self.tags_page))
        self.stacked_widget.addWidget(self._wrap_with_scroll(self.posts_manage_page))
        self.stacked_widget.addWidget(self._wrap_with_scroll(self.settings_page))
        self.stacked_widget.addWidget(self._wrap_with_scroll(self.about_page))

        content_layout_main.addWidget(self.stacked_widget, 1)
        content_layout.addWidget(self.content_frame, 1)
        main_layout.addWidget(content_container, 1)
        self.task_queue.task_finished.connect(self._on_background_task_finished)
        self._scheduler_plan = None
        self._scheduler_silent = False
        self.task_queue.progress_percent.connect(self.download_page.set_progress)
        self.task_queue.log_line.connect(self.log)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(self.styles['statusbar'])
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

        self.sidebar.buttons['dashboard'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['download'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['search'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['stats'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['storage'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['posts_manage'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['teachers'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['departments'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['tags'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['settings'].clicked_signal.connect(self.switch_page)
        self.sidebar.buttons['about'].clicked_signal.connect(self.switch_page)
        

        self.download_page.download_btn.clicked.connect(self.start_download)
        self.download_page.manual_add_btn.clicked.connect(self.add_manual_post)
        self.search_page.search_btn.clicked.connect(self.search_page.run_search)

        attach_press_animation_all(self)
        setup_all_combos(self)
        setup_all_date_fields(self)
        self._refresh_compact_field_pages()

    def _refresh_compact_field_pages(self) -> None:
        for page in (
            self.search_page,
            self.stats_page,
            self.download_page,
        ):
            if hasattr(page, "_apply_field_styles"):
                page._apply_field_styles()
            for w in getattr(page, "_compact_form_widgets", []) or []:
                from ui.form_layout import FormGrid
                from ui.date_field_effects import refresh_date_field
                from PySide6.QtWidgets import QDateEdit, QDateTimeEdit

                FormGrid.fix_field(w)
                if isinstance(w, (QDateEdit, QDateTimeEdit)):
                    refresh_date_field(w)

    def switch_page(self, page_name):
        pages = {
            'dashboard': 0,
            'download': 1,
            'search': 2,
            'stats': 3,
            'storage': 4,
            'teachers': 5,
            'departments': 6,
            'tags': 7,
            'posts_manage': 8,
            'settings': 9,
            'about': 10,
        }
        if page_name not in pages:
            return
        for btn in self.sidebar.buttons.values():
            btn.setChecked(False)
        if page_name in self.sidebar.buttons:
            self.sidebar.buttons[page_name].setChecked(True)
        self.stacked_widget.setCurrentIndex(pages[page_name])
        if page_name == 'dashboard':
            self.dashboard_page.refresh()
        elif page_name == 'storage':
            self.load_storage_posts()
        elif page_name == 'posts_manage':
            self.posts_manage_page.reload_table()
        elif page_name == 'search':
            self.search_page.reload_filter_lists()
        elif page_name == 'stats':
            self.stats_page.refresh_statistics()

    def closeEvent(self, event):
        """Безопасное завершение работы"""
        self.timer.stop()
        
        if hasattr(self, 'syncer') and self.syncer:
            self.syncer.stop_automatic_sync()
        if self.task_queue.is_busy():
            self.task_queue.cancel_current()
            if self.task_queue._current_thread:
                self.task_queue._current_thread.wait(3000)
        if hasattr(self, 'storage_page'):
            self.storage_page.cleanup_players()
            self.storage_page.cleanup_temp_folder()
            
        self.save_settings()
        logger.info("Приложение закрыто пользователем")
        event.accept()

    def apply_theme(self, theme):
        """Применяет тему ко всему окну (вызывается после сохранения настроек)."""
        app = QApplication.instance()
        effective = apply_theme_dynamic(app, theme)
        self.current_theme = effective
        self.saved_theme = effective
        refresh_ui_scale()
        self.styles = STYLES.get_styles()
        self.header.apply_scale()
        self.header.update_theme(effective)
        self.sidebar.apply_scale()
        self.sidebar.update_theme(effective)
        c = get_theme_colors(effective)
        self.content_frame.setStyleSheet(f"background-color: {c['content_bg']};")
        self.status_bar.setStyleSheet(self.styles['statusbar'])

        for page in (
            self.dashboard_page,
            self.download_page,
            self.search_page,
            self.stats_page,
            self.storage_page,
            self.posts_manage_page,
            self.teachers_page,
            self.departments_page,
            self.tags_page,
            self.settings_page,
            self.about_page,
        ):
            if hasattr(page, 'update_styles'):
                page.update_styles(self.styles)
        if hasattr(self.settings_page, 'task_queue_panel') and self.settings_page.task_queue_panel:
            self.settings_page.task_queue_panel.update_styles(self.styles)

        attach_press_animation_all(self)
        setup_all_combos(self)
        setup_all_date_fields(self)
        self._refresh_compact_field_pages()
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
            if self.task_queue.is_busy():
                return
            db = Database()
            stats = db.get_stats()
            db.close()
            self.status_bar.showMessage(
                f"Постов: {stats['total']} | Файлов: {stats.get('files', 0)} | "
                f"лайки {stats.get('likes', 0)} | {os.path.abspath(DATA_DIR)}"
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

        if self.task_queue.is_busy():
            QMessageBox.information(
                self,
                "Очередь занята",
                "Дождитесь завершения текущей задачи или отмените её в Настройки → Фоновые задачи.",
            )
            return

        self.download_page.reset_progress()
        self.download_page.download_btn.setEnabled(False)
        self.log("🔄 Загрузка добавлена в очередь…")

        self.task_queue.enqueue_download(token, group_input, count=100)

    def _on_background_task_finished(self, title: str, ok: bool):
        self._scheduler_continue_after_task(title, ok)

        if title == "Загрузка из ВКонтакте":
            self.download_page.download_btn.setEnabled(True)
            if not ok:
                self.download_page.reset_progress()
                QMessageBox.critical(
                    self, "Ошибка",
                    "Загрузка завершилась с ошибкой. См. журнал в Настройки → Фоновые задачи.",
                )
                return
            self.download_page.set_progress(100)
            self._on_posts_archive_changed()
            self.search_page.reload_filter_lists()
            if not self._scheduler_silent:
                QMessageBox.information(
                    self,
                    "Готово",
                    "Архив успешно обновлен!\n\nФайлы в Exports_data/\nНастройки в .env",
                )
        elif title == "Проверка целостности архива":
            report = self.task_queue.last_integrity_report()
            if report:
                self.settings_page.show_integrity_report(report)

    def _open_post_in_storage(self, original_post_id: int):
        self.switch_page('storage')
        if not self.storage_page.focus_post(original_post_id):
            QMessageBox.information(
                self,
                "Хранилище",
                f"Пост #{original_post_id} не найден в текущей подгрузке.",
            )

    def _check_scheduler(self, manual: bool = False):
        """Планировщик: справочники → теги → (retag) → ВК. Только пока приложение открыто."""
        if self._scheduler_plan is not None:
            return
        if self.task_queue.is_busy():
            return
        plan = build_scheduler_cycle(
            token=self.saved_token,
            group=self.saved_group_link,
            manual=manual,
        )
        if not plan:
            return
        self._scheduler_plan = plan
        self.log(f"Планировщик: {plan.summary()}")
        self._scheduler_run_next_step()

    def _scheduler_run_next_step(self):
        if not self._scheduler_plan or self.task_queue.is_busy():
            return
        if not self._scheduler_plan.steps:
            self.log("Планировщик: цикл завершён")
            self._scheduler_plan = None
            self._scheduler_silent = False
            self.search_page.reload_filter_lists()
            return

        step = self._scheduler_plan.steps.popleft()
        plan = self._scheduler_plan

        if step == "dept_sync":
            self.log("Планировщик: синхронизация кафедр и преподавателей…")
            self.task_queue.enqueue_dept_sync()
            return

        if step == "ensure_tags":
            added = ensure_tag_dictionary()
            if added:
                self.log(f"Планировщик: в словарь добавлено шаблонов — {added}")
            else:
                self.log("Планировщик: словарь тегов проверен")
            QTimer.singleShot(0, self._scheduler_run_next_step)
            return

        if step == "retag":
            self.log("Планировщик: пересчёт тегов по обновлённым справочникам…")
            self.task_queue.enqueue_retag()
            return

        if step == "vk_download":
            self.log("Планировщик: догрузка постов из ВК…")
            self.task_queue.enqueue_download(plan.token, plan.group, count=100)
            mark_ran("vk_download")
            return

        if step == "vk_stats":
            self.log("Планировщик: обновление метрик из ВК…")
            self.task_queue.enqueue_wall_stats_refresh(plan.token, plan.group)
            mark_ran("vk_stats")
            return

    def _scheduler_continue_after_task(self, title: str, ok: bool):
        if not self._scheduler_plan:
            return
        if title == "Синхронизация кафедр":
            if ok:
                mark_ran("dept_sync")
                self.log("Планировщик: кафедры и преподаватели обновлены")
            else:
                self.log("Планировщик: синхронизация кафедр не удалась — цикл остановлен")
                self._scheduler_plan = None
                self._scheduler_silent = False
                return
            QTimer.singleShot(0, self._scheduler_run_next_step)
            return
        if title == "Пересчёт тегов архива":
            if ok:
                mark_ran("retag_after_prep")
                self.log("Планировщик: теги постов пересчитаны")
            else:
                self.log("Планировщик: пересчёт тегов прерван")
                self._scheduler_plan = None
                self._scheduler_silent = False
                return
            QTimer.singleShot(0, self._scheduler_run_next_step)
            return
        if title in ("Загрузка из ВКонтакте", "Обновление метрик из ВК"):
            QTimer.singleShot(0, self._scheduler_run_next_step)

    def add_manual_post(self):
        data = self.download_page.get_manual_import_data()
        if not (data.get('text', '').strip() or data.get('file_paths')):
            QMessageBox.warning(
                self,
                "Ручная загрузка",
                "Укажите текст поста или выберите хотя бы один файл.",
            )
            return

        similar = find_similar_posts(
            posted_at=data['posted_at'],
            text=data.get('text', ''),
            file_paths=data.get('file_paths'),
        )
        if similar:
            lines = "\n".join(
                f"#{s['original_post_id']} ({s.get('date', '')}) — {s.get('reasons', '')}"
                for s in similar[:5]
            )
            ans = QMessageBox.question(
                self,
                "Похожие посты",
                f"Найдены возможные дубликаты:\n{lines}\n\nВсё равно добавить?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return

        self.download_page.manual_add_btn.setEnabled(False)
        self.log("Добавление материала в архив…")
        try:
            db = Database()
            service = ManualImportService(db)
            ok, message, post_id = service.import_post(
                posted_at=data['posted_at'],
                text=data['text'],
                file_paths=data['file_paths'],
                source_label=data['source_label'],
                manual_tags_text=data.get('manual_tags', ''),
            )
            db.close()
            if not ok:
                QMessageBox.warning(self, "Ручная загрузка", message)
                self.log(message)
                return
            self.download_page.clear_manual_form()
            self.download_page.reload_manual_sources()
            self._on_posts_archive_changed()
            self.log(message)
            QMessageBox.information(
                self,
                "Добавлено в архив",
                f"{message}\n\nОткройте «Хранилище постов», чтобы просмотреть запись.",
            )
        except Exception as e:
            logger.error("add_manual_post: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить материал:\n{e}")
        finally:
            self.download_page.manual_add_btn.setEnabled(True)

    def _on_posts_archive_changed(self):
        try:
            db = Database()
            db.recalculate_posts_importance()
            db.close()
        except Exception as e:
            logger.error("recalculate importance: %s", e)
        self.update_stats()
        self.storage_page.update_storage_stats()
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.refresh()
        if hasattr(self, 'posts_manage_page'):
            self.posts_manage_page.reload_table()

    def load_storage_posts(self):
        """Загрузка постов в хранилище"""
        try:
            self.storage_page.reload_posts()
            self.storage_page.update_storage_stats()
        except Exception as e:
            logger.error(f"[Storage] Error loading posts: {e}")
            import traceback
            traceback.print_exc()
