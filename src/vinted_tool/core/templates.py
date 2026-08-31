"""Template rendering with ``{{variable}}`` placeholders.

Supported syntax:
    {{brand}}                       – value or empty string
    {{brand|Marke unbekannt}}       – fallback when the value is missing
    {{#brand}}Marke: {{brand}}{{/brand}} – block, rendered only if filled
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*(?:\|([^}]*))?\}\}")
BLOCK_RE = re.compile(r"\{\{#\s*([a-zA-Z0-9_]+)\s*\}\}(.*?)\{\{/\s*\1\s*\}\}", re.DOTALL)

KNOWN_VARIABLES: tuple[str, ...] = (
    "brand", "product", "title", "size", "condition", "color", "material",
    "category", "price", "currency", "keywords", "features", "damages", "shipping",
)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return f"{value:g}"
    if isinstance(value, Mapping):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, Iterable):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value)


def render(template: str, values: Mapping[str, Any]) -> str:
    """Render *template*; unknown variables collapse to an empty string."""
    if not template:
        return ""
    data = {k: _stringify(v) for k, v in values.items()}

    def block_sub(match: re.Match[str]) -> str:
        name, body = match.group(1), match.group(2)
        return body if data.get(name) else ""

    text = BLOCK_RE.sub(block_sub, template)

    def var_sub(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        value = data.get(name, "")
        if value:
            return value
        return (fallback or "").strip()

    text = VARIABLE_RE.sub(var_sub, text)
    # tidy up the blanks left behind by empty variables
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def used_variables(template: str) -> list[str]:
    names = [m.group(1) for m in VARIABLE_RE.finditer(template or "")]
    names += [m.group(1) for m in BLOCK_RE.finditer(template or "")]
    seen: list[str] = []
    for name in names:
        if name not in seen:
            seen.append(name)
    return seen


def unknown_variables(template: str) -> list[str]:
    return [n for n in used_variables(template) if n not in KNOWN_VARIABLES]


DEFAULT_TEMPLATES: tuple[tuple[str, str, bool], ...] = (
    (
        "Standard",
        "{{#brand}}{{brand}} {{/brand}}{{product}}{{#size}} in Größe {{size}}{{/size}}."
        "\n{{#color}}Farbe: {{color}}.{{/color}}{{#material}} Material: {{material}}.{{/material}}"
        "\n{{#condition}}Zustand: {{condition}}.{{/condition}}"
        "\n{{#features}}Details: {{features}}.{{/features}}"
        "\n{{#damages}}Hinweis zum Zustand: {{damages}}.{{/damages}}"
        "\n\n{{#shipping}}{{shipping}}{{/shipping}}"
        "\nPrivatverkauf, daher keine Rücknahme und keine Garantie. Bei Fragen gerne melden.",
        True,
    ),
    (
        "Kurz & sachlich",
        "{{#brand}}{{brand}} · {{/brand}}{{product}}{{#size}} · Größe {{size}}{{/size}}"
        "{{#color}} · {{color}}{{/color}}"
        "\nZustand: {{condition|bitte erfragen}}."
        "\n{{#damages}}Mängel: {{damages}}.{{/damages}}"
        "\nPrivatverkauf. Versand möglich.",
        False,
    ),
    (
        "Freundlich",
        "Hallo! Ich verkaufe {{#brand}}dieses Teil von {{brand}}{{/brand}}"
        " – {{product}}{{#size}} in Größe {{size}}{{/size}}."
        "\n{{#color}}Die Farbe ist {{color}}.{{/color}}"
        "{{#material}} Material: {{material}}.{{/material}}"
        "\nDer Zustand ist {{condition|auf den Fotos gut zu sehen}}."
        "\n{{#damages}}Ehrlich gesagt: {{damages}}.{{/damages}}"
        "\n\n{{#shipping}}{{shipping}}{{/shipping}}"
        "\nBei Fragen schreib mir einfach – ich melde mich schnell zurück. Privatverkauf.",
        False,
    ),
)
