"""Плавная анимация нажатия для QPushButton (QSS отключает нативный отклик Qt)."""
from __future__ import annotations

from PySide6.QtCore import QObject, QEvent, QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtWidgets import QPushButton, QGraphicsOpacityEffect

_DURATION_MS = 110
_PRESSED_OPACITY = 0.72
_ATTACHED: set[int] = set()


def _apply_press_property(button: QPushButton, pressed: bool) -> None:
    button.setProperty("pressAnim", "true" if pressed else "false")
    style = button.style()
    style.unpolish(button)
    style.polish(button)
    button.update()


class _PressAnimationFilter(QObject):
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(obj, QPushButton) or not obj.isEnabled():
            return False

        effect = obj.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            return False

        et = event.type()
        if et == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            _apply_press_property(obj, True)
            self._animate(effect, _PRESSED_OPACITY)
        elif et == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            anim = self._animate(effect, 1.0)
            anim.finished.connect(lambda b=obj: _apply_press_property(b, False))
        return False

    @staticmethod
    def _animate(effect: QGraphicsOpacityEffect, target: float) -> QPropertyAnimation:
        prev = getattr(effect, "_opacity_anim", None)
        if isinstance(prev, QPropertyAnimation) and prev.state() == QPropertyAnimation.State.Running:
            prev.stop()
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(_DURATION_MS)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        effect._opacity_anim = anim
        anim.start()
        return anim


def attach_press_animation(button: QPushButton) -> None:
    """Подключает плавный отклик на нажатие (без повторного подключения)."""
    bid = id(button)
    if bid in _ATTACHED:
        return
    _ATTACHED.add(bid)

    effect = QGraphicsOpacityEffect(button)
    effect.setOpacity(1.0)
    button.setGraphicsEffect(effect)

    filt = _PressAnimationFilter(button)
    button.installEventFilter(filt)
    button._press_anim_filter = filt  # noqa: SLF001 — удерживаем фильтр


def attach_press_animation_all(root) -> None:
    for btn in root.findChildren(QPushButton):
        attach_press_animation(btn)


def mark_compact_toolbar_button(button: QPushButton, *, primary: bool) -> None:
    """Метка для QSS-селектора анимации нажатия компактных кнопок."""
    button.setProperty("primary", "true" if primary else "false")
    button.setProperty("pressAnim", "false")
    button.style().unpolish(button)
    button.style().polish(button)
