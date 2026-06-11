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


def test_format_traceability_markdown_includes_intent_source_and_timings() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="local",
        intent_confidence=0.87,
        degraded_mode=False,
        warning=None,
        timing_ms={"routing": 5.0, "retrieval": 120.0, "generation": 80.0},
    )

    markdown = format_traceability_markdown(intent="alarm_lookup", snapshot=snapshot)

    assert "alarm_lookup" in markdown
    assert "local" in markdown
    assert "5.0 ms" in markdown
    assert "120.0 ms" in markdown
    assert "80.0 ms" in markdown
