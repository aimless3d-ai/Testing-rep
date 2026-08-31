"""Turns an analysis plus user defaults into a complete listing."""
from __future__ import annotations

import logging

from vinted_tool.core import templates as template_engine
from vinted_tool.core.categories import find_by_path, match_categories
from vinted_tool.core.dedupe import DuplicateHit, find_duplicates
from vinted_tool.core.pricing import PriceInputs, suggest_price
from vinted_tool.core.validation import ValidationResult, validate_listing
from vinted_tool.database.repositories import ListingRepository, TemplateRepository
from vinted_tool.models.analysis import ImageAnalysis
from vinted_tool.models.enums import Condition, ListingStatus, PriceStrategy
from vinted_tool.models.listing import Listing, ListingImage
from vinted_tool.services.settings_service import SettingsService
from vinted_tool.utils.text import build_keywords, build_title, humanize_list, titleize

log = logging.getLogger(__name__)


class ListingService:
    def __init__(
        self,
        listing_repo: ListingRepository,
        template_repo: TemplateRepository,
        settings_service: SettingsService,
    ) -> None:
        self.repo = listing_repo
        self.templates = template_repo
        self.settings_service = settings_service

    # ------------------------------------------------------------------ build
    def build_listing(
        self,
        analysis: ImageAnalysis,
        images: list[ListingImage],
        *,
        template_body: str | None = None,
        existing: Listing | None = None,
        batch_id: str | None = None,
    ) -> Listing:
        settings = self.settings_service.load()
        listing = existing or Listing()
        listing.images = images
        listing.batch_id = batch_id or listing.batch_id
        listing.analysis = analysis.to_dict()

        matches = match_categories(
            product_type=analysis.product_type,
            keywords=analysis.keywords + analysis.category_candidates,
            text=" ".join(filter(None, [analysis.notes, analysis.model, analysis.material])),
        )
        listing.category_candidates = [m.label for m in matches]
        if matches:
            listing.category_path = matches[0].path
        elif settings.preferred_categories:
            preferred = find_by_path(settings.preferred_categories[0])
            listing.category_path = list(preferred.path) if preferred else []

        listing.brand = analysis.brand or ""
        listing.color = analysis.color or ""
        listing.material = analysis.material or ""
        listing.size = analysis.size or ""
        listing.condition = analysis.condition or settings.default_condition
        listing.currency = settings.currency
        listing.shipping = settings.default_shipping

        listing.title = build_title(
            brand=analysis.brand,
            product_type=analysis.product_type or (matches[0].entry.path[-1] if matches else None),
            model=analysis.model,
            color=analysis.color,
            size=analysis.size,
            pattern=analysis.pattern,
        )
        listing.keywords = build_keywords(
            analysis.keywords
            + [analysis.brand, analysis.product_type, analysis.color, analysis.material]
        )
        listing.description = self.render_description(listing, analysis, template_body)

        listing.price_suggestion = self.suggest_price(listing, analysis)
        if not listing.price:
            listing.price = listing.price_suggestion.recommended
        listing.status = ListingStatus.DRAFT.value
        return listing

    def render_description(
        self, listing: Listing, analysis: ImageAnalysis | None, template_body: str | None = None
    ) -> str:
        settings = self.settings_service.load()
        if template_body is None:
            default = self.templates.get_default()
            template_body = default.body if default else template_engine.DEFAULT_TEMPLATES[0][1]
        analysis = analysis or ImageAnalysis.from_dict(listing.analysis or {})
        values = {
            "brand": listing.brand,
            "product": titleize(
                analysis.product_type
                or (listing.category_path[-1] if listing.category_path else "")
            ),
            "title": listing.title,
            "size": listing.size,
            "condition": listing.condition,
            "color": humanize_list([listing.color] + (analysis.secondary_colors or [])),
            "material": listing.material,
            "category": " > ".join(listing.category_path),
            "price": f"{listing.price:.2f}" if listing.price else "",
            "currency": listing.currency,
            "keywords": ", ".join(listing.keywords),
            "features": humanize_list(analysis.features or []),
            "damages": humanize_list([d.description for d in analysis.damages]),
            "shipping": listing.shipping or settings.default_shipping,
        }
        body = template_engine.render(template_body, values)
        if settings.default_description.strip():
            body = f"{body}\n\n{settings.default_description.strip()}"
        return body.strip()

    def suggest_price(self, listing: Listing, analysis: ImageAnalysis | None = None):
        settings = self.settings_service.load()
        analysis = analysis or ImageAnalysis.from_dict(listing.analysis or {})
        severities = [d.severity for d in analysis.damages] or ["leicht"]
        worst = "stark" if "stark" in severities else "mittel" if "mittel" in severities else "leicht"
        try:
            strategy = PriceStrategy(settings.price_strategy)
        except ValueError:
            strategy = PriceStrategy.NORMAL
        return suggest_price(
            PriceInputs(
                category_path=listing.category_path,
                brand=listing.brand,
                condition=listing.condition or settings.default_condition,
                damages=len(analysis.damages),
                damage_severity=worst,
                strategy=strategy,
                rounding=settings.price_rounding,
                currency=settings.currency,
            )
        )

    # -------------------------------------------------------------- persistence
    def save(self, listing: Listing) -> Listing:
        return self.repo.save(listing)

    def save_as_draft(self, listing: Listing) -> Listing:
        listing.status = ListingStatus.DRAFT.value
        return self.repo.save(listing)

    def mark_ready(self, listing: Listing) -> Listing:
        listing.status = ListingStatus.READY.value
        return self.repo.save(listing)

    def mark_status(self, listing: Listing, status: ListingStatus) -> Listing:
        listing.status = status.value
        return self.repo.save(listing)

    def delete(self, listing: Listing) -> None:
        if listing.id is not None:
            self.repo.delete(listing.id)

    # ---------------------------------------------------------------- checking
    def validate(self, listing: Listing) -> ValidationResult:
        return validate_listing(listing)

    def check_duplicates(self, listing: Listing) -> list[DuplicateHit]:
        settings = self.settings_service.load()
        candidates = [
            {"sha256": image.sha256, "phash": image.phash} for image in listing.images
        ]
        known = self.repo.all_image_fingerprints(exclude_listing_id=listing.id)
        return find_duplicates(candidates, known, threshold=settings.duplicate_threshold)

    def condition_choices(self) -> list[str]:
        return Condition.values()
