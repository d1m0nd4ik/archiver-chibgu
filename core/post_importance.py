"""Актуальность поста по давности даты публикации (автоматически для всех записей)."""
from __future__ import annotations

import datetime

# 0 — свежий … 4 — самый старый (цвет: зелёный → красный)
IMPORTANCE_LEVELS: dict[int, str] = {
    0: "Меньше месяца",
    1: "Больше месяца",
    2: "Больше 3 месяцев",
    3: "Больше полугода",
    4: "Больше года",
}

IMPORTANCE_COLORS: dict[int, str] = {
    0: "#22c55e",
    1: "#65a30d",
    2: "#ca8a04",
    3: "#ea580c",
    4: "#dc2626",
}

# Пороги в днях (нижняя граница уровня)
_THRESHOLDS_DAYS = (
    (365, 4),
    (183, 3),   # ~6 месяцев
    (90, 2),
    (30, 1),
)


def parse_post_datetime(date_value: str | datetime.datetime | None) -> datetime.datetime | None:
    if date_value is None:
        return None
    if isinstance(date_value, datetime.datetime):
        return date_value
    text = str(date_value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def compute_importance_from_date(
    date_value: str | datetime.datetime | None,
    *,
    now: datetime.datetime | None = None,
) -> int:
    """Уровень 0–4 по разнице между датой поста и текущим моментом."""
    posted = parse_post_datetime(date_value)
    if not posted:
        return 0
    now = now or datetime.datetime.now()
    age_days = max(0, (now - posted).days)
    for min_days, level in _THRESHOLDS_DAYS:
        if age_days >= min_days:
            return level
    return 0


def importance_label(level: int | None) -> str:
    try:
        key = int(level if level is not None else 0)
    except (TypeError, ValueError):
        key = 0
    return IMPORTANCE_LEVELS.get(key, IMPORTANCE_LEVELS[0])


def importance_color(level: int | None) -> str:
    try:
        key = int(level if level is not None else 0)
    except (TypeError, ValueError):
        key = 0
    return IMPORTANCE_COLORS.get(key, IMPORTANCE_COLORS[0])


def importance_badge_style(level: int | None, *, theme: str = "dark") -> str:
    color = importance_color(level)
    bg_alpha = "22" if theme == "dark" else "18"
    return (
        f"color: {color}; font-size: 12px; font-weight: 600; "
        f"padding: 4px 10px; border-radius: 8px; "
        f"background-color: {color}{bg_alpha};"
    )


def importance_filter_choices() -> list[tuple[int | None, str]]:
    return [(None, "Все")] + [(k, v) for k, v in sorted(IMPORTANCE_LEVELS.items())]
