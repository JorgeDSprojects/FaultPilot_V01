"""State definitions for LangGraph RAG pipeline."""

from __future__ import annotations

from typing import TypedDict

from faultpilot.rag.schemas import Citation
from faultpilot.retrieval.schemas import RetrievalFilters, RetrievalResult
from faultpilot.routing.schemas import IntentType


class RagGraphState(TypedDict, total=False):
    """Mutable state carried across graph nodes."""

    query: str
    filters: RetrievalFilters
    intent: IntentType
    intent_override: IntentType | None
    intent_confidence: float
    routing_source: str
    degraded_mode: bool
    warning: str | None
    retrieval_result: RetrievalResult
    context: str
    citations: list[Citation]
    draft_answer: str
    final_answer: str
    routing_ms: float
    retrieval_ms: float
    generation_ms: float
