from faultpilot.retrieval.reranker import CrossEncoderReranker
from faultpilot.retrieval.schemas import RetrievedChunk


def _chunk(chunk_id: str, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        alarm_code=None,
        equipment="CC220",
        manufacturer="Bosch",
        source_doc="bosch.pdf",
        page=1,
    )


def test_reranker_uses_custom_scorer() -> None:
    reranker = CrossEncoderReranker(
        scorer=lambda query, docs: [0.9 if "panel" in doc else 0.1 for doc in docs]
    )
    hits = [_chunk("1", "general alarm"), _chunk("2", "panel transfer fault")]

    reranked = reranker.rerank("panel error", hits, top_n=2)

    assert reranked[0].chunk_id == "2"
    assert reranked[0].scores["rerank"] > reranked[1].scores["rerank"]
