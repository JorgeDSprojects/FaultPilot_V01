"""Shared schemas for the retrieval domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalFilters:
    """Optional metadata filters for retrieval queries."""

    manufacturer: str | None = None
    equipment: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """One candidate returned by sparse/dense retrieval."""

    chunk_id: str
    content: str
    alarm_code: str | None
    equipment: str
    manufacturer: str
    source_doc: str
    page: int
    language: str | None = None
    scores: dict[str, float] = field(default_factory=dict)
    ranks: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalMeta:
    """Execution metadata for one retrieval call."""

    route: str
    final_k: int
    degraded_mode: bool = False
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalResult:
    """Top-k retrieval output with metadata."""

    hits: tuple[RetrievedChunk, ...]
    meta: RetrievalMeta
