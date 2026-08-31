"""Anthropic Messages API provider."""
from __future__ import annotations

from vinted_tool.ai.base import AIProvider, AnalysisRequest, ProviderStatus, encode_image
from vinted_tool.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from vinted_tool.ai.schema import parse_analysis
from vinted_tool.core.errors import AIError
from vinted_tool.models.analysis import ImageAnalysis

API_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    kind = "anthropic"

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self._require_key(),
            "anthropic-version": API_VERSION,
        }

    def _content(self, request: AnalysisRequest) -> list[dict]:
        content: list[dict] = []
        for path in request.image_paths:
            mime, payload = encode_image(path)
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": payload},
                }
            )
        content.append({"type": "text", "text": build_user_prompt(request.hint)})
        return content

    def analyze(self, request: AnalysisRequest) -> ImageAnalysis:
        url = f"{self.config.resolved_base_url()}/messages"
        body = {
            "model": self.model,
            "max_tokens": 900,
            "temperature": 0.1,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": self._content(request)}],
        }
        data = self._post(url, headers=self._headers(), json_body=body)
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        if not text:
            raise AIError("Anthropic lieferte keinen Textinhalt zurück.")
        usage = data.get("usage") or {}
        tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
        return parse_analysis(text, source=self.kind, model=self.model, tokens=tokens)

    def test_connection(self) -> ProviderStatus:
        url = f"{self.config.resolved_base_url()}/messages"
        body = {
            "model": self.model,
            "max_tokens": 8,
            "messages": [{"role": "user", "content": "Antworte nur mit: OK"}],
        }
        data = self._post(url, headers=self._headers(), json_body=body)
        blocks = data.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict)).strip()
        if not text:
            return ProviderStatus(False, "Leere Antwort erhalten.", self.model)
        return ProviderStatus(True, f"Verbindung erfolgreich. Antwort: {text[:40]}", self.model)
