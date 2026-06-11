"""Post-processing guards for grounded RAG answers."""

from __future__ import annotations

from faultpilot.rag.schemas import Citation


class CitationGuard:
    """Ensure answer includes valid source/page traceability."""

    def __init__(self, max_regeneration_attempts: int = 1) -> None:
        self._max_attempts = max_regeneration_attempts

    def enforce(
        self,
        query: str,
        intent: str,
        context: str,
        citations: list[Citation],
        draft_answer: str,
        generator,
    ) -> tuple[str, bool, str | None]:
        """Ensure citation presence, regenerate once, else return safe fallback."""
        if _has_citation(draft_answer, citations):
            return draft_answer, False, None

        answer = draft_answer
        for _ in range(self._max_attempts):
            answer = generator.generate(
                query=query,
                intent=intent,
                context=context,
                citations=citations,
                strict=True,
            )
            if _has_citation(answer, citations):
                return answer, False, None

        safe_answer = _safe_fallback(citations)
        return safe_answer, True, "citation_guard_fallback"


def _has_citation(answer: str, citations: list[Citation]) -> bool:
    lowered = answer.lower()
    for citation in citations:
        source_ok = citation.source_doc.lower() in lowered
        page_ok = f"p.{citation.page}" in lowered or f"page {citation.page}" in lowered
        if source_ok and page_ok:
            return True
    return False


def _safe_fallback(citations: list[Citation]) -> str:
    if not citations:
        return "Unable to produce grounded answer with valid citations."

    lines = ["Unable to produce grounded answer with valid citations.", "Available sources:"]
    for citation in citations[:3]:
        lines.append(f"- {citation.source_doc} (page {citation.page})")
    return "\n".join(lines)
