"""View-model formatters for Gradio markdown panels."""

from __future__ import annotations

from faultpilot.rag.schemas import Citation, TraceabilitySnapshot


def format_sources_markdown(citations: tuple[Citation, ...]) -> str:
    """Render source citations for markdown display."""
    if not citations:
        return "### Sources\n- No grounded sources available"

    lines = ["### Sources"]
    for citation in citations:
        lines.append(f"- `{citation.source_doc}` (p.{citation.page})")
    return "\n".join(lines)


def format_traceability_markdown(intent: str, snapshot: TraceabilitySnapshot) -> str:
    """Render traceability metadata for markdown display."""
    timing = snapshot.timing_ms
    return (
        "### Traceability\n"
        f"- Intent: `{intent}`\n"
        f"- Router source: `{snapshot.routing_source}`\n"
        f"- Confidence: `{snapshot.intent_confidence:.2f}`\n"
        f"- Routing: `{timing['routing']:.1f} ms`\n"
        f"- Retrieval: `{timing['retrieval']:.1f} ms`\n"
        f"- Generation: `{timing['generation']:.1f} ms`"
    )
