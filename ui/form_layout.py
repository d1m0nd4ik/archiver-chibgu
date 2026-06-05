"""Единое позиционирование подписей и полей в формах (светлая / тёмная тема)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ui.styles import apply_panel_label_style, compact_field_outer_height, get_panel_filter_label_style
from ui.ui_scale import UiScale

_FIELD_TYPES = (QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QAbstractSpinBox)
_SIZE_MAX = 16777215  # Qt default max widget size
_TEXT_ALIGN = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


def release_fixed_height(widget: QWidget) -> None:
    """Снимает setFixedHeight, если он был задан ранее (после смены темы)."""
    if widget.maximumHeight() >= _SIZE_MAX:
        return
    widget.setMaximumHeight(_SIZE_MAX)
    if widget.minimumHeight() == widget.maximumHeight():
        widget.setMinimumHeight(0)


class FormGrid:
    """Сетки «подпись — поле» с одинаковым выравниванием по всему приложению."""

    @staticmethod
    def field_height(*, compact: bool = True) -> int:
        """Минимальная высота поля; фактическая задаётся QSS (padding + border)."""
        return UiScale.px(30 if compact else 40)

    @staticmethod
    def label_width(*, narrow: bool = False) -> int:
        if narrow:
            return UiScale.px(34)
        return UiScale.px(0)

    @classmethod
    def make_label(
        cls,
        text: str,
        *,
        narrow: bool = False,
        wide: bool = False,
        top: bool = False,
        compact: bool = True,
    ) -> QLabel:
        del wide  # ширина колонки — по содержимому, без фиксированного зазора
        lbl = QLabel(text)
        apply_panel_label_style(lbl, get_panel_filter_label_style())
        lbl.setProperty("formLabel", True)
        h = cls.field_height(compact=compact)
        if top:
            lbl.setProperty("formLabelTop", True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            lbl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        elif narrow:
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            lbl.setMinimumWidth(cls.label_width(narrow=True))
            lbl.setMinimumHeight(h)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        else:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setMinimumHeight(h)
            lbl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        return lbl

    @classmethod
    def setup_two_column(cls, grid: QGridLayout, *, wide_labels: bool = False) -> None:
        del wide_labels
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(UiScale.px(10))
        grid.setVerticalSpacing(UiScale.px(8))

    @classmethod
    def setup_multi_field_grid(cls, grid: QGridLayout) -> None:
        """6 колонок: подпись | поле | подпись | поле | подпись | поле (поиск, статистика)."""
        grid.setHorizontalSpacing(UiScale.px(8))
        grid.setVerticalSpacing(UiScale.px(6))
        for col, min_w, stretch in (
            (0, 100, 0), (1, 0, 1),
            (2, 76, 0), (3, 0, 1),
            (4, 68, 0), (5, 0, 1),
        ):
            if min_w:
                grid.setColumnMinimumWidth(col, UiScale.px(min_w))
            grid.setColumnStretch(col, stretch)

    @classmethod
    def setup_quad_column(cls, grid: QGridLayout) -> None:
        """4 колонки: подпись | поле | подпись | поле."""
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)
        grid.setHorizontalSpacing(UiScale.px(10))
        grid.setVerticalSpacing(UiScale.px(8))

    @staticmethod
    def _align_field_text(widget: QWidget) -> None:
        if isinstance(widget, QLineEdit):
            widget.setAlignment(_TEXT_ALIGN)
        elif isinstance(widget, (QDateEdit, QDateTimeEdit, QAbstractSpinBox)):
            widget.setAlignment(_TEXT_ALIGN)
            if isinstance(widget, (QDateEdit, QDateTimeEdit)):
                for le in widget.findChildren(QLineEdit):
                    if le.parent() is widget:
                        le.setAlignment(_TEXT_ALIGN)
        elif isinstance(widget, QComboBox) and widget.isEditable():
            editor = widget.lineEdit()
            if editor is not None:
                editor.setAlignment(_TEXT_ALIGN)

    @staticmethod
    def _reset_internal_line_edits(widget: QWidget) -> None:
        """Сброс прямого QSS на встроенных QLineEdit (после apply_theme_to_page)."""
        if not isinstance(widget, (QComboBox, QDateEdit, QDateTimeEdit, QAbstractSpinBox)):
            return
        for le in widget.findChildren(QLineEdit):
            if isinstance(le.parent(), (QComboBox, QDateEdit, QDateTimeEdit, QAbstractSpinBox)):
                le.setStyleSheet("")
                le.setAlignment(_TEXT_ALIGN)

    @classmethod
    def fix_field(cls, widget: QWidget, *, compact: bool = True) -> None:
        """Высота и выравнивание поля после применения QSS."""
        if not isinstance(widget, _FIELD_TYPES):
            return
        cls._align_field_text(widget)
        cls._reset_internal_line_edits(widget)
        if compact and isinstance(widget, (QDateEdit, QDateTimeEdit)):
            h = compact_field_outer_height()
        elif compact and widget.styleSheet():
            h = max(widget.sizeHint().height(), cls.field_height(compact=True))
        else:
            h = cls.field_height(compact=compact)
        widget.setMinimumHeight(h)
        widget.setMaximumHeight(h if compact else _SIZE_MAX)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed if compact else QSizePolicy.Policy.Preferred,
        )

    @classmethod
    def sync_grid(
        cls,
        grid: QGridLayout,
        *,
        compact: bool = True,
        labels: list[QLabel] | None = None,
    ) -> None:
        """Выравнивание в сетке; размеры полей не трогаем (их задаёт QSS)."""
        vcenter = Qt.AlignmentFlag.AlignVCenter
        label_set = set(labels) if labels is not None else None

        for i in range(grid.count()):
            item = grid.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None:
                continue

            if isinstance(w, QLabel):
                if label_set is not None and w not in label_set:
                    if not w.property("formLabel"):
                        continue
                if w.property("formLabelTop"):
                    grid.setAlignment(
                        w, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                    )
                    continue
                if w.property("formLabel") or (label_set is not None and w in label_set):
                    grid.setAlignment(w, vcenter)
                continue

            if isinstance(w, _FIELD_TYPES):
                grid.setAlignment(w, vcenter)
            elif isinstance(w, QPushButton):
                grid.setAlignment(w, vcenter)
            elif isinstance(w, QWidget) and w.layout() is None:
                grid.setAlignment(w, vcenter)
