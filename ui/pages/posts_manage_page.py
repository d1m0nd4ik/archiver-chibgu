"""Управление постами архива: просмотр, фильтры, редактирование, удаление."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QLineEdit, QMessageBox, QDialog, QInputDialog,
)
from PySide6.QtCore import Qt

from core.database import Database
from core.manual_sources import load_manual_source_labels
from core.post_importance import (
    importance_filter_choices,
    importance_color,
    importance_label,
)
from PySide6.QtGui import QColor
from core.logging_config import logger
from ui.dialogs.post_edit_dialog import PostEditDialog
from ui.styles import (
    STYLES, get_theme_colors, get_table_stylesheet,
    get_page_header_style, get_page_hint_style, apply_theme_to_page,
)


class PostsManagePage(QWidget):
    def __init__(self, styles=None, on_changed=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self._on_changed = on_changed
        self._rows: list[dict] = []
        self.init_ui()
        self.reload_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        c = get_theme_colors()
        self.header_label = QLabel("Управление постами")
        self.header_label.setStyleSheet(get_page_header_style())
        layout.addWidget(self.header_label)

        hint = QLabel(
            "Актуальность считается по дате поста (зелёный — свежий, красный — старше года). "
            "Пересчёт тегов по словарю — на вкладке «Тэги»."
        )
        hint.setWordWrap(True)
        hint.setProperty('uiRole', 'hint')
        hint.setStyleSheet(get_page_hint_style())
        self.hint_label = hint
        layout.addWidget(hint)

        legend = QLabel(
            "🟢 меньше месяца  ·  🟡 больше 3 месяцев  ·  🟠 больше полугода  ·  🔴 больше года"
        )
        legend.setStyleSheet(f"color: {get_theme_colors()['text_muted']}; font-size: 11px;")
        layout.addWidget(legend)

        filters = QFrame()
        filters.setStyleSheet(self.styles['frame'])
        f_layout = QHBoxLayout(filters)
        f_layout.setContentsMargins(14, 12, 14, 12)
        f_layout.setSpacing(12)

        f_layout.addWidget(QLabel("Источник:"))
        self.source_filter = QComboBox()
        self.source_filter.addItem("Все", "")
        self.source_filter.addItem("ВКонтакте", "vk")
        self.source_filter.addItem("Ручные", "manual")
        self.source_filter.setMinimumWidth(140)
        f_layout.addWidget(self.source_filter)

        f_layout.addWidget(QLabel("Давность:"))
        self.importance_filter = QComboBox()
        for level, label in importance_filter_choices():
            self.importance_filter.addItem(label, level)
        self.importance_filter.setMinimumWidth(220)
        f_layout.addWidget(self.importance_filter)

        f_layout.addWidget(QLabel("Поиск:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Текст, теги, источник…")
        self.search_input.setStyleSheet(self.styles['input'])
        self.search_input.setMinimumHeight(36)
        f_layout.addWidget(self.search_input, 1)

        self.apply_filter_btn = QPushButton("Применить")
        self.apply_filter_btn.setStyleSheet(self.styles['button_secondary'])
        self.apply_filter_btn.clicked.connect(self.reload_table)
        f_layout.addWidget(self.apply_filter_btn)

        layout.addWidget(filters)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Источник", "Давность в архиве", "Текст", "Теги", "Тип",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(320)
        layout.addWidget(self.table, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.setAlignment(Qt.AlignVCenter)
        self.edit_btn = QPushButton("Редактировать")
        self.delete_btn = QPushButton("Удалить")
        self.source_btn = QPushButton("Сменить источник")
        self.reload_btn = QPushButton("Обновить")
        for btn in (self.edit_btn, self.delete_btn, self.source_btn, self.reload_btn):
            btn.setFixedHeight(40)
            btns.addWidget(btn, 0, Qt.AlignVCenter)
        btns.addStretch()
        layout.addLayout(btns)

        self.edit_btn.clicked.connect(self.edit_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.source_btn.clicked.connect(self.change_source_selected)
        self.reload_btn.clicked.connect(self.reload_table)
        self.search_input.returnPressed.connect(self.reload_table)

        self._primary_buttons = [self.edit_btn]
        self._secondary_buttons = [
            self.delete_btn, self.source_btn,
            self.reload_btn, self.apply_filter_btn,
        ]
        self._apply_styles()

    def _apply_styles(self):
        c = get_theme_colors()
        self.setStyleSheet(f"background-color: {c['page_bg']};")
        if self.header_label:
            self.header_label.setStyleSheet(
                f"color: {c['text']}; font-size: 22px; font-weight: bold; padding: 10px 0;"
            )
        self.table.setStyleSheet(get_table_stylesheet())
        for w in (self.source_filter, self.importance_filter):
            w.setStyleSheet(self.styles.get('combo', self.styles['input']))
        for btn in self._primary_buttons:
            btn.setStyleSheet(self.styles['button'])
            btn.setCursor(Qt.PointingHandCursor)
        for btn in self._secondary_buttons:
            btn.setStyleSheet(self.styles['button_secondary'])
            btn.setCursor(Qt.PointingHandCursor)

    def _selected_post(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return None
        return self._rows[row]

    def _selected_posts(self) -> list[dict]:
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        return [self._rows[r] for r in rows if 0 <= r < len(self._rows)]

    def reload_table(self):
        try:
            db = Database()
            db.recalculate_posts_importance()
            self._rows = db.list_posts_admin(
                source=self.source_filter.currentData() or None,
                importance=self.importance_filter.currentData(),
                search=self.search_input.text().strip(),
                limit=1000,
            )
            db.close()
            self.table.setRowCount(len(self._rows))
            for row_idx, post in enumerate(self._rows):
                oid = post['original_post_id']
                src = post.get('source_label') or ''
                if post.get('post_source') == 'vk':
                    src = "ВКонтакте"
                preview = (post.get('text') or '')[:80]
                if len(post.get('text') or '') > 80:
                    preview += "…"
                values = [
                    str(oid),
                    post.get('date', ''),
                    src,
                    importance_label(post.get('importance')),
                    preview,
                    (post.get('tags') or '')[:60],
                    "Ручной" if post.get('post_source') == 'manual' else "ВК",
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    item.setData(Qt.UserRole, oid)
                    if col == 3:
                        level = int(post.get('importance') or 0)
                        item.setForeground(QColor(importance_color(level)))
                    self.table.setItem(row_idx, col, item)
        except Exception as e:
            logger.error("reload_table: %s", e, exc_info=True)
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить список:\n{e}")

    def edit_selected(self):
        post = self._selected_post()
        if not post:
            QMessageBox.information(self, "Выбор", "Выберите пост в таблице.")
            return
        db = Database()
        full = db.get_post_by_original_id(post['original_post_id'])
        db.close()
        if not full:
            QMessageBox.warning(self, "Ошибка", "Пост не найден в базе.")
            return
        dlg = PostEditDialog(full, self, self.styles)
        if dlg.exec() == QDialog.Accepted and dlg.was_saved():
            self.reload_table()
            self._notify_changed()

    def delete_selected(self):
        posts = self._selected_posts()
        if not posts:
            QMessageBox.information(self, "Выбор", "Выберите один или несколько постов.")
            return
        answer = QMessageBox.question(
            self,
            "Удалить посты",
            f"Удалить {len(posts)} пост(ов) из архива?\nФайлы вложений будут удалены с диска.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        db = Database()
        ok_count = 0
        for post in posts:
            if db.delete_post(post['original_post_id'], remove_files=True):
                ok_count += 1
        db.close()
        QMessageBox.information(self, "Готово", f"Удалено постов: {ok_count}")
        self.reload_table()
        self._notify_changed()

    def change_source_selected(self):
        posts = [p for p in self._selected_posts() if p.get("post_source") == "manual"]
        if not posts:
            QMessageBox.information(
                self, "Источник", "Выберите ручные посты (не ВКонтакте)."
            )
            return
        labels = load_manual_source_labels()
        label, ok = QInputDialog.getItem(
            self, "Сменить источник", "Новая подпись:", labels, 0, False
        )
        if not ok or not label.strip():
            return
        db = Database()
        n = 0
        for post in posts:
            if db.update_post(post["original_post_id"], source_label=label.strip()):
                n += 1
        db.close()
        QMessageBox.information(self, "Готово", f"Обновлено постов: {n}")
        self.reload_table()
        self._notify_changed()

    def _notify_changed(self):
        if callable(self._on_changed):
            self._on_changed()

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self._apply_styles()
