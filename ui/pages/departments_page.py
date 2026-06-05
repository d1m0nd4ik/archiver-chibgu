from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QInputDialog, QMessageBox, QTextEdit, QProgressBar, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from core.database import Database
from core.employee_tagger import sync_departments_to_db, make_department_hashtag, normalize_name
from core.name_normalizer import normalize_and_reorder
from ui.styles import (
    STYLES,
    get_theme_colors,
    get_section_title_style,
    get_table_stylesheet,
    get_panel_frame_stylesheet,
    apply_table_theme,
    scale_stylesheet,
)
from ui.ui_scale import UiScale
from core.logging_config import logger
from core.task_queue import AppTaskQueue


class SyncThread(QThread):
    progress = Signal(str)
    finished_signal = Signal(dict)

    def __init__(self, urls=None, parent=None):
        super().__init__(parent)
        self.urls = urls
        self._is_running = True

    def run(self):
        try:
            def cb(msg):
                self.progress.emit(str(msg))

            result = sync_departments_to_db(extra_urls=self.urls, progress_callback=cb)
            self.finished_signal.emit(result)
        except Exception as e:
            logger.error('SyncThread error: %s', e, exc_info=True)
            self.finished_signal.emit({'success': False, 'error': str(e)})


class DepartmentsPage(QWidget):
    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.db = Database()
        self.sync_thread = None
        self._counter_timer = QTimer(self)
        self._counter_timer.setSingleShot(True)
        self._counter_timer.setInterval(100)
        self._counter_timer.timeout.connect(self._update_counters)
        self.init_ui()
        self.load_departments()
        q = AppTaskQueue.instance()
        q.log_line.connect(self.append_log)
        q.task_result.connect(self._on_queue_task_result)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*UiScale.page_margins())
        layout.setSpacing(UiScale.px(20))

        from ui.styles import get_page_header_style
        c = get_theme_colors()
        self.header_label = QLabel('Кафедры и преподаватели')
        self.header_label.setStyleSheet(get_page_header_style())
        layout.addWidget(self.header_label)

        self.summary_label = QLabel('Всего: 0 кафедр, 0 преподавателей')
        self.summary_label.setStyleSheet(
            scale_stylesheet(
                f"color: {c['text_muted']}; font-size: 14px; padding: 0 4px 8px 4px;"
            )
        )
        layout.addWidget(self.summary_label)

        self._compact = UiScale.is_compact()
        if self._compact:
            content = QVBoxLayout()
        else:
            content = QHBoxLayout()
        content.setSpacing(UiScale.px(16))
        content.setAlignment(Qt.AlignTop)

        self.left_panel = QFrame()
        self.left_panel.setObjectName('deptPanel')
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(*UiScale.panel_margins())
        left_layout.setSpacing(UiScale.px(10))
        self.dept_header_label = QLabel('Кафедры (0)')
        left_layout.addWidget(self.dept_header_label, 0, Qt.AlignTop)
        self.dept_table = self._create_data_table(['Кафедра', 'Хэштег'])
        self.dept_table.itemSelectionChanged.connect(self.on_department_selected)
        left_layout.addWidget(self.dept_table, 1)
        dept_btns = QHBoxLayout()
        dept_btns.setSpacing(8)
        self.add_dept_btn = QPushButton('Добавить')
        self.edit_dept_btn = QPushButton('Редактировать')
        self.del_dept_btn = QPushButton('Удалить')
        self.add_dept_btn.clicked.connect(self.add_department)
        self.edit_dept_btn.clicked.connect(self.edit_department)
        self.del_dept_btn.clicked.connect(self.delete_department)
        for btn in (self.add_dept_btn, self.edit_dept_btn, self.del_dept_btn):
            dept_btns.addWidget(btn, 1)
        left_layout.addLayout(dept_btns)
        self.left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.addWidget(self.left_panel, 1)

        self.right_panel = QFrame()
        self.right_panel.setObjectName('teacherPanel')
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(*UiScale.panel_margins())
        right_layout.setSpacing(UiScale.px(10))
        self.teacher_header_label = QLabel('Преподаватели (выберите кафедру слева)')
        self.teacher_header_label.setWordWrap(True)
        self.teacher_header_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.teacher_header_label.setMinimumHeight(UiScale.px(40))
        self.teacher_header_label.setMaximumHeight(UiScale.px(56))
        self.teacher_header_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(self.teacher_header_label, 0, Qt.AlignTop)
        self.teacher_table = self._create_data_table(['Преподаватель', 'Хэштег'])
        right_layout.addWidget(self.teacher_table, 1)
        teacher_btns = QHBoxLayout()
        teacher_btns.setSpacing(8)
        self.add_teacher_btn = QPushButton('Добавить')
        self.edit_teacher_btn = QPushButton('Изменить хэштег')
        self.del_teacher_btn = QPushButton('Удалить')
        self.add_teacher_btn.clicked.connect(self.add_teacher)
        self.edit_teacher_btn.clicked.connect(self.edit_teacher_hashtag)
        self.del_teacher_btn.clicked.connect(self.delete_teacher)
        for btn in (self.add_teacher_btn, self.edit_teacher_btn, self.del_teacher_btn):
            teacher_btns.addWidget(btn, 1)
        right_layout.addLayout(teacher_btns)

        self.sync_btn = QPushButton('Синхронизировать кафедры')
        self.sync_btn.clicked.connect(self.start_sync)
        right_layout.addWidget(self.sync_btn)
        self.dept_report_btn = QPushButton('Отчёт Word по кафедре (период)')
        self.dept_report_btn.clicked.connect(self.export_dept_report)
        right_layout.addWidget(self.dept_report_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(UiScale.px(26))
        right_layout.addWidget(self.progress)

        self.log_label = QLabel('Лог синхронизации')
        right_layout.addWidget(self.log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_h = UiScale.px(100) if self._compact else UiScale.px(120)
        self.log_text.setMinimumHeight(log_h)
        self.log_text.setMaximumHeight(log_h)
        right_layout.addWidget(self.log_text)

        self.right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content.addWidget(self.right_panel, 1)

        layout.addLayout(content, 1)

        self._primary_buttons = [self.add_dept_btn, self.add_teacher_btn]
        self._secondary_buttons = [
            self.edit_dept_btn, self.del_dept_btn,
            self.edit_teacher_btn, self.del_teacher_btn, self.sync_btn,
            self.dept_report_btn,
        ]
        self._section_labels = [
            self.dept_header_label, self.teacher_header_label, self.log_label,
        ]
        self._apply_widget_styles()

    def _apply_widget_styles(self):
        theme = STYLES._theme
        c = get_theme_colors(theme)
        section_style = get_section_title_style(theme)
        table_style = get_table_stylesheet(theme)
        panel_qss = get_panel_frame_stylesheet(theme)

        self.setStyleSheet(f"background-color: {c['page_bg']};")
        from ui.styles import get_page_header_style
        self.header_label.setStyleSheet(get_page_header_style(theme))
        self.summary_label.setStyleSheet(
            scale_stylesheet(
                f"color: {c['text_muted']}; font-size: 14px; padding: 0 0 4px 0;"
            )
        )
        for panel in (self.left_panel, self.right_panel):
            panel.setStyleSheet(panel_qss)
        for label in self._section_labels:
            label.setStyleSheet(section_style)

        for table in (self.dept_table, self.teacher_table):
            table.setStyleSheet(table_style)
            apply_table_theme(table, theme)
        self.log_text.setStyleSheet(self.styles['textedit'])
        self.progress.setStyleSheet(self.styles['progressbar'])

        btn_h = UiScale.px(40)
        for btn in self._primary_buttons:
            btn.setStyleSheet(self.styles['button'])
            btn.setMinimumHeight(btn_h)
            btn.setCursor(Qt.PointingHandCursor)
        for btn in self._secondary_buttons:
            btn.setStyleSheet(self.styles['button_secondary'])
            btn.setMinimumHeight(btn_h)
            btn.setCursor(Qt.PointingHandCursor)

    @staticmethod
    def _create_data_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.verticalHeader().setDefaultSectionSize(UiScale.px(34))
        table.horizontalHeader().setMinimumHeight(UiScale.px(36))
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.setShowGrid(False)
        table.setMinimumHeight(UiScale.px(160) if UiScale.is_compact() else UiScale.px(200))
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return table

    @staticmethod
    def _set_table_row(table: QTableWidget, row: int, values: list[str]) -> None:
        for col, value in enumerate(values):
            text = value or ''
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item.setToolTip(text)
            table.setItem(row, col, item)

    def _selected_department_name(self) -> str | None:
        row = self.dept_table.currentRow()
        if row < 0:
            return None
        item = self.dept_table.item(row, 0)
        return item.text().strip() if item else None

    def _selected_teacher_name(self) -> str | None:
        row = self.teacher_table.currentRow()
        if row < 0:
            return None
        item = self.teacher_table.item(row, 0)
        return item.text().strip() if item else None

    def _schedule_counter_update(self):
        self._counter_timer.start()

    def _update_counters(self):
        try:
            depts = self.db.get_departments() or []
            dept_count = len(depts)
            employees = self.db.get_all_employee_details() or []
            total_teachers = len(employees)

            self.dept_header_label.setText(
                f'Кафедра (1)' if dept_count == 1 else f'Кафедры ({dept_count})'
            )
            self.summary_label.setText(
                f'Всего: {dept_count} {self._noun(dept_count, "кафедра", "кафедры", "кафедр")}, '
                f'{total_teachers} {self._noun(total_teachers, "преподаватель", "преподавателя", "преподавателей")}'
            )

            name = self._selected_department_name()
            if name:
                dept = self.db.get_department_by_name(name)
                if dept:
                    dept_teachers = len(self.db.get_employees_by_department_id(dept['id']) or [])
                    title = f'Преподаватели — {name} ({dept_teachers})'
                    self.teacher_header_label.setText(title)
                    self.teacher_header_label.setToolTip(title)
                    return
            fallback = f'Преподаватели (всего {total_teachers}, выберите кафедру слева)'
            self.teacher_header_label.setText(fallback)
            self.teacher_header_label.setToolTip(fallback)
        except Exception as e:
            logger.error('Update counters: %s', e, exc_info=True)

    @staticmethod
    def _noun(count: int, one: str, few: str, many: str) -> str:
        n = abs(count) % 100
        if 11 <= n <= 14:
            return many
        n = n % 10
        if n == 1:
            return one
        if 2 <= n <= 4:
            return few
        return many

    def load_departments(self):
        try:
            current_row = self.dept_table.currentRow()
            depts = self.db.get_departments() or []
            self.dept_table.setRowCount(len(depts))
            for row, d in enumerate(depts):
                self._set_table_row(
                    self.dept_table, row,
                    [d.get('name') or '', d.get('hashtag') or ''],
                )
            if depts and current_row >= 0:
                self.dept_table.setCurrentCell(min(current_row, len(depts) - 1), 0)
            elif depts:
                self.dept_table.setCurrentCell(0, 0)
            self.on_department_selected()
            self._schedule_counter_update()
        except Exception as e:
            logger.error('Load departments: %s', e, exc_info=True)

    def on_department_selected(self):
        try:
            name = self._selected_department_name()
            if not name:
                self.teacher_table.setRowCount(0)
                self._schedule_counter_update()
                return
            dept = self.db.get_department_by_name(name)
            if not dept:
                return
            employees = self.db.get_employees_by_department_id(dept['id']) or []
            self.teacher_table.setRowCount(len(employees))
            for row, emp in enumerate(employees):
                self._set_table_row(
                    self.teacher_table, row,
                    [emp.get('full_name') or '', emp.get('hashtag') or ''],
                )
            self._schedule_counter_update()
        except Exception as e:
            logger.error('Department select: %s', e, exc_info=True)

    def export_dept_report(self):
        name = self._selected_department_name()
        if not name:
            QMessageBox.information(
                self, 'Кафедра', 'Выберите кафедру в таблице слева.'
            )
            return
        dept = self.db.get_department_by_name(name)
        if not dept:
            return
        d_from, ok1 = QInputDialog.getText(
            self, 'Период', 'Дата от (ГГГГ-ММ-ДД):', text='2025-01-01'
        )
        d_to, ok2 = QInputDialog.getText(
            self, 'Период', 'Дата до (ГГГГ-ММ-ДД):', text='2025-12-31'
        )
        if not (ok1 and ok2 and d_from.strip() and d_to.strip()):
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            'Сохранить отчёт',
            f"report_{dept['id']}.docx",
            'Word (*.docx)',
        )
        if not path:
            return
        from core.department_report import export_department_report

        ok, msg = export_department_report(
            dept['id'], d_from.strip(), d_to.strip(), path, self.db
        )
        if ok:
            QMessageBox.information(self, 'Отчёт', f'Сохранено:\n{msg}')
        else:
            QMessageBox.warning(self, 'Ошибка', msg)

    def add_department(self):
        name, ok = QInputDialog.getText(self, 'Добавить кафедру', 'Название кафедры:')
        if not ok or not name.strip():
            return
        name = normalize_name(name.strip())
        hashtag = make_department_hashtag(name, {d['hashtag'] for d in self.db.get_departments() if d.get('hashtag')})
        self.db.upsert_department(name, hashtag=hashtag)
        self.load_departments()

    def edit_department(self):
        name = self._selected_department_name()
        if not name:
            QMessageBox.information(self, 'Выберите кафедру', 'Сначала выберите кафедру в таблице слева.')
            return
        dept = self.db.get_department_by_name(name)
        if not dept:
            return
        new_hashtag, ok = QInputDialog.getText(self, 'Редактировать хэштег', 'Хэштег кафедры:', text=dept.get('hashtag') or '')
        if not ok:
            return
        new_hashtag = new_hashtag.strip()
        if not new_hashtag:
            QMessageBox.warning(self, 'Пустой хэштег', 'Хэштег не может быть пустым.')
            return
        # upsert_department updates hashtag when name exists
        self.db.upsert_department(dept.get('name'), hashtag=new_hashtag, url=dept.get('url'))
        self.load_departments()

    def delete_department(self):
        name = self._selected_department_name()
        if not name:
            QMessageBox.information(self, 'Выберите кафедру', 'Сначала выберите кафедру в таблице слева.')
            return
        dept = self.db.get_department_by_name(name)
        if not dept:
            return
        ok = QMessageBox.question(self, 'Удалить кафедру', f"Удалить кафедру '{name}' и всех связанных преподавателей?", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        self.db.delete_department(dept['id'])
        self.load_departments()
        self.teacher_table.setRowCount(0)
        self._schedule_counter_update()

    def add_teacher(self):
        name = self._selected_department_name()
        if not name:
            QMessageBox.information(self, 'Выберите кафедру', 'Сначала выберите кафедру в таблице слева.')
            return
        dept = self.db.get_department_by_name(name)
        if not dept:
            return
        full_name, ok = QInputDialog.getText(self, 'Добавить преподавателя', 'ФИО преподавателя:')
        if not ok or not full_name.strip():
            return
        full_name = normalize_and_reorder(full_name.strip())
        hashtag, ok2 = QInputDialog.getText(self, 'Хэштег (необязательно)', 'Хэштег преподавателя (например #Ivanov_I):')
        if ok2 and hashtag.strip():
            hashtag = hashtag.strip()
        else:
            hashtag = None
        self.db.upsert_employee(full_name=full_name, normalized_name=full_name.lower().replace('ё','е'), hashtag=hashtag, department_id=dept['id'])
        self.on_department_selected()

    def edit_teacher_hashtag(self):
        full_name = self._selected_teacher_name()
        if not full_name:
            QMessageBox.information(self, 'Выберите преподавателя', 'Сначала выберите преподавателя в таблице справа.')
            return
        dept_name = self._selected_department_name()
        if not dept_name:
            return
        dept = self.db.get_department_by_name(dept_name)
        employees = self.db.get_employees_by_department_id(dept['id'])
        emp = next((e for e in employees if e.get('full_name') == full_name), None)
        if not emp:
            return
        new_tag, ok = QInputDialog.getText(self, 'Редактировать хэштег', 'Хэштег преподавателя:', text=emp.get('hashtag') or '')
        if not ok:
            return
        new_tag = new_tag.strip()
        if not new_tag:
            QMessageBox.warning(self, 'Пустой хэштег', 'Хэштег не может быть пустым.')
            return
        self.db.update_employee_hashtag(emp['id'], new_tag)
        self.on_department_selected()

    def delete_teacher(self):
        full_name = self._selected_teacher_name()
        if not full_name:
            QMessageBox.information(self, 'Выберите преподавателя', 'Сначала выберите преподавателя в таблице справа.')
            return
        dept_name = self._selected_department_name()
        if not dept_name:
            return
        dept = self.db.get_department_by_name(dept_name)
        employees = self.db.get_employees_by_department_id(dept['id'])
        emp = next((e for e in employees if e.get('full_name') == full_name), None)
        if not emp:
            return
        ok = QMessageBox.question(self, 'Удалить преподавателя', f"Удалить '{full_name}'?", QMessageBox.Yes | QMessageBox.No)
        if ok != QMessageBox.Yes:
            return
        self.db.delete_employee(emp['id'])
        self.on_department_selected()

    def start_sync(self):
        queue = AppTaskQueue.instance()
        if queue.is_busy():
            QMessageBox.information(
                self, 'Синхронизация',
                'Дождитесь завершения текущей задачи или отмените её в Настройки → Фоновые задачи.',
            )
            return
        urls_text, ok = QInputDialog.getText(
            self, 'Список URL (необязательно)',
            'Введите node-URL через запятую (оставьте пустым для автоматического обнаружения):',
        )
        if not ok:
            return
        urls = None
        if urls_text.strip():
            urls = [u.strip() for u in urls_text.split(',') if u.strip()]
        self.progress.setVisible(True)
        self.log_text.clear()
        queue.enqueue_dept_sync(urls=urls)

    def _on_queue_task_result(self, title: str, result):
        if title == 'Синхронизация кафедр':
            self.on_sync_finished(result)

    def append_log(self, msg: str):
        self.log_text.append(str(msg))
        if AppTaskQueue.instance().is_busy():
            self._schedule_counter_update()

    def on_sync_finished(self, result: dict, *, show_dialog: bool | None = None):
        if show_dialog is None:
            main = self.window()
            show_dialog = not getattr(main, '_scheduler_silent', False)
        try:
            self.progress.setVisible(False)
            if result.get('success'):
                summary = (
                    f"Кафедр: {result.get('departments', '—')}, "
                    f"преподавателей: {result.get('employees', '—')}."
                )
                if result.get('dept_errors'):
                    summary += f"\nОшибок при загрузке кафедр: {result['dept_errors']}."
                if not result.get('college_synced'):
                    summary += "\nКолледж не загружен — см. лог."
                if show_dialog:
                    QMessageBox.information(
                        self, 'Синхронизация', 'Синхронизация завершена.\n' + summary,
                    )
            else:
                if show_dialog:
                    QMessageBox.warning(
                        self, 'Синхронизация',
                        'Ошибка при синхронизации: ' + str(result.get('error') or 'Неизвестная ошибка')
                        + '\n\nПодробности — в логе ниже.',
                    )
            self.load_departments()
        except Exception as e:
            logger.error('Sync finished handling error: %s', e, exc_info=True)

    def log(self, message: str):
        self.log_text.append(str(message))

    def update_styles(self, styles):
        self.styles = styles
        from ui.styles import apply_theme_to_page
        apply_theme_to_page(self, styles)
        self._apply_widget_styles()