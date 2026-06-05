"""Подписи источника для ручных материалов в архиве."""
from __future__ import annotations

from core.database import Database

DEFAULT_MANUAL_SOURCE_LABELS = [
    "Юбилей кафедры",
    "Внутреннее мероприятие",
    "Статья с сайта",
    "Праздник / день факультета",
    "Фото с мероприятия",
    "Ручная загрузка",
]


def load_manual_source_labels(db: Database | None = None) -> list[str]:
    """Предустановки + уже использованные подписи из архива."""
    labels: list[str] = []
    seen: set[str] = set()
    for item in DEFAULT_MANUAL_SOURCE_LABELS:
        key = item.strip().lower()
        if key and key not in seen:
            labels.append(item.strip())
            seen.add(key)
    own_db = db is None
    if own_db:
        db = Database()
    try:
        if db:
            for row in db.list_distinct_manual_source_labels():
                key = row.strip().lower()
                if key and key not in seen:
                    labels.append(row.strip())
                    seen.add(key)
    finally:
        if own_db and db:
            db.close()
    return labels
