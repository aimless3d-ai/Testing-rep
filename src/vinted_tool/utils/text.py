"""Text helpers for titles, keywords and descriptions."""
from __future__ import annotations

import re

TITLE_MAX = 100
_STOPWORDS = {"und", "mit", "für", "der", "die", "das", "ein", "eine", "von", "aus", "im", "in"}


def collapse_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", (text or "").replace("\r\n", "\n")).strip()


def titleize(text: str) -> str:
    """Capitalise words but keep existing upper-case brand spellings intact."""
    words = []
    for word in collapse_whitespace(text).split(" "):
        if not word:
            continue
        words.append(word if any(c.isupper() for c in word[1:]) else word[:1].upper() + word[1:])
    return " ".join(words)


def build_title(
    *,
    brand: str | None,
    product_type: str | None,
    model: str | None = None,
    color: str | None = None,
    size: str | None = None,
    pattern: str | None = None,
    max_length: int = TITLE_MAX,
) -> str:
    """Assemble a Vinted style title from known facts only."""
    parts: list[str] = []
    for value in (brand, product_type, model):
        cleaned = collapse_whitespace(value or "")
        if cleaned and cleaned.lower() not in " ".join(parts).lower():
            parts.append(titleize(cleaned))
    optional = [collapse_whitespace(v or "") for v in (pattern, color)]
    optional = [titleize(v) for v in optional if v]
    if size:
        optional.append(f"Gr. {collapse_whitespace(size)}")

    title = " ".join(parts)
    for extra in optional:
        candidate = f"{title} {extra}".strip()
        if len(candidate) <= max_length:
            title = candidate
    title = collapse_whitespace(title)
    return title[:max_length].strip()


def build_keywords(values: list[str | None], limit: int = 12) -> list[str]:
    """Deduplicated, lower-cased search terms in their original order."""
    keywords: list[str] = []
    for value in values:
        for token in re.split(r"[,\n]| {2,}", collapse_whitespace(value or "")):
            token = token.strip().lower()
            if len(token) < 3 or token in _STOPWORDS or token in keywords:
                continue
            keywords.append(token)
            if len(keywords) >= limit:
                return keywords
    return keywords


def humanize_list(values: list[str]) -> str:
    values = [v.strip() for v in values if v and v.strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + " und " + values[-1]
