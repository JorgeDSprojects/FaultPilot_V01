from faultpilot.retrieval.config import FaultPilotSettings, RetrievalSettings, RouteProfile
from faultpilot.retrieval.schemas import RetrievedChunk, RetrievalFilters
from faultpilot.retrieval.service import HybridRetrievalService


class _FakeRetriever:
    def __init__(self, hits: list[RetrievedChunk]) -> None:
        self.hits = hits
        self.last_top_k = 0
        self.last_query = ""

    def search(self, query: str, top_k: int, filters: RetrievalFilters | None = None):
        self.last_top_k = top_k
        self.last_query = query
        return self.hits[:top_k]


class _FakeReranker:
    def rerank(self, query: str, hits: list[RetrievedChunk], top_n: int) -> list[RetrievedChunk]:
        return hits[:top_n]


def _chunk(chunk_id: str, content: str, alarm_code: str | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content=content,
        alarm_code=alarm_code,
        equipment="CC220/320",
        manufacturer="Bosch",
        source_doc="bosch.pdf",
        page=10,
    )


def test_service_applies_route_profile_and_returns_final_k() -> None:
    settings = FaultPilotSettings(
        retrieval=RetrievalSettings(
            bm25_k=5,
            dense_k=5,
            rrf_k=60,
            top_n_rerank=4,
            final_k=2,
            min_rrf_score=0.0,
            max_context_chars=1000,
            dedup_by="chunk_id",
            route_profiles={
                "alarm_lookup": RouteProfile(bm25_k=3, dense_k=2, top_n_rerank=2)
            },
        ),
        raw={},
    )
    sparse = _FakeRetriever([_chunk("A", "AL-09"), _chunk("B", "AL-01")])
    dense = _FakeRetriever([_chunk("A", "AL-09"), _chunk("C", "panel")])
    service = HybridRetrievalService(
        settings=settings,
        sparse_retriever=sparse,
        dense_retriever=dense,
        reranker=_FakeReranker(),
    )

    result = service.hybrid_retrieve("AL-09", route="alarm_lookup")

    assert sparse.last_top_k == 3
    assert dense.last_top_k == 2
    assert len(result.hits) <= 2
    assert result.meta.route == "alarm_lookup"


def test_service_normalizes_alarm_query_and_keeps_exact_alarm_hits() -> None:
    settings = FaultPilotSettings(
        retrieval=RetrievalSettings(
            bm25_k=5,
            dense_k=5,
            rrf_k=60,
            top_n_rerank=4,
            final_k=3,
            min_rrf_score=0.0,
            max_context_chars=1000,
            dedup_by="chunk_id",
            route_profiles={
                "alarm_lookup": RouteProfile(bm25_k=5, dense_k=5, top_n_rerank=4)
            },
        ),
        raw={},
    )
    sparse = _FakeRetriever(
        [
            _chunk("A", "AL-09 Overheat", alarm_code="AL-09"),
            _chunk("B", "AL-10 Low voltage", alarm_code="AL-10"),
        ]
    )
    dense = _FakeRetriever(
        [
            _chunk("C", "AL-09 Radiator", alarm_code="AL-09"),
            _chunk("D", "AL-11 Link high", alarm_code="AL-11"),
        ]
    )
    service = HybridRetrievalService(
        settings=settings,
        sparse_retriever=sparse,
        dense_retriever=dense,
        reranker=_FakeReranker(),
    )

    result = service.hybrid_retrieve("al 9", route="alarm_lookup")

    assert sparse.last_query == "AL-09"
    assert dense.last_query == "AL-09"
    assert result.hits
    assert {hit.alarm_code for hit in result.hits} == {"AL-09"}
