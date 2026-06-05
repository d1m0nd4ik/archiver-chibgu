"""Приведение QDateEdit / QDateTimeEdit к виду QComboBox после QSS."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDateEdit, QDateTimeEdit, QLineEdit

from ui.form_layout import FormGrid


def refresh_date_field(widget: QDateEdit | QDateTimeEdit) -> None:
    """Переполировка и выравнивание встроенного QLineEdit."""
    if not widget.styleSheet():
        return
    FormGrid._align_field_text(widget)
    FormGrid._reset_internal_line_edits(widget)
    for line_edit in widget.findChildren(QLineEdit):
        if line_edit.parent() is not widget:
            continue
        line_edit.setFrame(False)
        line_edit.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def setup_all_date_fields(root) -> None:
    for widget in root.findChildren(QDateEdit):
        refresh_date_field(widget)
    for widget in root.findChildren(QDateTimeEdit):
        refresh_date_field(widget)
