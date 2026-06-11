"""View-model formatters for Gradio markdown panels."""

from __future__ import annotations

from typing import Mapping

from faultpilot.rag.schemas import Citation, TraceabilitySnapshot


def format_sources_markdown(citations: tuple[Citation, ...]) -> str:
    """Render source citations for markdown display."""
    if not citations:
        return "### Sources\n- No grounded sources available"

    lines = ["### Sources"]
    for citation in citations:
        lines.append(f"- `{citation.source_doc}` (p.{citation.page})")
    return "\n".join(lines)


def format_traceability_markdown(
    intent: str,
    snapshot: TraceabilitySnapshot,
    citations: tuple[Citation, ...],
) -> str:
    """Render traceability metadata for markdown display."""
    timing = snapshot.timing_ms
    degraded = "yes" if snapshot.degraded_mode else "no"
    lines = [
        "### Traceability",
        f"- Intent: `{intent}`",
        f"- Router source: `{snapshot.routing_source}`",
        f"- Confidence: `{snapshot.intent_confidence:.2f}`",
        f"- Degraded: `{degraded}`",
    ]
    if snapshot.warning:
        lines.append(f"- Warning: `{snapshot.warning}`")

    lines.extend(
        (
            f"- Routing: `{_timing_value(timing, 'routing'):.1f} ms`",
            f"- Retrieval: `{_timing_value(timing, 'retrieval'):.1f} ms`",
            f"- Generation: `{_timing_value(timing, 'generation'):.1f} ms`",
        )
    )
    lines.append("- Top grounded context:")
    if citations:
        for citation in citations[:3]:
            lines.append(f"  - `{citation.source_doc}` (p.{citation.page})")
    else:
        lines.append("  - No grounded sources available")
    return "\n".join(lines)


def _timing_value(timing: Mapping[str, object], key: str) -> float:
    """Read a timing value with numeric fallback."""
    value = timing.get(key, 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
