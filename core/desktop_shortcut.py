"""Создание ярлыка на рабочем столе (Windows)."""
import ctypes
import subprocess
import sys
from pathlib import Path

from core.app_icon import (
    APP_DISPLAY_NAME,
    ensure_app_icons,
    get_launch_target,
    get_project_root,
)
from core.logging_config import logger

_SHCNE_ASSOCCHANGED = 0x08000000
_SHCNE_UPDATEITEM = 0x00002000
_SHCNF_IDLIST = 0x0000
_SHCNF_PATHW = 0x0001
_SHCNF_FLUSHNOWAIT = 0x3000


def get_primary_desktop_dir() -> Path:
    """Первый доступный каталог рабочего стола пользователя."""
    return _desktop_dirs()[0]


def _desktop_dirs() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "Рабочий стол",
        home / "OneDrive" / "Рабочий стол",
    ]
    seen: set[Path] = set()
    dirs: list[Path] = []
    for path in candidates:
        resolved = path.resolve() if path.exists() else path
        if resolved in seen:
            continue
        seen.add(resolved)
        if path.is_dir():
            dirs.append(path)
    if not dirs:
        fallback = home / "Desktop"
        fallback.mkdir(parents=True, exist_ok=True)
        dirs.append(fallback)
    return dirs


def _shortcut_icon_location(icon_path: str) -> str:
    if "," not in icon_path:
        return f"{icon_path},0"
    return icon_path


def _refresh_shell_icons(shortcut_path: Path | None = None) -> None:
    if sys.platform != "win32":
        return
    shell32 = ctypes.windll.shell32
    if shortcut_path is not None:
        shell32.SHChangeNotify(
            _SHCNE_UPDATEITEM,
            _SHCNF_PATHW | _SHCNF_FLUSHNOWAIT,
            str(shortcut_path),
            None,
        )
    shell32.SHChangeNotify(_SHCNE_ASSOCCHANGED, _SHCNF_IDLIST, None, None)


def _write_shortcut(shortcut_path: Path) -> None:
    target, arguments = get_launch_target()
    workdir = str(get_project_root())
    icon_location = _shortcut_icon_location(str(ensure_app_icons()))
    ps = f"""
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut({str(shortcut_path)!r})
$sc.TargetPath = {target!r}
$sc.Arguments = {arguments!r}
$sc.WorkingDirectory = {workdir!r}
$sc.IconLocation = ""
$sc.Save()
$sc.IconLocation = {icon_location!r}
$sc.Description = {APP_DISPLAY_NAME!r}
$sc.Save()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        logger.error("Shortcut creation failed: %s", err)
        raise RuntimeError(err or "Не удалось создать ярлык")

    if not shortcut_path.exists():
        raise RuntimeError("Ярлык не был создан")

    _refresh_shell_icons(shortcut_path)


def create_desktop_shortcut() -> Path:
    if sys.platform != "win32":
        raise OSError("Ярлык можно создать только в Windows.")

    shortcut_name = f"{APP_DISPLAY_NAME}.lnk"
    updated: list[Path] = []
    for desktop in _desktop_dirs():
        desktop.mkdir(parents=True, exist_ok=True)
        shortcut_path = desktop / shortcut_name
        _write_shortcut(shortcut_path)
        updated.append(shortcut_path)

    return updated[0]