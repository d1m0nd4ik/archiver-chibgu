from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout, QLineEdit, QPushButton,
    QMessageBox, QTabWidget, QCheckBox, QComboBox, QFileDialog, QTextEdit,
    QSpinBox, QHBoxLayout,
)
from PySide6.QtCore import Qt
import os
import subprocess

from core.config_manager import save_env_settings, get_effective_theme, load_env_settings
from core.url_parser import VKUrlParser
from core.desktop_shortcut import create_desktop_shortcut
from core.logging_config import logger, get_recent_errors, clear_error_log, LOG_DIR
from core.backup_service import create_archive_backup
from core.scheduler_prefs import load_scheduler_prefs, save_scheduler_prefs
from core.app_scheduler import load_scheduler_state
from ui.styles import (
    STYLES, apply_theme_to_page, get_theme_colors,
    get_tab_widget_stylesheet, get_page_header_style, get_page_hint_style,
    get_theme_toggle_button_styles, get_standard_frame_stylesheet,
)
from ui.panels.task_queue_panel import TaskQueuePanel
from ui.integrity_ui import run_integrity_check, show_integrity_report
from ui.ui_scale import UiScale
from ui.form_layout import FormGrid
import vk_api


class SettingsPage(QWidget):
    """Настройки: Основные, Архив, Загрузка (доп.), Журнал, Фоновые задачи."""

    def __init__(self, current_theme='system', saved_token='', saved_group_link='', styles=None):
        super().__init__()
        self.saved_token = saved_token or ''
        self.saved_group_link = saved_group_link or ''
        env = load_env_settings()
        self._env_post_count = env.get('post_count', '20')
        self._env_cookies_file = env.get('cookies_file', '')
        self._env_cookies_browser = env.get('cookies_browser', 'edge,chrome,firefox')
        self.styles = styles or STYLES.get_styles()
        self.selected_theme = get_effective_theme(current_theme)
        self.task_queue_panel = None
        self._form_labels: list[QLabel] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        header = QLabel("Настройки приложения")
        header.setStyleSheet(get_page_header_style())
        self.header_label = header
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(get_tab_widget_stylesheet())
        layout.addWidget(self.tabs, 1)

        self._build_general_tab()
        self._build_archive_tab()
        self._build_download_extra_tab()
        self._build_journal_tab()
        self._build_tasks_tab()

        self._secondary_buttons = [
            self.shortcut_btn,
            self.clear_log_btn,
            self.backup_btn,
            self.integrity_btn,
            self.integrity_report_btn,
            self.refresh_errors_btn,
            self.clear_errors_btn,
            self.open_logs_btn,
        ]

    def _build_general_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(8, 12, 8, 8)
        tab_layout.setSpacing(16)

        self.settings_frame = QFrame()
        self.settings_frame.setStyleSheet(self.styles['frame'])
        settings_layout = QVBoxLayout(self.settings_frame)
        settings_layout.setSpacing(20)

        vk_section = QFrame()
        vk_section.setStyleSheet("background-color: transparent;")
        self._vk_layout = QGridLayout(vk_section)
        vk_layout = self._vk_layout
        FormGrid.setup_two_column(vk_layout, wide_labels=True)

        self.vk_title = QLabel("Подключение к ВКонтакте")
        self.vk_title.setStyleSheet(self._get_label_style())
        vk_layout.addWidget(self.vk_title, 0, 0, 1, 2)

        tok_lbl = FormGrid.make_label("Токен доступа:", wide=True)
        self._form_labels.append(tok_lbl)
        vk_layout.addWidget(tok_lbl, 1, 0)
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Вставьте токен с vkhost.github.io")
        self.token_input.setText(self.saved_token)
        self.token_input.setStyleSheet(self.styles['input'])
        vk_layout.addWidget(self.token_input, 1, 1)

        grp_lbl = FormGrid.make_label("Ссылка на сообщество:", wide=True)
        self._form_labels.append(grp_lbl)
        vk_layout.addWidget(grp_lbl, 2, 0)
        self.group_input = QLineEdit()
        self.group_input.setPlaceholderText("https://vk.ru/имя_группы, club123 или 236813059")
        self.group_input.setText(self.saved_group_link)
        self.group_input.setStyleSheet(self.styles['input'])
        vk_layout.addWidget(self.group_input, 2, 1)

        for w in (self.token_input, self.group_input):
            FormGrid.fix_field(w, compact=False)
        FormGrid.sync_grid(vk_layout, compact=False, labels=self._form_labels)

        vk_hint = QLabel(
            "Сообщество: полная ссылка (vk.com / vk.ru), короткое имя или числовой ID. "
            "При сохранении короткое имя можно проверить через VK API."
        )
        vk_hint.setWordWrap(True)
        vk_hint.setProperty('uiRole', 'hint')
        vk_hint.setStyleSheet(get_page_hint_style())
        vk_layout.addWidget(vk_hint, 3, 0, 1, 2)
        settings_layout.addWidget(vk_section)

        self.line_vk = QFrame()
        self.line_vk.setFrameShape(QFrame.HLine)
        self.line_vk.setFixedHeight(1)
        settings_layout.addWidget(self.line_vk)

        theme_section = QFrame()
        theme_section.setStyleSheet("background-color: transparent;")
        self._theme_layout = QGridLayout(theme_section)
        theme_layout = self._theme_layout
        FormGrid.setup_two_column(theme_layout, wide_labels=True)

        self.theme_label = FormGrid.make_label("Тема оформления:", wide=True)
        self._form_labels.append(self.theme_label)
        theme_layout.addWidget(self.theme_label, 0, 0)

        self.theme_toggle_btn = QPushButton("Тёмная тема")
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setMinimumHeight(FormGrid.field_height(compact=False) + UiScale.px(8))
        self.theme_toggle_btn.clicked.connect(self.on_theme_toggle)
        self._update_theme_button_style()
        theme_layout.addWidget(self.theme_toggle_btn, 0, 1)
        FormGrid.sync_grid(theme_layout, compact=False, labels=self._form_labels)

        self.theme_info_label = QLabel()
        self._update_theme_info_label()
        self.theme_info_label.setProperty('uiRole', 'hint')
        self.theme_info_label.setStyleSheet(get_page_hint_style())
        theme_layout.addWidget(self.theme_info_label, 1, 0, 1, 2)
        settings_layout.addWidget(theme_section)

        self.line_theme = QFrame()
        self.line_theme.setFrameShape(QFrame.HLine)
        self.line_theme.setFixedHeight(1)
        settings_layout.addWidget(self.line_theme)

        sched_section = QFrame()
        sched_section.setStyleSheet("background-color: transparent;")
        self._sched_layout = QGridLayout(sched_section)
        sched_layout = self._sched_layout
        FormGrid.setup_two_column(sched_layout, wide_labels=True)
        sched_title = QLabel("Планировщик (пока приложение открыто):")
        sched_title.setStyleSheet(self._get_label_style())
        sched_layout.addWidget(sched_title, 0, 0, 1, 2)
        prefs = load_scheduler_prefs()
        self.scheduler_cb = QCheckBox("Включить догрузку и метрики по расписанию")
        self.scheduler_cb.setChecked(bool(prefs.get("enabled")))
        sched_layout.addWidget(self.scheduler_cb, 1, 0, 1, 2)
        interval_lbl = FormGrid.make_label("Интервал:", wide=True)
        self._form_labels.append(interval_lbl)
        sched_layout.addWidget(interval_lbl, 2, 0)
        self.scheduler_interval = QComboBox()
        self.scheduler_interval.addItem("Ежедневно", "daily")
        self.scheduler_interval.addItem("Еженедельно", "weekly")
        idx = self.scheduler_interval.findData(prefs.get("interval", "weekly"))
        self.scheduler_interval.setCurrentIndex(idx if idx >= 0 else 1)
        sched_layout.addWidget(self.scheduler_interval, 2, 1)
        FormGrid.fix_field(self.scheduler_interval, compact=False)
        FormGrid.sync_grid(sched_layout, compact=False, labels=self._form_labels)
        state = load_scheduler_state()
        self.scheduler_info = QLabel(
            f"Последний запуск: ВК {state.get('vk_download', '—')}, метрики {state.get('vk_stats', '—')}"
        )
        self.scheduler_info.setWordWrap(True)
        self.scheduler_info.setStyleSheet(self._get_info_style())
        sched_layout.addWidget(self.scheduler_info, 3, 0, 1, 2)
        sched_hint = QLabel(
            "Порядок: кафедры и преподаватели → словарь тегов → при необходимости пересчёт тегов "
            "на вкладке «Тэги» → догрузка из ВК. Обновление лайков вручную — в Хранилище."
        )
        sched_hint.setWordWrap(True)
        sched_hint.setProperty('uiRole', 'hint')
        sched_hint.setStyleSheet(get_page_hint_style())
        sched_layout.addWidget(sched_hint, 4, 0, 1, 2)
        settings_layout.addWidget(sched_section)

        settings_layout.addStretch()

        self.shortcut_btn = QPushButton("Создать или обновить ярлык на рабочем столе")
        self.shortcut_btn.setStyleSheet(self.styles['button_secondary'])
        self.shortcut_btn.setMinimumHeight(44)
        self.shortcut_btn.clicked.connect(self.on_create_shortcut_clicked)
        settings_layout.addWidget(self.shortcut_btn)

        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.setStyleSheet(self.styles['button'])
        self.save_btn.setMinimumHeight(50)
        self.save_btn.clicked.connect(self.on_save_clicked)
        settings_layout.addWidget(self.save_btn)

        tab_layout.addWidget(self.settings_frame)
        tab_layout.addStretch()
        self.tabs.addTab(tab, "Основные")

    def _build_archive_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 12, 8, 8)
        lay.setSpacing(12)

        frame = QFrame()
        frame.setStyleSheet(self.styles['frame'])
        inner = QVBoxLayout(frame)
        inner.setSpacing(14)

        hint = QLabel(
            "Резервная копия и проверка соответствия файлов на диске и записей в базе. "
            "Пересчёт тегов по словарю — на вкладке «Тэги»."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(self._get_info_style())
        inner.addWidget(hint)

        self.backup_btn = QPushButton("Резервная копия (Archive.db + Exports_data → ZIP)")
        self.backup_btn.setStyleSheet(self.styles['button_secondary'])
        self.backup_btn.setMinimumHeight(44)
        self.backup_btn.clicked.connect(self.on_backup_clicked)
        inner.addWidget(self.backup_btn)

        self.integrity_btn = QPushButton("Проверить целостность архива")
        self.integrity_btn.setStyleSheet(self.styles['button_secondary'])
        self.integrity_btn.setMinimumHeight(44)
        self.integrity_btn.clicked.connect(lambda: run_integrity_check(self))
        inner.addWidget(self.integrity_btn)

        self.integrity_report_btn = QPushButton("Показать последний отчёт")
        self.integrity_report_btn.setStyleSheet(self.styles['button_secondary'])
        self.integrity_report_btn.clicked.connect(self._show_last_integrity_report)
        inner.addWidget(self.integrity_report_btn)

        inner.addStretch()
        lay.addWidget(frame)
        lay.addStretch()
        self.tabs.addTab(tab, "Архив")

    def _build_download_extra_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 12, 8, 8)

        frame = QFrame()
        frame.setStyleSheet(self.styles['frame'])
        self._download_extra_grid = QGridLayout(frame)
        grid = self._download_extra_grid
        FormGrid.setup_two_column(grid, wide_labels=True)

        hint = QLabel(
            "Обычно менять не нужно. Заполните cookies, только если видео и клипы не скачиваются "
            "через yt-dlp. Сохранение — кнопка на вкладке «Основные»."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(self._get_info_style())
        grid.addWidget(hint, 0, 0, 1, 2)

        pc_lbl = FormGrid.make_label("Постов в запросе wall.get:", wide=True)
        self._form_labels.append(pc_lbl)
        grid.addWidget(pc_lbl, 1, 0)
        self.post_count_spin = QSpinBox()
        self.post_count_spin.setRange(1, 100)
        try:
            self.post_count_spin.setValue(int(self._env_post_count))
        except ValueError:
            self.post_count_spin.setValue(20)
        self.post_count_spin.setStyleSheet(self.styles.get('spinbox', self.styles['input']))
        grid.addWidget(self.post_count_spin, 1, 1)

        cookies_lbl = FormGrid.make_label("Файл cookies (yt-dlp):", wide=True)
        self._form_labels.append(cookies_lbl)
        grid.addWidget(cookies_lbl, 2, 0)
        cookies_row = QHBoxLayout()
        self.cookies_file_input = QLineEdit()
        self.cookies_file_input.setPlaceholderText("cookies.txt — необязательно")
        self.cookies_file_input.setText(self._env_cookies_file)
        self.cookies_file_input.setStyleSheet(self.styles['input'])
        cookies_row.addWidget(self.cookies_file_input, 1)
        browse = QPushButton("Обзор…")
        browse.setStyleSheet(self.styles['button_secondary'])
        browse.clicked.connect(self._browse_cookies_file)
        cookies_row.addWidget(browse)
        grid.addLayout(cookies_row, 2, 1)

        br_lbl = FormGrid.make_label("Браузеры для cookies:", wide=True)
        self._form_labels.append(br_lbl)
        grid.addWidget(br_lbl, 3, 0)
        self.cookies_browser_input = QLineEdit()
        self.cookies_browser_input.setPlaceholderText("edge,chrome,firefox")
        self.cookies_browser_input.setText(self._env_cookies_browser)
        self.cookies_browser_input.setStyleSheet(self.styles['input'])
        grid.addWidget(self.cookies_browser_input, 3, 1)

        for w in (self.post_count_spin, self.cookies_file_input, self.cookies_browser_input):
            FormGrid.fix_field(w, compact=False)
        FormGrid.sync_grid(grid, compact=False, labels=self._form_labels)

        lay.addWidget(frame)
        lay.addStretch()
        self.tabs.addTab(tab, "Загрузка (доп.)")

    def _build_journal_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(8, 12, 8, 8)
        lay.setSpacing(10)

        path_lbl = QLabel(f"Каталог журналов: {LOG_DIR}")
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet(self._get_info_style())
        lay.addWidget(path_lbl)

        btn_row = QHBoxLayout()
        self.refresh_errors_btn = QPushButton("Обновить")
        self.refresh_errors_btn.setStyleSheet(self.styles['button_secondary'])
        self.refresh_errors_btn.clicked.connect(self.refresh_errors_view)
        btn_row.addWidget(self.refresh_errors_btn)
        self.clear_errors_btn = QPushButton("Очистить errors.log")
        self.clear_errors_btn.setStyleSheet(self.styles['button_secondary'])
        self.clear_errors_btn.clicked.connect(self.on_clear_errors)
        btn_row.addWidget(self.clear_errors_btn)
        self.open_logs_btn = QPushButton("Открыть папку logs")
        self.open_logs_btn.setStyleSheet(self.styles['button_secondary'])
        self.open_logs_btn.clicked.connect(self._open_logs_folder)
        btn_row.addWidget(self.open_logs_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        self.errors_view = QTextEdit()
        self.errors_view.setReadOnly(True)
        self.errors_view.setStyleSheet(self.styles.get('input', ''))
        self.errors_view.setMinimumHeight(UiScale.px(280))
        lay.addWidget(self.errors_view, 1)

        note = QLabel(
            "Здесь только ошибки (errors.log). Журнал фоновых задач — вкладка «Фоновые задачи»."
        )
        note.setWordWrap(True)
        note.setStyleSheet(self._get_info_style())
        lay.addWidget(note)

        self.tabs.addTab(tab, "Журнал")
        self.refresh_errors_view()

    def _build_tasks_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(8, 12, 8, 8)
        tab_layout.setSpacing(12)

        hint = QLabel(
            "Загрузка из ВК, пересчёт тегов, синхронизация кафедр, проверка целостности. "
            "Одна задача за раз — отмена оранжевой кнопкой справа."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(self._get_info_style())
        tab_layout.addWidget(hint)

        self.task_queue_panel = TaskQueuePanel(self.styles, embedded=True)
        tab_layout.addWidget(self.task_queue_panel, 1)

        self.clear_log_btn = self.task_queue_panel.clear_log_btn
        self.tabs.addTab(tab, "Фоновые задачи")

    def _browse_cookies_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Файл cookies для yt-dlp", "", "Текстовые (*.txt);;Все (*.*)"
        )
        if path:
            self.cookies_file_input.setText(path)

    def _open_logs_folder(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(LOG_DIR))
        except AttributeError:
            subprocess.run(["xdg-open", str(LOG_DIR)], check=False)

    def refresh_errors_view(self):
        errors = get_recent_errors(40)
        body = "\n".join(errors) if errors else "Ошибок не зафиксировано."
        self.errors_view.setPlainText(body)

    def on_clear_errors(self):
        answer = QMessageBox.question(
            self,
            "Очистить журнал ошибок",
            "Удалить все записи из logs/errors.log?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        clear_error_log()
        self.refresh_errors_view()

    def _show_last_integrity_report(self):
        from core.task_queue import AppTaskQueue
        report = AppTaskQueue.instance().last_integrity_report()
        if report:
            show_integrity_report(self, report)
        else:
            show_integrity_report(self, None)

    def show_integrity_report(self, report: dict | None = None):
        show_integrity_report(self, report)

    def _get_header_style(self):
        c = get_theme_colors()
        return f"color: {c['text']}; font-size: 22px; font-weight: bold; padding: 10px 0;"

    def _get_label_style(self):
        c = get_theme_colors()
        return f"color: {c['text']}; font-size: 14px; font-weight: 600;"

    def _get_info_style(self):
        c = get_theme_colors()
        return f"color: {c['text_muted']}; font-size: 13px; font-style: italic;"

    def refresh_theme_sections(self):
        c = get_theme_colors()
        sep = f"background-color: {c['separator']}; max-height: 1px; border: none;"
        self.line_vk.setStyleSheet(sep)
        self.line_theme.setStyleSheet(sep)
        self.settings_frame.setStyleSheet(get_standard_frame_stylesheet())
        self.tabs.setStyleSheet(get_tab_widget_stylesheet())
        self.vk_title.setStyleSheet(self._get_label_style())

    def _update_theme_info_label(self):
        applied = STYLES._theme
        selected_name = 'Светлая' if self.selected_theme == 'light' else 'Тёмная'
        if self.selected_theme == applied:
            self.theme_info_label.setText(f"→ Активна: {selected_name} тема")
        else:
            self.theme_info_label.setText(
                f"→ Выбрана: {selected_name} тема (применится после «Сохранить настройки»)"
            )

    def _update_theme_button_style(self):
        light = self.selected_theme == 'light'
        self.theme_toggle_btn.setText("Светлая тема" if light else "Тёмная тема")
        self.theme_toggle_btn.setChecked(light)
        self.theme_toggle_btn.setStyleSheet(
            get_theme_toggle_button_styles(light_selected=light)
        )

    def on_backup_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка для резервной копии")
        if not folder:
            return
        ok, msg, path = create_archive_backup(folder)
        if ok:
            QMessageBox.information(self, "Резервная копия", f"{msg}\n\n{path}")
        else:
            QMessageBox.warning(self, "Ошибка", msg)

    def on_create_shortcut_clicked(self):
        try:
            path = create_desktop_shortcut()
            QMessageBox.information(
                self,
                "Ярлык обновлён",
                f"Ярлык «VK Media Archiver Pro» на рабочем столе обновлён:\n\n{path}",
            )
        except OSError as e:
            QMessageBox.warning(self, "Недоступно", str(e))
        except Exception as e:
            logger.error("Create shortcut: %s", e, exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать ярлык:\n\n{e}")

    def on_theme_toggle(self):
        self.selected_theme = 'light' if self.selected_theme == 'dark' else 'dark'
        self._update_theme_button_style()
        self._update_theme_info_label()

    def on_save_clicked(self):
        token = self.token_input.text().strip()
        group_link = self.group_input.text().strip()
        theme = self.selected_theme

        if not token or not group_link:
            QMessageBox.warning(
                self,
                "Не заполнены поля",
                "Укажите токен доступа и ссылку (или ID) сообщества ВКонтакте.",
            )
            return

        group_note = ""
        if not VKUrlParser._numeric_group_id(group_link):
            try:
                from core.vk_token import ensure_token_valid
                session = vk_api.VkApi(token=token)
                ensure_token_valid(session)
                resolved = VKUrlParser.resolve_group_id(group_link, session)
                if resolved is not None:
                    group_note = f"\nСообщество распознано, ID для API: {resolved}"
                else:
                    QMessageBox.warning(
                        self,
                        "Сообщество не найдено",
                        VKUrlParser.format_resolve_hint(group_link),
                    )
                    return
            except ValueError as e:
                QMessageBox.warning(self, "Сообщество не найдено", str(e))
                return
            except Exception as e:
                logger.warning("Проверка сообщества при сохранении: %s", e)
                QMessageBox.warning(
                    self,
                    "Не удалось проверить сообщество",
                    f"{e}\n\nНастройки не сохранены.",
                )
                return

        save_env_settings(
            token,
            group_link,
            str(self.post_count_spin.value()),
            theme,
            cookies_file=self.cookies_file_input.text().strip(),
            cookies_browser=self.cookies_browser_input.text().strip(),
        )
        save_scheduler_prefs({
            "enabled": self.scheduler_cb.isChecked(),
            "interval": self.scheduler_interval.currentData(),
            "run_dept_sync": True,
            "run_retag_after_prep": True,
            "run_vk_download": True,
            "run_vk_stats": True,
        })

        main_win = self.window()
        if hasattr(main_win, 'saved_token'):
            main_win.saved_token = token
            main_win.saved_group_link = group_link
            main_win.saved_post_count = str(self.post_count_spin.value())
        planner_line = ""
        if hasattr(main_win, "_check_scheduler"):
            main_win._scheduler_silent = True
            main_win._check_scheduler(manual=True)
            plan = getattr(main_win, "_scheduler_plan", None)
            if plan and plan.steps:
                planner_line = (
                    f"\n\nПланировщик: {plan.summary()}.\n"
                    "Ход выполнения — Настройки → Фоновые задачи."
                )
        if hasattr(main_win, 'apply_theme'):
            main_win.apply_theme(theme)

        self._update_theme_info_label()
        state = load_scheduler_state()
        self.scheduler_info.setText(
            f"Последний запуск: ВК {state.get('vk_download', '—')}, "
            f"метрики {state.get('vk_stats', '—')}"
        )

        theme_label = "Светлая" if theme == 'light' else "Тёмная"
        QMessageBox.information(
            self,
            "Настройки сохранены",
            (
                f"Токен и сообщество сохранены в .env{group_note}\n"
                f"Тема: {theme_label} — применена ко всему приложению.\n"
                f"Пакет wall.get: {self.post_count_spin.value()}."
                f"{planner_line}"
            ),
        )

    def get_theme(self):
        return self.selected_theme

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self.refresh_theme_sections()
        self.header_label.setStyleSheet(get_page_header_style())
        self.tabs.setStyleSheet(get_tab_widget_stylesheet())
        self.theme_info_label.setStyleSheet(self._get_info_style())
        self.shortcut_btn.setStyleSheet(self.styles['button_secondary'])
        self.save_btn.setStyleSheet(self.styles['button'])
        for btn in (
            self.backup_btn, self.integrity_btn, self.integrity_report_btn,
            self.refresh_errors_btn, self.clear_errors_btn, self.open_logs_btn,
            self.shortcut_btn,
        ):
            btn.setStyleSheet(self.styles['button_secondary'])
        self._update_theme_button_style()
        self._update_theme_info_label()
        if self.task_queue_panel:
            self.task_queue_panel.update_styles(styles)
