"""Фоновая проверка целостности архива."""
from PySide6.QtCore import QThread, Signal, QObject

from core.archive_integrity import check_archive_integrity
from core.database import Database
from core.logging_config import logger


class IntegrityWorkerSignals(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)


class IntegrityWorker(QThread):
    def __init__(self, scan_orphan_files: bool = True):
        super().__init__()
        self.scan_orphan_files = scan_orphan_files
        self.signals = IntegrityWorkerSignals()
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            self.signals.progress.emit("Проверка вложений в базе…")
            db = Database()
            if self._cancelled:
                return
            report = check_archive_integrity(
                db,
                scan_orphan_files=self.scan_orphan_files,
            )
            db.close()
            self.signals.finished.emit(report)
        except Exception as e:
            logger.error('IntegrityWorker: %s', e, exc_info=True)
            self.signals.error.emit(str(e))
