"""Действия по результатам проверки целостности."""
from __future__ import annotations

import os
import subprocess
import sys

from core.database import Database
from core.logging_config import logger
def delete_missing_attachment_records(db: Database, missing_files: list[dict]) -> int:
    """Удаляет записи вложений без файла на диске."""
    n = 0
    for m in missing_files:
        path = (m.get("media_path") or "").strip()
        pid = m.get("original_post_id")
        if path and pid is not None and db.delete_attachment_by_path(int(pid), path):
            n += 1
    return n


def register_orphan_file(db: Database, file_path: str, original_post_id: int) -> bool:
    """Привязывает файл с диска к посту (новая запись attachment)."""
    if not os.path.isfile(file_path):
        return False
    ext = os.path.splitext(file_path)[1].lower()
    media_type = "video" if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"} else "photo"
    size = os.path.getsize(file_path)
    key = f"orphan_{os.path.basename(file_path)}"
    return db.save_media(int(original_post_id), media_type, key, file_path, str(size))


def open_post_folder(original_post_id: int, db: Database | None = None) -> tuple[bool, str]:
    own = db is None
    if own:
        db = Database()
    try:
        paths = db.list_media_paths_for_post(int(original_post_id))
        if not paths:
            return False, "У поста нет вложений."
        folder = os.path.dirname(paths[0])
        if not os.path.isdir(folder):
            return False, "Папка не найдена."
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", folder], check=False)
        else:
            subprocess.run(["xdg-open", folder], check=False)
        return True, folder
    except Exception as e:
        logger.error("open_post_folder: %s", e)
        return False, str(e)
    finally:
        if own and db:
            db.close()
