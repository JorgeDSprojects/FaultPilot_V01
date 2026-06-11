"""Intent router combining local and LLM classifiers."""

from __future__ import annotations

from faultpilot.routing.schemas import IntentClassification, RoutingDecision


class IntentRouter:
    """Local-first router with LLM fallback."""

    def __init__(
        self,
        local_classifier,
        llm_classifier,
        ambiguous_threshold: float = 0.55,
        local_first: bool = True,
    ) -> None:
        self._local = local_classifier
        self._llm = llm_classifier
        self._threshold = ambiguous_threshold
        self._local_first = local_first

    def route(self, query: str) -> RoutingDecision:
        local_result: IntentClassification = self._local.classify(query)

        if self._local_first and local_result.confidence >= self._threshold:
            return RoutingDecision(
                intent=local_result.intent,
                confidence=local_result.confidence,
                source="local",
                degraded_mode=False,
            )

        try:
            llm_result: IntentClassification = self._llm.classify(query)
            return RoutingDecision(
                intent=llm_result.intent,
                confidence=llm_result.confidence,
                source="llm",
                degraded_mode=False,
            )
        except Exception:
            return RoutingDecision(
                intent="troubleshooting",
                confidence=0.0,
                source="fallback",
                degraded_mode=True,
                warning="llm_classifier_unavailable",
            )
