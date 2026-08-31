"""Duplicate detection based on exact hashes and perceptual hashes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


def hamming_distance(a: str | None, b: str | None) -> int:
    """Distance between two hex perceptual hashes; 999 when incomparable."""
    if not a or not b or len(a) != len(b):
        return 999
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 999


@dataclass(frozen=True, slots=True)
class DuplicateHit:
    listing_id: int
    listing_title: str
    image_path: str
    distance: int
    exact: bool

    @property
    def description(self) -> str:
        kind = "identisches Bild" if self.exact else f"sehr ähnliches Bild (Abstand {self.distance})"
        title = self.listing_title or f"Anzeige #{self.listing_id}"
        return f"{kind} wie in „{title}“"


def find_duplicates(
    candidates: Iterable[dict[str, Any]],
    known: Iterable[dict[str, Any]],
    threshold: int = 6,
) -> list[DuplicateHit]:
    """Compare new images (``phash``/``sha256``) against stored fingerprints."""
    known_list = list(known)
    hits: dict[tuple[int, str], DuplicateHit] = {}
    for candidate in candidates:
        for entry in known_list:
            exact = bool(
                candidate.get("sha256")
                and entry.get("sha256")
                and candidate["sha256"] == entry["sha256"]
            )
            distance = hamming_distance(candidate.get("phash"), entry.get("phash"))
            if not exact and distance > threshold:
                continue
            key = (int(entry["listing_id"]), str(entry.get("path", "")))
            hit = DuplicateHit(
                listing_id=int(entry["listing_id"]),
                listing_title=str(entry.get("title") or ""),
                image_path=str(entry.get("path") or ""),
                distance=0 if exact else distance,
                exact=exact,
            )
            existing = hits.get(key)
            if existing is None or hit.distance < existing.distance:
                hits[key] = hit
    return sorted(hits.values(), key=lambda h: (not h.exact, h.distance))
