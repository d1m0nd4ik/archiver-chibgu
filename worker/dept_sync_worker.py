"""Фоновая синхронизация кафедр с сайта университета."""
from PySide6.QtCore import QThread, Signal, QObject

from core.employee_tagger import sync_departments_to_db
from core.logging_config import logger


class DeptSyncWorkerSignals(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)


class DeptSyncWorker(QThread):
    def __init__(self, extra_urls=None):
        super().__init__()
        self.extra_urls = extra_urls
        self.signals = DeptSyncWorkerSignals()
        self._cancelled = False

    def stop(self):
        self._cancelled = True

    def run(self):
        try:
            def cb(msg):
                if self._cancelled:
                    return
                self.signals.progress.emit(str(msg))

            result = sync_departments_to_db(
                extra_urls=self.extra_urls,
                progress_callback=cb,
            )
            if self._cancelled:
                result = {**result, 'cancelled': True}
            self.signals.finished.emit(result)
        except Exception as e:
            logger.error('DeptSyncWorker: %s', e, exc_info=True)
            self.signals.error.emit(str(e))
