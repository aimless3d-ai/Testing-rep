"""Filesystem helpers: safe names, unique paths, folder opening."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                          "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})
_INVALID = re.compile(r"[^A-Za-z0-9._-]+")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".heic"}


def slugify(text: str, *, max_length: int = 60, fallback: str = "produkt") -> str:
    text = (text or "").translate(_UMLAUTS)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _INVALID.sub("-", text).strip("-_.")
    text = re.sub(r"-{2,}", "-", text)
    return (text[:max_length].strip("-_.") or fallback).lower()


def unique_path(path: Path) -> Path:
    """Return *path* or the first free ``name-2.ext`` style variant."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    for counter in range(2, 10_000):
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Kein freier Dateiname für {path}")


def is_image(path: Path | str) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


def collect_images(paths: list[Path | str]) -> list[Path]:
    """Expand a mixed list of files and folders into a sorted list of images."""
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(p for p in path.rglob("*") if p.is_file() and is_image(p)))
        elif path.is_file() and is_image(path):
            found.append(path)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def open_in_explorer(path: Path | str) -> bool:
    """Open a folder in the OS file manager. Returns ``False`` if unsupported."""
    path = Path(path)
    target = str(path if path.is_dir() else path.parent)
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", target], check=False)
        else:
            subprocess.run(["xdg-open", target], check=False)
        return True
    except (OSError, AttributeError):
        return False
