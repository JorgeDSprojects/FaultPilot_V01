from faultpilot.rag.context_builder import build_grounded_context
from faultpilot.retrieval.schemas import RetrievedChunk


def _chunk(idx: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"c{idx}",
        content=content,
        alarm_code=None,
        equipment="CC220/320",
        manufacturer="Bosch",
        source_doc="bosch.pdf",
        page=idx,
    )


def test_build_grounded_context_includes_sources() -> None:
    context, citations = build_grounded_context(
        hits=[_chunk(1, "No panel transfer"), _chunk(2, "Check cable")],
        max_chars=400,
    )

    assert "bosch.pdf" in context
    assert len(citations) == 2
    assert citations[0].page == 1


def test_build_grounded_context_respects_max_chars() -> None:
    context, citations = build_grounded_context(
        hits=[_chunk(1, "A" * 300), _chunk(2, "B" * 300)],
        max_chars=350,
    )

    assert len(context) <= 350
    assert len(citations) == 1
