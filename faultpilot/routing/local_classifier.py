"""Local regex/keyword intent classifier."""

from __future__ import annotations

import re

from faultpilot.alarm_codes import extract_alarm_code
from faultpilot.routing.schemas import IntentClassification

_NUMERIC_ERROR_RE = re.compile(r"\berror\s*\d{3,5}\b|\b\d{4}\b", re.IGNORECASE)

_PROGRAMMING_KEYWORDS = {
    "plc",
    "ladder",
    "timer",
    "rung",
    "instruction",
    "programming",
    "commissioning",
}

_TROUBLESHOOTING_KEYWORDS = {
    "overheat",
    "fault",
    "fails",
    "stops",
    "timeout",
    "trip",
    "vibration",
    "noise",
}


class LocalIntentClassifier:
    """Classifies intents using deterministic local rules."""

    def classify(self, query: str) -> IntentClassification:
        lower = query.lower()

        if extract_alarm_code(query) or _NUMERIC_ERROR_RE.search(query):
            return IntentClassification(
                intent="alarm_lookup",
                confidence=0.95,
                source="local",
                evidence="alarm_code_pattern",
            )

        if any(keyword in lower for keyword in _PROGRAMMING_KEYWORDS):
            return IntentClassification(
                intent="programming",
                confidence=0.85,
                source="local",
                evidence="programming_keywords",
            )

        if any(keyword in lower for keyword in _TROUBLESHOOTING_KEYWORDS):
            return IntentClassification(
                intent="troubleshooting",
                confidence=0.7,
                source="local",
                evidence="troubleshooting_keywords",
            )

        return IntentClassification(
            intent="troubleshooting",
            confidence=0.4,
            source="local",
            evidence="default_route",
        )
