"""Application specific exceptions with user friendly German messages."""
from __future__ import annotations


class VintedToolError(Exception):
    """Base class. ``user_message`` is what the UI shows."""

    default_message = "Es ist ein unerwarteter Fehler aufgetreten."

    def __init__(self, message: str = "", *, user_message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.user_message = user_message or message or self.default_message


class ConfigurationError(VintedToolError):
    default_message = "Die Konfiguration ist unvollständig."


class ProviderNotConfiguredError(ConfigurationError):
    default_message = (
        "Kein KI-Anbieter konfiguriert. Bitte in den Einstellungen Provider und API-Key hinterlegen."
    )


class AIError(VintedToolError):
    default_message = "KI-Analyse konnte nicht durchgeführt werden."


class AIAuthError(AIError):
    default_message = "Der API-Key wurde vom Anbieter abgelehnt. Bitte in den Einstellungen prüfen."


class AIRateLimitError(AIError):
    default_message = "Der Anbieter hat das Anfragelimit gemeldet. Bitte später erneut versuchen."


class AITimeoutError(AIError):
    default_message = "Die KI-Anfrage hat zu lange gedauert (Timeout)."


class AIResponseError(AIError):
    default_message = "Die Antwort der KI war nicht lesbar (kein gültiges JSON)."


class ImageError(VintedToolError):
    default_message = "Das Bild konnte nicht gelesen werden."


class ValidationError(VintedToolError):
    default_message = "Die Anzeige ist noch nicht vollständig."


class ExportError(VintedToolError):
    default_message = "Der Export konnte nicht erstellt werden."
