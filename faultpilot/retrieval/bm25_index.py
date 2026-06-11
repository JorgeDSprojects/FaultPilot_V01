"""Sparse retrieval index using BM25."""

from __future__ import annotations

from dataclasses import replace
import pickle
from pathlib import Path
import re

from faultpilot.retrieval.schemas import RetrievedChunk, RetrievalFilters

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-]+")


class Bm25Index:
    """In-memory BM25 index over chunk content."""

    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self._chunks = chunks
        self._tokenized = [_tokenize(chunk.content) for chunk in chunks]
        self._engine = _maybe_build_bm25(self._tokenized)

    def search(
        self,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        """Return top-k sparse matches with scores and ranks."""
        if not self._chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._score_query(query_tokens)
        ranked_ids = sorted(
            range(len(self._chunks)),
            key=lambda idx: scores[idx],
            reverse=True,
        )

        output: list[RetrievedChunk] = []
        rank = 1
        for idx in ranked_ids:
            chunk = self._chunks[idx]
            if not _matches_filters(chunk, filters):
                continue
            if scores[idx] <= 0:
                continue
            output.append(
                replace(
                    chunk,
                    scores={**chunk.scores, "bm25": float(scores[idx])},
                    ranks={**chunk.ranks, "bm25_rank": rank},
                )
            )
            rank += 1
            if len(output) >= top_k:
                break
        return output

    def _score_query(self, query_tokens: list[str]) -> list[float]:
        if self._engine is not None:
            scores = [float(score) for score in self._engine.get_scores(query_tokens)]
            if any(score > 0 for score in scores):
                return scores
        return [_fallback_score(tokens, query_tokens) for tokens in self._tokenized]


def build_bm25_index(chunks: list[RetrievedChunk]) -> Bm25Index:
    """Construct sparse index from chunk list."""
    return Bm25Index(chunks)


def save_bm25_index(path: Path, index: Bm25Index) -> None:
    """Persist BM25 index chunks for later reload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        pickle.dump(index._chunks, file)


def load_bm25_index(path: Path) -> Bm25Index:
    """Load BM25 index from disk."""
    with path.open("rb") as file:
        chunks = pickle.load(file)
    return Bm25Index(chunks)


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(value)]


def _fallback_score(tokens: list[str], query_tokens: list[str]) -> float:
    token_set = set(tokens)
    score = 0.0
    for token in query_tokens:
        if token in token_set:
            score += 1.0
    return score


def _matches_filters(chunk: RetrievedChunk, filters: RetrievalFilters | None) -> bool:
    if filters is None:
        return True
    if filters.manufacturer and chunk.manufacturer != filters.manufacturer:
        return False
    if filters.equipment and chunk.equipment != filters.equipment:
        return False
    if filters.language and chunk.language != filters.language:
        return False
    return True


def _maybe_build_bm25(tokenized_docs: list[list[str]]):
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None
    if not tokenized_docs:
        return None
    return BM25Okapi(tokenized_docs)
