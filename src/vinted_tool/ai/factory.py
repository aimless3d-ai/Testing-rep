"""Creates the provider selected in the settings."""
from __future__ import annotations

from vinted_tool.ai.base import AIProvider
from vinted_tool.ai.providers.anthropic import AnthropicProvider
from vinted_tool.ai.providers.offline import OfflineProvider
from vinted_tool.ai.providers.openai_compatible import (
    LocalProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)
from vinted_tool.core.config import ProviderConfig
from vinted_tool.models.enums import ProviderKind

_REGISTRY: dict[ProviderKind, type[AIProvider]] = {
    ProviderKind.OPENROUTER: OpenRouterProvider,
    ProviderKind.OPENAI: OpenAICompatibleProvider,
    ProviderKind.ANTHROPIC: AnthropicProvider,
    ProviderKind.LOCAL: LocalProvider,
    ProviderKind.OFFLINE: OfflineProvider,
}


def create_provider(config: ProviderConfig, *, timeout: int = 90, max_retries: int = 2) -> AIProvider:
    try:
        kind = ProviderKind(config.kind)
    except ValueError:
        kind = ProviderKind.OFFLINE
    provider_cls = _REGISTRY[kind]
    provider = provider_cls(config, timeout=timeout, max_retries=max_retries)
    provider.kind = kind.value
    return provider


def available_kinds() -> list[ProviderKind]:
    return list(_REGISTRY)
