"""Расширенный поиск по архиву с фильтрами и сортировкой."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QDialog, QSizePolicy, QInputDialog,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from core.database import Database
from core.post_search import PostSearchParams, SORT_OPTIONS
from core.post_importance import importance_label
from core.search_presets import list_presets, save_preset, load_preset, delete_preset
from core.thumb_cache import get_thumbnail_pixmap, resolve_media_preview_path
from ui.styles import (
    STYLES, apply_theme_to_page, get_theme_colors, get_page_header_style, get_page_hint_style,
    get_table_stylesheet, get_compact_input_stylesheet,
    get_compact_combo_stylesheet, get_compact_date_stylesheet,
    get_compact_button_stylesheet, get_panel_filter_label_style, apply_table_theme,
    apply_panel_label_style,
)
from ui.form_layout import FormGrid
from ui.button_effects import mark_compact_toolbar_button
from ui.ui_scale import UiScale
from ui.dialogs.post_edit_dialog import PostEditDialog


PAGE_SIZE = 100


class SearchPage(QWidget):
    def __init__(self, styles=None, on_archive_changed=None, on_open_in_storage=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self._on_archive_changed = on_archive_changed
        self._on_open_in_storage = on_open_in_storage
        self._results: list[dict] = []
        self._total_count = 0
        self._page_offset = 0
        self._filter_labels: list[QLabel] = []
        self._table_font = QFont()
        self.init_ui()

    def _make_filter_label(self, text: str, *, narrow: bool = False) -> QLabel:
        lbl = FormGrid.make_label(text, narrow=narrow)
        self._filter_labels.append(lbl)
        return lbl

    def init_ui(self):
        m = UiScale.px(20)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m, m, m, m)
        layout.setSpacing(UiScale.px(10))

        self.header_label = QLabel("Поиск в архиве")
        self.header_label.setStyleSheet(get_page_header_style())
        layout.addWidget(self.header_label)

        hint = QLabel(
            "FTS5 и фильтры · двойной щелчок по строке — редактирование"
        )
        hint.setProperty('uiRole', 'hint')
        hint.setStyleSheet(get_page_hint_style())
        self.hint_label = hint
        layout.addWidget(hint)

        self._input_style = get_compact_input_stylesheet()
        self._combo_style = get_compact_combo_stylesheet()
        self._date_style = get_compact_date_stylesheet()
        self._table_font.setPointSizeF(max(8.5, 10.0 * UiScale.factor()))

        filters_frame = QFrame()
        filters_frame.setObjectName("searchFilters")
        filters_frame.setStyleSheet(self.styles['frame'])
        self._filters_grid = QGridLayout(filters_frame)
        grid = self._filters_grid
        grid.setContentsMargins(UiScale.px(10), UiScale.px(8), UiScale.px(10), UiScale.px(8))
        FormGrid.setup_multi_field_grid(grid)

        row = 0
        grid.addWidget(self._make_filter_label("Запрос"), row, 0)
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Текст, #тег…")
        self.query_input.returnPressed.connect(self.run_search)
        grid.addWidget(self.query_input, row, 1, 1, 5)

        row += 1
        grid.addWidget(self._make_filter_label("Дата от"), row, 0)
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setSpecialValueText("—")
        self.date_from.setDate(QDate(2000, 1, 1))
        grid.addWidget(self.date_from, row, 1)
        grid.addWidget(self._make_filter_label("до", narrow=True), row, 2)
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        grid.addWidget(self.date_to, row, 3)
        grid.addWidget(self._make_filter_label("Тег"), row, 4)
        self.tag_combo = QComboBox()
        self.tag_combo.setProperty("comboAllowTyping", True)
        self.tag_combo.setEditable(True)
        self.tag_combo.setInsertPolicy(QComboBox.NoInsert)
        grid.addWidget(self.tag_combo, row, 5)

        row += 1
        grid.addWidget(self._make_filter_label("Кафедра"), row, 0)
        self.dept_combo = QComboBox()
        grid.addWidget(self.dept_combo, row, 1)
        grid.addWidget(self._make_filter_label("Автор"), row, 2)
        self.author_combo = QComboBox()
        grid.addWidget(self.author_combo, row, 3)
        grid.addWidget(self._make_filter_label("Медиа"), row, 4)
        self.media_combo = QComboBox()
        for label, val in [
            ("Любое", ""), ("Есть вложения", "any"), ("Без вложений", "none"),
            ("Фото", "photo"), ("Видео", "video"), ("Клип", "clip"),
        ]:
            self.media_combo.addItem(label, val)
        grid.addWidget(self.media_combo, row, 5)

        row += 1
        grid.addWidget(self._make_filter_label("Источник"), row, 0)
        self.source_combo = QComboBox()
        self.source_combo.addItem("Все", "")
        self.source_combo.addItem("ВКонтакте", "vk")
        self.source_combo.addItem("Ручные", "manual")
        grid.addWidget(self.source_combo, row, 1)
        grid.addWidget(self._make_filter_label("Сортировка"), row, 2)
        self.sort_combo = QComboBox()
        for key, label in SORT_OPTIONS.items():
            self.sort_combo.addItem(label, key)
        grid.addWidget(self.sort_combo, row, 3, 1, 3)

        row += 1
        grid.addWidget(self._make_filter_label("Пресет"), row, 0)
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        preset_row.addWidget(self.preset_combo, 1)
        self.load_preset_btn = QPushButton("Загрузить")
        self.save_preset_btn = QPushButton("Сохранить")
        self.del_preset_btn = QPushButton("Удалить")
        for b in (self.load_preset_btn, self.save_preset_btn, self.del_preset_btn):
            preset_row.addWidget(b)
        preset_wrap = QWidget()
        preset_wrap.setStyleSheet("background: transparent;")
        preset_wrap.setLayout(preset_row)
        grid.addWidget(preset_wrap, row, 1, 1, 5)
        self.load_preset_btn.clicked.connect(self._load_selected_preset)
        self.save_preset_btn.clicked.connect(self._save_current_preset)
        self.del_preset_btn.clicked.connect(self._delete_selected_preset)
        self._reload_presets_combo()

        self._compact_form_widgets = [
            self.query_input, self.date_from, self.date_to,
            self.tag_combo, self.dept_combo, self.author_combo,
            self.media_combo, self.source_combo, self.sort_combo, self.preset_combo,
        ]
        layout.addWidget(filters_frame)
        self._apply_field_styles()
        for w in self._compact_form_widgets:
            FormGrid.fix_field(w)
        FormGrid.sync_grid(grid, labels=self._filter_labels)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(UiScale.px(8))
        self.search_btn = QPushButton("Найти")
        self.search_btn.clicked.connect(self.run_search)
        btn_row.addWidget(self.search_btn)
        self.clear_btn = QPushButton("Сбросить")
        self.clear_btn.clicked.connect(self.clear_filters)
        btn_row.addWidget(self.clear_btn)
        self.open_storage_btn = QPushButton("Открыть в хранилище")
        self.open_storage_btn.clicked.connect(self._open_in_storage)
        btn_row.addWidget(self.open_storage_btn)
        self.prev_page_btn = QPushButton("← Назад")
        self.next_page_btn = QPushButton("Вперёд →")
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.next_page_btn.clicked.connect(self._next_page)
        btn_row.addWidget(self.prev_page_btn)
        btn_row.addWidget(self.next_page_btn)
        btn_row.addStretch()
        self.count_label = QLabel("")
        btn_row.addWidget(self.count_label)
        layout.addLayout(btn_row)
        self._apply_button_styles()

        self.results_table = QTableWidget(0, 12)
        self.results_table.setHorizontalHeaderLabels([
            "", "ID", "Дата", "Источник", "Автор", "Кафедра", "Текст", "Теги",
            "Медиа", "Лайки", "Коммент.", "Репосты",
        ])
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.verticalHeader().setDefaultSectionSize(UiScale.px(28))
        hdr = self.results_table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        self.results_table.setColumnWidth(0, UiScale.px(52))
        for col in (1, 2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.Stretch)
        hdr.setSectionResizeMode(7, QHeaderView.Fixed)
        self.results_table.setColumnWidth(7, UiScale.px(130))
        hdr.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        for col in (9, 10, 11):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.results_table.doubleClicked.connect(self._edit_selected_post)
        layout.addWidget(self.results_table, 1)
        self._apply_table_style()

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(UiScale.px(118))
        self.detail_text.setMaximumHeight(UiScale.px(140))
        self.detail_text.setPlaceholderText("Выберите строку — текст и пути к файлам…")
        layout.addWidget(self.detail_text)
        self._apply_detail_style()

        self.results_table.itemSelectionChanged.connect(self._show_selection_detail)

        self._secondary_buttons = [
            self.clear_btn, self.open_storage_btn,
            self.prev_page_btn, self.next_page_btn,
            self.load_preset_btn, self.save_preset_btn, self.del_preset_btn,
        ]
        self._apply_label_styles()
        self.reload_filter_lists()

    def _apply_field_styles(self):
        theme = getattr(STYLES, '_theme', None)
        self._input_style = get_compact_input_stylesheet(theme)
        self._combo_style = get_compact_combo_stylesheet(theme)
        self._date_style = get_compact_date_stylesheet(theme)
        self.query_input.setStyleSheet(self._input_style)
        for w in (
            self.tag_combo, self.dept_combo, self.author_combo,
            self.media_combo, self.source_combo, self.sort_combo, self.preset_combo,
        ):
            w.setStyleSheet(self._combo_style)
        from ui.date_field_effects import refresh_date_field

        for w in (self.date_from, self.date_to):
            w.setStyleSheet(self._date_style)
            FormGrid.fix_field(w)
            refresh_date_field(w)

    def _apply_button_styles(self):
        theme = getattr(STYLES, '_theme', None)
        c = get_theme_colors(theme)
        self._compact_toolbar_buttons = [
            self.search_btn, self.clear_btn, self.open_storage_btn,
            self.prev_page_btn, self.next_page_btn,
            self.load_preset_btn, self.save_preset_btn, self.del_preset_btn,
        ]
        mark_compact_toolbar_button(self.search_btn, primary=True)
        self.search_btn.setStyleSheet(get_compact_button_stylesheet(True, theme))
        for btn in self._compact_toolbar_buttons[1:]:
            mark_compact_toolbar_button(btn, primary=False)
            btn.setStyleSheet(get_compact_button_stylesheet(False, theme))
        self.count_label.setStyleSheet(
            f"color: {c['text_muted']}; font-size: {UiScale.font_small()}px;"
        )

    def _apply_table_style(self):
        apply_table_theme(self.results_table, compact=True)

    def _apply_detail_style(self):
        c = get_theme_colors()
        fs = UiScale.font_body()
        self.detail_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: 6px;
                font-size: {fs}px;
                padding: 6px 8px;
                line-height: 1.35;
            }}
        """)

    def _apply_label_styles(self):
        style = get_panel_filter_label_style()
        for lbl in self._filter_labels:
            apply_panel_label_style(lbl, style)

    def reload_filter_lists(self):
        db = Database()
        try:
            self.tag_combo.clear()
            self.tag_combo.addItem("— любой —", "")
            for tag in db.get_dictionary_hashtags(only_active=True):
                self.tag_combo.addItem(tag, tag)

            self.dept_combo.clear()
            self.dept_combo.addItem("— любая —", None)
            for d in db.get_departments():
                label = d['name']
                if d.get('hashtag'):
                    label += f" ({d['hashtag']})"
                self.dept_combo.addItem(label, d['id'])

            self.author_combo.clear()
            self.author_combo.addItem("— любой —", None)
            for e in db.list_employees_for_filter():
                label = e['full_name']
                if e.get('hashtag'):
                    label += f" {e['hashtag']}"
                self.author_combo.addItem(label, e['id'])
        finally:
            db.close()

    @staticmethod
    def _preview_text(raw: str | None, max_len: int) -> tuple[str, str]:
        """Однострочный фрагмент для ячейки и полный текст для подсказки."""
        full = " ".join((raw or "").replace("\n", " ").split())
        if not full:
            return "—", ""
        if len(full) <= max_len:
            return full, ""
        return full[: max_len - 1] + "…", full

    def _use_date_from(self) -> bool:
        return self.date_from.date() > QDate(2000, 1, 2)

    def build_params(self) -> PostSearchParams:
        tag = self.tag_combo.currentData()
        if tag is None and self.tag_combo.currentText().strip():
            tag = self.tag_combo.currentText().strip()

        date_from = None
        if self._use_date_from():
            d = self.date_from.date()
            date_from = f"{d.year():04d}-{d.month():02d}-{d.day():02d}"

        d_to = self.date_to.date()
        date_to = f"{d_to.year():04d}-{d_to.month():02d}-{d_to.day():02d}"

        return PostSearchParams(
            query=self.query_input.text().strip(),
            date_from=date_from,
            date_to=date_to,
            tag_hashtag=tag or None,
            department_id=self.dept_combo.currentData(),
            author_employee_id=self.author_combo.currentData(),
            media_type=self.media_combo.currentData() or None,
            post_source=self.source_combo.currentData() or None,
            sort=self.sort_combo.currentData() or 'date_desc',
            limit=PAGE_SIZE,
            offset=self._page_offset,
        )

    def run_search(self, *, reset_page: bool = True):
        if reset_page:
            self._page_offset = 0
        params = self.build_params()
        db = Database()
        try:
            self._total_count = db.count_posts_filtered(params)
            self._results = db.search_posts_filtered(params)
        finally:
            db.close()

        self.results_table.setRowCount(len(self._results))
        for row, post in enumerate(self._results):
            src = "ВК" if post.get('post_source') == 'vk' else (post.get('source_label') or "Ручной")
            media = post.get('media_types') or ''
            media_short = media.replace(',', ', ')[:28] if media else "—"
            author = post.get('author_name') or post.get('teacher_hashtag') or "—"
            if len(author) > 22:
                author = author[:20] + "…"
            dept_raw = post.get('department_name') or post.get('department_hashtag')
            dept, dept_tip = self._preview_text(dept_raw, 36)
            text_cell, text_tip = self._preview_text(post.get('text'), 200)
            tags_cell, tags_tip = self._preview_text(post.get('tags'), 42)
            paths = [p.strip() for p in (post.get('media_paths') or '').split(',') if p.strip()]
            types = [t.strip() for t in (post.get('media_types') or '').split(',') if t.strip()]
            thumb_path = ""
            for mtype, mpath in zip(types, paths):
                preview = resolve_media_preview_path(mpath, mtype)
                if preview:
                    thumb_path = preview
                    break
            if thumb_path:
                lbl = QLabel()
                pm = get_thumbnail_pixmap(thumb_path, (44, 44))
                if pm:
                    lbl.setPixmap(pm)
                    lbl.setAlignment(Qt.AlignCenter)
                    self.results_table.setCellWidget(row, 0, lbl)
            values = [
                str(post['original_post_id']),
                (post.get('date') or '')[:16],
                src[:12],
                author,
                dept,
                text_cell,
                tags_cell,
                media_short,
                str(post.get('likes', 0)),
                str(post.get('comments', 0)),
                str(post.get('shares', 0)),
            ]
            tooltips = {5: dept_tip, 6: text_tip, 7: tags_tip}
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setFont(self._table_font)
                item.setData(Qt.UserRole, post)
                table_col = col + 1
                if table_col in (1, 2, 3, 9, 10, 11):
                    item.setTextAlignment(Qt.AlignCenter)
                tip = tooltips.get(col + 1)
                if tip:
                    item.setToolTip(tip)
                self.results_table.setItem(row, table_col, item)

        self.results_table.setColumnWidth(7, UiScale.px(130))
        shown_from = self._page_offset + 1 if self._results else 0
        shown_to = self._page_offset + len(self._results)
        self.count_label.setText(
            f"Показано {shown_from}–{shown_to} из {self._total_count}"
            if self._total_count else "Ничего не найдено"
        )
        self.prev_page_btn.setEnabled(self._page_offset > 0)
        self.next_page_btn.setEnabled(
            self._page_offset + len(self._results) < self._total_count
        )
        self.detail_text.clear()
        if not self._results:
            self.detail_text.setPlainText("Ничего не найдено.")

    def clear_filters(self):
        self.query_input.clear()
        self.date_from.setDate(QDate(2000, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.tag_combo.setCurrentIndex(0)
        self.dept_combo.setCurrentIndex(0)
        self.author_combo.setCurrentIndex(0)
        self.media_combo.setCurrentIndex(0)
        self.source_combo.setCurrentIndex(0)
        self.sort_combo.setCurrentIndex(0)
        self.results_table.setRowCount(0)
        self.detail_text.clear()
        self.count_label.setText("")
        self._results = []
        self._total_count = 0
        self._page_offset = 0

    def _prev_page(self):
        if self._page_offset >= PAGE_SIZE:
            self._page_offset -= PAGE_SIZE
            self.run_search(reset_page=False)

    def _next_page(self):
        if self._page_offset + PAGE_SIZE < self._total_count:
            self._page_offset += PAGE_SIZE
            self.run_search(reset_page=False)

    def _open_in_storage(self):
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self._results):
            QMessageBox.information(self, "Выбор", "Выберите строку в таблице.")
            return
        post_id = self._results[row]['original_post_id']
        if self._on_open_in_storage:
            self._on_open_in_storage(post_id)

    def _reload_presets_combo(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("— выберите пресет —", "")
        for p in list_presets():
            self.preset_combo.addItem(p.get("name", ""), p.get("name"))
        self.preset_combo.blockSignals(False)

    def _load_selected_preset(self):
        name = self.preset_combo.currentData()
        if not name:
            return
        params = load_preset(name)
        if not params:
            return
        self.query_input.setText(params.query)
        if params.date_from:
            parts = params.date_from.split("-")
            if len(parts) >= 3:
                self.date_from.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        if params.date_to:
            parts = params.date_to.split("-")
            if len(parts) >= 3:
                self.date_to.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        self.run_search()

    def _save_current_preset(self):
        name, ok = QInputDialog.getText(self, "Сохранить пресет", "Название:")
        if ok and name.strip():
            save_preset(name.strip(), self.build_params())
            self._reload_presets_combo()

    def _delete_selected_preset(self):
        name = self.preset_combo.currentData()
        if name:
            delete_preset(name)
            self._reload_presets_combo()

    def _show_selection_detail(self):
        row = self.results_table.currentRow()
        if row < 0 or row >= len(self._results):
            return
        post = self._results[row]
        lines = [
            f"ID {post['original_post_id']} · {post.get('date', '')} · "
            f"{importance_label(post.get('importance'))}",
            f"Автор: {post.get('author_name') or '—'} · "
            f"Кафедра: {post.get('department_name') or '—'}",
            f"Лайки: {post.get('likes')} · Коммент.: {post.get('comments')} · "
            f"Репосты: {post.get('shares')}",
            f"Теги: {(post.get('tags') or '—')[:120]}",
            "",
            (post.get('text') or '')[:1200],
        ]
        paths = (post.get('media_paths') or '').split(',')
        types = (post.get('media_types') or '').split(',')
        if paths and paths[0]:
            lines.append("")
            for mtype, mpath in zip(types, paths):
                mpath = (mpath or '').strip()
                if not mpath:
                    continue
                mark = "есть" if os.path.isfile(mpath) else "нет"
                name = os.path.basename(mpath)
                lines.append(f"  {mark} [{mtype}] {name}")
        self.detail_text.setPlainText("\n".join(lines))

    def _edit_selected_post(self):
        row = self.results_table.currentRow()
        if row < 0:
            return
        post = self._results[row]
        db = Database()
        full = db.get_post_by_original_id(post['original_post_id'])
        db.close()
        if not full:
            QMessageBox.warning(self, "Ошибка", "Пост не найден в базе.")
            return
        dlg = PostEditDialog(full, self, styles=self.styles)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.was_saved():
            if self._on_archive_changed:
                self._on_archive_changed()
            self.run_search()

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self._apply_field_styles()
        self._apply_button_styles()
        for w in self._compact_form_widgets:
            FormGrid.fix_field(w)
        self._apply_table_style()
        self._apply_detail_style()
        self._apply_label_styles()
