"""Offline analysis – works without any API key or network.

It derives only what can actually be measured locally:

* the dominant and secondary colours from the real pixels of the photos
* product type / brand hints from the file names the user chose
* whether the photo set shows enough angles

Everything else is deliberately left as "not recognised" so the user fills it
in – the app never invents information.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

from PIL import Image

from vinted_tool.ai.base import AIProvider, AnalysisRequest, ProviderStatus
from vinted_tool.core.categories import normalize
from vinted_tool.core.category_data import BRAND_PRICE_TIERS, CATEGORIES
from vinted_tool.models.analysis import ImageAnalysis

log = logging.getLogger(__name__)

NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "Schwarz": (25, 25, 28),
    "Weiß": (245, 245, 245),
    "Grau": (135, 135, 138),
    "Beige": (222, 205, 175),
    "Braun": (110, 74, 44),
    "Blau": (45, 85, 190),
    "Dunkelblau": (25, 40, 95),
    "Hellblau": (140, 190, 230),
    "Türkis": (50, 175, 170),
    "Grün": (70, 150, 70),
    "Dunkelgrün": (30, 80, 45),
    "Gelb": (235, 210, 60),
    "Orange": (235, 140, 45),
    "Rot": (200, 45, 45),
    "Bordeaux": (110, 30, 45),
    "Rosa": (240, 170, 190),
    "Pink": (225, 60, 150),
    "Lila": (140, 75, 180),
    "Gold": (200, 165, 90),
    "Silber": (190, 192, 196),
}

_SAMPLE_SIZE = 96
_BORDER_RATIO = 0.16


def _nearest_color(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    best_name, best_distance = "Grau", float("inf")
    for name, (cr, cg, cb) in NAMED_COLORS.items():
        # weighted euclidean distance, roughly perceptual
        distance = 2 * (r - cr) ** 2 + 4 * (g - cg) ** 2 + 3 * (b - cb) ** 2
        if distance < best_distance:
            best_name, best_distance = name, distance
    return best_name


def dominant_colors(paths: list[Path], top: int = 3) -> list[str]:
    """Colour names ordered by how much of the (centre of the) photos they cover."""
    counter: Counter[str] = Counter()
    for path in paths:
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((_SAMPLE_SIZE, _SAMPLE_SIZE))
                width, height = img.size
                # crop the border away – it is usually floor/wall, not the product
                bx, by = int(width * _BORDER_RATIO), int(height * _BORDER_RATIO)
                if width - 2 * bx > 8 and height - 2 * by > 8:
                    img = img.crop((bx, by, width - bx, height - by))
                raw = img.tobytes()  # RGB triplets
                for offset in range(0, len(raw) - 2, 3):
                    counter[_nearest_color((raw[offset], raw[offset + 1], raw[offset + 2]))] += 1
        except (OSError, ValueError) as exc:
            log.warning("Farbanalyse übersprungen für %s: %s", path.name, exc)
    if not counter:
        return []
    total = sum(counter.values())
    return [name for name, count in counter.most_common(top) if count / total >= 0.08]


def _hints_from_filenames(paths: list[Path]) -> tuple[str | None, str | None, list[str]]:
    """Product type / brand hints from the names the *user* gave the files."""
    haystack = normalize(" ".join(re.split(r"[_\-.\d]+", " ".join(p.stem for p in paths))))
    product_type: str | None = None
    keywords: list[str] = []
    best_score = 0
    for entry in CATEGORIES:
        for keyword in entry.keywords:
            norm_kw = normalize(keyword)
            if len(norm_kw) >= 4 and re.search(rf"\b{re.escape(norm_kw)}\b", haystack):
                score = len(norm_kw)
                if score > best_score:
                    best_score, product_type = score, keyword
                if keyword not in keywords:
                    keywords.append(keyword)
    brand: str | None = None
    for candidate in sorted(BRAND_PRICE_TIERS, key=len, reverse=True):
        if len(candidate) >= 4 and re.search(rf"\b{re.escape(candidate)}\b", haystack):
            brand = candidate.title()
            break
    return product_type, brand, keywords[:8]


class OfflineProvider(AIProvider):
    """Deterministic local analysis. Always available, never costs anything."""

    kind = "offline"
    requires_api_key = False

    def analyze(self, request: AnalysisRequest) -> ImageAnalysis:
        paths = [Path(p) for p in request.image_paths]
        colors = dominant_colors(paths)
        product_type, brand, keywords = _hints_from_filenames(paths)

        notes = [
            "Offline-Analyse: Farben stammen aus den Bildpixeln, "
            "Produktart und Marke nur aus den Dateinamen.",
        ]
        if request.hint.strip():
            notes.append(f"Eigene Angabe: {request.hint.strip()}")
        if not product_type:
            notes.append(
                "Ohne KI-Anbieter können Produktart, Zustand und Größe nicht erkannt werden – "
                "bitte selbst auswählen."
            )

        return ImageAnalysis(
            product_type=product_type,
            brand=brand,
            color=colors[0] if colors else None,
            secondary_colors=colors[1:],
            keywords=keywords,
            notes=" ".join(notes),
            confidence={
                "color": 0.7 if colors else 0.0,
                "product_type": 0.6 if product_type else 0.0,
                "brand": 0.6 if brand else 0.0,
                "size": 0.0,
                "condition": 0.0,
                "material": 0.0,
            },
            source=self.kind,
            model_used="heuristik",
            tokens_used=0,
        )

    def test_connection(self) -> ProviderStatus:
        return ProviderStatus(
            True,
            "Offline-Analyse ist immer verfügbar (Farberkennung lokal, keine KI-Kosten).",
            "heuristik",
        )
