"""Cross-encoder reranker adapter."""

from __future__ import annotations

from dataclasses import replace
from typing import Callable

from faultpilot.retrieval.schemas import RetrievedChunk


ScoreFn = Callable[[str, list[str]], list[float]]


class CrossEncoderReranker:
    """Rerank fused candidates with an injected or model-backed scorer."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        scorer: ScoreFn | None = None,
    ) -> None:
        self._model_name = model_name
        self._custom_scorer = scorer
        self._model = None

    def rerank(
        self,
        query: str,
        hits: list[RetrievedChunk],
        top_n: int,
    ) -> list[RetrievedChunk]:
        """Return reranked top-N candidates with reranker score attached."""
        if not hits:
            return []

        subset = hits[:top_n]
        docs = [hit.content for hit in subset]
        scores = self._score(query, docs)

        scored_hits = [
            replace(hit, scores={**hit.scores, "rerank": score})
            for hit, score in zip(subset, scores)
        ]
        scored_hits.sort(key=lambda hit: hit.scores["rerank"], reverse=True)
        return scored_hits

    def _score(self, query: str, docs: list[str]) -> list[float]:
        if self._custom_scorer is not None:
            return self._custom_scorer(query, docs)

        model = self._load_model()
        pairs = [[query, doc] for doc in docs]
        output = model.predict(pairs)
        return [float(score) for score in output]

    def _load_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for reranking. Install sentence-transformers."
            ) from exc

        self._model = CrossEncoder(self._model_name)
        return self._model
