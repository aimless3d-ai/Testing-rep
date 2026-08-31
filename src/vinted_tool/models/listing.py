"""Listing and image domain models."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from vinted_tool.models.enums import ListingStatus


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class ListingImage:
    path: str
    original_name: str = ""
    thumbnail_path: str | None = None
    phash: str | None = None
    sha256: str | None = None
    width: int = 0
    height: int = 0
    position: int = 0
    is_primary: bool = False
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ListingImage":
        known = set(cls.__slots__)
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})


@dataclass(slots=True)
class PriceSuggestion:
    quick: float = 0.0
    recommended: float = 0.0
    high: float = 0.0
    currency: str = "EUR"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PriceSuggestion":
        known = set(cls.__slots__)
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})


@dataclass(slots=True)
class Listing:
    title: str = ""
    description: str = ""
    category_path: list[str] = field(default_factory=list)
    category_candidates: list[str] = field(default_factory=list)
    brand: str = ""
    size: str = ""
    color: str = ""
    condition: str = ""
    material: str = ""
    price: float = 0.0
    currency: str = "EUR"
    keywords: list[str] = field(default_factory=list)
    shipping: str = ""
    status: str = ListingStatus.DRAFT.value
    images: list[ListingImage] = field(default_factory=list)
    price_suggestion: PriceSuggestion = field(default_factory=PriceSuggestion)
    analysis: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    batch_id: str | None = None
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)
    id: int | None = None

    @property
    def primary_image(self) -> ListingImage | None:
        for image in self.images:
            if image.is_primary:
                return image
        return self.images[0] if self.images else None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["images"] = [i.to_dict() for i in self.images]
        data["price_suggestion"] = self.price_suggestion.to_dict()
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Listing":
        raw = dict(raw or {})
        images = [ListingImage.from_dict(i) for i in raw.get("images") or []]
        price = PriceSuggestion.from_dict(raw.get("price_suggestion") or {})
        known = set(cls.__slots__)
        payload = {k: v for k, v in raw.items() if k in known}
        payload["images"] = images
        payload["price_suggestion"] = price
        return cls(**payload)
