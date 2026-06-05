"""Единая анимация выпадающего списка QComboBox (как у «Тег»)."""
from __future__ import annotations

from weakref import ref

from PySide6.QtCore import QPoint, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import QComboBox

_DURATION_MS = 140
_SLIDE_PX = 6
_ATTACHED: set[int] = set()
_CONFIGURED: set[int] = set()


def configure_combo_like_tag(combo: QComboBox, *, allow_typing: bool = False) -> None:
    """Editable + NoInsert — тот же режим, что у комбобокса «Тег»."""
    cid = id(combo)
    if cid in _CONFIGURED:
        return
    _CONFIGURED.add(cid)

    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    line_edit = combo.lineEdit()
    if line_edit is not None:
        line_edit.setReadOnly(not allow_typing)


def _popup_window(combo: QComboBox):
    view = combo.view()
    if view is None:
        return None
    window = view.window()
    if window is None or window is combo:
        return None
    return window


def _run_popup_animation(combo: QComboBox) -> None:
    popup = _popup_window(combo)
    if popup is None:
        return

    for attr in ("_popup_op_anim", "_popup_pos_anim"):
        prev = getattr(combo, attr, None)
        if isinstance(prev, QPropertyAnimation) and prev.state() == QPropertyAnimation.State.Running:
            prev.stop()

    end_pos = popup.pos()
    start_pos = QPoint(end_pos.x(), end_pos.y() - _SLIDE_PX)
    popup.move(start_pos)
    popup.setWindowOpacity(0.0)

    pos_anim = QPropertyAnimation(popup, b"pos", popup)
    pos_anim.setDuration(_DURATION_MS)
    pos_anim.setStartValue(start_pos)
    pos_anim.setEndValue(end_pos)
    pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    op_anim = QPropertyAnimation(popup, b"windowOpacity", popup)
    op_anim.setDuration(_DURATION_MS)
    op_anim.setStartValue(0.0)
    op_anim.setEndValue(1.0)
    op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    combo_ref = ref(combo)

    def _cleanup() -> None:
        c = combo_ref()
        if c is None:
            return
        c._popup_op_anim = None
        c._popup_pos_anim = None

    op_anim.finished.connect(_cleanup)
    combo._popup_op_anim = op_anim
    combo._popup_pos_anim = pos_anim
    pos_anim.start()
    op_anim.start()


def attach_combo_popup_animation(combo: QComboBox) -> None:
    """Плавное появление списка: fade + лёгкий сдвиг вниз."""
    cid = id(combo)
    if cid in _ATTACHED:
        return
    _ATTACHED.add(cid)

    original_show = combo.showPopup

    def animated_show_popup() -> None:
        original_show()
        QTimer.singleShot(0, lambda c=combo: _run_popup_animation(c))

    combo.showPopup = animated_show_popup  # type: ignore[method-assign]


def setup_combo(combo: QComboBox) -> None:
    if combo.property("comboSkipTagLike"):
        attach_combo_popup_animation(combo)
        return
    allow_typing = bool(combo.property("comboAllowTyping"))
    configure_combo_like_tag(combo, allow_typing=allow_typing)
    attach_combo_popup_animation(combo)


def setup_all_combos(root) -> None:
    for combo in root.findChildren(QComboBox):
        setup_combo(combo)
