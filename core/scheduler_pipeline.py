"""Цепочка задач планировщика: справочники → теги → ВК."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from core.app_scheduler import is_due, load_scheduler_state
from core.archive_prerequisites import assess_prerequisites, ensure_tag_dictionary
from core.scheduler_prefs import load_scheduler_prefs


@dataclass
class SchedulerCyclePlan:
    token: str
    group: str
    interval: str
    steps: deque = field(default_factory=deque)
    retag_after_prep: bool = False

    def summary(self) -> str:
        names = {
            "dept_sync": "синхронизация кафедр",
            "ensure_tags": "словарь тегов",
            "retag": "пересчёт тегов постов",
            "vk_download": "догрузка из ВК",
            "vk_stats": "метрики из ВК",
        }
        return " → ".join(names.get(s, s) for s in list(self.steps))


def build_scheduler_cycle(
    *,
    token: str,
    group: str,
    manual: bool = False,
) -> SchedulerCyclePlan | None:
    """
    Собирает очередь шагов. Сначала справочники (кафедры, преподаватели, теги),
    при необходимости retag, затем задачи ВК.
    """
    prefs = load_scheduler_prefs()
    if not prefs.get("enabled") and not manual:
        return None
    if not token.strip() or not group.strip():
        return None

    db_assess = assess_prerequisites()
    state = load_scheduler_state()
    interval = prefs.get("interval", "weekly")

    steps: list[str] = []

    if db_assess["needs_dept_sync"]:
        steps.append("dept_sync")
    elif prefs.get("run_dept_sync", True) and is_due(interval, state.get("dept_sync")):
        steps.append("dept_sync")

    steps.append("ensure_tags")

    retag_after = bool(
        prefs.get("run_retag_after_prep", True)
        and db_assess["posts"] > 0
        and (
            db_assess["needs_dept_sync"]
            or db_assess["needs_tag_dictionary"]
            or db_assess["weak_staff_hashtags"]
        )
    )

    if retag_after:
        steps.append("retag")

    # ВК — только после подготовки в этом же цикле или если справочники уже готовы
    prep_in_cycle = bool(steps)

    if (db_assess["ready_for_vk_import"] or prep_in_cycle):
        if prefs.get("run_vk_download") and is_due(interval, state.get("vk_download")):
            steps.append("vk_download")
        if prefs.get("run_vk_stats") and is_due(interval, state.get("vk_stats")):
            steps.append("vk_stats")

    if not steps:
        return None

    plan = SchedulerCyclePlan(
        token=token.strip(),
        group=group.strip(),
        interval=interval,
        steps=deque(steps),
        retag_after_prep=retag_after,
    )
    return plan
