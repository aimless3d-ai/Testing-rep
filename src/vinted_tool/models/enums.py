"""Enumerations shared across the whole application."""
from __future__ import annotations

from enum import Enum

UNKNOWN = "Nicht sicher erkannt – bitte auswählen."
"""Sentinel used everywhere the AI is not confident. Never guess instead."""


class Condition(str, Enum):
    NEW_WITH_TAG = "Neu mit Etikett"
    NEW_WITHOUT_TAG = "Neu ohne Etikett"
    VERY_GOOD = "Sehr gut"
    GOOD = "Gut"
    SATISFACTORY = "Zufriedenstellend"

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]

    @classmethod
    def from_text(cls, text: str | None) -> "Condition | None":
        if not text:
            return None
        needle = text.strip().casefold()
        for member in cls:
            if member.value.casefold() == needle:
                return member
        aliases = {
            "new with tags": cls.NEW_WITH_TAG,
            "neu mit etiketten": cls.NEW_WITH_TAG,
            "new without tags": cls.NEW_WITHOUT_TAG,
            "neuwertig": cls.NEW_WITHOUT_TAG,
            "very good": cls.VERY_GOOD,
            "good": cls.GOOD,
            "satisfactory": cls.SATISFACTORY,
            "befriedigend": cls.SATISFACTORY,
            "akzeptabel": cls.SATISFACTORY,
        }
        return aliases.get(needle)

    @property
    def quality_factor(self) -> float:
        """Multiplier applied to the base price of a category."""
        return {
            Condition.NEW_WITH_TAG: 1.0,
            Condition.NEW_WITHOUT_TAG: 0.88,
            Condition.VERY_GOOD: 0.72,
            Condition.GOOD: 0.58,
            Condition.SATISFACTORY: 0.42,
        }[self]


class ListingStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    EXPORTED = "exported"
    PUBLISHED = "published"
    ARCHIVED = "archived"

    @property
    def label(self) -> str:
        return {
            ListingStatus.DRAFT: "Entwurf",
            ListingStatus.READY: "Bereit",
            ListingStatus.EXPORTED: "Exportiert",
            ListingStatus.PUBLISHED: "Veröffentlicht",
            ListingStatus.ARCHIVED: "Archiviert",
        }[self]


class QualityLevel(str, Enum):
    READY = "ready"
    REVIEW = "review"
    INCOMPLETE = "incomplete"

    @property
    def badge(self) -> str:
        return {
            QualityLevel.READY: "🟢 Bereit",
            QualityLevel.REVIEW: "🟡 Überprüfung empfohlen",
            QualityLevel.INCOMPLETE: "🔴 Informationen fehlen",
        }[self]


class PriceStrategy(str, Enum):
    QUICK = "quick"
    NORMAL = "normal"
    HIGH = "high"

    @property
    def label(self) -> str:
        return {
            PriceStrategy.QUICK: "Schnellverkauf",
            PriceStrategy.NORMAL: "Normal",
            PriceStrategy.HIGH: "Höherer Startpreis",
        }[self]


class ProviderKind(str, Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    OFFLINE = "offline"

    @property
    def label(self) -> str:
        return {
            ProviderKind.OPENROUTER: "OpenRouter",
            ProviderKind.OPENAI: "OpenAI",
            ProviderKind.ANTHROPIC: "Anthropic",
            ProviderKind.LOCAL: "Lokales Modell (OpenAI-kompatibel)",
            ProviderKind.OFFLINE: "Offline-Analyse (ohne KI)",
        }[self]
