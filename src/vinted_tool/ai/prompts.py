"""Prompts. Kept short on purpose – every token is paid for."""
from __future__ import annotations

import json

from vinted_tool.ai.schema import ANALYSIS_JSON_SCHEMA

SYSTEM_PROMPT = (
    "Du bist ein Experte für Second-Hand-Mode und analysierst Produktfotos für Vinted-Anzeigen.\n"
    "Regeln:\n"
    "1. Erfinde NIEMALS Angaben. Wenn etwas auf den Bildern nicht klar erkennbar ist, "
    "setze den Wert auf null.\n"
    "2. Lies Marken/Größen nur aus sichtbaren Etiketten, Logos oder Prints ab.\n"
    "3. Alle Bilder zeigen dasselbe Produkt aus verschiedenen Perspektiven.\n"
    "4. Zustand nur aus sichtbaren Merkmalen ableiten (Etikett vorhanden, Pilling, Flecken, "
    "Abnutzung).\n"
    "5. Gib für jedes Kernfeld eine Confidence zwischen 0 und 1 an. "
    "Unsicher heißt Wert null oder Confidence unter 0.55.\n"
    "6. Antworte ausschließlich mit einem JSON-Objekt nach dem vorgegebenen Schema, ohne Fließtext."
)

USER_PROMPT = (
    "Analysiere die Produktfotos und fülle das JSON-Schema aus.\n"
    "Sprache aller Textwerte: Deutsch.\n"
    "condition muss exakt einer dieser Werte oder null sein: "
    "\"Neu mit Etikett\", \"Neu ohne Etikett\", \"Sehr gut\", \"Gut\", \"Zufriedenstellend\".\n"
    "keywords: 5-10 kurze Suchbegriffe, die Käufer bei Vinted eingeben würden.\n"
    "category_guess: eine kurze Kategoriebezeichnung, z. B. \"Damen Hoodie\".\n"
    "Schema:\n"
)


def build_user_prompt(extra_hint: str = "") -> str:
    prompt = USER_PROMPT + json.dumps(ANALYSIS_JSON_SCHEMA, ensure_ascii=False, separators=(",", ":"))
    if extra_hint.strip():
        prompt += f"\nZusatzinfo des Verkäufers (als Fakt behandeln): {extra_hint.strip()}"
    return prompt
