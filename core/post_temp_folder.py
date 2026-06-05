"""Временная папка на рабочем столе с файлами одного поста."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from core.database import Database
from core.desktop_shortcut import get_primary_desktop_dir
from core.logging_config import logger

TEMP_ROOT_NAME = "VK_Archiver_CHIBGU_временно"


class PostTempFolderManager:
    """Одна активная временная папка; при новом посте предыдущая удаляется."""

    def __init__(self):
        self._folder: Path | None = None
        self._post_id: int | None = None

    @property
    def current_folder(self) -> Path | None:
        return self._folder if self._folder and self._folder.is_dir() else None

    @property
    def current_post_id(self) -> int | None:
        return self._post_id

    def folder_label(self) -> str:
        folder = self.current_folder
        if not folder:
            return ""
        return str(folder)

    def remove_folder(self) -> bool:
        folder = self._folder
        self._folder = None
        self._post_id = None
        if not folder or not folder.exists():
            return True
        try:
            shutil.rmtree(folder, ignore_errors=False)
            logger.info("Удалена временная папка: %s", folder)
            self._cleanup_empty_root()
            return True
        except OSError as e:
            logger.error("remove_folder %s: %s", folder, e)
            return False

    def cleanup(self):
        """Удалить активную папку и корень на рабочем столе, если пуст."""
        self.remove_folder()

    def export_post(
        self,
        original_post_id: int,
        *,
        date_str: str | None = None,
        open_explorer: bool = True,
    ) -> tuple[bool, str]:
        """
        Копирует вложения поста во временную папку на рабочем столе.
        Возвращает (успех, сообщение для пользователя).
        """
        try:
            post_id = int(original_post_id)
        except (TypeError, ValueError):
            return False, "Некорректный ID поста."

        if self._post_id is not None and self._post_id != post_id:
            self.remove_folder()
        elif self._post_id == post_id and self.current_folder:
            if open_explorer:
                self.open_in_explorer(self.current_folder)
            return True, f"Папка уже создана:\n{self.current_folder}"

        db = Database()
        try:
            post = db.get_post_by_original_id(post_id)
            rows = db.list_post_files_for_export(post_id)
        finally:
            db.close()

        if not post and not rows:
            return False, "Пост не найден в архиве."

        safe_date = ""
        if date_str:
            safe_date = re.sub(r'[^\d\-]', '_', date_str.strip())[:16]
        folder_name = f"post_{post_id}"
        if safe_date:
            folder_name += f"_{safe_date}"

        root = get_primary_desktop_dir() / TEMP_ROOT_NAME
        target = root / folder_name
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)

        copied = 0
        missing: list[str] = []
        used_names: set[str] = set()

        for idx, row in enumerate(rows, 1):
            src = (row.get('media_path') or '').strip()
            if not src:
                missing.append(f"#{idx}: пустой путь в БД")
                continue
            if not os.path.isfile(src):
                missing.append(f"#{idx}: {os.path.basename(src)}")
                continue
            mtype = (row.get('media_type') or 'file').lower()
            base = os.path.basename(src)
            dest_name = f"{idx:02d}_{mtype}_{base}"
            if dest_name in used_names:
                stem, ext = os.path.splitext(dest_name)
                n = 2
                while f"{stem}_{n}{ext}" in used_names:
                    n += 1
                dest_name = f"{stem}_{n}{ext}"
            used_names.add(dest_name)
            shutil.copy2(src, target / dest_name)
            copied += 1

        self._write_post_info(target, post, copied, missing)

        self._folder = target
        self._post_id = post_id

        if copied == 0:
            msg = (
                f"Папка создана, но файлы на диске не найдены:\n{target}\n\n"
                "Проверьте целостность архива (Поиск → Проверить целостность)."
            )
        else:
            msg = f"Скопировано файлов: {copied}\n{target}"
            if missing:
                msg += f"\n\nНе найдено на диске: {len(missing)}"

        if open_explorer:
            self.open_in_explorer(target)

        return True, msg

    @staticmethod
    def _write_post_info(
        folder: Path,
        post: dict | None,
        copied: int,
        missing: list[str],
    ):
        lines = ["VK Archiver CHIBGU — файлы поста", ""]
        if post:
            lines.extend([
                f"ID: {post.get('original_post_id')}",
                f"Дата: {post.get('date', '')}",
                f"Источник: {post.get('post_source', 'vk')}",
                f"Теги: {post.get('tags', '')}",
                "",
                (post.get('text') or '')[:8000],
                "",
            ])
        lines.append(f"Скопировано файлов: {copied}")
        if missing:
            lines.append("Отсутствуют на диске:")
            lines.extend(f"  - {m}" for m in missing[:50])
        try:
            (folder / "post_info.txt").write_text("\n".join(lines), encoding="utf-8")
        except OSError as e:
            logger.warning("post_info.txt: %s", e)

    def _cleanup_empty_root(self):
        root = get_primary_desktop_dir() / TEMP_ROOT_NAME
        try:
            if root.is_dir() and not any(root.iterdir()):
                root.rmdir()
        except OSError:
            pass

    @staticmethod
    def open_in_explorer(path: Path | str):
        path = Path(path)
        if not path.is_dir():
            return
        path_str = str(path.resolve())
        if sys.platform == "win32":
            os.startfile(path_str)
        elif sys.platform == "darwin":
            subprocess.run(["open", path_str], check=False)
        else:
            subprocess.run(["xdg-open", path_str], check=False)


_manager: PostTempFolderManager | None = None


def get_post_temp_folder_manager() -> PostTempFolderManager:
    global _manager
    if _manager is None:
        _manager = PostTempFolderManager()
    return _manager
