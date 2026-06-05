"""Поиск возможных дубликатов перед ручным добавлением."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime

from core.database import Database


def _text_key(text: str) -> str:
    t = " ".join((text or "").split()).strip().lower()
    return t[:500] if t else ""


def _file_fingerprint(paths: list[str]) -> str:
    parts = []
    for p in sorted(paths):
        if not os.path.isfile(p):
            continue
        try:
            st = os.stat(p)
            parts.append(f"{os.path.basename(p)}:{st.st_size}")
        except OSError:
            parts.append(os.path.basename(p))
    return "|".join(parts)


def find_similar_posts(
    *,
    posted_at: datetime,
    text: str = "",
    file_paths: list[str] | None = None,
    db: Database | None = None,
    limit: int = 5,
) -> list[dict]:
    own = db is None
    if own:
        db = Database()
    try:
        date_str = posted_at.strftime("%Y-%m-%d")
        candidates = db.find_posts_by_date_prefix(date_str, limit=200)
        text_key = _text_key(text)
        fp = _file_fingerprint(file_paths or [])
        results: list[dict] = []
        for post in candidates:
            score = 0
            reasons: list[str] = []
            if text_key and _text_key(post.get("text")) == text_key:
                score += 3
                reasons.append("тот же текст")
            post_fp = _file_fingerprint(
                [p.strip() for p in (post.get("media_paths") or "").split(",") if p.strip()]
            )
            if fp and post_fp and fp == post_fp:
                score += 2
                reasons.append("те же файлы")
            if (post.get("date") or "")[:10] == date_str:
                score += 1
            if score >= 2:
                results.append({
                    "original_post_id": post["original_post_id"],
                    "date": post.get("date"),
                    "text_preview": (post.get("text") or "")[:120],
                    "score": score,
                    "reasons": ", ".join(reasons),
                })
        results.sort(key=lambda x: -x["score"])
        return results[:limit]
    finally:
        if own and db:
            db.close()
