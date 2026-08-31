from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from PIL import Image

from vinted_tool.app.logging_setup import RedactingFilter, redact, register_secret, setup_logging
from vinted_tool.automation.vinted_assist import build_publish_steps
from vinted_tool.automation.vinted_export import export_listing, export_many
from vinted_tool.core.secrets import decrypt, encrypt, mask
from vinted_tool.models.enums import ListingStatus, ProviderKind
from vinted_tool.services.batch_service import group_by_prefix, group_by_similarity


def make_images(tmp_path: Path, names: list[str]) -> list[Path]:
    paths = []
    for index, name in enumerate(names):
        path = tmp_path / name
        Image.new("RGB", (200, 260), (index * 30 % 255, 40, 90)).save(path)
        paths.append(path)
    return paths


# ------------------------------------------------------------------ batch mode
def test_group_by_prefix(tmp_path):
    paths = make_images(tmp_path, ["kleid_1.jpg", "kleid_2.jpg", "hose_1.jpg"])
    groups = group_by_prefix(paths)
    assert len(groups) == 2
    assert sorted(len(g) for g in groups) == [1, 2]


def test_group_by_similarity_keeps_identical_photos_together(tmp_path):
    same = tmp_path / "a1.jpg"
    Image.new("RGB", (200, 200), (10, 10, 10)).save(same)
    copy = tmp_path / "a2.jpg"
    Image.open(same).save(copy)
    groups = group_by_similarity([same, copy])
    assert len(groups) == 1


def test_batch_creates_one_draft_per_product(context, tmp_path):
    paths = make_images(tmp_path, ["nike_hoodie_1.jpg", "nike_hoodie_2.jpg", "zara_kleid_1.jpg"])
    seen = []
    result = context.batch_service.run(
        paths, mode="prefix", use_ai=False,
        progress=lambda i, total, name: seen.append((i, total)),
    )
    assert result.created == 2
    assert result.failed == 0
    assert seen[-1] == (2, 2)
    drafts = context.listing_repo.list(status=ListingStatus.DRAFT.value)
    assert len(drafts) == 2
    assert all(d.batch_id == result.batch_id for d in drafts)


def test_batch_continues_after_a_broken_file(context, tmp_path):
    good = make_images(tmp_path, ["gut_1.jpg"])[0]
    broken = tmp_path / "kaputt_1.jpg"
    broken.write_text("no image")
    result = context.batch_service.run([good, broken], mode="prefix", use_ai=False)
    assert result.created == 1
    assert result.failed == 1


def test_batch_can_be_cancelled(context, tmp_path):
    paths = make_images(tmp_path, [f"p{i}_1.jpg" for i in range(4)])
    result = context.batch_service.run(
        paths, mode="single", use_ai=False, should_cancel=lambda: True
    )
    assert result.items == []


def test_batch_flags_duplicates(context, tmp_path):
    path = make_images(tmp_path, ["shirt_1.jpg"])[0]
    context.batch_service.run([path], mode="single", use_ai=False)
    second = context.batch_service.run([path], mode="single", use_ai=False)
    assert second.items[0].duplicate_of


# ---------------------------------------------------------------------- export
def test_export_writes_images_and_all_formats(context, tmp_path):
    paths = make_images(tmp_path, ["a.jpg", "b.jpg"])
    images, _ = context.image_service.import_many(paths)
    from vinted_tool.models.analysis import ImageAnalysis

    listing = context.listing_service.save_as_draft(
        context.listing_service.build_listing(
            ImageAnalysis(product_type="Hoodie", brand="Nike", size="M",
                          condition="Sehr gut", color="Blau", source="test"),
            images,
        )
    )
    result = export_listing(listing, tmp_path / "out")
    assert len(result.image_paths) == 2
    assert result.image_paths[0].name.startswith("01-")
    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["title"] == listing.title
    assert "Nike" in result.text_path.read_text(encoding="utf-8")
    with result.csv_path.open(encoding="utf-8-sig") as handle:
        row = next(csv.DictReader(handle, delimiter=";"))
    assert row["marke"] == "Nike"
    assert row["preis"] == f"{listing.price:.2f}"


