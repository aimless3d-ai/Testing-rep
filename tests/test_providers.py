"""Provider behaviour is tested against a stubbed HTTP layer – no network."""
from __future__ import annotations

import json

import httpx
import pytest

from vinted_tool.ai.base import AIProvider
from vinted_tool.ai.factory import create_provider
from vinted_tool.ai.providers.anthropic import AnthropicProvider
from vinted_tool.ai.providers.offline import OfflineProvider, dominant_colors
from vinted_tool.ai.providers.openai_compatible import OpenAICompatibleProvider
from vinted_tool.core.config import ProviderConfig
from vinted_tool.core.errors import (
    AIAuthError,
    AIError,
    AIRateLimitError,
    AITimeoutError,
    ProviderNotConfiguredError,
)
from vinted_tool.models.enums import ProviderKind
from vinted_tool.ai.base import AnalysisRequest

PAYLOAD = {
    "product_type": "Hoodie", "brand": "Nike", "color": "Schwarz", "size": "M",
    "condition": "Sehr gut", "keywords": ["hoodie"],
    "confidence": {"product_type": 0.9, "brand": 0.9, "color": 0.9,
                   "size": 0.9, "condition": 0.9, "material": 0.9},
}


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or json.dumps(body or {})

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def patch_client(monkeypatch, responses):
    """Replace httpx.Client with a stub yielding queued responses."""
    calls = {"n": 0, "requests": []}
    queue = list(responses)

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            calls["n"] += 1
            calls["requests"].append({"url": url, "headers": headers or {}, "json": json})
            item = queue.pop(0) if queue else responses[-1]
            if isinstance(item, Exception):
                raise item
            return item

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr("vinted_tool.ai.base.time.sleep", lambda *_: None)
    return calls


def openai_body(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}], "usage": {"total_tokens": 321}}


@pytest.fixture
def image(tmp_path):
    from PIL import Image

    path = tmp_path / "p.jpg"
    Image.new("RGB", (50, 50), (10, 10, 12)).save(path)
    return path


def test_openai_provider_parses_answer(monkeypatch, image):
    calls = patch_client(monkeypatch, [FakeResponse(200, openai_body(json.dumps(PAYLOAD)))])
    provider = OpenAICompatibleProvider(ProviderConfig("openai", "gpt-4.1-mini", "", "sk-test"))
    analysis = provider.analyze(AnalysisRequest([image]))
    assert analysis.brand == "Nike"
    assert analysis.tokens_used == 321
    body = calls["requests"][0]["json"]
    assert body["model"] == "gpt-4.1-mini"
    assert any(c["type"] == "image_url" for c in body["messages"][1]["content"])
    assert calls["requests"][0]["headers"]["Authorization"].startswith("Bearer ")


def test_openrouter_sends_attribution_headers(monkeypatch, image):
    calls = patch_client(monkeypatch, [FakeResponse(200, openai_body(json.dumps(PAYLOAD)))])
    provider = create_provider(ProviderConfig(ProviderKind.OPENROUTER.value, api_key="sk-or-x"))
    provider.analyze(AnalysisRequest([image]))
    assert "X-Title" in calls["requests"][0]["headers"]


def test_anthropic_provider(monkeypatch, image):
    body = {"content": [{"type": "text", "text": json.dumps(PAYLOAD)}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}
    calls = patch_client(monkeypatch, [FakeResponse(200, body)])
    provider = AnthropicProvider(ProviderConfig("anthropic", "claude-sonnet-4-5", "", "sk-ant-x"))
    analysis = provider.analyze(AnalysisRequest([image]))
    assert analysis.tokens_used == 150
    assert calls["requests"][0]["headers"]["x-api-key"] == "sk-ant-x"


def test_auth_error_is_not_retried(monkeypatch, image):
    calls = patch_client(monkeypatch, [FakeResponse(401, {}, "unauthorized")])
    provider = OpenAICompatibleProvider(ProviderConfig("openai", api_key="bad"))
    with pytest.raises(AIAuthError):
        provider.analyze(AnalysisRequest([image]))
    assert calls["n"] == 1


def test_rate_limit_is_retried_then_reported(monkeypatch, image):
    calls = patch_client(monkeypatch, [FakeResponse(429, {}, "slow down")])
    provider = OpenAICompatibleProvider(
        ProviderConfig("openai", api_key="k"), max_retries=2
    )
    with pytest.raises(AIRateLimitError):
        provider.analyze(AnalysisRequest([image]))
    assert calls["n"] == 3


def test_server_error_then_success(monkeypatch, image):
    patch_client(monkeypatch, [
        FakeResponse(500, {}, "boom"),
        FakeResponse(200, openai_body(json.dumps(PAYLOAD))),
    ])
    provider = OpenAICompatibleProvider(ProviderConfig("openai", api_key="k"), max_retries=1)
    assert provider.analyze(AnalysisRequest([image])).brand == "Nike"


def test_timeout_raises_timeout_error(monkeypatch, image):
    patch_client(monkeypatch, [httpx.TimeoutException("timeout")])
    provider = OpenAICompatibleProvider(ProviderConfig("openai", api_key="k"), max_retries=0)
    with pytest.raises(AITimeoutError):
        provider.analyze(AnalysisRequest([image]))


def test_bad_request_reports_status(monkeypatch, image):
    patch_client(monkeypatch, [FakeResponse(400, {}, "model not found")])
    provider = OpenAICompatibleProvider(ProviderConfig("openai", api_key="k"))
    with pytest.raises(AIError) as exc:
        provider.analyze(AnalysisRequest([image]))
    assert "400" in str(exc.value)


def test_missing_api_key_is_reported_clearly(image):
    provider = OpenAICompatibleProvider(ProviderConfig("openai", api_key=""))
    with pytest.raises(ProviderNotConfiguredError):
        provider.analyze(AnalysisRequest([image]))


def test_local_provider_drops_response_format(monkeypatch, image):
    calls = patch_client(monkeypatch, [FakeResponse(200, openai_body(json.dumps(PAYLOAD)))])
    provider = create_provider(ProviderConfig(ProviderKind.LOCAL.value))
    provider.analyze(AnalysisRequest([image]))
    assert "response_format" not in calls["requests"][0]["json"]


def test_offline_provider_detects_colour_and_filename_hints(tmp_path):
    from PIL import Image

    path = tmp_path / "nike_hoodie_1.jpg"
    Image.new("RGB", (200, 200), (200, 40, 40)).save(path)
    provider = OfflineProvider(ProviderConfig("offline"))
    analysis = provider.analyze(AnalysisRequest([path]))
    assert analysis.color == "Rot"
    assert analysis.brand == "Nike"
    assert analysis.product_type == "hoodie"
    assert analysis.size is None and analysis.condition is None  # never guessed
    assert provider.test_connection().ok is True


def test_dominant_colors_ignores_missing_files(tmp_path):
    assert dominant_colors([tmp_path / "missing.jpg"]) == []


def test_factory_falls_back_to_offline_for_unknown_kind():
    provider = create_provider(ProviderConfig("does-not-exist"))
    assert isinstance(provider, OfflineProvider)
    assert isinstance(provider, AIProvider)
