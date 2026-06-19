"""Provider-agnostic answer generator adapter."""

from __future__ import annotations

from typing import Protocol

from faultpilot.rag.schemas import Citation


class TextGenerationClient(Protocol):
    """Minimal interface for LLM-backed text generation clients."""

    def generate_text(self, prompt: str) -> str:
        """Generate answer text for prompt."""


class RagAnswerGenerator:
    """Generate answers using either LLM client or deterministic fallback."""

    def __init__(self, client: TextGenerationClient | None = None) -> None:
        self._client = client

    def generate(
        self,
        query: str,
        intent: str,
        context: str,
        citations: list[Citation],
        strict: bool = False,
    ) -> str:
        """Generate answer text for query and grounded context."""
        if self._client is None:
            return _fallback_answer(query, intent, context, citations)

        directive = _strict_citation_directive(citations) if strict else ""
        prompt = (
            f"Intent: {intent}\n"
            f"Question: {query}\n"
            f"Context:\n{context}\n"
            f"{directive}"
        )
        return self._client.generate_text(prompt)


def _fallback_answer(
    query: str,
    intent: str,
    context: str,
    citations: list[Citation],
) -> str:
    if not citations:
        return "No grounded sources available for this query."

    primary = citations[0]
    return (
        f"Intent: {intent}.\n"
        f"Based on retrieved context: {context[:220]}\n"
        f"Source [{primary.source_doc}:p.{primary.page}]"
    )


def _strict_citation_directive(citations: list[Citation]) -> str:
    if not citations:
        return "Always include source and page citations."

    tokens: list[str] = []
    seen: set[str] = set()
    for citation in citations:
        candidates = [
            f"[{citation.source_doc}:p.{citation.page}]",
            f"[{citation.source_doc}:{citation.page}]",
        ]
        for token in candidates:
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)

    lines = [
        "Use one of these exact citation tokens in the final answer:",
        *(f"- {token}" for token in tokens),
        "Do not invent citations.",
    ]
    return "\n".join(lines)