def test_export_many_writes_an_overview(context, tmp_path):
    from vinted_tool.models.listing import Listing

    listings = [context.listing_repo.save(Listing(title=f"Artikel {i}", price=i + 1.0))
                for i in range(3)]
    folder = export_many(listings, tmp_path / "batchout")
    overview = folder / "uebersicht.csv"
    assert overview.exists()
    with overview.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert len(rows) == 3


def test_publish_steps_skip_empty_fields():
    from vinted_tool.models.listing import Listing, ListingImage

    listing = Listing(title="Nike Hoodie", description="Text", brand="", size="",
                      condition="Gut", price=20.0, images=[ListingImage(path="/a.jpg")])
    steps = build_publish_steps(listing, Path("/tmp/export"))
    titles = [s.title for s in steps]
    assert "Marke eintragen" not in titles
    assert "Größe wählen" not in titles
    assert steps[0].action == "open_url"
    assert any(s.action == "open_folder" for s in steps)
    assert steps[-1].title.startswith("Prüfen")
    assert [s.number for s in steps] == sorted(s.number for s in steps)


# -------------------------------------------------------------------- settings
def test_api_key_is_encrypted_at_rest(context):
    context.settings_service.set_api_key(ProviderKind.OPENROUTER, "sk-or-v1-supersecret")
    stored = context.provider_repo.get("openrouter")["api_key"]
    assert stored.startswith("enc:")
    assert "supersecret" not in stored
    assert context.settings_service.get_api_key("openrouter") == "sk-or-v1-supersecret"


def test_provider_config_prefers_settings_then_defaults(context):
    context.settings_service.update(provider_kind="anthropic", model="", base_url="")
    config = context.settings_service.provider_config()
    assert config.resolved_model() == "claude-sonnet-4-5"
    assert config.resolved_base_url().endswith("anthropic.com/v1")


def test_api_key_from_environment(context, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
    context.settings_service.update(provider_kind="openai")
    assert context.settings_service.provider_config().resolved_api_key() == "sk-env-key"


def test_settings_survive_a_restart(context, data_dir):
    from vinted_tool.app.context import AppContext

    context.settings_service.update(currency="PLN", price_strategy="quick", theme="light")
    context.close()
    reopened = AppContext(db_path=data_dir / "test.sqlite3")
    assert reopened.settings.currency == "PLN"
    assert reopened.settings.price_strategy == "quick"
    assert reopened.settings.theme == "light"
    reopened.close()


def test_encryption_roundtrip_and_masking(data_dir):
    token = encrypt("sk-test-1234567890")
    assert token != "sk-test-1234567890"
    assert decrypt(token) == "sk-test-1234567890"
    assert decrypt("") == "" and encrypt("") == ""
    assert mask("sk-test-1234567890").startswith("sk-t")
    assert "1234567890" not in mask("sk-test-1234567890")


# --------------------------------------------------------------------- logging
def test_logs_never_contain_api_keys(data_dir, caplog):
    register_secret("mein-geheimer-key-123")
    assert "sk-or-v1-abcdefghijkl" not in redact("key=sk-or-v1-abcdefghijkl")
    assert "REDACTED" in redact("Authorization: Bearer abcdefghijklmnop")
    assert "REDACTED" in redact('{"api_key": "verysecretvalue"}')
    assert "REDACTED" in redact("hier steht mein-geheimer-key-123 drin")


def test_log_file_is_written_and_redacted(data_dir):
    log_path = setup_logging(log_file=data_dir / "test.log")
    logging.getLogger("test").warning("token sk-ant-abcdefghijklmnop verwendet")
    logging.shutdown()
    content = log_path.read_text(encoding="utf-8")
    assert "sk-ant-abcdefghijklmnop" not in content
    assert "REDACTED" in content


def test_redacting_filter_handles_args():
    record = logging.LogRecord("t", logging.INFO, "f", 1, "key %s", ("sk-abcdefghijkl",), None)
    RedactingFilter().filter(record)
    assert "sk-abcdefghijkl" not in record.getMessage()
