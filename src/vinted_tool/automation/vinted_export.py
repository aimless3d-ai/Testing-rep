"""Export a listing into a folder that can be uploaded to Vinted by hand.

Vinted offers no public API for creating listings, and this tool deliberately
does not automate the login or work around any protection mechanism. Instead it
prepares everything so that publishing is a matter of drag & drop plus copy &
paste.
"""
from __future__ import annotations

import csv
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from vinted_tool.app.paths import exports_dir
from vinted_tool.core.errors import ExportError
from vinted_tool.models.listing import Listing
from vinted_tool.utils.files import slugify

log = logging.getLogger(__name__)

CSV_COLUMNS = [
    "titel", "beschreibung", "kategorie", "marke", "groesse", "farbe",
    "zustand", "material", "preis", "waehrung", "suchbegriffe", "bilder",
]


@dataclass(slots=True)
class ExportResult:
    folder: Path
    image_paths: list[Path]
    json_path: Path
    text_path: Path
    csv_path: Path


def listing_to_row(listing: Listing) -> dict[str, str]:
    return {
        "titel": listing.title,
        "beschreibung": listing.description,
        "kategorie": " > ".join(listing.category_path),
        "marke": listing.brand,
        "groesse": listing.size,
        "farbe": listing.color,
        "zustand": listing.condition,
        "material": listing.material,
        "preis": f"{listing.price:.2f}",
        "waehrung": listing.currency,
        "suchbegriffe": ", ".join(listing.keywords),
        "bilder": " | ".join(Path(i.path).name for i in listing.images),
    }


def _text_block(listing: Listing) -> str:
    row = listing_to_row(listing)
    lines = [
        "VINTED-ANZEIGE",
        "=" * 40,
        f"Titel:        {row['titel']}",
        f"Kategorie:    {row['kategorie']}",
        f"Marke:        {row['marke']}",
        f"Größe:        {row['groesse']}",
        f"Farbe:        {row['farbe']}",
        f"Material:     {row['material']}",
        f"Zustand:      {row['zustand']}",
        f"Preis:        {row['preis']} {row['waehrung']}",
        f"Suchbegriffe: {row['suchbegriffe']}",
        "",
        "Beschreibung:",
        "-" * 40,
        listing.description,
        "",
        "Bilder (in dieser Reihenfolge hochladen):",
    ]
    lines += [f"  {n + 1}. {Path(i.path).name}" for n, i in enumerate(listing.images)]
    return "\n".join(lines) + "\n"


def export_listing(listing: Listing, target_dir: Path | str | None = None) -> ExportResult:
    """Write images plus all fields into one folder."""
    base = Path(target_dir) if target_dir else exports_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = base / f"{stamp}-{slugify(listing.title, fallback='anzeige')}"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        image_paths: list[Path] = []
        for position, image in enumerate(listing.images, start=1):
            source = Path(image.path)
            if not source.is_file():
                log.warning("Bild fehlt beim Export: %s", source)
                continue
            target = folder / f"{position:02d}-{slugify(listing.title, fallback='bild')}{source.suffix}"
            shutil.copy2(source, target)
            image_paths.append(target)

        json_path = folder / "anzeige.json"
        payload = listing.to_dict()
        payload["exported_at"] = datetime.now().isoformat(timespec="seconds")
        payload["images"] = [{"file": p.name} for p in image_paths]
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        text_path = folder / "anzeige.txt"
        text_path.write_text(_text_block(listing), encoding="utf-8")

        csv_path = folder / "anzeige.csv"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, delimiter=";")
            writer.writeheader()
            writer.writerow(listing_to_row(listing))
    except OSError as exc:
        raise ExportError(f"Export nach {folder} fehlgeschlagen: {exc}") from exc

    return ExportResult(folder, image_paths, json_path, text_path, csv_path)


def export_many(listings: list[Listing], target_dir: Path | str | None = None) -> Path:
    """Export several listings plus one combined CSV overview."""
    base = Path(target_dir) if target_dir else exports_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = base / f"{stamp}-sammelexport"
    folder.mkdir(parents=True, exist_ok=True)
    for listing in listings:
        export_listing(listing, folder)
    overview = folder / "uebersicht.csv"
    try:
        with overview.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, delimiter=";")
            writer.writeheader()
            for listing in listings:
                writer.writerow(listing_to_row(listing))
    except OSError as exc:
        raise ExportError(f"Übersicht konnte nicht geschrieben werden: {exc}") from exc
    return folder
