"""Кэш миниатюр для таблиц и карточек."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from config.paths import get_data_root
from core.logging_config import logger

CACHE_DIR = get_data_root() / ".cache" / "thumbs"
THUMB_SIZE = (64, 64)


from core.media_paths import resolve_storage_path


def resolve_media_preview_path(media_path: str, media_type: str) -> str:
    """Путь к файлу для превью: фото, либо *_thumb.jpg для видео/клипа."""
    mpath = resolve_storage_path(media_path)
    if not mpath:
        return ""
    mtype = (media_type or "").strip().lower()
    if mtype == "photo" and os.path.isfile(mpath):
        return mpath
    if mtype in ("video", "clip"):
        base, ext = os.path.splitext(mpath)
        candidates = [
            f"{base}_thumb.jpg",
            mpath.replace(ext, "_thumb.jpg") if ext else f"{mpath}_thumb.jpg",
            os.path.join(
                os.path.dirname(mpath),
                "thumbnails",
                os.path.basename(base) + ".thumb.jpg",
            ),
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
    return ""


def _cache_path(source_path: str) -> Path | None:
    if not source_path or not os.path.isfile(source_path):
        return None
    key = hashlib.sha1(os.path.normpath(source_path).encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{key}.jpg"


def get_thumbnail_pixmap(source_path: str, size: tuple[int, int] = THUMB_SIZE) -> QPixmap | None:
    """Возвращает QPixmap миниатюры (из кэша или создаёт JPEG в .cache/thumbs)."""
    try:
        cache = _cache_path(source_path)
        if cache is None:
            return None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        src_mtime = os.path.getmtime(source_path)
        if not cache.is_file() or cache.stat().st_mtime < src_mtime:
            with Image.open(source_path) as img:
                img = img.convert("RGB")
                img.thumbnail(size, Image.Resampling.LANCZOS)
                cache.parent.mkdir(parents=True, exist_ok=True)
                img.save(cache, "JPEG", quality=85)
        pm = QPixmap(str(cache))
        if pm.isNull():
            return None
        return pm.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        logger.debug("thumb_cache %s: %s", source_path, e)
        return None
