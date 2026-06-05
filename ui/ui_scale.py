"""
Масштабирование интерфейса под разрешение экрана.
Эталон: 1920×1080 (коэффициент 1.0).
"""
from __future__ import annotations

import re

from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtCore import QSize

REFERENCE_WIDTH = 1920
REFERENCE_HEIGHT = 1080
SCALE_MIN = 0.72
SCALE_MAX = 1.0

# Ниже этих размеров включается компактная вёрстка (колонки, прокрутка)
COMPACT_WIDTH = 1500
COMPACT_HEIGHT = 850


class UiScale:
    _factor: float = 1.0
    _screen_w: int = REFERENCE_WIDTH
    _screen_h: int = REFERENCE_HEIGHT
    _initialized: bool = False

    @classmethod
    def init_from_screen(cls, screen=None) -> float:
        screen = screen or QGuiApplication.primaryScreen()
        if screen is None:
            cls._factor = 1.0
            cls._screen_w = REFERENCE_WIDTH
            cls._screen_h = REFERENCE_HEIGHT
            cls._initialized = True
            return cls._factor

        geom = screen.availableGeometry()
        cls._screen_w = max(1, geom.width())
        cls._screen_h = max(1, geom.height())
        w_ratio = cls._screen_w / REFERENCE_WIDTH
        h_ratio = cls._screen_h / REFERENCE_HEIGHT
        cls._factor = max(SCALE_MIN, min(SCALE_MAX, min(w_ratio, h_ratio)))
        cls._initialized = True
        return cls._factor

    @classmethod
    def factor(cls) -> float:
        if not cls._initialized:
            cls.init_from_screen()
        return cls._factor

    @classmethod
    def screen_size(cls) -> tuple[int, int]:
        if not cls._initialized:
            cls.init_from_screen()
        return cls._screen_w, cls._screen_h

    @classmethod
    def is_compact(cls) -> bool:
        w, h = cls.screen_size()
        return w < COMPACT_WIDTH or h < COMPACT_HEIGHT

    @classmethod
    def px(cls, value: float) -> int:
        return max(1, int(round(value * cls.factor())))

    @classmethod
    def minimum_window_size(cls) -> QSize:
        w, h = cls.screen_size()
        if w < 1280:
            return QSize(cls.px(880), cls.px(580))
        if w < 1366:
            return QSize(cls.px(960), cls.px(620))
        return QSize(cls.px(1024), cls.px(700))

    @classmethod
    def page_margins(cls) -> tuple[int, int, int, int]:
        m = cls.px(30)
        return m, m, m, m

    @classmethod
    def panel_margins(cls) -> tuple[int, int, int, int]:
        m = cls.px(16)
        return m, m, m, m

    @classmethod
    def font_header_page(cls) -> int:
        return cls.px(22)

    @classmethod
    def font_header_widget(cls) -> int:
        return cls.px(24)

    @classmethod
    def font_body(cls) -> int:
        return cls.px(13)

    @classmethod
    def font_small(cls) -> int:
        return cls.px(11)

    @classmethod
    def sidebar_width(cls) -> int:
        return max(cls.px(200), cls.px(280))

    @classmethod
    def header_height(cls) -> int:
        return cls.px(70)

    @classmethod
    def logo_size(cls) -> int:
        return cls.px(48)


def scale_stylesheet(css: str, factor: float | None = None) -> str:
    """Масштабирует все значения Npx в QSS (кроме url(...))."""
    if not css:
        return css
    factor = factor if factor is not None else UiScale.factor()
    if abs(factor - 1.0) < 0.01:
        return css

    placeholders: list[str] = []

    def stash_url(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"__QSS_URL_{len(placeholders) - 1}__"

    protected = re.sub(r"url\((?:\"[^\"]*\"|'[^']*'|[^)]+)\)", stash_url, css, flags=re.IGNORECASE)

    def repl(match: re.Match) -> str:
        scaled = max(1, int(round(int(match.group(1)) * factor)))
        return f"{scaled}px"

    scaled = re.sub(r"(\d+)px", repl, protected)
    for i, url in enumerate(placeholders):
        scaled = scaled.replace(f"__QSS_URL_{i}__", url)
    return scaled


def scale_stylesheet_dict(styles: dict) -> dict:
    factor = UiScale.factor()
    return {
        key: scale_stylesheet(value, factor) if isinstance(value, str) else value
        for key, value in styles.items()
    }


def apply_application_font(app) -> None:
    """Базовый шрифт приложения — системный UI-шрифт, масштаб по экрану."""
    base_pt = 10.0 * UiScale.factor()
    for family in ("Segoe UI", "Tahoma", "Arial", "sans-serif"):
        font = QFont(family)
        if family == "sans-serif" or font.exactMatch():
            break
    font.setPointSizeF(max(9.0, base_pt))
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
