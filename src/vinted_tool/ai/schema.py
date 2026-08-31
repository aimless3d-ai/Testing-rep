"""JSON contract between the app and any AI provider."""
from __future__ import annotations

import json
import re
from typing import Any

from vinted_tool.core.errors import AIResponseError
from vinted_tool.models.analysis import Damage, ImageAnalysis

ANALYSIS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "product_type": {"type": ["string", "null"]},
        "brand": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "color": {"type": ["string", "null"]},
        "secondary_colors": {"type": "array", "items": {"type": "string"}},
        "pattern": {"type": ["string", "null"]},
        "material": {"type": ["string", "null"]},
        "size": {"type": ["string", "null"]},
        "condition": {
            "type": ["string", "null"],
            "enum": [
                "Neu mit Etikett", "Neu ohne Etikett", "Sehr gut", "Gut",
                "Zufriedenstellend", None,
            ],
        },
        "damages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["leicht", "mittel", "stark"]},
                },
                "required": ["description", "severity"],
            },
        },
        "features": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "category_guess": {"type": ["string", "null"]},
        "notes": {"type": ["string", "null"]},
        "confidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "product_type": {"type": "number"},
                "brand": {"type": "number"},
                "color": {"type": "number"},
                "size": {"type": "number"},
                "condition": {"type": "number"},
                "material": {"type": "number"},
            },
            "required": ["product_type", "brand", "color", "size", "condition", "material"],
        },
    },
    "required": [
        "product_type", "brand", "model", "color", "secondary_colors", "pattern",
        "material", "size", "condition", "damages", "features", "keywords",
        "category_guess", "notes", "confidence",
    ],
}

_NULLISH = {
    "", "null", "none", "unknown", "unbekannt", "n/a", "na", "keine angabe",
    "nicht erkennbar", "nicht sicher", "nicht sicher erkannt", "-", "?",
}
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
MIN_CONFIDENCE = 0.55


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in _NULLISH:
        return None
    return text


def _clean_list(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        cleaned = _clean(item)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out[:limit]


def extract_json(raw: str) -> dict[str, Any]:
    """Pull a JSON object out of a model answer, tolerating fences and prose."""
    if not raw or not raw.strip():
        raise AIResponseError("Die KI hat eine leere Antwort geliefert.")
    text = raw.strip()
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise AIResponseError("In der KI-Antwort war kein JSON enthalten.") from None
        try:
            data = json.loads(text[start : end + 1])
        except ValueError as exc:
            raise AIResponseError(f"JSON der KI-Antwort ist ungültig: {exc}") from exc
    if not isinstance(data, dict):
        raise AIResponseError("Die KI-Antwort war kein JSON-Objekt.")
    return data


def parse_analysis(raw: str | dict[str, Any], *, source: str, model: str | None = None,
                   tokens: int = 0) -> ImageAnalysis:
    """Validate a provider answer and drop every low-confidence value."""
    data = raw if isinstance(raw, dict) else extract_json(raw)
    confidence_raw = data.get("confidence") or {}
    confidence: dict[str, float] = {}
    if isinstance(confidence_raw, dict):
        for key, value in confidence_raw.items():
            try:
                confidence[str(key)] = max(0.0, min(1.0, float(value)))
            except (TypeError, ValueError):
                continue

    def gated(field: str, value: Any) -> str | None:
        cleaned = _clean(value)
        if cleaned is None:
            return None
        if confidence and confidence.get(field, 1.0) < MIN_CONFIDENCE:
            return None  # not confident enough → the user chooses instead
        return cleaned

    damages: list[Damage] = []
    for item in data.get("damages") or []:
        if isinstance(item, dict):
            description = _clean(item.get("description"))
            if description:
                severity = (_clean(item.get("severity")) or "leicht").lower()
                damages.append(Damage(description, severity if severity in
                                      {"leicht", "mittel", "stark"} else "leicht"))
        else:
            description = _clean(item)
            if description:
                damages.append(Damage(description))

    category_guess = _clean(data.get("category_guess"))
    return ImageAnalysis(
        product_type=gated("product_type", data.get("product_type")),
        brand=gated("brand", data.get("brand")),
        model=_clean(data.get("model")),
        color=gated("color", data.get("color")),
        secondary_colors=_clean_list(data.get("secondary_colors"), 5),
        pattern=_clean(data.get("pattern")),
        material=gated("material", data.get("material")),
        size=gated("size", data.get("size")),
        condition=gated("condition", data.get("condition")),
        damages=damages,
        features=_clean_list(data.get("features"), 10),
        keywords=_clean_list(data.get("keywords"), 15),
        category_candidates=[category_guess] if category_guess else [],
        notes=_clean(data.get("notes")),
        confidence=confidence,
        source=source,
        model_used=model,
        tokens_used=tokens,
    )
