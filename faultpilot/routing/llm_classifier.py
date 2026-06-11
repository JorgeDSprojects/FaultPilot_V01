"""LLM fallback intent classifier."""

from __future__ import annotations

from typing import Protocol

from faultpilot.routing.schemas import IntentClassification


class IntentLlmClient(Protocol):
    """Minimal protocol for intent classification using an LLM."""

    def classify_intent(self, query: str) -> IntentClassification:
        """Classify query intent."""


class LlmIntentClassifier:
    """Adapter that delegates intent classification to an LLM client."""

    def __init__(self, client: IntentLlmClient) -> None:
        self._client = client

    def classify(self, query: str) -> IntentClassification:
        result = self._client.classify_intent(query)
        return IntentClassification(
            intent=result.intent,
            confidence=result.confidence,
            source="llm",
            evidence=result.evidence,
        )
