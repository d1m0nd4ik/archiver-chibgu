"""Сохранённые пресеты фильтров поиска (JSON)."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from config.settings import _PROJECT_ROOT
from core.post_search import PostSearchParams

PRESETS_PATH = Path(_PROJECT_ROOT) / "search_presets.json"


def _params_to_dict(p: PostSearchParams) -> dict:
    d = asdict(p)
    d.pop("limit", None)
    d.pop("offset", None)
    return d


def _dict_to_params(d: dict) -> PostSearchParams:
    return PostSearchParams(
        query=d.get("query", ""),
        date_from=d.get("date_from"),
        date_to=d.get("date_to"),
        tag_hashtag=d.get("tag_hashtag"),
        department_id=d.get("department_id"),
        author_employee_id=d.get("author_employee_id"),
        media_type=d.get("media_type"),
        post_source=d.get("post_source"),
        sort=d.get("sort", "date_desc"),
    )


def list_presets() -> list[dict]:
    if not PRESETS_PATH.is_file():
        return []
    try:
        data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_preset(name: str, params: PostSearchParams) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    items = list_presets()
    entry = {"name": name, "params": _params_to_dict(params)}
    items = [e for e in items if e.get("name") != name]
    items.append(entry)
    PRESETS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def delete_preset(name: str) -> bool:
    items = [e for e in list_presets() if e.get("name") != name]
    PRESETS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def load_preset(name: str) -> PostSearchParams | None:
    for e in list_presets():
        if e.get("name") == name:
            return _dict_to_params(e.get("params") or {})
    return None
