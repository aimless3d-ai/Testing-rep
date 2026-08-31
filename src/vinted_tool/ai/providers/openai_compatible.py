"""OpenAI-compatible chat completions – used by OpenAI, OpenRouter and local servers."""
from __future__ import annotations

import logging

from vinted_tool.ai.base import AIProvider, AnalysisRequest, ProviderStatus, encode_image
from vinted_tool.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from vinted_tool.ai.schema import parse_analysis
from vinted_tool.core.errors import AIError
from vinted_tool.models.analysis import ImageAnalysis

log = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    kind = "openai"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key = self._require_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _build_messages(self, request: AnalysisRequest) -> list[dict]:
        content: list[dict] = [{"type": "text", "text": build_user_prompt(request.hint)}]
        for path in request.image_paths:
            mime, payload = encode_image(path)
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{payload}"}}
            )
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]

    def _body(self, request: AnalysisRequest) -> dict:
        return {
            "model": self.model,
            "messages": self._build_messages(request),
            "temperature": 0.1,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
        }

    def analyze(self, request: AnalysisRequest) -> ImageAnalysis:
        url = f"{self.config.resolved_base_url()}/chat/completions"
        data = self._post(url, headers=self._headers(), json_body=self._body(request))
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError(f"Unerwartete Antwortstruktur von {self.kind}.") from exc
        if isinstance(content, list):  # some gateways return content parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        tokens = int((data.get("usage") or {}).get("total_tokens") or 0)
        return parse_analysis(content, source=self.kind, model=self.model, tokens=tokens)

    def test_connection(self) -> ProviderStatus:
        url = f"{self.config.resolved_base_url()}/chat/completions"
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Antworte nur mit: OK"}],
            "max_tokens": 5,
            "temperature": 0,
        }
        data = self._post(url, headers=self._headers(), json_body=body)
        try:
            reply = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ProviderStatus(False, "Antwort konnte nicht gelesen werden.", self.model)
        return ProviderStatus(True, f"Verbindung erfolgreich. Antwort: {str(reply).strip()[:40]}",
                              self.model)


class OpenRouterProvider(OpenAICompatibleProvider):
    kind = "openrouter"

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["HTTP-Referer"] = "https://github.com/aimless3d-ai/testing-rep"
        headers["X-Title"] = "Vinted Auto Listing Tool"
        return headers


class LocalProvider(OpenAICompatibleProvider):
    """Any local OpenAI-compatible server (Ollama, LM Studio, llama.cpp)."""

    kind = "local"
    requires_api_key = False

    def _body(self, request: AnalysisRequest) -> dict:
        body = super()._body(request)
        # small local models often choke on response_format
        body.pop("response_format", None)
        return body
