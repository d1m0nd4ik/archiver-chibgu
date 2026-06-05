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

from ui.styles import apply_panel_label_style, get_panel_filter_label_style
from ui.ui_scale import UiScale

_FIELD_TYPES = (QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QAbstractSpinBox)


class FormGrid:
    """Сетки «подпись — поле» с одинаковым выравниванием по всему приложению."""

    @staticmethod
    def field_height(*, compact: bool = True) -> int:
        return UiScale.px(30 if compact else 36)

    @staticmethod
    def label_width(*, narrow: bool = False, wide: bool = False) -> int:
        if narrow:
            return UiScale.px(34)
        if wide:
            return UiScale.px(168)
        return UiScale.px(112)

    @classmethod
    def make_label(
        cls,
        text: str,
        *,
        narrow: bool = False,
        wide: bool = False,
        top: bool = False,
    ) -> QLabel:
        lbl = QLabel(text)
        apply_panel_label_style(lbl, get_panel_filter_label_style())
        lbl.setProperty("formLabel", True)
        if top:
            lbl.setProperty("formLabelTop", True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            lbl.setMinimumWidth(cls.label_width(wide=wide))
        elif narrow:
            lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            lbl.setFixedHeight(cls.field_height())
            lbl.setMinimumWidth(cls.label_width(narrow=True))
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        else:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl.setFixedHeight(cls.field_height())
            lbl.setMinimumWidth(cls.label_width(wide=wide))
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return lbl

    @classmethod
    def setup_two_column(cls, grid: QGridLayout, *, wide_labels: bool = False) -> None:
        lw = cls.label_width(wide=wide_labels)
        grid.setColumnMinimumWidth(0, lw)
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
        lw = cls.label_width()
        grid.setColumnMinimumWidth(0, lw)
        grid.setColumnMinimumWidth(2, lw)
        for col, stretch in ((0, 0), (1, 1), (2, 0), (3, 1)):
            grid.setColumnStretch(col, stretch)
        grid.setHorizontalSpacing(UiScale.px(10))
        grid.setVerticalSpacing(UiScale.px(8))

    @classmethod
    def fix_field(cls, widget: QWidget, *, compact: bool = True) -> None:
        if isinstance(widget, _FIELD_TYPES):
            widget.setFixedHeight(cls.field_height(compact=compact))
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @classmethod
    def sync_grid(
        cls,
        grid: QGridLayout,
        *,
        compact: bool = True,
        labels: list[QLabel] | None = None,
    ) -> None:
        h = cls.field_height(compact=compact)
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
                    w.setFixedHeight(h)
                continue

            if isinstance(w, _FIELD_TYPES):
                grid.setAlignment(w, vcenter)
                w.setFixedHeight(h)
            elif isinstance(w, QPushButton):
                grid.setAlignment(w, vcenter)
                w.setMinimumHeight(h)
            elif isinstance(w, QWidget) and w.layout() is None:
                grid.setAlignment(w, vcenter)
                w.setMinimumHeight(h)
