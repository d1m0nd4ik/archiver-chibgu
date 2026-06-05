"""Резервное копирование Archive.db и Exports_data."""
from __future__ import annotations

import os
import zipfile
from datetime import datetime
from pathlib import Path

from config.settings import DB_NAME, DATA_DIR, _PROJECT_ROOT
from core.logging_config import logger


def create_archive_backup(dest_dir: str | Path | None = None) -> tuple[bool, str, str | None]:
    """
    Создаёт zip с Archive.db и Exports_data.
    Возвращает (успех, сообщение, путь к zip).
    """
    dest_dir = Path(dest_dir or _PROJECT_ROOT)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = dest_dir / f"VK_Archiver_backup_{stamp}.zip"
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(DB_NAME):
                zf.write(DB_NAME, arcname="Archive.db")
            if os.path.isdir(DATA_DIR):
                for root, _dirs, files in os.walk(DATA_DIR):
                    for name in files:
                        full = os.path.join(root, name)
                        arc = os.path.relpath(full, _PROJECT_ROOT)
                        zf.write(full, arcname=arc)
        size_mb = zip_path.stat().st_size / (1024 * 1024)
        return True, f"Резервная копия: {zip_path.name} ({size_mb:.1f} МБ)", str(zip_path)
    except Exception as e:
        logger.error("create_archive_backup: %s", e, exc_info=True)
        return False, f"Ошибка резервного копирования: {e}", None
