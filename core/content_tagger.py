"""
Умная генерация контентных хэштегов для поиска:
- словарь вкладки «Тэги» (в т.ч. многословные фразы);
- самодельные из текста — только одиночные слова, не более MAX_CUSTOM_TAGS.
"""
from __future__ import annotations

import re

from config.settings import MAX_CUSTOM_TAGS, MIN_WORD_LENGTH
from core.nlp_processor import (
    NLPProcessor,
    STOP_WORDS,
    dedupe_hashtags,
    normalize_hashtag,
    normalize_text,
)
from core.logging_config import logger
from core.smart_tagger import SmartTagger

PHRASE_SKIP_WORDS = frozenset(
    STOP_WORDS
    | {
        'и', 'а', 'но', 'или', 'да', 'же', 'ли', 'бы', 'что', 'как', 'то',
        'это', 'тот', 'та', 'те', 'так', 'у', 'в', 'во', 'на', 'над', 'под',
        'с', 'со', 'по', 'для', 'от', 'до', 'из', 'к', 'ко', 'о', 'об', 'обо',
        'при', 'без', 'про', 'не', 'ни', 'уже', 'ещё', 'еще', 'все', 'всё',
        'вся', 'весь', 'сам', 'сама', 'само', 'сами', 'там', 'тут', 'здесь',
    }
)


def _norm_key(tag: str) -> str:
    return normalize_hashtag(tag).lower().replace('ё', 'е')


def _is_single_word_key(key: str) -> bool:
    return '_' not in key.lstrip('#')


def _tokenize_content(text: str) -> list[str]:
    return re.findall(r'[а-яёa-z0-9]+', normalize_text(text))


def _is_content_token(word: str) -> bool:
    if not word or len(word) < MIN_WORD_LENGTH or word.isdigit():
        return False
    return word not in PHRASE_SKIP_WORDS


class ContentTagger:
    def __init__(self):
        self._nlp = NLPProcessor()

    def _extract_word_candidates(self, text: str, exclude_words: set[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        for idx, word in enumerate(_tokenize_content(text)):
            if word in exclude_words or not _is_content_token(word):
                continue
            norm = self._nlp._normal_form(word)
            if not norm or not self._nlp._is_valid_normal_form(norm, 'NOUN'):
                continue
            tag = normalize_hashtag(norm)
            key = _norm_key(tag)
            if not _is_single_word_key(key):
                continue
            scores[key] = max(scores.get(key, 0.0), 1.2 + max(0.0, 0.5 - idx * 0.02))
        return scores

    def _extract_natasha_word_candidates(self, text: str, exclude_words: set[str]) -> dict[str, float]:
        if not self._nlp.natasha_ready:
            return {}
        result: dict[str, float] = {}
        raw = self._nlp._extract_candidates_natasha(text, exclude_words)
        for token, score in raw.items():
            key = _norm_key(normalize_hashtag(token))
            if not _is_single_word_key(key):
                continue
            parts = key.lstrip('#').split('_')
            if len(parts) != 1 or parts[0] in PHRASE_SKIP_WORDS:
                continue
            result[key] = score
        return result

    def build(
        self,
        text: str,
        smart: SmartTagger,
        exclude_words: set[str] | None = None,
        reserved_hashtags: set[str] | None = None,
        max_custom_tags: int | None = None,
    ) -> list[str]:
        text = (text or '').strip()
        if len(text) < 2:
            return []

        max_custom = max_custom_tags or MAX_CUSTOM_TAGS
        exclude_words = exclude_words or set()
        reserved = {_norm_key(h) for h in (reserved_hashtags or set())}

        dictionary_tags = smart.match_tags(
            text,
            reserved_hashtags=reserved,
            exclude_words=exclude_words,
            max_tags=None,
        )
        dict_keys = {_norm_key(t) for t in dictionary_tags}

        custom_scored: dict[str, float] = {}
        try:
            for source in (
                self._extract_natasha_word_candidates,
                self._extract_word_candidates,
            ):
                for key, score in source(text, exclude_words).items():
                    if key in reserved or key in dict_keys:
                        continue
                    if not _is_single_word_key(key):
                        continue
                    if smart.matches_dictionary(key.lstrip('#')):
                        continue
                    custom_scored[key] = max(custom_scored.get(key, 0.0), score)
        except Exception as e:
            logger.warning("Извлечение самодельных тегов: %s", e)

        custom_tags: list[str] = []
        if custom_scored:
            ranked = sorted(custom_scored.items(), key=lambda kv: (-kv[1], kv[0]))
            for key, _ in ranked:
                tag = normalize_hashtag(key.lstrip('#'))
                if tag and _norm_key(tag) not in reserved and _norm_key(tag) not in dict_keys:
                    custom_tags.append(tag)
                if len(custom_tags) >= max_custom:
                    break

        return dedupe_hashtags(dictionary_tags + custom_tags)
