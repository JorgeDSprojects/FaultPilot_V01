"""Hybrid retrieval service orchestration."""

from __future__ import annotations

from dataclasses import replace

from faultpilot.alarm_codes import extract_alarm_code, normalize_alarm_code
from faultpilot.retrieval.config import FaultPilotSettings
from faultpilot.retrieval.fusion import reciprocal_rank_fusion
from faultpilot.retrieval.schemas import (
    RetrievalFilters,
    RetrievalMeta,
    RetrievalResult,
)


class HybridRetrievalService:
    """Coordinates sparse, dense, fusion, and reranking stages."""

    def __init__(
        self,
        settings: FaultPilotSettings,
        sparse_retriever,
        dense_retriever,
        reranker,
    ) -> None:
        self._settings = settings
        self._sparse = sparse_retriever
        self._dense = dense_retriever
        self._reranker = reranker

    def hybrid_retrieve(
        self,
        query: str,
        route: str,
        filters: RetrievalFilters | None = None,
    ) -> RetrievalResult:
        profile = self._settings.retrieval.profile_for_route(route)
        query_alarm_code = extract_alarm_code(query) if route == "alarm_lookup" else None
        retrieval_query = query_alarm_code or query

        bm25_hits = self._sparse.search(
            retrieval_query,
            top_k=profile.bm25_k,
            filters=filters,
        )
        dense_hits = self._dense.search(
            retrieval_query,
            top_k=profile.dense_k,
            filters=filters,
        )

        fused_hits = reciprocal_rank_fusion(
            bm25_hits=bm25_hits,
            dense_hits=dense_hits,
            k=self._settings.retrieval.rrf_k,
        )
        min_rrf = self._settings.retrieval.min_rrf_score
        filtered_hits = [
            hit for hit in fused_hits if hit.scores.get("rrf", 0.0) >= min_rrf
        ]
        if query_alarm_code:
            exact_code_hits = [
                hit
                for hit in filtered_hits
                if normalize_alarm_code(hit.alarm_code) == query_alarm_code
            ]
            if exact_code_hits:
                filtered_hits = exact_code_hits

        reranked_hits = self._reranker.rerank(
            query=retrieval_query,
            hits=filtered_hits,
            top_n=profile.top_n_rerank,
        )
        final_k = self._settings.retrieval.final_k
        final_hits = [
            replace(hit, ranks={**hit.ranks, "final_rank": idx})
            for idx, hit in enumerate(reranked_hits[:final_k], start=1)
        ]

        return RetrievalResult(
            hits=tuple(final_hits),
            meta=RetrievalMeta(route=route, final_k=final_k),
        )
