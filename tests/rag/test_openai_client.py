from __future__ import annotations

from types import SimpleNamespace

import pytest

from faultpilot.rag.openai_client import OpenAiTextGenerationClient, OpenAiTextGenerationError


class _FakeResponsesApi:
    def __init__(self, payload: object | None = None, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._payload


class _FakeOpenAiClient:
    def __init__(self, responses_api: _FakeResponsesApi) -> None:
        self.responses = responses_api


def test_openai_client_returns_text_and_uses_model_defaults() -> None:
    responses_api = _FakeResponsesApi(payload=SimpleNamespace(output_text="Grounded answer"))
    prompt = "Intent: alarm_lookup"

    client = OpenAiTextGenerationClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    answer = client.generate_text(prompt)

    assert answer == "Grounded answer"
    assert len(responses_api.calls) == 1
    assert responses_api.calls[0]["model"] == "gpt-4o-mini"
    assert responses_api.calls[0]["input"] == prompt
    assert responses_api.calls[0]["temperature"] == 0.1
    assert responses_api.calls[0]["max_output_tokens"] == 450


def test_openai_client_repr_does_not_expose_api_key() -> None:
    client = OpenAiTextGenerationClient(api_key="sk-secret-key")

    assert "sk-secret-key" not in repr(client)


def test_openai_client_raises_for_empty_api_key_before_request() -> None:
    factory_called = False

    def _factory(api_key: str):
        nonlocal factory_called
        factory_called = True
        return _FakeOpenAiClient(_FakeResponsesApi(payload=SimpleNamespace(output_text="unused")))

    client = OpenAiTextGenerationClient(api_key="   ", client_factory=_factory)

    with pytest.raises(OpenAiTextGenerationError, match="API key"):
        client.generate_text("Intent: troubleshooting")

    assert factory_called is False


def test_openai_client_raises_when_provider_returns_empty_text() -> None:
    responses_api = _FakeResponsesApi(payload=SimpleNamespace(output_text="   "))

    client = OpenAiTextGenerationClient(
        api_key="sk-test",
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    with pytest.raises(OpenAiTextGenerationError, match="empty response"):
        client.generate_text("Intent: troubleshooting")


def test_openai_client_wraps_provider_failures() -> None:
    api_key = "sk-secret-key"
    responses_api = _FakeResponsesApi(
        error=RuntimeError(f"401 Unauthorized for API key: {api_key}")
    )

    client = OpenAiTextGenerationClient(
        api_key=api_key,
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    with pytest.raises(OpenAiTextGenerationError, match="OpenAI request failed") as exc_info:
        client.generate_text("Intent: programming")

    assert api_key not in str(exc_info.value)
