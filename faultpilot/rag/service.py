"""High-level service wrapper around the compiled RAG graph."""

from __future__ import annotations

from faultpilot.rag.schemas import RagAnswer, TraceabilitySnapshot
from faultpilot.retrieval.schemas import RetrievalFilters


class RagPipelineService:
    """Invoke graph and return stable response contract."""

    def __init__(self, graph) -> None:
        self._graph = graph

    def answer(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
    ) -> RagAnswer:
        state = {
            "query": query,
            "filters": filters or RetrievalFilters(),
        }
        output = self._graph.invoke(state)
        warnings = tuple(filter(None, [output.get("warning")]))
        traceability = TraceabilitySnapshot(
            routing_source=output.get("routing_source", "unknown"),
            intent_confidence=float(output.get("intent_confidence", 0.0)),
            degraded_mode=bool(output.get("degraded_mode", False)),
            warning=output.get("warning"),
            timing_ms={
                "routing": float(output.get("routing_ms", 0.0)),
                "retrieval": float(output.get("retrieval_ms", 0.0)),
                "generation": float(output.get("generation_ms", 0.0)),
            },
        )
        return RagAnswer(
            intent=output["intent"],
            answer_text=output.get("final_answer", ""),
            citations=tuple(output.get("citations", [])),
            degraded_mode=bool(output.get("degraded_mode", False)),
            warnings=warnings,
            traceability=traceability,
        )
