"""Единая очередь фоновых задач с отменой и логом."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal, QThread

from core.logging_config import logger


@dataclass
class _QueuedJob:
    title: str
    factory: Callable[[], QThread]
    wire: Callable[[QThread], None]


class AppTaskQueue(QObject):
    """Последовательное выполнение долгих операций (одна активная задача)."""

    log_line = Signal(str)
    progress_percent = Signal(int)
    progress_message = Signal(str)
    busy_changed = Signal(bool)
    task_started = Signal(str)
    task_finished = Signal(str, bool)
    task_result = Signal(str, object)

    _instance: AppTaskQueue | None = None

    def __init__(self):
        super().__init__()
        self._queue: deque[_QueuedJob] = deque()
        self._current_thread: QThread | None = None
        self._current_title = ''
        self._busy = False
        self._last_task_ok = True

    @classmethod
    def instance(cls) -> AppTaskQueue:
        if cls._instance is None:
            cls._instance = AppTaskQueue()
        return cls._instance

    def is_busy(self) -> bool:
        return self._busy

    def pending_count(self) -> int:
        return len(self._queue) + (1 if self._busy else 0)

    def _set_busy(self, busy: bool):
        if self._busy != busy:
            self._busy = busy
            self.busy_changed.emit(busy)

    def _log(self, message: str):
        self.log_line.emit(message)
        logger.info("[TaskQueue] %s", message)

    def enqueue(self, title: str, factory: Callable[[], QThread], wire: Callable[[QThread], None]):
        self._queue.append(_QueuedJob(title=title, factory=factory, wire=wire))
        self._log(f"В очереди: {title} (ожидает: {len(self._queue)})")
        if not self._busy:
            self._run_next()

    def cancel_current(self):
        thread = self._current_thread
        if thread is None:
            return
        self._log(f"Отмена: {self._current_title}…")
        if hasattr(thread, 'stop'):
            thread.stop()
        elif hasattr(thread, 'is_running'):
            thread.is_running = False
        thread.requestInterruption()

    def clear_queue(self):
        self._queue.clear()
        self._log("Очередь очищена (текущая задача не прерывается)")

    def _run_next(self):
        if not self._queue:
            self._set_busy(False)
            self._current_thread = None
            self._current_title = ''
            return
        job = self._queue.popleft()
        self._current_title = job.title
        self._set_busy(True)
        self.task_started.emit(job.title)
        self._log(f"Старт: {job.title}")
        try:
            thread = job.factory()
            self._current_thread = thread
            job.wire(thread)
            thread.finished.connect(self._on_thread_finished)
            thread.start()
        except Exception as e:
            logger.error("TaskQueue start %s: %s", job.title, e, exc_info=True)
            self._log(f"Ошибка запуска «{job.title}»: {e}")
            self.task_finished.emit(job.title, False)
            self._run_next()

    def _on_worker_error(self, message: str):
        self._last_task_ok = False
        self._log(f"Ошибка: {message}")

    def _on_thread_finished(self):
        title = self._current_title
        ok = self._last_task_ok
        self._last_task_ok = True
        self._current_thread = None
        self.task_finished.emit(title, ok)
        self._run_next()

    # --- готовые фабрики ---

    def enqueue_download(self, token: str, group: str, count: int = 100):
        from worker.download_worker import DownloadWorker

        def factory():
            return DownloadWorker(token, group, count=count)

        def wire(w: DownloadWorker):
            w.signals.progress.connect(lambda m: self.progress_message.emit(m))
            w.signals.progress_value.connect(self.progress_percent.emit)
            w.signals.progress.connect(self._log)
            w.signals.finished.connect(lambda: self._log("Загрузка из ВК завершена"))
            w.signals.error.connect(self._on_worker_error)

        self.enqueue("Загрузка из ВКонтакте", factory, wire)

    def enqueue_retag(self):
        from worker.retag_worker import RetagWorker

        def factory():
            return RetagWorker()

        def wire(w: RetagWorker):
            def on_retag_progress(pct, msg):
                self.progress_percent.emit(pct)
                if msg:
                    self.progress_message.emit(msg)
                    self._log(f"{pct}% — {msg}")

            w.signals.progress.connect(on_retag_progress)
            w.signals.finished.connect(lambda n: self._log(f"Пересчёт тегов: обновлено {n} постов"))
            w.signals.error.connect(self._on_worker_error)

        self.enqueue("Пересчёт тегов архива", factory, wire)

    def enqueue_dept_sync(self, urls=None):
        from worker.dept_sync_worker import DeptSyncWorker

        def factory():
            return DeptSyncWorker(extra_urls=urls)

        def wire(w: DeptSyncWorker):
            w.signals.progress.connect(self._log)
            def on_dept_done(r):
                if not r.get('success', True):
                    self._on_worker_error(str(r.get('error', 'ошибка синхронизации')))
                else:
                    self._log("Синхронизация кафедр завершена")
                self.task_result.emit("Синхронизация кафедр", r)

            w.signals.finished.connect(on_dept_done)
            w.signals.error.connect(self._on_worker_error)

        self.enqueue("Синхронизация кафедр", factory, wire)

    def enqueue_wall_stats_refresh(self, token: str, group: str):
        from worker.download_worker import WallStatsRefreshWorker

        def factory():
            return WallStatsRefreshWorker(token, group)

        def wire(w: WallStatsRefreshWorker):
            w.signals.progress.connect(self._log)
            w.signals.finished.connect(
                lambda n, miss: self._log(
                    f"Метрики VK: обновлено {n}, не найдено {miss}"
                )
            )
            w.signals.error.connect(self._on_worker_error)

        self.enqueue("Обновление метрик из ВК", factory, wire)

    def enqueue_integrity_check(self, scan_orphans: bool = True):
        from worker.integrity_worker import IntegrityWorker

        def factory():
            return IntegrityWorker(scan_orphan_files=scan_orphans)

        def wire(w: IntegrityWorker):
            w.signals.progress.connect(self._log)
            w.signals.finished.connect(self._on_integrity_done)
            w.signals.error.connect(self._on_worker_error)

        self.enqueue("Проверка целостности архива", factory, wire)

    def _on_integrity_done(self, report: dict):
        missing = len(report.get('missing_files', []))
        orphans = len(report.get('orphan_files', []))
        empty = len(report.get('empty_paths', []))
        self._log(
            f"Проверка: отсутствует файлов {missing}, пустых путей {empty}, "
            f"лишних на диске {orphans}, постов без вложений {report.get('posts_without_attachments', 0)}"
        )
        self._last_integrity_report = report

    def last_integrity_report(self) -> dict | None:
        return getattr(self, '_last_integrity_report', None)
