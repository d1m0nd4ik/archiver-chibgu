"""Проверка готовности справочников перед догрузкой постов из ВК."""
from __future__ import annotations

from core.database import Database
from core.smart_tagger import SmartTagger


def assess_prerequisites(db: Database | None = None) -> dict:
    """
    Без кафедр/преподавателей и активного словаря тегов посты не получат
    привязку к авторам и хэштеги из словаря.
    """
    own = db is None
    if own:
        db = Database()
    try:
        cur = db._get_cursor()
        dept_count = int(cur.execute("SELECT COUNT(*) FROM departments").fetchone()[0] or 0)
        emp_count = int(cur.execute("SELECT COUNT(*) FROM employees").fetchone()[0] or 0)
        emp_with_ht = int(
            cur.execute(
                "SELECT COUNT(*) FROM employees WHERE TRIM(COALESCE(hashtag, '')) != ''"
            ).fetchone()[0]
            or 0
        )
        tag_active = len(db.get_tag_dictionary(only_active=True))
        posts = db.get_posts_count()

        needs_dept = dept_count == 0 or emp_count == 0
        needs_tags = tag_active == 0
        weak_staff = emp_count > 0 and emp_with_ht == 0

        return {
            "departments": dept_count,
            "employees": emp_count,
            "employees_with_hashtag": emp_with_ht,
            "active_tags": tag_active,
            "posts": posts,
            "needs_dept_sync": needs_dept,
            "needs_tag_dictionary": needs_tags,
            "weak_staff_hashtags": weak_staff,
            "ready_for_vk_import": not needs_dept and not needs_tags,
        }
    finally:
        if own and db:
            db.close()


def ensure_tag_dictionary(db: Database | None = None) -> int:
    """Заполняет словарь шаблонами по умолчанию, если он пуст."""
    own = db is None
    if own:
        db = Database()
    try:
        before = len(db.get_tag_dictionary(only_active=True))
        SmartTagger(db).ensure_dictionary()
        after = len(db.get_tag_dictionary(only_active=True))
        return max(0, after - before)
    finally:
        if own and db:
            db.close()
