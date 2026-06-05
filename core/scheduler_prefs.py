"""Настройки планировщика (работает, пока приложение запущено)."""
from __future__ import annotations

import json
from pathlib import Path

from config.settings import _PROJECT_ROOT

PREFS_PATH = Path(_PROJECT_ROOT) / "scheduler_prefs.json"


def load_scheduler_prefs() -> dict:
    default = {
        "enabled": False,
        "interval": "weekly",
        "run_dept_sync": True,
        "run_retag_after_prep": True,
        "run_vk_download": True,
        "run_vk_stats": True,
    }
    if not PREFS_PATH.is_file():
        return default
    try:
        data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
        return {**default, **(data if isinstance(data, dict) else {})}
    except Exception:
        return default


def save_scheduler_prefs(prefs: dict) -> None:
    PREFS_PATH.write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
