"""UI event controllers and streaming helpers."""

from __future__ import annotations

from typing import Callable, Iterator, Literal, Protocol, TypedDict

from faultpilot.rag.openai_client import OpenAiTextGenerationError
from faultpilot.rag.schemas import RagAnswer, TraceabilitySnapshot
from faultpilot.retrieval.schemas import RetrievalFilters
from faultpilot.routing.schemas import IntentType
from faultpilot.ui.viewmodels import format_sources_markdown, format_traceability_markdown


class RagServiceProtocol(Protocol):
    def answer(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        intent_override: IntentType | None = None,
    ) -> RagAnswer: ...


class ChatMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


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


def _normalize_intent_override(value: str | None) -> IntentType | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized or normalized == "auto":
        return None
    if normalized in {"alarm_lookup", "troubleshooting", "programming"}:
        return normalized
    return None


def _degraded_payload(
    conversation_prefix: list[ChatMessage],
    assistant_message: str,
    warning: str,
) -> tuple[list[ChatMessage], str, str, str]:
    fallback_snapshot = TraceabilitySnapshot(
        routing_source="fallback",
        intent_confidence=0.0,
        degraded_mode=True,
        warning=warning,
        timing_ms={"routing": 0.0, "retrieval": 0.0, "generation": 0.0},
    )
    traceability_md = format_traceability_markdown(
        intent="troubleshooting",
        snapshot=fallback_snapshot,
        citations=(),
    )
    sources_md = format_sources_markdown(())
    return (
        [
            *conversation_prefix,
            {"role": "assistant", "content": assistant_message},
        ],
        traceability_md,
        sources_md,
        "",
    )


def stream_chat_response(
    rag_service: RagServiceProtocol,
    query: str,
    history: list[ChatMessage],
    manufacturer: str | None,
    equipment: str | None,
    intent_mode: str | None,
    rag_service_factory: Callable[[str], RagServiceProtocol] | None = None,
    api_key: str | None = None,
) -> Iterator[tuple[list[ChatMessage], str, str, str]]:
    clean_query = query.strip()
    if not clean_query:
        yield [*history], "### Traceability\n- Empty query", "### Sources\n- N/A", ""
        return

    clean_api_key = (api_key or "").strip()

    filters = RetrievalFilters(
        manufacturer=_normalize_filter(manufacturer),
        equipment=_normalize_filter(equipment),
    )
    intent_override = _normalize_intent_override(intent_mode)

    # Keep heavy RAG stages before chunked UI streaming.
    history_snapshot = [*history]
    conversation_prefix: list[ChatMessage] = [
        *history_snapshot,
        {"role": "user", "content": clean_query},
    ]

    if not clean_api_key:
        yield _degraded_payload(
            conversation_prefix=conversation_prefix,
            assistant_message=(
                "Please provide an OpenAI API key to run grounded answer generation."
            ),
            warning="missing_api_key",
        )
        return

    active_service = rag_service
    if rag_service_factory is not None:
        try:
            active_service = rag_service_factory(clean_api_key)
        except Exception:
            yield _degraded_payload(
                conversation_prefix=conversation_prefix,
                assistant_message=(
                    "Backend unavailable. Returning degraded response with no grounded context."
                ),
                warning="backend_error",
            )
            return

    try:
        answer = active_service.answer(
            clean_query,
            filters=filters,
            intent_override=intent_override,
        )
    except OpenAiTextGenerationError:
        yield _degraded_payload(
            conversation_prefix=conversation_prefix,
            assistant_message=(
                "OpenAI provider error. Check your API key, quota, and connectivity, "
                "then retry."
            ),
            warning="provider_error",
        )
        return
    except Exception:
        yield _degraded_payload(
            conversation_prefix=conversation_prefix,
            assistant_message=(
                "Backend unavailable. Returning degraded response with no grounded context."
            ),
            warning="backend_error",
        )
        return

    traceability_md = format_traceability_markdown(
        intent=answer.intent,
        snapshot=answer.traceability,
        citations=answer.citations,
    )
    sources_md = format_sources_markdown(answer.citations)

    assistant_text = ""
    for piece in _chunk_text(answer.answer_text):
        assistant_text += piece
        chat_snapshot: list[ChatMessage] = [
            *conversation_prefix,
            {"role": "assistant", "content": assistant_text},
        ]
        yield chat_snapshot, traceability_md, sources_md, ""
