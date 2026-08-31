"""Category matching: text in, ranked Vinted category candidates out."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from vinted_tool.core.category_data import CATEGORIES, CategoryEntry

_GENDER_HINTS = {
    "Damen": ("damen", "frauen", "women", "womens", "female", "girl", "mädchen", "w"),
    "Herren": ("herren", "männer", "manner", "men", "mens", "male", "junge", "boy", "m"),
    "Kinder": ("kinder", "kids", "baby", "child", "children", "kleinkind", "säugling"),
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.lower()).strip()


@dataclass(frozen=True, slots=True)
class CategoryMatch:
    entry: CategoryEntry
    score: float

    @property
    def label(self) -> str:
        return self.entry.label

    @property
    def path(self) -> list[str]:
        return list(self.entry.path)


def _gender_from_text(haystack: str) -> str | None:
    for gender, hints in _GENDER_HINTS.items():
        for hint in hints:
            if len(hint) <= 2:
                continue
            if re.search(rf"\b{re.escape(hint)}\b", haystack):
                return gender
    return None


def match_categories(
    *,
    product_type: str | None = None,
    keywords: list[str] | None = None,
    text: str | None = None,
    gender: str | None = None,
    limit: int = 5,
) -> list[CategoryMatch]:
    """Rank catalogue entries against the recognised product information."""
    parts = [product_type or "", " ".join(keywords or []), text or ""]
    haystack = normalize(" ".join(p for p in parts if p))
    if not haystack:
        return []

    detected_gender = gender or _gender_from_text(haystack)
    scored: list[CategoryMatch] = []
    for entry in CATEGORIES:
        score = 0.0
        for keyword in entry.keywords:
            norm_kw = normalize(keyword)
            if not norm_kw:
                continue
            if re.search(rf"\b{re.escape(norm_kw)}\b", haystack):
                score += 3.0 + 0.4 * norm_kw.count(" ")
            elif len(norm_kw) >= 5 and norm_kw in haystack:
                score += 1.5
        # the leaf name itself is a strong signal
        leaf = normalize(entry.path[-1])
        for token in re.split(r"[ &,]+", leaf):
            if len(token) >= 4 and re.search(rf"\b{re.escape(token)}\b", haystack):
                score += 1.2
        if score <= 0:
            continue
        if detected_gender:
            score += 2.0 if entry.path[0] == detected_gender else -1.2
        scored.append(CategoryMatch(entry, round(score, 2)))

    scored.sort(key=lambda m: (-m.score, m.entry.label))
    return scored[:limit]


def find_by_path(path: list[str] | tuple[str, ...] | str) -> CategoryEntry | None:
    if isinstance(path, str):
        wanted = normalize(path)
        for entry in CATEGORIES:
            if normalize(entry.label) == wanted:
                return entry
        return None
    wanted_tuple = tuple(path)
    for entry in CATEGORIES:
        if entry.path == wanted_tuple:
            return entry
    return find_by_path(" > ".join(wanted_tuple))


def all_labels() -> list[str]:
    return [entry.label for entry in CATEGORIES]


def size_options(entry: CategoryEntry | None) -> list[str]:
    from vinted_tool.core.category_data import CLOTHING_SIZES, KIDS_SIZES, SHOE_SIZES

    if entry is None:
        return CLOTHING_SIZES
    return {
        "clothing": CLOTHING_SIZES,
        "shoes": SHOE_SIZES,
        "kids": KIDS_SIZES,
        "none": [],
    }[entry.size_system]
