# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: VK Archiver CHIBGU (режим onedir — exe + папка _internal)."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
PROJECT = Path(SPECPATH)

_app_name = "VK_Archiver_CHIBGU"
_icon = PROJECT / "assets" / "Logo_programm.ico"

_packages = ("PySide6", "natasha", "pymorphy3", "pymorphy3_dicts_ru")
_datas = [("assets", "assets")]
_binaries = []
_hidden = [
    "PIL",
    "PIL.Image",
    "vk_api",
    "yt_dlp",
    "bs4",
    "openpyxl",
    "docx",
    "browser_cookie3",
    "dotenv",
    "requests",
]

for _pkg in _packages:
    _pkg_datas, _pkg_binaries, _pkg_hidden = collect_all(_pkg)
    _datas += _pkg_datas
    _binaries += _pkg_binaries
    _hidden += _pkg_hidden

_hidden += collect_submodules("core")
_hidden += collect_submodules("ui")
_hidden += collect_submodules("worker")
_hidden += collect_submodules("services")
_hidden = sorted(set(_hidden))

a = Analysis(
    [str(PROJECT / "main.py")],
    pathex=[str(PROJECT)],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=_app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_icon) if _icon.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=_app_name,
)
