"""UI event controllers and streaming helpers."""

from __future__ import annotations

from typing import Iterator, Protocol

from faultpilot.rag.schemas import RagAnswer
from faultpilot.retrieval.schemas import RetrievalFilters
from faultpilot.ui.viewmodels import format_sources_markdown, format_traceability_markdown


class RagServiceProtocol(Protocol):
    def answer(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
    ) -> RagAnswer: ...


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized or normalized.casefold() == "all":
        return None
    return normalized


def _chunk_text(value: str, size: int = 32) -> list[str]:
    if not value:
        return [""]
    return [value[i : i + size] for i in range(0, len(value), size)]


def stream_chat_response(
    rag_service: RagServiceProtocol,
    query: str,
    history: list[tuple[str, str]],
    manufacturer: str | None,
    equipment: str | None,
) -> Iterator[tuple[list[tuple[str, str]], str, str, str]]:
    clean_query = query.strip()
    if not clean_query:
        yield [*history], "### Traceability\n- Empty query", "### Sources\n- N/A", ""
        return

    filters = RetrievalFilters(
        manufacturer=_normalize_filter(manufacturer),
        equipment=_normalize_filter(equipment),
    )

    # Keep heavy RAG stages before chunked UI streaming.
    answer = rag_service.answer(clean_query, filters=filters)
    traceability_md = format_traceability_markdown(answer.intent, answer.traceability)
    sources_md = format_sources_markdown(answer.citations)

    history_snapshot = [*history]
    assistant_text = ""
    for piece in _chunk_text(answer.answer_text):
        assistant_text += piece
        chat_snapshot = [*history_snapshot, (clean_query, assistant_text)]
        yield chat_snapshot, traceability_md, sources_md, ""
