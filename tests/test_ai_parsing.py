from __future__ import annotations

import json

import pytest

from vinted_tool.ai.schema import extract_json, parse_analysis
from vinted_tool.core.errors import AIResponseError

FULL = {
    "product_type": "Hoodie",
    "brand": "Nike",
    "model": None,
    "color": "Schwarz",
    "secondary_colors": ["Weiß"],
    "pattern": None,
    "material": "Baumwolle",
    "size": "M",
    "condition": "Sehr gut",
    "damages": [{"description": "leichtes Pilling", "severity": "leicht"}],
    "features": ["Kapuze"],
    "keywords": ["nike", "hoodie", "schwarz"],
    "category_guess": "Damen Hoodie",
    "notes": None,
    "confidence": {
        "product_type": 0.95, "brand": 0.9, "color": 0.85,
        "size": 0.8, "condition": 0.7, "material": 0.6,
    },
}


def test_parses_a_clean_answer():
    analysis = parse_analysis(json.dumps(FULL), source="openrouter", model="m", tokens=42)
    assert analysis.brand == "Nike"
    assert analysis.size == "M"
    assert analysis.damages[0].severity == "leicht"
    assert analysis.category_candidates == ["Damen Hoodie"]
    assert analysis.tokens_used == 42


def test_low_confidence_values_are_dropped_not_guessed():
    payload = dict(FULL, confidence=dict(FULL["confidence"], brand=0.2, size=0.1))
    analysis = parse_analysis(json.dumps(payload), source="openai")
    assert analysis.brand is None
    assert analysis.size is None
    assert "Marke" in analysis.missing_fields()


@pytest.mark.parametrize("value", ["", "null", "unbekannt", "Nicht sicher erkannt", "-", "n/a"])
def test_nullish_strings_become_none(value):
    payload = dict(FULL, brand=value)
    assert parse_analysis(json.dumps(payload), source="x").brand is None


def test_json_inside_code_fence_and_prose():
    raw = "Klar!\n```json\n" + json.dumps(FULL) + "\n```\nViel Erfolg."
    assert parse_analysis(raw, source="x").product_type == "Hoodie"


def test_json_without_fence_but_with_prose():
    raw = "Hier das Ergebnis: " + json.dumps(FULL) + " Ende."
    assert extract_json(raw)["brand"] == "Nike"


@pytest.mark.parametrize("raw", ["", "   ", "kein json hier", "[1,2,3]", "{kaputt"])
def test_invalid_answers_raise_a_clear_error(raw):
    with pytest.raises(AIResponseError):
        parse_analysis(raw, source="x")


def test_missing_keys_are_tolerated():
    analysis = parse_analysis('{"product_type": "Kleid"}', source="x")
    assert analysis.product_type == "Kleid"
    assert analysis.brand is None
    assert analysis.keywords == []


def test_damages_accept_plain_strings():
    analysis = parse_analysis('{"damages": ["Fleck am Saum", ""]}', source="x")
    assert [d.description for d in analysis.damages] == ["Fleck am Saum"]


def test_roundtrip_through_dict():
    from vinted_tool.models.analysis import ImageAnalysis

    analysis = parse_analysis(json.dumps(FULL), source="x")
    restored = ImageAnalysis.from_dict(analysis.to_dict())
    assert restored.brand == analysis.brand
    assert restored.damages[0].description == "leichtes Pilling"
