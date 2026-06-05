"""Фоновый пересчёт тегов архива по словарю."""
from PySide6.QtCore import QThread, Signal, QObject

from core.database import Database
from core.employee_tagger import EmployeeTagger
from core.logging_config import logger
from core.post_tags import retag_all_posts


class RetagWorkerSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(int)
    error = Signal(str)


class RetagWorker(QThread):
    def __init__(self):
        super().__init__()
        self.signals = RetagWorkerSignals()
        self._db = Database()
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            tagger = EmployeeTagger(self._db, refresh_on_init=False)
            count = retag_all_posts(
                self._db,
                tagger,
                progress_callback=self.signals.progress.emit,
                cancel_check=lambda: self._cancelled,
            )
            self.signals.finished.emit(count)
        except Exception as e:
            logger.error("RetagWorker: %s", e, exc_info=True)
            self.signals.error.emit(str(e))
