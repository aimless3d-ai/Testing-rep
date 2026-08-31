"""Analysis orchestration: cache lookup, image selection, provider call."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from vinted_tool.ai.base import AnalysisRequest
from vinted_tool.ai.factory import create_provider
from vinted_tool.ai.providers.offline import OfflineProvider, dominant_colors
from vinted_tool.core.errors import AIError, VintedToolError
from vinted_tool.database.repositories import AnalysisCacheRepository
from vinted_tool.models.analysis import ImageAnalysis
from vinted_tool.services.settings_service import SettingsService
from vinted_tool.utils.hashing import sha256_file, sha256_text

log = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalysisOutcome:
    analysis: ImageAnalysis
    from_cache: bool = False
    warning: str = ""


class AnalysisService:
    """The only entry point the UI uses to run an analysis."""

    def __init__(self, settings_service: SettingsService, cache_repo: AnalysisCacheRepository) -> None:
        self.settings_service = settings_service
        self.cache = cache_repo

    # ------------------------------------------------------------------ cache
    def cache_key(self, paths: list[Path], provider_kind: str, model: str, hint: str) -> str:
        digests = sorted(sha256_file(p) for p in paths)
        payload = json.dumps(
            {"images": digests, "provider": provider_kind, "model": model, "hint": hint.strip()},
            sort_keys=True,
        )
        return sha256_text(payload)

    # ---------------------------------------------------------------- analyse
    def analyze(
        self,
        image_paths: list[Path | str],
        *,
        hint: str = "",
        force_refresh: bool = False,
    ) -> AnalysisOutcome:
        paths = [Path(p) for p in image_paths if Path(p).is_file()]
        if not paths:
            raise AIError("Keine Bilder zum Analysieren vorhanden.",
                          user_message="Bitte zuerst mindestens ein Bild importieren.")

        settings = self.settings_service.load()
        config = self.settings_service.provider_config()
        provider = create_provider(
            config, timeout=settings.request_timeout, max_retries=settings.max_retries
        )
        # Only the first N photos go to the model – they carry almost all the
        # information and every extra image costs tokens.
        selected = paths[: max(1, settings.ai_image_count)]
        key = self.cache_key(selected, config.kind, provider.model, hint)

        if settings.cache_enabled and not force_refresh:
            cached = self.cache.get(key)
            if cached:
                analysis = ImageAnalysis.from_dict(cached)
                analysis.cached = True
                log.info("Analyse aus dem Cache (%s Bilder)", len(selected))
                return AnalysisOutcome(analysis, from_cache=True)

        request = AnalysisRequest(image_paths=selected, hint=hint, language=settings.language)
        try:
            analysis = provider.analyze(request)
            warning = ""
        except VintedToolError as exc:
            log.warning("Provider %s fehlgeschlagen: %s", config.kind, exc)
            if isinstance(provider, OfflineProvider):
                raise
            raise AIError(str(exc), user_message=exc.user_message) from exc

        analysis = self._enrich_with_local_signals(analysis, paths)
        if settings.cache_enabled:
            self.cache.put(
                key, analysis.to_dict(), config.kind, provider.model, analysis.tokens_used
            )
        return AnalysisOutcome(analysis, from_cache=False, warning=warning)

    def analyze_offline(self, image_paths: list[Path | str], *, hint: str = "") -> AnalysisOutcome:
        """Local fallback used by the "Manuell ausfüllen" path – never fails on network."""
        paths = [Path(p) for p in image_paths if Path(p).is_file()]
        provider = OfflineProvider(self.settings_service.provider_config("offline"))
        analysis = provider.analyze(AnalysisRequest(image_paths=paths, hint=hint))
        return AnalysisOutcome(analysis, from_cache=False, warning="Offline-Analyse verwendet.")

    # ---------------------------------------------------------------- helpers
    def _enrich_with_local_signals(self, analysis: ImageAnalysis, paths: list[Path]) -> ImageAnalysis:
        """Fill only colour gaps from real pixels – measured, not guessed."""
        if analysis.color:
            return analysis
        colors = dominant_colors(paths[:3])
        if colors:
            analysis.color = colors[0]
            analysis.secondary_colors = colors[1:]
            analysis.confidence.setdefault("color", 0.6)
            note = "Farbe wurde lokal aus den Bildpixeln bestimmt."
            analysis.notes = f"{analysis.notes} {note}".strip() if analysis.notes else note
        return analysis

    def test_connection(self, kind: str | None = None):
        settings = self.settings_service.load()
        config = self.settings_service.provider_config(kind)
        provider = create_provider(
            config, timeout=min(settings.request_timeout, 30), max_retries=0
        )
        return provider.test_connection()

    def cache_stats(self) -> dict[str, int]:
        return self.cache.stats()

    def clear_cache(self) -> int:
        return self.cache.clear()
