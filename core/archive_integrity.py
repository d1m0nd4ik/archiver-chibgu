"""Проверка целостности архива: файлы на диске ↔ записи в БД."""
from __future__ import annotations

import os

from config.settings import DATA_DIR
from core.database import Database
from core.logging_config import logger


def check_archive_integrity(
    db: Database | None = None,
    *,
    scan_orphan_files: bool = True,
) -> dict:
    """
    Возвращает:
    missing_files — вложения в БД без файла на диске;
    empty_paths — записи без пути;
    orphan_files — файлы в Exports_data, не привязанные к БД;
    posts_without_attachments — посты без вложений (информационно).
    """
    db = db or Database()
    missing_files: list[dict] = []
    empty_paths: list[dict] = []
    known_paths: set[str] = set()

    try:
        rows = db.get_all_attachments()
        for row in rows:
            path = (row.get('media_path') or '').strip()
            norm = os.path.normpath(path) if path else ''
            if path:
                known_paths.add(norm)
                if os.path.isfile(path):
                    continue
                missing_files.append({
                    'original_post_id': row['original_post_id'],
                    'media_type': row.get('media_type'),
                    'media_path': path,
                })
            else:
                empty_paths.append({
                    'original_post_id': row['original_post_id'],
                    'media_type': row.get('media_type'),
                })
    except Exception as e:
        logger.error("check_archive_integrity attachments: %s", e)

    orphan_files: list[str] = []
    if scan_orphan_files and os.path.isdir(DATA_DIR):
        media_ext = {'.jpg', '.jpeg', '.png', '.mp4', '.webm', '.mov', '.mkv'}
        for root, _dirs, files in os.walk(DATA_DIR):
            for name in files:
                if name.endswith('_thumb.jpg'):
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext not in media_ext:
                    continue
                full = os.path.normpath(os.path.join(root, name))
                if full not in known_paths:
                    orphan_files.append(full)

    posts_without_attachments = 0
    try:
        posts_without_attachments = db.count_posts_without_attachments()
    except Exception as e:
        logger.error("count_posts_without_attachments: %s", e)

    return {
        'missing_files': missing_files,
        'empty_paths': empty_paths,
        'orphan_files': orphan_files,
        'posts_without_attachments': posts_without_attachments,
        'total_attachments': len(known_paths) + len(empty_paths),
    }
