"""State definitions for LangGraph RAG pipeline."""

from __future__ import annotations

from typing import TypedDict

from faultpilot.rag.schemas import Citation
from faultpilot.retrieval.schemas import RetrievalFilters, RetrievalResult


class RagGraphState(TypedDict, total=False):
    """Mutable state carried across graph nodes."""

    query: str
    filters: RetrievalFilters
    intent: str
    intent_confidence: float
    routing_source: str
    degraded_mode: bool
    warning: str | None
    retrieval_result: RetrievalResult
    context: str
    citations: list[Citation]
    draft_answer: str
    final_answer: str
