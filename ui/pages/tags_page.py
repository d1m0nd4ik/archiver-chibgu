from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QMessageBox, QComboBox, QSizePolicy, QProgressBar,
)
from PySide6.QtCore import Qt, Slot

from core.database import Database
from core.nlp_processor import DEFAULT_TAG_DICTIONARY
from core.smart_tagger import SmartTagger
from ui.styles import (
    STYLES, get_theme_colors, get_section_title_style, get_table_stylesheet,
    get_page_header_style, get_page_hint_style, get_panel_frame_stylesheet,
    get_panel_filter_label_style, apply_theme_to_page, apply_panel_label_style,
)
from core.logging_config import logger
from core.task_queue import AppTaskQueue


class TagsPage(QWidget):
    CATEGORY_LABELS = {
        "personal": "Персональные",
        "group": "Групповые",
        "event": "Событийные",
    }

    def __init__(self, styles=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self.db = Database()
        self.smart_tagger = SmartTagger(self.db)
        self.smart_tagger.ensure_dictionary()
        self.init_ui()
        self.load_tags()
        AppTaskQueue.instance().task_finished.connect(self._on_queue_task_finished)
        AppTaskQueue.instance().progress_percent.connect(self._on_queue_percent)

    def _on_queue_percent(self, percent: int):
        if not self.retag_btn.isEnabled():
            self._show_progress(percent, "")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        c = get_theme_colors()
        self.header_label = QLabel("Тэги и словарь тегирования")
        self.header_label.setStyleSheet(get_page_header_style())
        layout.addWidget(self.header_label)

        self.summary_label = QLabel("Словарь: 0 записей")
        self.summary_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 14px; padding: 0 4px 8px 4px;"
        )
        layout.addWidget(self.summary_label)

        self.hint_label = QLabel(
            "Теги постов подбираются по активным записям словаря: если фраза из таблицы "
            "встречается в тексте — соответствующий хэштег добавляется в хранилище. "
            "Колонка «Родитель»: при совпадении подтипа автоматически добавляется родительский хэштег "
            "(иерархия событие → подтип)."
        )
        self.hint_label.setWordWrap(True)
        self.hint_label.setProperty('uiRole', 'hint')
        self.hint_label.setStyleSheet(get_page_hint_style())
        layout.addWidget(self.hint_label)

        self.retag_progress = QProgressBar()
        self.retag_progress.setRange(0, 100)
        self.retag_progress.setValue(0)
        self.retag_progress.setFormat("%p%")
        self.retag_progress.setTextVisible(True)
        self.retag_progress.setVisible(False)
        layout.addWidget(self.retag_progress)

        self.retag_status_label = QLabel("")
        self.retag_status_label.setWordWrap(True)
        self.retag_status_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
        layout.addWidget(self.retag_status_label)

        panel = QFrame()
        panel.setObjectName("tagsPanel")
        self.panel = panel
        body = QVBoxLayout(panel)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(10)

        filters = QHBoxLayout()
        filters.setSpacing(10)
        self.filter_label = QLabel("Категория:")
        self.category_filter = QComboBox()
        self.category_filter.addItem("Все", "")
        self.category_filter.addItem("Персональные", "personal")
        self.category_filter.addItem("Групповые", "group")
        self.category_filter.addItem("Событийные", "event")
        self.category_filter.setMinimumWidth(220)
        self.category_filter.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.category_filter.setMaxVisibleItems(12)
        self.category_filter.currentIndexChanged.connect(self.load_tags)
        self.category_filter.view().setMinimumWidth(260)
        filters.addWidget(self.filter_label)
        filters.addWidget(self.category_filter)
        filters.addStretch()
        body.addLayout(filters)

        self.tags_table = QTableWidget(0, 6)
        self.tags_table.setHorizontalHeaderLabels([
            "Категория", "Фраза", "Хэштег", "Родитель", "Вес", "Статус",
        ])
        self.tags_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tags_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tags_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.verticalHeader().setVisible(False)
        self.tags_table.horizontalHeader().setStretchLastSection(True)
        self.tags_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tags_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tags_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tags_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tags_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tags_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tags_table.setWordWrap(False)
        self.tags_table.setTextElideMode(Qt.ElideRight)
        self.tags_table.verticalHeader().setDefaultSectionSize(34)
        self.tags_table.setShowGrid(False)
        self.tags_table.setMinimumHeight(250)
        self.tags_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tags_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body.addWidget(self.tags_table, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.add_btn = QPushButton("Добавить")
        self.edit_btn = QPushButton("Редактировать")
        self.toggle_btn = QPushButton("Вкл/Выкл")
        self.del_btn = QPushButton("Удалить")
        self.seed_btn = QPushButton("Заполнить по умолчанию")
        self.retag_btn = QPushButton("Пересчитать теги архива")
        self.reload_btn = QPushButton("Обновить")
        self.add_btn.clicked.connect(self.add_tag)
        self.edit_btn.clicked.connect(self.edit_tag)
        self.toggle_btn.clicked.connect(self.toggle_tag_active)
        self.del_btn.clicked.connect(self.delete_tag)
        self.seed_btn.clicked.connect(self.seed_defaults)
        self.retag_btn.clicked.connect(self.retag_archive)
        self.reload_btn.clicked.connect(self.load_tags)
        for btn in (
            self.add_btn, self.edit_btn, self.toggle_btn, self.del_btn,
            self.seed_btn, self.retag_btn, self.reload_btn,
        ):
            btns.addWidget(btn)
        body.addLayout(btns)

        layout.addWidget(panel, 1)

        self._primary_buttons = [self.add_btn]
        self._secondary_buttons = [
            self.edit_btn, self.toggle_btn, self.del_btn, self.seed_btn,
            self.retag_btn, self.reload_btn,
        ]
        self._apply_widget_styles()

    def _apply_widget_styles(self):
        c = get_theme_colors()
        section_style = get_section_title_style()
        table_style = get_table_stylesheet()
        panel_style = get_panel_frame_stylesheet()

        self.setStyleSheet(f"background-color: {c['page_bg']};")
        self.header_label.setStyleSheet(get_page_header_style())
        self.summary_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 14px; padding: 0 0 4px 0;"
        )
        self.panel.setStyleSheet(panel_style)
        apply_panel_label_style(self.filter_label, get_panel_filter_label_style())
        self.tags_table.setStyleSheet(table_style)
        self.category_filter.setStyleSheet(self.styles.get("combo", self.styles["input"]))

        for btn in self._primary_buttons:
            btn.setStyleSheet(self.styles["button"])
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
        for btn in self._secondary_buttons:
            btn.setStyleSheet(self.styles["button_secondary"])
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.PointingHandCursor)

    @Slot(int, str)
    def _show_progress(self, percent: int, message: str = ""):
        pct = min(100, max(0, int(percent)))
        self.retag_progress.setVisible(True)
        self.retag_progress.setValue(pct)
        self.retag_progress.setFormat(f"{pct}%")
        if message:
            self.retag_status_label.setText(f"{pct}% — {message}")

    def _hide_progress(self):
        self.retag_progress.setValue(0)
        self.retag_progress.setVisible(False)
        self.retag_status_label.setText("")

    def _selected_row(self):
        row = self.tags_table.currentRow()
        if row < 0:
            return None
        item = self.tags_table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _set_table_row(self, row: int, entry: dict):
        category = self.CATEGORY_LABELS.get(entry.get("category", ""), entry.get("category", ""))
        status = "Активен" if entry.get("active") else "Выключен"
        parent = entry.get("parent_hashtag") or "—"
        values = [
            category, entry.get("phrase", ""), entry.get("hashtag", ""),
            parent, str(entry.get("weight", 0)), status,
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if col == 0:
                item.setData(Qt.UserRole, entry)
            self.tags_table.setItem(row, col, item)

    def load_tags(self):
        try:
            category = self.category_filter.currentData()
            self.db.normalize_tag_dictionary_hashtags()
            if not self.db.get_tag_dictionary(only_active=False):
                self.db.seed_default_tag_dictionary(DEFAULT_TAG_DICTIONARY)
            self.db.prune_tag_dictionary()
            self.smart_tagger.refresh()
            entries = self.db.get_tag_dictionary(category=category or None, only_active=False)
            self.tags_table.setRowCount(len(entries))
            for row, entry in enumerate(entries):
                self._set_table_row(row, entry)
            active = sum(1 for e in entries if e.get("active"))
            self.summary_label.setText(
                f"Словарь: {len(entries)} записей (активных: {active})"
            )
        except Exception as e:
            logger.error("load_tags: %s", e, exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить словарь:\n{e}")

    def _ask_parent_hashtag(self, current: str = "") -> str | None:
        tags = ["— без родителя —"] + self.db.get_dictionary_hashtags(only_active=False)
        initial = current or ""
        idx = 0
        if initial and initial in tags:
            idx = tags.index(initial)
        value, ok = QInputDialog.getItem(
            self,
            "Родительский тег",
            "Подтип → родитель (например #олимпиада → #событие):",
            tags,
            idx,
            True,
        )
        if not ok:
            return None
        if not value or value.startswith("—"):
            return ""
        return value.strip()

    def _ask_category(self, initial: str = "event") -> str | None:
        labels = ["personal", "group", "event"]
        pretty = [self.CATEGORY_LABELS[k] for k in labels]
        current = max(0, labels.index(initial)) if initial in labels else 0
        value, ok = QInputDialog.getItem(
            self, "Категория", "Выберите категорию:", pretty, current, False
        )
        if not ok:
            return None
        reverse = {v: k for k, v in self.CATEGORY_LABELS.items()}
        return reverse.get(value)

    def add_tag(self):
        category = self._ask_category("event")
        if not category:
            return
        phrase, ok = QInputDialog.getText(self, "Фраза", "Ключевая фраза:")
        if not ok or not phrase.strip():
            return
        hashtag, ok = QInputDialog.getText(self, "Хэштег", "Хэштег (#слово_слово):")
        if not ok or not hashtag.strip():
            return
        weight, ok = QInputDialog.getInt(self, "Вес", "Приоритет (1..1000):", 200, 1, 1000)
        if not ok:
            return
        parent = self._ask_parent_hashtag()
        if parent is None:
            return
        created = self.db.add_tag_dictionary_entry(
            category, phrase.strip(), hashtag.strip(), weight, True,
            parent_hashtag=parent or None,
        )
        if not created:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить запись.")
            return
        self.smart_tagger.refresh()
        self.load_tags()

    def edit_tag(self):
        entry = self._selected_row()
        if not entry:
            QMessageBox.information(self, "Выберите запись", "Сначала выберите строку в таблице.")
            return
        category = self._ask_category(entry.get("category", "event"))
        if not category:
            return
        phrase, ok = QInputDialog.getText(
            self, "Фраза", "Ключевая фраза:", text=entry.get("phrase", "")
        )
        if not ok or not phrase.strip():
            return
        hashtag, ok = QInputDialog.getText(
            self, "Хэштег", "Хэштег (#слово_слово):", text=entry.get("hashtag", "")
        )
        if not ok or not hashtag.strip():
            return
        weight, ok = QInputDialog.getInt(
            self, "Вес", "Приоритет (1..1000):", int(entry.get("weight", 100)), 1, 1000
        )
        if not ok:
            return
        parent = self._ask_parent_hashtag(entry.get("parent_hashtag") or "")
        if parent is None:
            return
        ok = self.db.update_tag_dictionary_entry(
            entry["id"], category, phrase.strip(), hashtag.strip(),
            int(weight), bool(entry.get("active", True)),
            parent_hashtag=parent or None,
        )
        if not ok:
            QMessageBox.warning(self, "Ошибка", "Не удалось обновить запись.")
            return
        self.smart_tagger.refresh()
        self.load_tags()

    def toggle_tag_active(self):
        entry = self._selected_row()
        if not entry:
            QMessageBox.information(self, "Выберите запись", "Сначала выберите строку в таблице.")
            return
        new_active = not bool(entry.get("active", True))
        ok = self.db.update_tag_dictionary_entry(
            entry["id"],
            entry.get("category", "event"),
            entry.get("phrase", ""),
            entry.get("hashtag", ""),
            int(entry.get("weight", 100)),
            new_active,
            parent_hashtag=entry.get("parent_hashtag"),
        )
        if ok:
            self.smart_tagger.refresh()
            self.load_tags()

    def delete_tag(self):
        entry = self._selected_row()
        if not entry:
            QMessageBox.information(self, "Выберите запись", "Сначала выберите строку в таблице.")
            return
        answer = QMessageBox.question(
            self,
            "Удалить запись",
            f"Удалить запись словаря:\n{entry.get('phrase')} -> {entry.get('hashtag')}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if self.db.delete_tag_dictionary_entry(entry["id"]):
            self.smart_tagger.refresh()
            self.load_tags()

    def seed_defaults(self):
        self.db.normalize_tag_dictionary_hashtags()
        inserted = self.db.seed_default_tag_dictionary(DEFAULT_TAG_DICTIONARY)
        self.smart_tagger.refresh()
        self.load_tags()
        QMessageBox.information(self, "Готово", f"Добавлено новых шаблонов: {inserted}")

    def retag_archive(self):
        answer = QMessageBox.question(
            self,
            "Пересчитать теги",
            "Пересчитать теги для всех постов в архиве?\n"
            "Будут подобраны хэштеги из активного словаря, обновлены хэштеги кафедр; "
            "преподаватель остаётся только в блоке автора.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._start_retag_worker()

    def _start_retag_worker(self):
        queue = AppTaskQueue.instance()
        if queue.is_busy():
            QMessageBox.information(
                self,
                "Очередь занята",
                "Дождитесь завершения текущей задачи или отмените её в Настройки → Фоновые задачи.",
            )
            return
        self._show_progress(0, "Задача добавлена в очередь…")
        self.retag_btn.setEnabled(False)
        queue.enqueue_retag()

    def _on_queue_task_finished(self, title: str, _ok: bool):
        if title != "Пересчёт тегов архива":
            return
        self._hide_progress()
        self.retag_btn.setEnabled(True)

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self._apply_widget_styles()
