"""Result of an image analysis. Unknown fields stay ``None`` – never guessed."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Damage:
    description: str
    severity: str = "leicht"  # leicht | mittel | stark

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Damage":
        return cls(
            description=str(raw.get("description", "")).strip(),
            severity=str(raw.get("severity", "leicht")).strip() or "leicht",
        )


@dataclass(slots=True)
class ImageAnalysis:
    """Everything the analysis layer could derive from the product photos.

    ``None`` means "not recognised" and must be surfaced to the user as
    "Nicht sicher erkannt – bitte auswählen." – it must never be invented.
    """

    product_type: str | None = None
    category_path: list[str] = field(default_factory=list)
    category_candidates: list[str] = field(default_factory=list)
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    secondary_colors: list[str] = field(default_factory=list)
    pattern: str | None = None
    material: str | None = None
    size: str | None = None
    condition: str | None = None
    damages: list[Damage] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    notes: str | None = None
    confidence: dict[str, float] = field(default_factory=dict)
    source: str = "offline"
    model_used: str | None = None
    tokens_used: int = 0
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["damages"] = [d.to_dict() for d in self.damages]
        return data

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ImageAnalysis":
        raw = dict(raw or {})
        damages = [
            Damage.from_dict(d) if isinstance(d, dict) else Damage(str(d))
            for d in (raw.get("damages") or [])
        ]
        known = {f for f in cls.__slots__}
        payload = {k: v for k, v in raw.items() if k in known}
        payload["damages"] = damages
        return cls(**payload)

    def missing_fields(self) -> list[str]:
        checks = {
            "Produktart": self.product_type,
            "Marke": self.brand,
            "Farbe": self.color,
            "Größe": self.size,
            "Zustand": self.condition,
            "Kategorie": self.category_path,
        }
        return [label for label, value in checks.items() if not value]
