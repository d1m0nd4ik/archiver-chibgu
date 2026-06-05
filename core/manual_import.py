"""Импорт материалов в архив без ВКонтакте."""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from core.database import Database
from core.employee_tagger import EmployeeTagger
from core.logging_config import logger
from core.media_processor import MediaProcessor
from core.post_tags import build_post_tags, apply_manual_tags_to_post
from core.smart_tagger import SmartTagger

POST_SOURCE_VK = "vk"
POST_SOURCE_MANUAL = "manual"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv"}


def media_type_for_path(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "photo"


class ManualImportService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def import_post(
        self,
        *,
        posted_at: datetime,
        text: str = "",
        file_paths: list[str] | None = None,
        source_label: str = "",
        manual_tags_text: str = "",
    ) -> tuple[bool, str, int | None]:
        """
        Сохраняет пост и вложения в архив.
        Возвращает (успех, сообщение, original_post_id).
        """
        text = (text or "").strip()
        file_paths = [p for p in (file_paths or []) if p and os.path.isfile(p)]
        if not text and not file_paths:
            return False, "Добавьте текст поста или хотя бы один файл.", None

        post_id = self.db.allocate_manual_post_id()
        if post_id is None:
            return False, "Не удалось выделить ID для записи.", None

        tagger = EmployeeTagger(self.db, refresh_on_init=False)
        smart = SmartTagger(self.db)
        smart.ensure_dictionary()

        tags_str, teacher_ht, dept_ht, emp_id, dept_id = build_post_tags(
            text, tagger, smart
        )
        if (manual_tags_text or "").strip():
            tags_str, teacher_ht, dept_ht, emp_id, dept_id = apply_manual_tags_to_post(
                tags_str, manual_tags_text, tagger, text
            )

        date_str = posted_at.strftime("%Y-%m-%d %H:%M")
        label = (source_label or "").strip() or "Ручная загрузка"

        ok = self.db.save_post(
            original_post_id=post_id,
            date=date_str,
            text=text,
            tags=tags_str,
            author_employee_id=emp_id,
            author_department_id=dept_id,
            teacher_hashtag=teacher_ht,
            department_hashtag=dept_ht,
            post_source=POST_SOURCE_MANUAL,
            source_label=label,
        )
        if not ok:
            return False, "Не удалось сохранить пост в базу данных.", None

        saved_files = 0
        ts = int(posted_at.timestamp())
        folder = MediaProcessor.get_date_folder_path(ts)
        os.makedirs(folder, exist_ok=True)

        photo_idx = 0
        video_idx = 0
        for src in file_paths:
            try:
                media_type = media_type_for_path(src)
                ext = os.path.splitext(src)[1].lower() or (
                    ".mp4" if media_type == "video" else ".jpg"
                )
                if media_type == "video":
                    video_idx += 1
                    key = f"video_{video_idx}"
                    dest = os.path.join(folder, f"post_{post_id}_video_{video_idx}{ext}")
                else:
                    photo_idx += 1
                    key = f"photo_{photo_idx}"
                    dest = os.path.join(folder, f"post_{post_id}_photo_{photo_idx}{ext}")

                shutil.copy2(src, dest)
                size = MediaProcessor.get_file_size(dest)
                self.db.save_media(post_id, media_type, key, dest, size)
                saved_files += 1
            except Exception as e:
                logger.error("manual import file %s: %s", src, e, exc_info=True)

        parts = [f"Запись #{post_id} добавлена в архив."]
        if saved_files:
            parts.append(f"Файлов: {saved_files}.")
        if tags_str:
            parts.append(f"Теги: {tags_str}.")
        return True, " ".join(parts), post_id
