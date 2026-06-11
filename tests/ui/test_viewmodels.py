from faultpilot.rag.schemas import Citation, TraceabilitySnapshot
from faultpilot.ui.viewmodels import format_sources_markdown, format_traceability_markdown


def test_format_sources_markdown_includes_doc_and_page() -> None:
    markdown = format_sources_markdown(
        (
            Citation(source_doc="ac_spindle_alarm_list.pdf", page=2),
            Citation(source_doc="bosch_cc220_manual.pdf", page=14),
        )
    )

    assert "ac_spindle_alarm_list.pdf" in markdown
    assert "p.2" in markdown
    assert "bosch_cc220_manual.pdf" in markdown
    assert "p.14" in markdown


def test_format_sources_markdown_handles_empty_citations() -> None:
    markdown = format_sources_markdown(())

    assert "### Sources" in markdown
    assert "No grounded sources available" in markdown


def test_format_traceability_markdown_includes_intent_source_and_timings() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="local",
        intent_confidence=0.87,
        degraded_mode=False,
        warning=None,
        timing_ms={"routing": 5.0, "retrieval": 120.0, "generation": 80.0},
    )

    markdown = format_traceability_markdown(
        intent="alarm_lookup",
        snapshot=snapshot,
        citations=(Citation(source_doc="ac_spindle_alarm_list.pdf", page=2),),
    )

    assert "alarm_lookup" in markdown
    assert "local" in markdown
    assert "5.0 ms" in markdown
    assert "120.0 ms" in markdown
    assert "80.0 ms" in markdown
    assert "Top grounded context" in markdown
    assert "ac_spindle_alarm_list.pdf" in markdown


def test_format_traceability_markdown_includes_degraded_warning() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="fallback",
        intent_confidence=0.41,
        degraded_mode=True,
        warning="Router fallback activated",
        timing_ms={"routing": 8.0, "retrieval": 0.0, "generation": 0.0},
    )

    markdown = format_traceability_markdown(
        intent="troubleshooting",
        snapshot=snapshot,
        citations=(),
    )

    assert "troubleshooting" in markdown
    assert "fallback" in markdown
    assert "Degraded" in markdown
    assert "yes" in markdown.lower()
    assert "Router fallback activated" in markdown


def test_format_traceability_markdown_uses_timing_fallback_for_missing_values() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="local",
        intent_confidence=0.95,
        degraded_mode=False,
        warning=None,
        timing_ms={"routing": 7.5},  # type: ignore[arg-type]
    )

    markdown = format_traceability_markdown(
        intent="alarm_lookup",
        snapshot=snapshot,
        citations=(),
    )

    assert "7.5 ms" in markdown
    assert "0.0 ms" in markdown


def test_format_traceability_markdown_limits_top_grounded_context_items() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="local",
        intent_confidence=0.95,
        degraded_mode=False,
        warning=None,
        timing_ms={"routing": 7.5, "retrieval": 0.0, "generation": 0.0},
    )
    markdown = format_traceability_markdown(
        intent="alarm_lookup",
        snapshot=snapshot,
        citations=(
            Citation(source_doc="doc-1.pdf", page=1),
            Citation(source_doc="doc-2.pdf", page=2),
            Citation(source_doc="doc-3.pdf", page=3),
            Citation(source_doc="doc-4.pdf", page=4),
        ),
    )

    assert "doc-1.pdf" in markdown
    assert "doc-2.pdf" in markdown
    assert "doc-3.pdf" in markdown
    assert "doc-4.pdf" not in markdown
