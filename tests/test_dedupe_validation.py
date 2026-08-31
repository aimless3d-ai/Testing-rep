from __future__ import annotations

from vinted_tool.core.dedupe import find_duplicates, hamming_distance
from vinted_tool.core.validation import validate_listing
from vinted_tool.models.enums import Condition, QualityLevel
from vinted_tool.models.listing import Listing, ListingImage, PriceSuggestion


def test_hamming_distance():
    assert hamming_distance("ff", "ff") == 0
    assert hamming_distance("f0", "f1") == 1
    assert hamming_distance("ff", None) == 999
    assert hamming_distance("ff", "ffff") == 999


def test_exact_duplicate_detected_by_sha():
    known = [{"listing_id": 7, "title": "Alt", "path": "/a.jpg", "sha256": "abc", "phash": "0f0f"}]
    hits = find_duplicates([{"sha256": "abc", "phash": "ffff"}], known)
    assert hits[0].exact is True
    assert "identisches Bild" in hits[0].description


def test_similar_image_within_threshold():
    known = [{"listing_id": 3, "title": "Alt", "path": "/a.jpg", "sha256": "x", "phash": "0000"}]
    assert find_duplicates([{"sha256": "y", "phash": "0001"}], known, threshold=6)
    assert not find_duplicates([{"sha256": "y", "phash": "ffff"}], known, threshold=6)


def test_no_duplicates_for_empty_history():
    assert find_duplicates([{"sha256": "a", "phash": "0"}], []) == []


def ready_listing() -> Listing:
    return Listing(
        title="Nike Hoodie Schwarz",
        description="Sehr gut erhaltener Hoodie von Nike in Größe M, kaum getragen.",
        category_path=["Damen", "Kleidung", "Pullover & Sweatshirts", "Hoodies"],
        brand="Nike",
        size="M",
        color="Schwarz",
        condition=Condition.VERY_GOOD.value,
        price=24.5,
        images=[ListingImage(path="/a.jpg", is_primary=True)],
        price_suggestion=PriceSuggestion(quick=18, recommended=24.5, high=32),
    )


def test_complete_listing_is_green():
    result = validate_listing(ready_listing())
    assert result.level is QualityLevel.READY
    assert result.is_publishable


def test_empty_listing_is_red_and_lists_everything():
    result = validate_listing(Listing())
    fields = {issue.field_name for issue in result.blocking}
    assert result.level is QualityLevel.INCOMPLETE
    assert {"title", "description", "images", "category", "price", "condition"} <= fields
    assert not result.is_publishable


def test_missing_size_blocks_clothing():
    listing = ready_listing()
    listing.size = ""
    assert not validate_listing(listing).is_publishable


def test_size_not_required_for_accessories():
    listing = ready_listing()
    listing.category_path = ["Damen", "Accessoires", "Uhren"]
    listing.size = ""
    assert validate_listing(listing).is_publishable


def test_contradiction_new_but_damaged_is_a_warning():
    listing = ready_listing()
    listing.condition = Condition.NEW_WITH_TAG.value
    listing.analysis = {"damages": [{"description": "Fleck", "severity": "mittel"}]}
    result = validate_listing(listing)
    assert result.level is QualityLevel.REVIEW
    assert result.is_publishable


def test_price_far_above_suggestion_warns():
    listing = ready_listing()
    listing.price = 200.0
    assert validate_listing(listing).level is QualityLevel.REVIEW


def test_missing_brand_is_only_a_warning():
    listing = ready_listing()
    listing.brand = ""
    result = validate_listing(listing)
    assert result.is_publishable
    assert any(i.field_name == "brand" for i in result.warnings)
