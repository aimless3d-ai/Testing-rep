from __future__ import annotations

from vinted_tool.core import templates as engine
from vinted_tool.core.categories import find_by_path, match_categories, size_options


def test_matches_the_obvious_category():
    matches = match_categories(product_type="Hoodie", keywords=["damen", "kapuzenpullover"])
    assert matches
    assert matches[0].label.endswith("Hoodies")
    assert matches[0].score > 0


def test_gender_hint_moves_men_categories_up():
    women = match_categories(product_type="Sneaker", keywords=["damen"])[0]
    men = match_categories(product_type="Sneaker", keywords=["herren"])[0]
    assert women.path[0] == "Damen"
    assert men.path[0] == "Herren"


def test_unknown_product_yields_no_match():
    assert match_categories(product_type="Zeitmaschine", keywords=[]) == []
    assert match_categories() == []


def test_find_by_path_accepts_both_forms():
    entry = find_by_path(["Damen", "Schuhe", "Sneaker"])
    assert entry is not None
    assert find_by_path("Damen > Schuhe > Sneaker") == entry
    assert find_by_path("Gibt es nicht") is None


def test_size_options_depend_on_the_category():
    assert "42" in size_options(find_by_path(["Damen", "Schuhe", "Sneaker"]))
    assert "XL" in size_options(find_by_path(["Damen", "Kleidung", "Kleider", "Freizeitkleider"]))
    assert size_options(find_by_path(["Damen", "Accessoires", "Uhren"])) == []


def test_template_renders_values_and_skips_empty_blocks():
    body = "{{brand}} {{product}}{{#size}} Gr. {{size}}{{/size}}."
    assert engine.render(body, {"brand": "Nike", "product": "Hoodie", "size": "M"}) \
        == "Nike Hoodie Gr. M."
    assert engine.render(body, {"brand": "Nike", "product": "Hoodie"}) == "Nike Hoodie."


def test_template_fallback_value():
    body = "Zustand: {{condition|bitte erfragen}}."
    assert engine.render(body, {}) == "Zustand: bitte erfragen."
    assert engine.render(body, {"condition": "Gut"}) == "Zustand: Gut."


def test_template_formats_lists_and_numbers():
    body = "{{keywords}} / {{price}}"
    assert engine.render(body, {"keywords": ["a", "b"], "price": 12.5}) == "a, b / 12.5"


def test_unknown_variables_are_detected_but_render_empty():
    body = "{{brand}} {{gibtsnicht}}"
    assert engine.unknown_variables(body) == ["gibtsnicht"]
    assert engine.render(body, {"brand": "Nike"}) == "Nike"


def test_default_templates_are_valid():
    for name, body, _ in engine.DEFAULT_TEMPLATES:
        assert engine.unknown_variables(body) == [], name
        rendered = engine.render(body, {"product": "Hoodie", "condition": "Gut"})
        assert "{{" not in rendered and "}}" not in rendered
