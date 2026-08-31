from __future__ import annotations

import pytest

from vinted_tool.core.pricing import PriceInputs, brand_factor, round_price, suggest_price
from vinted_tool.models.enums import Condition, PriceStrategy

HOODIE = ["Damen", "Kleidung", "Pullover & Sweatshirts", "Hoodies"]


def test_price_order_is_always_quick_lower_than_high():
    suggestion = suggest_price(PriceInputs(category_path=HOODIE, brand="Nike", condition="Gut"))
    assert suggestion.quick < suggestion.recommended < suggestion.high
    assert suggestion.currency == "EUR"
    assert "Nike" in suggestion.rationale


def test_better_condition_costs_more():
    def price(condition: Condition) -> float:
        return suggest_price(
            PriceInputs(category_path=HOODIE, brand="Nike", condition=condition.value)
        ).recommended

    assert price(Condition.NEW_WITH_TAG) > price(Condition.VERY_GOOD) > price(Condition.SATISFACTORY)


def test_premium_brand_beats_value_brand():
    def price(brand: str) -> float:
        return suggest_price(
            PriceInputs(category_path=HOODIE, brand=brand, condition="Sehr gut")
        ).recommended

    assert price("Gucci") > price("Nike") > price("H&M")


def test_unknown_brand_gets_moderate_factor():
    assert brand_factor("Irgendeine Marke") == 1.15
    assert brand_factor(None) == 1.0
    assert brand_factor("nike") == brand_factor("Nike")


def test_damages_reduce_the_price():
    clean = suggest_price(PriceInputs(category_path=HOODIE, brand="Nike", condition="Gut"))
    damaged = suggest_price(
        PriceInputs(category_path=HOODIE, brand="Nike", condition="Gut",
                    damages=2, damage_severity="stark")
    )
    assert damaged.recommended < clean.recommended
    assert "Mängel" in damaged.rationale


def test_strategy_shifts_the_recommendation():
    def price(strategy: PriceStrategy) -> float:
        return suggest_price(
            PriceInputs(category_path=HOODIE, brand="Nike", condition="Gut", strategy=strategy)
        ).recommended

    assert price(PriceStrategy.QUICK) < price(PriceStrategy.NORMAL) < price(PriceStrategy.HIGH)


@pytest.mark.parametrize(
    "value,mode,expected",
    [
        (12.3, "0.50", 12.5), (12.1, "0.50", 12.0),
        (12.4, "1.00", 12.0), (12.6, "1.00", 13.0),
        (19.7, "psychological", 18.99), (12.345, "off", 12.35),
        (0.2, "0.50", 1.0),  # never below the minimum price
    ],
)
def test_rounding_modes(value, mode, expected):
    assert round_price(value, mode) == pytest.approx(expected)


def test_unknown_category_uses_a_conservative_default():
    suggestion = suggest_price(PriceInputs(category_path=None, brand=None, condition=None))
    assert suggestion.recommended > 0
    assert "Standardwert" in suggestion.rationale
