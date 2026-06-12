"""OpenAI text generation adapter for FaultPilot RAG."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


class _ResponsesApi(Protocol):
    def create(self, **kwargs):
        raise NotImplementedError


class _OpenAiClientProtocol(Protocol):
    responses: _ResponsesApi


ClientFactory = Callable[[str], _OpenAiClientProtocol]


class OpenAiTextGenerationError(RuntimeError):
    """Raised when OpenAI generation fails or returns unusable output."""


def _default_client_factory(api_key: str) -> _OpenAiClientProtocol:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError(
            "openai dependency is required for provider-backed generation."
        ) from exc
    return OpenAI(api_key=api_key)


@dataclass(frozen=True)
class OpenAiTextGenerationClient:
    """Minimal adapter implementing TextGenerationClient protocol."""

    api_key: str = field(repr=False)
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_output_tokens: int = 450
    client_factory: ClientFactory = _default_client_factory

    def generate_text(self, prompt: str) -> str:
        if not self.api_key.strip():
            raise OpenAiTextGenerationError("OpenAI API key is empty or missing.")

        client = self.client_factory(self.api_key)
        try:
            response = client.responses.create(
                model=self.model,
                input=prompt,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            )
        except Exception as exc:
            raise OpenAiTextGenerationError(
                "OpenAI request failed. Check API key, quota, or connectivity."
            ) from exc

        output = getattr(response, "output_text", "")
        if not isinstance(output, str) or not output.strip():
            raise OpenAiTextGenerationError("OpenAI returned an empty response.")
        return output.strip()
