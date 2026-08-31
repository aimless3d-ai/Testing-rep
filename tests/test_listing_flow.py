from __future__ import annotations

import json

from vinted_tool.ai.service import AnalysisOutcome
from vinted_tool.models.analysis import Damage, ImageAnalysis
from vinted_tool.models.enums import ListingStatus
from vinted_tool.services.image_service import ImportOptions


def analysis() -> ImageAnalysis:
    return ImageAnalysis(
        product_type="Hoodie",
        brand="Nike",
        color="Schwarz",
        material="Baumwolle",
        size="M",
        condition="Sehr gut",
        keywords=["hoodie", "nike"],
        features=["Kapuze"],
        damages=[Damage("leichtes Pilling", "leicht")],
        source="test",
    )


def test_build_listing_fills_everything(context, make_image):
    images, _ = context.image_service.import_many([make_image("nike_hoodie.jpg")])
    listing = context.listing_service.build_listing(analysis(), images)
    assert listing.title.startswith("Nike Hoodie")
    assert listing.category_path[-1] == "Hoodies"
    assert listing.brand == "Nike" and listing.size == "M"
    assert listing.price == listing.price_suggestion.recommended > 0
    assert "Nike" in listing.description
    assert "Pilling" in listing.description
    assert "hoodie" in listing.keywords
    assert listing.status == ListingStatus.DRAFT.value


def test_unknown_values_are_left_empty_not_invented(context, make_image):
    images, _ = context.image_service.import_many([make_image("foto.jpg")])
    sparse = ImageAnalysis(product_type="Kleid", source="test")
    listing = context.listing_service.build_listing(sparse, images)
    assert listing.brand == ""
    assert listing.size == ""
    assert listing.condition == context.settings.default_condition  # user default, not a guess
    assert "Kleid" in listing.title


def test_draft_survives_a_restart(context, make_image, data_dir):
    from vinted_tool.app.context import AppContext

    images, _ = context.image_service.import_many([make_image("a.jpg")])
    listing = context.listing_service.build_listing(analysis(), images)
    saved = context.listing_service.save_as_draft(listing)
    context.close()

    reopened = AppContext(db_path=data_dir / "test.sqlite3")
    loaded = reopened.listing_repo.get(saved.id)
    assert loaded.title == saved.title
    assert loaded.status == ListingStatus.DRAFT.value
    assert len(loaded.images) == 1
    reopened.close()


def test_duplicate_detection_across_listings(context, make_image):
    path = make_image("shirt.jpg")
    first, _ = context.image_service.import_many([path])
    listing = context.listing_service.save_as_draft(
        context.listing_service.build_listing(analysis(), first)
    )
    assert context.listing_service.check_duplicates(listing) == []

    second, _ = context.image_service.import_many([path])
    other = context.listing_service.build_listing(analysis(), second)
    hits = context.listing_service.check_duplicates(other)
    assert hits and hits[0].listing_id == listing.id


def test_status_transitions(context, make_image):
    images, _ = context.image_service.import_many([make_image("a.jpg")])
    listing = context.listing_service.save_as_draft(
        context.listing_service.build_listing(analysis(), images)
    )
    context.listing_service.mark_ready(listing)
    assert context.listing_repo.get(listing.id).status == ListingStatus.READY.value
    context.listing_service.mark_status(listing, ListingStatus.PUBLISHED)
    assert context.listing_repo.get(listing.id).status == ListingStatus.PUBLISHED.value


def test_template_choice_changes_the_description(context, make_image):
    images, _ = context.image_service.import_many([make_image("a.jpg")])
    listing = context.listing_service.build_listing(
        analysis(), images, template_body="Nur: {{brand}} {{product}}"
    )
    assert listing.description.startswith("Nur: Nike Hoodie")


def test_settings_defaults_are_applied(context, make_image):
    context.settings_service.update(
        currency="CHF", price_rounding="1.00", default_shipping="Nur Abholung."
    )
    images, _ = context.image_service.import_many([make_image("a.jpg")])
    listing = context.listing_service.build_listing(analysis(), images)
    assert listing.currency == "CHF"
    assert listing.price == float(int(listing.price))
    assert "Nur Abholung." in listing.description


def test_analysis_cache_prevents_a_second_provider_call(context, make_image, monkeypatch):
    images, _ = context.image_service.import_many([make_image("a.jpg")])
    calls = {"n": 0}

    class StubProvider:
        kind = "stub"
        model = "stub-model"

        def analyze(self, request):
            calls["n"] += 1
            return analysis()

    monkeypatch.setattr(
        "vinted_tool.ai.service.create_provider", lambda *a, **kw: StubProvider()
    )
    paths = [i.path for i in images]
    first = context.analysis_service.analyze(paths)
    second = context.analysis_service.analyze(paths)
    assert calls["n"] == 1
    assert first.from_cache is False and second.from_cache is True
    assert second.analysis.brand == "Nike"

    third = context.analysis_service.analyze(paths, force_refresh=True)
    assert calls["n"] == 2 and third.from_cache is False


def test_analysis_errors_are_wrapped_for_the_ui(context, make_image, monkeypatch):
    from vinted_tool.core.errors import AIError, AITimeoutError

    images, _ = context.image_service.import_many([make_image("a.jpg")])

    class FailingProvider:
        kind = "stub"
        model = "m"

        def analyze(self, request):
            raise AITimeoutError()

    monkeypatch.setattr(
        "vinted_tool.ai.service.create_provider", lambda *a, **kw: FailingProvider()
    )
    try:
        context.analysis_service.analyze([i.path for i in images])
    except AIError as exc:
        assert "Timeout" in exc.user_message
    else:  # pragma: no cover
        raise AssertionError("expected an AIError")


def test_analysis_without_images_is_rejected(context):
    from vinted_tool.core.errors import AIError

    try:
        context.analysis_service.analyze([])
    except AIError as exc:
        assert "Bild" in exc.user_message
    else:  # pragma: no cover
        raise AssertionError("expected an AIError")


def test_offline_analysis_always_works(context, make_image):
    images, _ = context.image_service.import_many([make_image("nike_jeans.jpg", (40, 60, 160))])
    outcome = context.analysis_service.analyze_offline([i.path for i in images])
    assert isinstance(outcome, AnalysisOutcome)
    assert outcome.analysis.color
    assert outcome.analysis.condition is None


def test_stored_analysis_is_json_serialisable(context, make_image):
    images, _ = context.image_service.import_many([make_image("a.jpg")])
    listing = context.listing_service.save_as_draft(
        context.listing_service.build_listing(analysis(), images)
    )
    reloaded = context.listing_repo.get(listing.id)
    assert json.dumps(reloaded.analysis)
    assert ImageAnalysis.from_dict(reloaded.analysis).brand == "Nike"
