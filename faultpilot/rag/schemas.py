"""Schemas for RAG pipeline responses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    """Traceability reference for generated answers."""

    source_doc: str
    page: int
    alarm_code: str | None = None


@dataclass(frozen=True)
class RagAnswer:
    """Final answer returned by RAG pipeline."""

    intent: str
    answer_text: str
    citations: tuple[Citation, ...]
    degraded_mode: bool
    warnings: tuple[str, ...]
