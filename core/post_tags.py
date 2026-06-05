"""Сборка тегов поста: авторство, кафедра, хэштеги из словаря «Тэги»."""

import re

from core.logging_config import logger
from core.smart_tagger import SmartTagger
from core.content_tagger import ContentTagger
from core.nlp_processor import normalize_hashtag, dedupe_hashtags

_TEACHER_HT_RE = re.compile(r'#([A-Za-zА-Яа-яЁё0-9_]+)')


def is_teacher_hashtag_in_text(text: str, teacher_hashtag: str | None) -> bool:
    """Хэштег преподавателя должен буквально присутствовать в тексте поста."""
    if not text or not teacher_hashtag:
        return False
    key = normalize_hashtag(teacher_hashtag).lower().replace('ё', 'е')
    for raw in _TEACHER_HT_RE.findall(text):
        if normalize_hashtag(raw).lower().replace('ё', 'е') == key:
            return True
    return False

_content_tagger = ContentTagger()


def _norm_key(tag: str) -> str:
    return normalize_hashtag(tag).lower().replace('ё', 'е')


def resolve_author_and_department(tagger, text: str):
    teacher_hashtag = None
    department_hashtag = None
    author_employee_id = None
    author_department_id = None

    for raw in tagger.extract_teacher_hashtags(text):
        employee = tagger.find_employee_by_hashtag(raw)
        if employee:
            teacher_hashtag = employee.get('hashtag') or raw
            author_employee_id = employee.get('id')
            author_department_id = employee.get('department_id')
            department_hashtag = employee.get('department_hashtag')
            break

    # Авторство только при хэштеге преподавателя в тексте поста (не по ФИО в тексте)
    if not teacher_hashtag:
        department_hashtag = None
        author_employee_id = None
        author_department_id = None

    return (
        teacher_hashtag,
        department_hashtag,
        author_employee_id,
        author_department_id,
    )


def build_content_tags(
    text: str,
    smart: SmartTagger,
    tagger,
    reserved: set[str],
) -> list[str]:
    """Словарь + умное извлечение из текста для поиска."""
    exclude_words = set()
    for name in tagger.find_employees_in_text(text):
        for part in name.split():
            exclude_words.add(part.lower().replace('ё', 'е'))

    return _content_tagger.build(
        text, smart, exclude_words=exclude_words, reserved_hashtags=reserved
    )


def build_post_tags(text: str, tagger, smart: SmartTagger | None = None):
    """
    Возвращает:
    tags_string, teacher_hashtag, department_hashtag, author_employee_id, author_department_id
    """
    smart = smart or SmartTagger(tagger.db)
    smart.ensure_dictionary()
    text = text or ''

    teacher_hashtag, department_hashtag, author_employee_id, author_department_id = (
        resolve_author_and_department(tagger, text)
    )

    reserved = set()
    if teacher_hashtag:
        reserved.add(_norm_key(teacher_hashtag))
    if department_hashtag:
        reserved.add(_norm_key(department_hashtag))

    content = build_content_tags(text, smart, tagger, reserved)

    tags_string = ' '.join(dedupe_hashtags(content))
    return (
        tags_string,
        teacher_hashtag,
        department_hashtag,
        author_employee_id,
        author_department_id,
    )


def parse_manual_tags(tags_text: str) -> list[str]:
    """Извлекает хэштеги из строки (ручной ввод или поле тегов)."""
    if not tags_text:
        return []
    found = _TEACHER_HT_RE.findall(tags_text)
    if not found and '#' in tags_text:
        found = [t.lstrip('#') for t in tags_text.split() if t.startswith('#')]
    return dedupe_hashtags([normalize_hashtag(h) for h in found if h])


def apply_manual_tags_to_post(
    tags_str: str,
    manual_tags_text: str,
    tagger,
    text: str,
):
    """
    Объединяет автотеги с ручными и при необходимости уточняет автора по хэштегу.
    Возвращает tags_string, teacher_hashtag, department_hashtag, author_employee_id, author_department_id.
    """
    manual_list = parse_manual_tags(manual_tags_text)
    merged = dedupe_hashtags(parse_manual_tags(tags_str) + manual_list)
    tags_string = ' '.join(merged)

    teacher_ht, dept_ht, emp_id, dept_id = resolve_author_and_department(tagger, text)
    for tag in manual_list:
        emp = tagger.find_employee_by_hashtag(tag)
        if emp:
            teacher_ht = emp.get('hashtag') or tag
            emp_id = emp.get('id')
            dept_id = emp.get('department_id')
            dept_ht = emp.get('department_hashtag')
            break
    return tags_string, teacher_ht, dept_ht, emp_id, dept_id


def retag_all_posts(db, tagger, progress_callback=None, cancel_check=None) -> int:
    """Пересчитывает теги для всех постов в архиве."""
    smart = SmartTagger(db)
    smart.ensure_dictionary()
    updated = 0
    total = db.get_posts_count()
    if total <= 0:
        if progress_callback:
            progress_callback(100, "Нет постов для обновления")
        return 0

    if progress_callback:
        progress_callback(0, f"Пересчёт тегов: 0 из {total}…")

    offset = 0
    batch = 200
    while True:
        if cancel_check and cancel_check():
            if progress_callback:
                progress_callback(updated and min(99, int(100 * updated / total)) or 0, "Отменено")
            return updated
        rows = db.get_posts_paginated(limit=batch, offset=offset)
        if not rows:
            break
        for row in rows:
            if cancel_check and cancel_check():
                if progress_callback:
                    progress_callback(min(99, int(100 * updated / max(total, 1))), "Отменено")
                return updated
            post_id = row[0]
            text = row[3] or ''
            try:
                tags_str, teacher_ht, dept_ht, emp_id, dept_id = build_post_tags(
                    text, tagger, smart
                )
                db.update_post_tags(
                    post_id,
                    tags=tags_str,
                    teacher_hashtag=teacher_ht,
                    department_hashtag=dept_ht,
                    author_employee_id=emp_id,
                    author_department_id=dept_id,
                )
                updated += 1
                if progress_callback:
                    pct = min(99, int(100 * updated / total))
                    progress_callback(
                        pct,
                        f"Обновлено {updated} из {total} (пост {post_id})…",
                    )
            except Exception as e:
                logger.error("retag post %s: %s", post_id, e, exc_info=True)
        if len(rows) < batch:
            break
        offset += batch

    if progress_callback:
        progress_callback(100, f"Готово: обновлено {updated} постов")
    return updated
