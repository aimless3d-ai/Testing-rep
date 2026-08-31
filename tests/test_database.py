from __future__ import annotations

from vinted_tool.database.db import Database
from vinted_tool.database.repositories import (
    AnalysisCacheRepository,
    ListingRepository,
    SettingsRepository,
    TemplateRepository,
)
from vinted_tool.models.enums import ListingStatus
from vinted_tool.models.listing import Listing, ListingImage
from vinted_tool.models.template_model import Template


def test_schema_created(data_dir):
    db = Database(data_dir / "a.sqlite3")
    tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"listings", "images", "templates", "settings", "analysis_cache"} <= tables
    db.close()


def test_listing_roundtrip_with_images(data_dir):
    db = Database(data_dir / "b.sqlite3")
    repo = ListingRepository(db)
    listing = Listing(
        title="Nike Hoodie",
        brand="Nike",
        price=24.5,
        category_path=["Damen", "Kleidung"],
        keywords=["nike", "hoodie"],
        images=[
            ListingImage(path="/a.jpg", phash="ff00", sha256="abc", is_primary=True),
            ListingImage(path="/b.jpg", phash="ff01", sha256="def"),
        ],
    )
    saved = repo.save(listing)
    loaded = repo.get(saved.id)
    assert loaded.title == "Nike Hoodie"
    assert loaded.category_path == ["Damen", "Kleidung"]
    assert loaded.keywords == ["nike", "hoodie"]
    assert len(loaded.images) == 2
    assert loaded.primary_image.path == "/a.jpg"
    db.close()


def test_save_replaces_images_instead_of_duplicating(data_dir):
    db = Database(data_dir / "c.sqlite3")
    repo = ListingRepository(db)
    listing = repo.save(Listing(title="X", images=[ListingImage(path="/a.jpg")]))
    listing.images.append(ListingImage(path="/b.jpg"))
    repo.save(listing)
    assert len(repo.get(listing.id).images) == 2


def test_search_and_status_filter(data_dir):
    db = Database(data_dir / "d.sqlite3")
    repo = ListingRepository(db)
    repo.save(Listing(title="Rotes Kleid", status=ListingStatus.DRAFT.value))
    repo.save(Listing(title="Blaue Jeans", status=ListingStatus.PUBLISHED.value, brand="Levis"))
    assert len(repo.list(search="kleid")) == 1
    assert len(repo.list(search="levis")) == 1
    assert len(repo.list(status=ListingStatus.PUBLISHED.value)) == 1
    assert repo.counts_by_status()[ListingStatus.DRAFT.value] == 1


def test_delete_cascades_images(data_dir):
    db = Database(data_dir / "e.sqlite3")
    repo = ListingRepository(db)
    listing = repo.save(Listing(title="Weg", images=[ListingImage(path="/a.jpg")]))
    repo.delete(listing.id)
    assert repo.get(listing.id) is None
    assert db.query("SELECT * FROM images") == []


def test_settings_and_templates(data_dir):
    db = Database(data_dir / "f.sqlite3")
    settings = SettingsRepository(db)
    settings.set("app_settings", {"currency": "CHF"})
    assert settings.get_all()["app_settings"]["currency"] == "CHF"

    templates = TemplateRepository(db)
    templates.save(Template(name="A", body="{{brand}}", is_default=True))
    templates.save(Template(name="B", body="x", is_default=True))
    default = templates.get_default()
    assert default.name == "B"  # only one default at a time
    assert len(templates.list()) == 2


def test_analysis_cache(data_dir):
    db = Database(data_dir / "g.sqlite3")
    cache = AnalysisCacheRepository(db)
    assert cache.get("k") is None
    cache.put("k", {"brand": "Nike"}, "openrouter", "m", 120)
    assert cache.get("k")["brand"] == "Nike"
    assert cache.stats() == {"entries": 1, "tokens": 120}
    assert cache.clear() == 1
    assert cache.get("k") is None
