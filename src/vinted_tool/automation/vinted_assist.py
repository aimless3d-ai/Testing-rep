"""Assisted publishing.

The app opens the official Vinted upload page in the user's own browser and
hands over the fields step by step via the clipboard. There is no automated
login, no captcha handling and no hidden request – the user stays in control
and completes the publication themselves.
"""
from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from pathlib import Path

from vinted_tool.models.listing import Listing

UPLOAD_URL = "https://www.vinted.de/items/new"
CATALOG_SEARCH_URL = "https://www.vinted.de/catalog?search_text={query}"


@dataclass(slots=True)
class PublishStep:
    number: int
    title: str
    detail: str
    clipboard_text: str = ""
    action: str = ""  # "" | "open_url" | "open_folder"
    payload: str = ""

    @property
    def has_clipboard(self) -> bool:
        return bool(self.clipboard_text.strip())


def build_publish_steps(listing: Listing, export_folder: Path | None = None) -> list[PublishStep]:
    steps: list[PublishStep] = [
        PublishStep(
            1,
            "Vinted öffnen und anmelden",
            "Die offizielle Seite „Artikel einstellen“ wird in deinem Browser geöffnet. "
            "Melde dich dort wie gewohnt selbst an – die App speichert keine Zugangsdaten.",
            action="open_url",
            payload=UPLOAD_URL,
        ),
    ]
    if export_folder:
        steps.append(
            PublishStep(
                2,
                "Bilder hochladen",
                f"Der Ordner mit {len(listing.images)} vorbereiteten Bildern wird geöffnet. "
                "Ziehe die Bilder in der Reihenfolge 01, 02, … in das Vinted-Formular.",
                action="open_folder",
                payload=str(export_folder),
            )
        )
    number = len(steps) + 1
    fields: list[tuple[str, str, str]] = [
        ("Titel einfügen", listing.title, "Feld „Titel“"),
        ("Beschreibung einfügen", listing.description, "Feld „Beschreibung“"),
        ("Kategorie wählen", " > ".join(listing.category_path), "Feld „Kategorie“"),
        ("Marke eintragen", listing.brand, "Feld „Marke“"),
        ("Größe wählen", listing.size, "Feld „Größe“"),
        ("Zustand wählen", listing.condition, "Feld „Zustand“"),
        ("Farbe wählen", listing.color, "Feld „Farbe“"),
        ("Material eintragen", listing.material, "Feld „Material“ (optional)"),
        ("Preis eintragen", f"{listing.price:.2f}", "Feld „Preis“"),
    ]
    for label, value, target in fields:
        if not str(value).strip():
            continue
        steps.append(
            PublishStep(
                number,
                label,
                f"In die Zwischenablage kopieren und in {target} einfügen.",
                clipboard_text=str(value),
            )
        )
        number += 1
    steps.append(
        PublishStep(
            number,
            "Prüfen und veröffentlichen",
            "Kontrolliere alle Angaben im Vinted-Formular und klicke dort auf „Hochladen“. "
            "Danach kannst du die Anzeige hier als „Veröffentlicht“ markieren.",
        )
    )
    return steps


def open_upload_page() -> bool:
    return webbrowser.open(UPLOAD_URL)


def open_price_research(listing: Listing) -> bool:
    """Open a Vinted search for comparable items so the user can check the price."""
    query = " ".join(filter(None, [listing.brand, listing.title]))[:80].strip()
    if not query:
        return False
    return webbrowser.open(CATALOG_SEARCH_URL.format(query=query.replace(" ", "%20")))
