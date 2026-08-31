"""Locates bundled assets both from source and from a PyInstaller bundle."""
from __future__ import annotations

import sys
from pathlib import Path


def assets_dir() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        packed = Path(bundle) / "vinted_tool" / "assets"
        if packed.is_dir():
            return packed
        return Path(bundle) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def icon_path() -> Path | None:
    for name in ("app.ico", "app.png"):
        candidate = assets_dir() / name
        if candidate.is_file():
            return candidate
    return None
