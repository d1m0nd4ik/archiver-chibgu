"""
Подбор хэштегов по тексту поста на основе словаря вкладки «Тэги».
Только записи из tag_dictionary (активные): фраза в тексте → хэштег в хранилище.
"""
from __future__ import annotations

import re
from typing import Callable

from config.settings import MAX_TAGS
from core.database import Database
from core.logging_config import logger
from core.nlp_processor import (
    DEFAULT_TAG_DICTIONARY,
    KNOWN_PHRASES,
    dedupe_hashtags,
    normalize_hashtag,
    normalize_text,
)

ProgressCallback = Callable[[int, str], None] | None


def _norm_key(tag: str) -> str:
    return normalize_hashtag(tag).lower().replace('ё', 'е')


class SmartTagger:
    """Сопоставление текста поста со словарём тегов."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self._entries: list[dict] = []
        self._hashtag_by_key: dict[str, str] = {}
        self._ready = False

    def ensure_dictionary(self) -> None:
        self.db.normalize_tag_dictionary_hashtags()
        if not self.db.get_tag_dictionary(only_active=False):
            inserted = self.db.seed_default_tag_dictionary(DEFAULT_TAG_DICTIONARY)
            if inserted:
                logger.info("Словарь тегов: добавлено %s шаблонов", inserted)
        removed = self.db.prune_tag_dictionary()
        if removed:
            logger.info("Словарь тегов: удалено лишних записей %s", removed)
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.get_tag_dictionary(only_active=True)
        self._entries = sorted(
            rows,
            key=lambda r: (-int(r.get('weight') or 0), (r.get('phrase') or '')),
        )
        self._hashtag_by_key = {}
        for row in self._entries:
            tag = normalize_hashtag(row.get('hashtag', ''))
            if tag:
                self._hashtag_by_key[_norm_key(tag)] = tag
        self._ready = True

    def _phrase_in_text(self, phrase: str, norm_text: str) -> bool:
        phrase = normalize_text(phrase).strip()
        if not phrase:
            return False
        if ' ' not in phrase:
            pattern = rf'(?<!\w){re.escape(phrase)}(?!\w)'
            return bool(re.search(pattern, norm_text))
        pattern = rf'(?<!\w){re.escape(phrase)}(?!\w)'
        if re.search(pattern, norm_text):
            return True
        words = phrase.split()
        if len(words) < 2:
            return False
        window = len(words) + 6
        tokens = re.findall(r'[а-яёa-z0-9]+', norm_text)
        for i in range(len(tokens)):
            chunk = tokens[i:i + window]
            if len(chunk) < len(words):
                break
            for j in range(len(chunk) - len(words) + 1):
                if chunk[j:j + len(words)] == words:
                    return True
        return False

    def match_tags(
        self,
        text: str,
        reserved_hashtags: set[str] | None = None,
        exclude_words: set[str] | None = None,
        max_tags: int | None = None,
    ) -> list[str]:
        """
        Возвращает список хэштегов из словаря, подходящих к тексту.
        """
        if not self._ready:
            self.ensure_dictionary()

        text = (text or '').strip()
        if len(text) < 2:
            return []

        max_tags = max_tags or MAX_TAGS
        reserved = {_norm_key(h) for h in (reserved_hashtags or set())}
        exclude_words = exclude_words or set()

        norm_text = f" {normalize_text(text)} "
        scored: dict[str, float] = {}

        for row in self._entries:
            phrase = (row.get('phrase') or '').strip()
            if not phrase:
                continue
            if any(part in exclude_words for part in phrase.split()):
                continue
            if not self._phrase_in_text(phrase, norm_text):
                continue
            tag = normalize_hashtag(row.get('hashtag', ''))
            key = _norm_key(tag)
            if not tag or key in reserved:
                continue
            weight = float(row.get('weight') or 100)
            scored[key] = max(scored.get(key, 0.0), weight)
            parent_raw = (row.get('parent_hashtag') or '').strip()
            if parent_raw:
                parent_tag = normalize_hashtag(parent_raw)
                pk = _norm_key(parent_tag)
                if parent_tag and pk not in reserved:
                    scored[pk] = max(scored.get(pk, 0.0), weight * 0.95)

        for src, dst in KNOWN_PHRASES.items():
            if src not in norm_text:
                continue
            tag = normalize_hashtag(dst)
            key = _norm_key(tag)
            if key in self._hashtag_by_key:
                tag = self._hashtag_by_key[key]
            if key in reserved:
                continue
            scored[key] = max(scored.get(key, 0.0), 280.0)

        for raw in re.findall(r'#([A-Za-zА-Яа-яЁё0-9_]+)', text):
            tag = normalize_hashtag(raw)
            key = _norm_key(tag)
            if key not in self._hashtag_by_key or key in reserved:
                continue
            scored[key] = max(scored.get(key, 0.0), 300.0)

        if not scored:
            return []

        ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
        result = []
        for key, _ in ranked:
            tag = self._hashtag_by_key.get(key)
            if tag:
                result.append(tag)
            if max_tags is not None and len(result) >= max_tags:
                break
        return dedupe_hashtags(result)

    def matches_dictionary(self, tag: str) -> bool:
        if not self._ready:
            self.ensure_dictionary()
        return _norm_key(tag) in self._hashtag_by_key
