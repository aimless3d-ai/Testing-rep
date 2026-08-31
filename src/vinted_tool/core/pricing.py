"""Price suggestion engine.

The price is derived from a category base price, a brand tier factor and the
condition, then adjusted by the user's strategy. Every step is explained in
``rationale`` so the user can judge the number instead of trusting it blindly.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from vinted_tool.core.categories import find_by_path, normalize
from vinted_tool.core.category_data import BRAND_PRICE_TIERS
from vinted_tool.models.enums import Condition, PriceStrategy
from vinted_tool.models.listing import PriceSuggestion

STRATEGY_FACTORS = {
    PriceStrategy.QUICK: 0.85,
    PriceStrategy.NORMAL: 1.0,
    PriceStrategy.HIGH: 1.18,
}

DAMAGE_PENALTY = {"leicht": 0.93, "mittel": 0.82, "stark": 0.65}
MIN_PRICE = 1.0


@dataclass(frozen=True, slots=True)
class PriceInputs:
    category_path: list[str] | None = None
    brand: str | None = None
    condition: str | None = None
    damages: int = 0
    damage_severity: str = "leicht"
    strategy: PriceStrategy = PriceStrategy.NORMAL
    rounding: str = "0.50"
    currency: str = "EUR"


def brand_factor(brand: str | None) -> float:
    if not brand:
        return 1.0
    return BRAND_PRICE_TIERS.get(normalize(brand), 1.15)  # unknown named brand ≈ slight premium


def round_price(value: float, mode: str) -> float:
    value = max(MIN_PRICE, value)
    if mode == "off":
        return round(value, 2)
    if mode == "1.00":
        return float(max(MIN_PRICE, math.floor(value + 0.5)))
    if mode == "psychological":
        base = max(MIN_PRICE, math.floor(value))
        return float(base) - 0.01 if base >= 2 else float(base)
    # default: half-euro steps
    return max(MIN_PRICE, round(value * 2) / 2)


def suggest_price(inputs: PriceInputs) -> PriceSuggestion:
    entry = find_by_path(inputs.category_path) if inputs.category_path else None
    base = entry.base_price if entry else 12.0
    reasons = [
        f"Basis {'Kategorie ' + entry.label if entry else 'Standardwert (keine Kategorie erkannt)'}: "
        f"{base:.2f} {inputs.currency}"
    ]

    factor_brand = brand_factor(inputs.brand)
    if inputs.brand:
        known = normalize(inputs.brand) in BRAND_PRICE_TIERS
        reasons.append(
            f"Marke {inputs.brand}: ×{factor_brand:.2f}"
            + ("" if known else " (Marke nicht in der Preisliste – vorsichtiger Aufschlag)")
        )

    condition = Condition.from_text(inputs.condition)
    factor_condition = condition.quality_factor if condition else 0.65
    reasons.append(
        f"Zustand {condition.value if condition else 'unbekannt'}: ×{factor_condition:.2f}"
    )

    factor_damage = 1.0
    if inputs.damages:
        per_damage = DAMAGE_PENALTY.get(inputs.damage_severity, 0.9)
        factor_damage = per_damage ** min(inputs.damages, 3)
        reasons.append(f"{inputs.damages} Mangel/Mängel ({inputs.damage_severity}): ×{factor_damage:.2f}")

    recommended_raw = base * factor_brand * factor_condition * factor_damage
    strategy_factor = STRATEGY_FACTORS[inputs.strategy]
    if strategy_factor != 1.0:
        reasons.append(f"Strategie {inputs.strategy.label}: ×{strategy_factor:.2f}")
    recommended_raw *= strategy_factor

    recommended = round_price(recommended_raw, inputs.rounding)
    quick = round_price(recommended_raw * 0.78, inputs.rounding)
    high = round_price(recommended_raw * 1.3, inputs.rounding)
    if quick >= recommended:
        quick = round_price(max(MIN_PRICE, recommended - 1), inputs.rounding)
    if high <= recommended:
        high = round_price(recommended + 1, inputs.rounding)

    return PriceSuggestion(
        quick=quick,
        recommended=recommended,
        high=high,
        currency=inputs.currency,
        rationale=" · ".join(reasons),
    )
