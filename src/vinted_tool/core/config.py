"""User settings, defaults and provider configuration."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from vinted_tool.core.secrets import decrypt, encrypt
from vinted_tool.models.enums import Condition, PriceStrategy, ProviderKind

DEFAULT_MODELS = {
    ProviderKind.OPENROUTER: "google/gemini-2.5-flash",
    ProviderKind.OPENAI: "gpt-4.1-mini",
    ProviderKind.ANTHROPIC: "claude-sonnet-4-5",
    ProviderKind.LOCAL: "llava",
    ProviderKind.OFFLINE: "heuristik",
}

DEFAULT_BASE_URLS = {
    ProviderKind.OPENROUTER: "https://openrouter.ai/api/v1",
    ProviderKind.OPENAI: "https://api.openai.com/v1",
    ProviderKind.ANTHROPIC: "https://api.anthropic.com/v1",
    ProviderKind.LOCAL: "http://localhost:11434/v1",
    ProviderKind.OFFLINE: "",
}

ENV_KEYS = {
    ProviderKind.OPENROUTER: "OPENROUTER_API_KEY",
    ProviderKind.OPENAI: "OPENAI_API_KEY",
    ProviderKind.ANTHROPIC: "ANTHROPIC_API_KEY",
    ProviderKind.LOCAL: "LOCAL_AI_API_KEY",
}


@dataclass(slots=True)
class ProviderConfig:
    kind: str = ProviderKind.OFFLINE.value
    model: str = ""
    base_url: str = ""
    api_key: str = ""

    def resolved_model(self) -> str:
        if self.model:
            return self.model
        return DEFAULT_MODELS.get(ProviderKind(self.kind), "")

    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        return DEFAULT_BASE_URLS.get(ProviderKind(self.kind), "").rstrip("/")

    def resolved_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_name = ENV_KEYS.get(ProviderKind(self.kind))
        return os.environ.get(env_name, "") if env_name else ""


@dataclass(slots=True)
class AppSettings:
    """Everything the user can configure. Stored as JSON values in SQLite."""

    provider_kind: str = ProviderKind.OFFLINE.value
    model: str = ""
    base_url: str = ""
    language: str = "Deutsch"
    currency: str = "EUR"
    price_strategy: str = PriceStrategy.NORMAL.value
    price_rounding: str = "0.50"  # "off" | "0.50" | "1.00" | "psychological"
    default_condition: str = Condition.VERY_GOOD.value
    default_shipping: str = "Versand als versichertes Paket, Abholung nach Absprache möglich."
    default_description: str = ""
    seller_style: str = "sachlich"  # sachlich | freundlich | knapp
    preferred_categories: list[str] = field(default_factory=list)
    auto_analyze_on_import: bool = True
    cache_enabled: bool = True
    max_image_dimension: int = 1600
    ai_image_count: int = 3
    request_timeout: int = 90
    max_retries: int = 2
    theme: str = "dark"
    duplicate_threshold: int = 6
    last_export_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppSettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (raw or {}).items() if k in known})

    @property
    def strategy(self) -> PriceStrategy:
        try:
            return PriceStrategy(self.price_strategy)
        except ValueError:
            return PriceStrategy.NORMAL

    @property
    def kind(self) -> ProviderKind:
        try:
            return ProviderKind(self.provider_kind)
        except ValueError:
            return ProviderKind.OFFLINE


def provider_config_from_settings(settings: AppSettings, api_key_encrypted: str) -> ProviderConfig:
    return ProviderConfig(
        kind=settings.provider_kind,
        model=settings.model,
        base_url=settings.base_url,
        api_key=decrypt(api_key_encrypted),
    )


def encrypt_api_key(value: str) -> str:
    return encrypt(value.strip())
