"""Главная сводка по архиву."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QPushButton,
)
from PySide6.QtCore import Qt

from core.database import Database
from ui.styles import (
    STYLES, apply_theme_to_page, get_page_header_style, get_stat_card_styles,
)


class DashboardPage(QWidget):
    def __init__(self, styles=None, on_navigate=None):
        super().__init__()
        self.styles = styles or STYLES.get_styles()
        self._on_navigate = on_navigate
        self._cards: list[QLabel] = []
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        self.header_label = QLabel("Сводка архива")
        self.header_label.setStyleSheet(get_page_header_style())
        layout.addWidget(self.header_label)

        self.grid_frame = QFrame()
        self.grid_frame.setStyleSheet(self.styles['frame'])
        self.grid = QGridLayout(self.grid_frame)
        self.grid.setSpacing(12)
        layout.addWidget(self.grid_frame)

        nav = QHBoxLayout()
        self._nav_buttons = []
        for label, page in (
            ("Поиск", "search"),
            ("Хранилище", "storage"),
            ("Загрузка", "download"),
            ("Статистика", "stats"),
        ):
            btn = QPushButton(label)
            btn.setStyleSheet(self.styles['button_secondary'])
            btn.clicked.connect(lambda _=False, p=page: self._go(p))
            self._nav_buttons.append(btn)
            nav.addWidget(btn)
        nav.addStretch()
        layout.addLayout(nav)
        layout.addStretch()
        self._secondary_buttons = self._nav_buttons

    def _go(self, page: str):
        if self._on_navigate:
            self._on_navigate(page)

    def refresh(self):
        db = Database()
        try:
            s = db.get_stats()
        finally:
            db.close()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()
        scs = get_stat_card_styles()
        items = [
            ("Всего постов", str(s['total'])),
            ("За текущий месяц", str(s.get('month', 0))),
            ("Из ВК / ручных", f"{s.get('vk', 0)} / {s.get('manual', 0)}"),
            ("Файлов вложений", str(s.get('files', 0))),
            ("Лайки / коммент. / репосты", f"{s['likes']} / {s['comments']} / {s['shares']}"),
            ("Топ кафедра", f"{s.get('top_department', '—')} ({s.get('top_department_count', 0)})"),
            ("Без автора", str(s.get('no_author', 0))),
            ("Без тегов", str(s.get('no_tags', 0))),
            ("Без вложений", str(s.get('no_files', 0))),
        ]
        for i, (title, value) in enumerate(items):
            card = QFrame()
            card.setObjectName("StatCard")
            card.setStyleSheet(scs['frame'])
            vl = QVBoxLayout(card)
            t = QLabel(title)
            t.setStyleSheet(scs['title'])
            v = QLabel(value)
            v.setStyleSheet(scs['value'])
            vl.addWidget(t)
            vl.addWidget(v)
            self.grid.addWidget(card, i // 3, i % 3)
            self._cards.append(v)

    def update_styles(self, styles):
        self.styles = styles
        apply_theme_to_page(self, styles)
        self.refresh()
