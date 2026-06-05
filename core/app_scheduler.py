"""Планировщик задач, пока приложение запущено (не требует работы 24/7)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import _PROJECT_ROOT

STATE_PATH = Path(_PROJECT_ROOT) / "scheduler_state.json"


def load_scheduler_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_scheduler_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_due(interval: str, last_run_iso: str | None) -> bool:
    """interval: 'daily' | 'weekly' | 'off'"""
    if interval in (None, "", "off"):
        return False
    if not last_run_iso:
        return True
    try:
        last = datetime.fromisoformat(last_run_iso)
    except ValueError:
        return True
    delta = timedelta(days=7 if interval == "weekly" else 1)
    return datetime.now() - last >= delta


def mark_ran(task_key: str) -> None:
    state = load_scheduler_state()
    state[task_key] = datetime.now().isoformat(timespec="seconds")
    save_scheduler_state(state)
