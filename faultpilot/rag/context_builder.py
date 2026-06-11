"""Context assembly for grounded answer generation."""

from __future__ import annotations

from faultpilot.rag.schemas import Citation
from faultpilot.retrieval.schemas import RetrievedChunk


def build_grounded_context(
    hits: list[RetrievedChunk] | tuple[RetrievedChunk, ...],
    max_chars: int,
) -> tuple[str, list[Citation]]:
    """Build bounded context string and citation list from retrieval hits."""
    context_blocks: list[str] = []
    citations: list[Citation] = []
    total_chars = 0

    for idx, hit in enumerate(hits, start=1):
        block = (
            f"[{idx}] {hit.content}\n"
            f"Source: {hit.source_doc} | Page: {hit.page}"
        )
        next_size = total_chars + len(block) + (2 if context_blocks else 0)
        if next_size > max_chars:
            break

        context_blocks.append(block)
        total_chars = next_size
        citations.append(
            Citation(
                source_doc=hit.source_doc,
                page=hit.page,
                alarm_code=hit.alarm_code,
            )
        )

    context = "\n\n".join(context_blocks)
    return context, citations
