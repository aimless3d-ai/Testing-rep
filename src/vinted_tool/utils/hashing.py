"""Hashes used for caching and duplicate detection."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps

_DHASH_SIZE = 8


def sha256_file(path: Path | str, chunk_size: int = 1 << 16) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dhash(path: Path | str, size: int = _DHASH_SIZE) -> str:
    """Difference hash: robust against re-compression, scaling and small edits."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        pixels = img.tobytes()  # one byte per pixel in mode "L"
    bits = 0
    for row in range(size):
        offset = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | int(pixels[offset + col] < pixels[offset + col + 1])
    return f"{bits:0{size * size // 4}x}"


def image_fingerprint(path: Path | str) -> dict[str, str]:
    return {"sha256": sha256_file(path), "phash": dhash(path)}
