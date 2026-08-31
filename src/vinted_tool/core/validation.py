"""Quality gate that runs before a listing may be created."""
from __future__ import annotations

from dataclasses import dataclass, field

from vinted_tool.models.enums import Condition, QualityLevel
from vinted_tool.models.listing import Listing

TITLE_MIN = 8
TITLE_MAX = 100
DESCRIPTION_MIN = 25


@dataclass(slots=True)
class ValidationIssue:
    field_name: str
    message: str
    blocking: bool = True


@dataclass(slots=True)
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def blocking(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.blocking]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if not i.blocking]

    @property
    def level(self) -> QualityLevel:
        if self.blocking:
            return QualityLevel.INCOMPLETE
        if self.warnings:
            return QualityLevel.REVIEW
        return QualityLevel.READY

    @property
    def is_publishable(self) -> bool:
        return not self.blocking

    def summary(self) -> str:
        if not self.issues:
            return "Alle Pflichtangaben vorhanden."
        return "\n".join(("• " if i.blocking else "◦ ") + i.message for i in self.issues)


def validate_listing(listing: Listing) -> ValidationResult:
    result = ValidationResult()
    add = result.issues.append

    title = (listing.title or "").strip()
    if not title:
        add(ValidationIssue("title", "Titel fehlt."))
    elif len(title) < TITLE_MIN:
        add(ValidationIssue("title", f"Titel ist sehr kurz (mindestens {TITLE_MIN} Zeichen)."))
    elif len(title) > TITLE_MAX:
        add(ValidationIssue("title", f"Titel ist länger als {TITLE_MAX} Zeichen."))

    description = (listing.description or "").strip()
    if not description:
        add(ValidationIssue("description", "Beschreibung fehlt."))
    elif len(description) < DESCRIPTION_MIN:
        add(ValidationIssue("description", "Beschreibung ist sehr kurz.", blocking=False))

    if not listing.images:
        add(ValidationIssue("images", "Mindestens ein Bild wird benötigt."))
    elif not any(i.is_primary for i in listing.images):
        add(ValidationIssue("images", "Kein Hauptbild ausgewählt.", blocking=False))

    if not listing.category_path:
        add(ValidationIssue("category", "Kategorie fehlt."))

    if not listing.price or listing.price <= 0:
        add(ValidationIssue("price", "Preis fehlt oder ist 0."))
    elif listing.price > 5000:
        add(ValidationIssue("price", "Preis wirkt ungewöhnlich hoch – bitte prüfen.", blocking=False))

    if not (listing.condition or "").strip():
        add(ValidationIssue("condition", "Zustand fehlt."))
    elif Condition.from_text(listing.condition) is None:
        add(ValidationIssue("condition", "Zustand entspricht keiner Vinted-Auswahl.", blocking=False))

    if not (listing.brand or "").strip():
        add(ValidationIssue("brand", "Marke fehlt – ohne Marke wird die Anzeige seltener gefunden.",
                            blocking=False))

    needs_size = _needs_size(listing)
    if needs_size and not (listing.size or "").strip():
        add(ValidationIssue("size", "Größe fehlt für diese Kategorie."))

    if not (listing.color or "").strip():
        add(ValidationIssue("color", "Farbe fehlt.", blocking=False))

    # obvious contradictions
    condition = Condition.from_text(listing.condition)
    damages = (listing.analysis or {}).get("damages") or []
    if condition in (Condition.NEW_WITH_TAG, Condition.NEW_WITHOUT_TAG) and damages:
        add(ValidationIssue(
            "condition",
            "Zustand ist „neu“, es wurden aber Mängel erkannt – bitte prüfen.",
            blocking=False,
        ))
    if description and title and listing.brand:
        brand = listing.brand.strip().lower()
        if brand and brand not in title.lower() and brand not in description.lower():
            add(ValidationIssue("brand", "Marke kommt weder im Titel noch in der Beschreibung vor.",
                                blocking=False))
    if listing.price and listing.price_suggestion.high and listing.price > listing.price_suggestion.high * 2:
        add(ValidationIssue("price", "Preis liegt weit über dem Vorschlag – bitte prüfen.",
                            blocking=False))
    return result


def _needs_size(listing: Listing) -> bool:
    from vinted_tool.core.categories import find_by_path

    entry = find_by_path(listing.category_path) if listing.category_path else None
    return bool(entry and entry.size_system != "none")
