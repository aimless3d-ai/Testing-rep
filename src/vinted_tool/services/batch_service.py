"""Batch mode: many photos in, one draft per product out."""
from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from vinted_tool.ai.service import AnalysisService
from vinted_tool.core.dedupe import hamming_distance
from vinted_tool.core.errors import VintedToolError
from vinted_tool.models.listing import Listing
from vinted_tool.services.image_service import ImageService, ImportOptions
from vinted_tool.services.listing_service import ListingService
from vinted_tool.services.settings_service import SettingsService
from vinted_tool.utils.hashing import dhash

log = logging.getLogger(__name__)

GROUP_SIMILARITY = 12  # dhash distance below which two photos show the same product


@dataclass(slots=True)
class BatchItem:
    sources: list[Path]
    listing: Listing | None = None
    error: str = ""
    duplicate_of: str = ""

    @property
    def label(self) -> str:
        if self.listing and self.listing.title:
            return self.listing.title
        return self.sources[0].name if self.sources else "Unbenannt"


@dataclass(slots=True)
class BatchResult:
    batch_id: str
    items: list[BatchItem] = field(default_factory=list)

    @property
    def created(self) -> int:
        return sum(1 for i in self.items if i.listing is not None)

    @property
    def failed(self) -> int:
        return sum(1 for i in self.items if i.error)


def group_by_prefix(paths: list[Path]) -> list[list[Path]]:
    """Group by the file name prefix (``kleid_1.jpg`` + ``kleid_2.jpg``)."""
    groups: dict[str, list[Path]] = {}
    for path in sorted(paths):
        key = re.sub(r"[ _\-.]*\d+$", "", path.stem).strip().lower() or path.stem.lower()
        groups.setdefault(key, []).append(path)
    return list(groups.values())


def group_by_similarity(paths: list[Path], threshold: int = GROUP_SIMILARITY) -> list[list[Path]]:
    """Group consecutive photos that look like the same product."""
    groups: list[list[Path]] = []
    previous_hash: str | None = None
    for path in sorted(paths):
        try:
            current = dhash(path)
        except (OSError, ValueError):
            current = None
        if (
            groups
            and current
            and previous_hash
            and hamming_distance(current, previous_hash) <= threshold
        ):
            groups[-1].append(path)
        else:
            groups.append([path])
        previous_hash = current or previous_hash
    return groups


class BatchService:
    GROUPING_MODES = {
        "single": "Ein Bild = ein Produkt",
        "prefix": "Nach Dateiname gruppieren (produkt_1, produkt_2 …)",
        "similarity": "Ähnliche Bilder automatisch gruppieren",
    }

    def __init__(
        self,
        image_service: ImageService,
        analysis_service: AnalysisService,
        listing_service: ListingService,
        settings_service: SettingsService,
    ) -> None:
        self.images = image_service
        self.analysis = analysis_service
        self.listings = listing_service
        self.settings_service = settings_service

    def group(self, paths: list[Path], mode: str) -> list[list[Path]]:
        if mode == "prefix":
            return group_by_prefix(paths)
        if mode == "similarity":
            return group_by_similarity(paths)
        return [[p] for p in sorted(paths)]

    def run(
        self,
        paths: list[Path],
        *,
        mode: str = "prefix",
        progress: Callable[[int, int, str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
        use_ai: bool = True,
    ) -> BatchResult:
        batch_id = uuid.uuid4().hex[:12]
        groups = self.group(paths, mode)
        result = BatchResult(batch_id=batch_id)
        settings = self.settings_service.load()
        total = len(groups)

        for index, group in enumerate(groups, start=1):
            if should_cancel and should_cancel():
                log.info("Batch abgebrochen nach %s/%s", index - 1, total)
                break
            if progress:
                progress(index, total, group[0].name)
            item = BatchItem(sources=group)
            try:
                images, errors = self.images.import_many(
                    list(group),
                    ImportOptions(max_dimension=settings.max_image_dimension,
                                  name_hint=group[0].stem),
                )
                if not images:
                    item.error = "; ".join(errors) or "Keine gültigen Bilder."
                    result.items.append(item)
                    continue
                outcome = (
                    self.analysis.analyze([i.path for i in images])
                    if use_ai
                    else self.analysis.analyze_offline([i.path for i in images])
                )
                listing = self.listings.build_listing(
                    outcome.analysis, images, batch_id=batch_id
                )
                duplicates = self.listings.check_duplicates(listing)
                if duplicates:
                    item.duplicate_of = duplicates[0].description
                    listing.notes = f"Mögliches Duplikat: {duplicates[0].description}"
                item.listing = self.listings.save_as_draft(listing)
            except VintedToolError as exc:
                item.error = exc.user_message
                log.warning("Batch-Element fehlgeschlagen (%s): %s", group[0].name, exc)
            except Exception as exc:  # noqa: BLE001 - one bad item must not kill the batch
                item.error = f"Unerwarteter Fehler: {exc}"
                log.exception("Unerwarteter Fehler im Batch-Modus")
            result.items.append(item)
        return result
