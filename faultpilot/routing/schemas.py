"""Routing domain schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IntentType = Literal["alarm_lookup", "troubleshooting", "programming"]


@dataclass(frozen=True)
class IntentClassification:
    """Intent classification output."""

    intent: IntentType
    confidence: float
    source: Literal["local", "llm", "fallback"]
    evidence: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    """Final routing decision for a query."""

    intent: IntentType
    confidence: float
    source: Literal["local", "llm", "fallback"]
    degraded_mode: bool = False
    warning: str | None = None
