from dataclasses import dataclass

from faultpilot.routing.intent_router import IntentRouter
from faultpilot.routing.schemas import IntentClassification


class _StubLocalClassifier:
    def __init__(self, result: IntentClassification) -> None:
        self.result = result

    def classify(self, query: str) -> IntentClassification:
        return self.result


class _StubLlmClassifier:
    def __init__(self, result: IntentClassification | None = None, should_raise: bool = False) -> None:
        self.result = result
        self.should_raise = should_raise

    def classify(self, query: str) -> IntentClassification:
        if self.should_raise:
            raise RuntimeError("llm unavailable")
        assert self.result is not None
        return self.result


def test_router_uses_local_intent_when_confident() -> None:
    router = IntentRouter(
        local_classifier=_StubLocalClassifier(
            IntentClassification(intent="alarm_lookup", confidence=0.95, source="local")
        ),
        llm_classifier=_StubLlmClassifier(
            IntentClassification(intent="troubleshooting", confidence=0.8, source="llm")
        ),
        ambiguous_threshold=0.55,
        local_first=True,
    )

    decision = router.route("AL-09")

    assert decision.intent == "alarm_lookup"
    assert decision.source == "local"


def test_router_uses_llm_fallback_when_ambiguous() -> None:
    router = IntentRouter(
        local_classifier=_StubLocalClassifier(
            IntentClassification(intent="troubleshooting", confidence=0.3, source="local")
        ),
        llm_classifier=_StubLlmClassifier(
            IntentClassification(intent="programming", confidence=0.8, source="llm")
        ),
        ambiguous_threshold=0.55,
        local_first=True,
    )

    decision = router.route("How to implement timer")

    assert decision.intent == "programming"
    assert decision.source == "llm"


def test_router_falls_back_to_troubleshooting_on_llm_error() -> None:
    router = IntentRouter(
        local_classifier=_StubLocalClassifier(
            IntentClassification(intent="troubleshooting", confidence=0.3, source="local")
        ),
        llm_classifier=_StubLlmClassifier(should_raise=True),
        ambiguous_threshold=0.55,
        local_first=True,
    )

    decision = router.route("ambiguous question")

    assert decision.intent == "troubleshooting"
    assert decision.degraded_mode is True
