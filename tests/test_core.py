"""Базовые тесты ядра архива."""
import logging
import os
import tempfile
import unittest
from datetime import datetime
from logging.handlers import RotatingFileHandler

from core.database import Database
from core.post_tags import build_post_tags, parse_manual_tags, apply_manual_tags_to_post
from core.archive_integrity import check_archive_integrity
from core.manual_import import ManualImportService, POST_SOURCE_MANUAL
from core.duplicate_check import find_similar_posts, _text_key
from core.archive_prerequisites import assess_prerequisites
from core.scheduler_pipeline import build_scheduler_cycle


def _detach_error_log_file():
    """Тесты не должны писать ложные ERROR в logs/errors.log пользователя."""
    log = logging.getLogger("VKArchiver")
    for h in list(log.handlers):
        if isinstance(h, RotatingFileHandler):
            log.removeHandler(h)


_detach_error_log_file()


class TestPostTags(unittest.TestCase):
    def test_parse_manual_tags(self):
        tags = parse_manual_tags("#Test_one #test_two")
        self.assertEqual(len(tags), 2)

    def test_text_key(self):
        self.assertEqual(_text_key("  Hello\nworld  "), "hello world")


def _fresh_db(path: str) -> Database:
    Database._schema_ready.clear()
    Database._instances.clear()
    return Database(path)


class TestDatabaseSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = _fresh_db(self.tmp.name)

    def tearDown(self):
        self.db.close()
        Database._instances.clear()
        os.unlink(self.tmp.name)

    def test_search_and_count(self):
        from core.post_search import PostSearchParams

        self.db.save_post(
            1, "2025-01-01 12:00", "текст юбилея", "#юбилей",
            post_source=POST_SOURCE_MANUAL, source_label="Юбилей",
        )
        params = PostSearchParams(query="юбилей", limit=10)
        rows = self.db.search_posts_filtered(params)
        self.assertGreaterEqual(len(rows), 1)
        cnt = self.db.count_posts_filtered(params)
        self.assertGreaterEqual(cnt, 1)

    def test_integrity_empty_db(self):
        report = check_archive_integrity(self.db, scan_orphan_files=False)
        self.assertIn("missing_files", report)


class TestManualImport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = _fresh_db(self.tmp.name)

    def tearDown(self):
        self.db.close()
        Database._instances.clear()
        os.unlink(self.tmp.name)

    def test_import_text_only(self):
        svc = ManualImportService(self.db)
        ok, msg, pid = svc.import_post(
            posted_at=datetime(2025, 6, 1, 10, 0),
            text="Тестовый пост архива",
            source_label="Тест",
            manual_tags_text="#test_tag",
        )
        self.assertTrue(ok)
        self.assertIsNotNone(pid)
        post = self.db.get_post_by_original_id(pid)
        self.assertTrue(post.get("tags"))


class TestSchedulerPipeline(unittest.TestCase):
    def test_empty_db_needs_prep_before_vk(self):
        path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        db = _fresh_db(path)
        try:
            a = assess_prerequisites(db)
            self.assertTrue(a["needs_dept_sync"])
            self.assertTrue(a["needs_tag_dictionary"])
            self.assertFalse(a["ready_for_vk_import"])
            prefs_path = __import__("core.scheduler_prefs", fromlist=["PREFS_PATH"]).PREFS_PATH
            old = prefs_path.is_file()
            if old:
                backup = prefs_path.read_text(encoding="utf-8")
            prefs_path.write_text(
                '{"enabled": true, "interval": "daily", "run_vk_download": true}',
                encoding="utf-8",
            )
            plan = build_scheduler_cycle(token="t", group="g", manual=True)
            if old:
                prefs_path.write_text(backup, encoding="utf-8")
            else:
                prefs_path.unlink(missing_ok=True)
            self.assertIsNotNone(plan)
            steps = list(plan.steps)
            self.assertEqual(steps[0], "dept_sync")
            self.assertIn("ensure_tags", steps)
            self.assertIn("vk_download", steps)
        finally:
            db.close()
            Database._instances.clear()
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
