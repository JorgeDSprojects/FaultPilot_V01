from faultpilot.retrieval.fusion import reciprocal_rank_fusion
from faultpilot.retrieval.schemas import RetrievedChunk


def _chunk(chunk_id: str, alarm_code: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=f"{alarm_code} content",
        alarm_code=alarm_code,
        equipment="E",
        manufacturer="Fanuc",
        source_doc="doc.pdf",
        page=1,
    )


def test_rrf_prefers_documents_present_in_both_lists() -> None:
    shared = _chunk("shared", "AL-09")
    bm25_only = _chunk("bm25-only", "AL-01")
    dense_only = _chunk("dense-only", "2641")

    fused = reciprocal_rank_fusion(
        bm25_hits=[shared, bm25_only],
        dense_hits=[shared, dense_only],
        k=60,
    )

    assert fused[0].chunk_id == "shared"
