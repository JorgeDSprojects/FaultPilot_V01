"""Schemas for RAG pipeline responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Citation:
    """Traceability reference for generated answers."""

    source_doc: str
    page: int
    alarm_code: str | None = None


class TimingMs(TypedDict):
    """Per-stage execution timings in milliseconds."""

    routing: float
    retrieval: float
    generation: float


@dataclass(frozen=True)
class TraceabilitySnapshot:
    """Traceability metadata captured for a RAG answer."""

    routing_source: str
    intent_confidence: float
    degraded_mode: bool
    warning: str | None
    timing_ms: TimingMs


@dataclass(frozen=True)
class RagAnswer:
    """Final answer returned by RAG pipeline."""

    intent: str
    answer_text: str
    citations: tuple[Citation, ...]
    degraded_mode: bool
    warnings: tuple[str, ...]
    traceability: TraceabilitySnapshot
