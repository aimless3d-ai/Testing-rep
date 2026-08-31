# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec – builds VintedAutoListingTool.exe (one folder + one file)."""
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR.parent
SRC = ROOT / "src"

datas = [
    (str(SRC / "vinted_tool" / "assets"), "vinted_tool/assets"),
    (str(SRC / "vinted_tool" / "database" / "schema.sql"), "vinted_tool/database"),
]

hiddenimports = collect_submodules("vinted_tool")

# Qt modules the app does not use – leaving them out keeps the build small.
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQml", "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSerialPort",
    "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtSql",
    "tkinter", "matplotlib", "numpy", "scipy", "pandas", "IPython", "pytest",
]

a = Analysis(
    [str(SRC / "vinted_tool" / "app" / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VintedAutoListingTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(SRC / "vinted_tool" / "assets" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VintedAutoListingTool",
)
