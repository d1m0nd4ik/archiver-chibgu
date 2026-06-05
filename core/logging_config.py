import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import _PROJECT_ROOT

LOG_DIR = Path(_PROJECT_ROOT) / "logs"
APP_LOG = LOG_DIR / "vk_archiver.log"
ERROR_LOG = LOG_DIR / "errors.log"
SYNC_LOG = Path(_PROJECT_ROOT) / "sync_log.txt"


def rotate_sync_log(max_bytes: int = 512_000, backup_count: int = 3) -> None:
    """Ротация sync_log.txt в sync_log.txt.1 …"""
    if not SYNC_LOG.is_file() or SYNC_LOG.stat().st_size <= max_bytes:
        return
    for i in range(backup_count, 0, -1):
        src = SYNC_LOG.with_suffix(f".txt.{i}" if i > 1 else ".txt.1")
        if i == 1:
            src = Path(str(SYNC_LOG) + ".1")
        dst_num = i + 1
        if dst_num <= backup_count:
            dst = Path(str(SYNC_LOG) + f".{dst_num}")
            if src.is_file():
                if dst.is_file():
                    dst.unlink()
                src.rename(dst)
    backup = Path(str(SYNC_LOG) + ".1")
    if backup.is_file():
        backup.unlink()
    SYNC_LOG.rename(backup)
    SYNC_LOG.write_text("", encoding="utf-8")


def clear_error_log() -> None:
    """Очищает logs/errors.log."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_LOG.write_text("", encoding="utf-8")


def get_recent_errors(limit: int = 30) -> list[str]:
    if not ERROR_LOG.is_file():
        return []
    try:
        lines = ERROR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        err = [ln for ln in lines if "| ERROR" in ln or "| CRITICAL" in ln]
        return err[-limit:]
    except Exception:
        return []


def setup_logger(name="VKArchiver", level=logging.INFO):
    """Консоль + ротируемые файлы logs/vk_archiver.log и logs/errors.log."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(APP_LOG, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    eh = RotatingFileHandler(ERROR_LOG, maxBytes=400_000, backupCount=3, encoding="utf-8")
    eh.setLevel(logging.ERROR)
    eh.setFormatter(fmt)
    logger.addHandler(eh)

    return logger


logger = setup_logger()