"""Provider interface. The rest of the app only ever talks to ``AIProvider``."""
from __future__ import annotations

import base64
import logging
import mimetypes
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from vinted_tool.core.config import ProviderConfig
from vinted_tool.core.errors import (
    AIAuthError,
    AIError,
    AIRateLimitError,
    AITimeoutError,
    ProviderNotConfiguredError,
)
from vinted_tool.models.analysis import ImageAnalysis

log = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalysisRequest:
    image_paths: list[Path]
    hint: str = ""
    language: str = "Deutsch"
    extra: dict = field(default_factory=dict)


@dataclass(slots=True)
class ProviderStatus:
    ok: bool
    message: str
    model: str = ""


def encode_image(path: Path) -> tuple[str, str]:
    """Return ``(mime_type, base64_payload)`` for a local image."""
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return mime, base64.b64encode(Path(path).read_bytes()).decode("ascii")


class AIProvider(ABC):
    """Base class with retry/timeout handling shared by all HTTP providers."""

    kind = "base"
    requires_api_key = True

    def __init__(self, config: ProviderConfig, *, timeout: int = 90, max_retries: int = 2) -> None:
        self.config = config
        self.timeout = timeout
        self.max_retries = max_retries

    # ------------------------------------------------------------- interface
    @property
    def model(self) -> str:
        return self.config.resolved_model()

    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> ImageAnalysis:
        """Analyse the product images and return a validated result."""

    @abstractmethod
    def test_connection(self) -> ProviderStatus:
        """Cheap round trip used by the "API-Verbindung testen" button."""

    # --------------------------------------------------------------- helpers
    def _require_key(self) -> str:
        key = self.config.resolved_api_key()
        if self.requires_api_key and not key:
            raise ProviderNotConfiguredError(
                f"Für {self.kind} ist kein API-Key hinterlegt."
            )
        return key

    def _post(self, url: str, *, headers: dict, json_body: dict) -> dict:
        """POST with retries on timeouts, 429 and 5xx; never retries on 4xx."""
        delay = 1.5
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, headers=headers, json=json_body)
            except httpx.TimeoutException as exc:
                last_error = AITimeoutError(
                    f"Zeitüberschreitung nach {self.timeout}s bei {self.kind}."
                )
                log.warning("AI timeout (attempt %s/%s): %s", attempt + 1, self.max_retries + 1, exc)
            except httpx.HTTPError as exc:
                last_error = AIError(f"Netzwerkfehler bei {self.kind}: {exc}")
                log.warning("AI network error (attempt %s): %s", attempt + 1, exc)
            else:
                if response.status_code in (401, 403):
                    raise AIAuthError(
                        f"{self.kind} hat den API-Key abgelehnt (HTTP {response.status_code})."
                    )
                if response.status_code == 429:
                    last_error = AIRateLimitError(f"{self.kind} meldet zu viele Anfragen (429).")
                elif response.status_code >= 500:
                    last_error = AIError(f"{self.kind} Serverfehler (HTTP {response.status_code}).")
                elif response.status_code >= 400:
                    raise AIError(
                        f"{self.kind} hat die Anfrage abgelehnt (HTTP {response.status_code}): "
                        f"{response.text[:300]}"
                    )
                else:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise AIError(f"{self.kind} lieferte keine JSON-Antwort.") from exc
            if attempt < self.max_retries:
                time.sleep(delay)
                delay *= 2
        raise last_error or AIError(f"{self.kind}: Anfrage fehlgeschlagen.")
