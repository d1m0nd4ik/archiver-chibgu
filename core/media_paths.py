"""Пути медиафайлов: относительно Exports_data, переносимая portable-сборка."""
from __future__ import annotations

import os

from config.settings import DATA_DIR

_EXPORTS_MARKER = "exports_data"


def to_storage_path(path: str) -> str:
    """Сохраняемый в БД путь — относительно Exports_data."""
    path = (path or "").strip()
    if not path:
        return path

    norm = os.path.normpath(path)
    data_dir = os.path.normpath(DATA_DIR)

    if not os.path.isabs(norm):
        rel = norm.lstrip("./\\")
        return rel.replace("\\", "/")

    try:
        rel = os.path.relpath(norm, data_dir)
        if not rel.startswith(".."):
            return rel.replace("\\", "/")
    except ValueError:
        pass

    parts = norm.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if part.lower() == _EXPORTS_MARKER:
            suffix = "/".join(parts[i + 1 :])
            return suffix.replace("\\", "/")

    return norm.replace("\\", "/")


def resolve_storage_path(stored: str) -> str:
    """Абсолютный путь к файлу в текущей установке программы."""
    stored = (stored or "").strip()
    if not stored:
        return ""

    data_dir = os.path.normpath(DATA_DIR)
    rel = to_storage_path(stored)
    if rel:
        return os.path.normpath(os.path.join(data_dir, rel))
    return os.path.normpath(stored)


def storage_key(stored: str) -> str:
    """Ключ для сравнения путей независимо от расположения папки программы."""
    rel = to_storage_path(stored)
    return os.path.normpath(rel).lower().replace("\\", "/")


def resolve_paths_csv(stored_csv: str) -> str:
    if not stored_csv:
        return ""
    parts = [
        resolve_storage_path(p.strip())
        for p in stored_csv.split(",")
        if p.strip() and p.strip().lower() != "none"
    ]
    return ",".join(parts)
