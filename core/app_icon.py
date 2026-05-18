"""Иконка приложения и логотипы для тем."""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

APP_DISPLAY_NAME = "VK Archiver CHIBGU"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

LOGO_WHITE = ASSETS_DIR / "Logo_white.png"      # шапка — тёмная тема
LOGO_BLACK = ASSETS_DIR / "Logo_black.png"      # шапка — светлая тема
LOGO_PROGRAM = ASSETS_DIR / "Logo_programm.png"  # окно, панель задач, ярлык
LOGO_PROGRAM_ICO = ASSETS_DIR / "Logo_programm.ico"


def _normalize_rgba_transparency(img):
    from PIL import Image

    rgba = img.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                pixels[x, y] = (0, 0, 0, 0)
    return rgba


def _ico_has_transparency() -> bool:
    if not LOGO_PROGRAM_ICO.exists():
        return False
    try:
        from PIL import Image

        sample = Image.open(LOGO_PROGRAM_ICO).convert("RGBA")
        return sample.getpixel((0, 0))[3] == 0
    except Exception:
        return False


def _build_program_ico() -> None:
    from PIL import Image

    img = _normalize_rgba_transparency(Image.open(LOGO_PROGRAM))
    img.save(LOGO_PROGRAM, format="PNG")
    img.save(
        LOGO_PROGRAM_ICO,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        bitmap_format="png",
    )


def _ensure_program_ico() -> None:
    if not LOGO_PROGRAM.exists():
        return
    if LOGO_PROGRAM_ICO.exists():
        if (
            LOGO_PROGRAM_ICO.stat().st_mtime >= LOGO_PROGRAM.stat().st_mtime
            and _ico_has_transparency()
        ):
            return
    try:
        _build_program_ico()
    except Exception:
        pass


def ensure_app_icons() -> Path:
    """Проверяет наличие файлов иконки программы."""
    _ensure_program_ico()
    if LOGO_PROGRAM_ICO.exists():
        return LOGO_PROGRAM_ICO
    if LOGO_PROGRAM.exists():
        return LOGO_PROGRAM
    raise FileNotFoundError(
        f"Не найден {LOGO_PROGRAM.name}. Положите логотипы в папку assets/."
    )


def get_header_logo_path(theme: str = "dark") -> Path:
    if theme == "light" and LOGO_BLACK.exists():
        return LOGO_BLACK
    if LOGO_WHITE.exists():
        return LOGO_WHITE
    if LOGO_BLACK.exists():
        return LOGO_BLACK
    return ensure_app_icons()


def get_icon_path() -> str:
    return str(ensure_app_icons())


def get_app_icon() -> QIcon:
    path = get_icon_path()
    icon = QIcon(path)
    if LOGO_PROGRAM.exists():
        icon.addFile(str(LOGO_PROGRAM))
    return icon


def get_logo_pixmap(size: int = 48, theme: str = "dark") -> QPixmap:
    pixmap = QPixmap(str(get_header_logo_path(theme)))
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_launch_target():
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve()), ""

    main_py = PROJECT_ROOT / "main.py"
    python = Path(sys.executable).resolve()
    pythonw = python.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else python
    return str(launcher), f'"{main_py}"'
