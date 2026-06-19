from faultpilot.rag.postprocess import CitationGuard
from faultpilot.rag.schemas import Citation


class _StubGenerator:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, query: str, intent: str, context: str, citations: list[Citation], strict: bool = False) -> str:
        self.calls += 1
        if strict:
            first = citations[0]
            return f"Answer with source [{first.source_doc}:p.{first.page}]"
        return "Answer without any citation"


def test_citation_guard_regenerates_when_missing_citations() -> None:
    guard = CitationGuard(max_regeneration_attempts=1)
    generator = _StubGenerator()
    citations = [Citation(source_doc="bosch.pdf", page=40, alarm_code="2641")]

    final_answer, degraded, warning = guard.enforce(
        query="what is 2641",
        intent="alarm_lookup",
        context="ctx",
        citations=citations,
        draft_answer="Missing source",
        generator=generator,
    )

    assert "bosch.pdf" in final_answer
    assert degraded is False
    assert warning is None


def test_citation_guard_accepts_bracket_doc_page_format_without_regeneration() -> None:
    guard = CitationGuard(max_regeneration_attempts=1)
    generator = _StubGenerator()
    citations = [Citation(source_doc="bosch.pdf", page=40, alarm_code="2641")]

    final_answer, degraded, warning = guard.enforce(
        query="what is 2641",
        intent="alarm_lookup",
        context="ctx",
        citations=citations,
        draft_answer="Use source [bosch.pdf:40] for details.",
        generator=generator,
    )

    assert final_answer == "Use source [bosch.pdf:40] for details."
    assert degraded is False
    assert warning is None
    assert generator.calls == 0
