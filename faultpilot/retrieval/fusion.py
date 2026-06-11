"""Rank fusion algorithms for hybrid retrieval."""

from __future__ import annotations

from dataclasses import replace

from faultpilot.retrieval.schemas import RetrievedChunk


def reciprocal_rank_fusion(
    bm25_hits: list[RetrievedChunk],
    dense_hits: list[RetrievedChunk],
    k: int,
) -> list[RetrievedChunk]:
    """Fuse sparse and dense rankings with reciprocal rank fusion."""
    by_id: dict[str, RetrievedChunk] = {}
    rrf_scores: dict[str, float] = {}

    for rank, hit in enumerate(bm25_hits, start=1):
        by_id.setdefault(hit.chunk_id, hit)
        rrf_scores[hit.chunk_id] = rrf_scores.get(hit.chunk_id, 0.0) + (1.0 / (k + rank))

    for rank, hit in enumerate(dense_hits, start=1):
        by_id.setdefault(hit.chunk_id, hit)
        rrf_scores[hit.chunk_id] = rrf_scores.get(hit.chunk_id, 0.0) + (1.0 / (k + rank))

    ranked_ids = sorted(rrf_scores, key=lambda chunk_id: rrf_scores[chunk_id], reverse=True)
    output: list[RetrievedChunk] = []
    for fused_rank, chunk_id in enumerate(ranked_ids, start=1):
        base = by_id[chunk_id]
        output.append(
            replace(
                base,
                scores={**base.scores, "rrf": rrf_scores[chunk_id]},
                ranks={**base.ranks, "fused_rank": fused_rank},
            )
        )
    return output
