"""Пути приложения: пользовательские данные и ресурсы сборки."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _dev_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_data_root() -> Path:
    """Archive.db, Exports_data, .env, logs — рядом с exe в сборке PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _dev_root()


def get_bundle_root() -> Path:
    """Ресурсы из сборки (assets и т.д.) — _MEIPASS или корень проекта."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _dev_root()


def get_assets_dir() -> Path:
    return get_bundle_root() / "assets"


def get_data_root_str() -> str:
    return os.fspath(get_data_root())
