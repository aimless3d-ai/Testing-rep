"""Loads and stores :class:`AppSettings` plus the encrypted API keys."""
from __future__ import annotations

import logging

from vinted_tool.app.logging_setup import register_secret
from vinted_tool.core.config import (
    DEFAULT_BASE_URLS,
    DEFAULT_MODELS,
    AppSettings,
    ProviderConfig,
    encrypt_api_key,
)
from vinted_tool.core.secrets import decrypt
from vinted_tool.database.repositories import ProviderConfigRepository, SettingsRepository
from vinted_tool.models.enums import ProviderKind

log = logging.getLogger(__name__)
_SETTINGS_KEY = "app_settings"


class SettingsService:
    def __init__(self, settings_repo: SettingsRepository, provider_repo: ProviderConfigRepository) -> None:
        self.repo = settings_repo
        self.provider_repo = provider_repo
        self._cached: AppSettings | None = None

    # --------------------------------------------------------------- settings
    def load(self) -> AppSettings:
        if self._cached is None:
            raw = self.repo.get_all().get(_SETTINGS_KEY) or {}
            self._cached = AppSettings.from_dict(raw if isinstance(raw, dict) else {})
        return self._cached

    def save(self, settings: AppSettings) -> AppSettings:
        self.repo.set(_SETTINGS_KEY, settings.to_dict())
        self._cached = settings
        return settings

    def update(self, **values) -> AppSettings:
        settings = self.load()
        for key, value in values.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        return self.save(settings)

    # -------------------------------------------------------------- providers
    def get_api_key(self, kind: str | ProviderKind) -> str:
        kind_value = kind.value if isinstance(kind, ProviderKind) else str(kind)
        row = self.provider_repo.get(kind_value)
        key = decrypt(row["api_key"]) if row else ""
        register_secret(key)
        return key

    def set_api_key(self, kind: str | ProviderKind, api_key: str) -> None:
        kind_value = kind.value if isinstance(kind, ProviderKind) else str(kind)
        row = self.provider_repo.get(kind_value) or {}
        register_secret(api_key)
        self.provider_repo.upsert(
            kind_value,
            model=row.get("model", ""),
            base_url=row.get("base_url", ""),
            api_key=encrypt_api_key(api_key),
        )

    def provider_config(self, kind: str | ProviderKind | None = None) -> ProviderConfig:
        settings = self.load()
        kind_value = (
            kind.value if isinstance(kind, ProviderKind) else (kind or settings.provider_kind)
        )
        try:
            provider_kind = ProviderKind(kind_value)
        except ValueError:
            provider_kind = ProviderKind.OFFLINE
        stored = self.provider_repo.get(provider_kind.value) or {}
        is_active = provider_kind.value == settings.provider_kind
        model = (settings.model if is_active else "") or stored.get("model") or DEFAULT_MODELS[provider_kind]
        base_url = (
            (settings.base_url if is_active else "")
            or stored.get("base_url")
            or DEFAULT_BASE_URLS[provider_kind]
        )
        api_key = self.get_api_key(provider_kind)
        return ProviderConfig(
            kind=provider_kind.value, model=model, base_url=base_url, api_key=api_key
        )

    def remember_provider_details(self, kind: str | ProviderKind, model: str, base_url: str) -> None:
        kind_value = kind.value if isinstance(kind, ProviderKind) else str(kind)
        row = self.provider_repo.get(kind_value) or {}
        self.provider_repo.upsert(
            kind_value, model=model, base_url=base_url, api_key=row.get("api_key", "")
        )
