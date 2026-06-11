"""LangGraph composition for routing + retrieval + generation."""

from __future__ import annotations

from time import perf_counter

from langgraph.graph import END, START, StateGraph

from faultpilot.rag.context_builder import build_grounded_context
from faultpilot.rag.postprocess import CitationGuard
from faultpilot.rag.state import RagGraphState
from faultpilot.retrieval.schemas import RetrievalFilters


def build_rag_graph(
    router,
    retrieval_service,
    generator,
    max_context_chars: int,
    citation_guard: CitationGuard | None = None,
):
    """Build and compile the Hito 3 LangGraph pipeline."""
    guard = citation_guard or CitationGuard(max_regeneration_attempts=1)

    def route_intent(state: RagGraphState) -> RagGraphState:
        started_at = perf_counter()
        intent_override = state.get("intent_override")
        if intent_override is not None:
            return {
                "intent": intent_override,
                "intent_confidence": 1.0,
                "routing_source": "manual_override",
                "degraded_mode": False,
                "warning": None,
                "routing_ms": (perf_counter() - started_at) * 1000.0,
            }

        decision = router.route(state["query"])
        return {
            "intent": decision.intent,
            "intent_confidence": decision.confidence,
            "routing_source": decision.source,
            "degraded_mode": decision.degraded_mode,
            "warning": decision.warning,
            "routing_ms": (perf_counter() - started_at) * 1000.0,
        }

    def retrieve(state: RagGraphState) -> RagGraphState:
        started_at = perf_counter()
        filters = state.get("filters", RetrievalFilters())
        result = retrieval_service.hybrid_retrieve(
            query=state["query"],
            route=state["intent"],
            filters=filters,
        )
        return {
            "retrieval_result": result,
            "retrieval_ms": (perf_counter() - started_at) * 1000.0,
        }

    def build_context(state: RagGraphState) -> RagGraphState:
        result = state["retrieval_result"]
        context, citations = build_grounded_context(result.hits, max_chars=max_context_chars)
        return {"context": context, "citations": citations}

    def generate_answer(state: RagGraphState) -> RagGraphState:
        started_at = perf_counter()
        draft = generator.generate(
            query=state["query"],
            intent=state["intent"],
            context=state.get("context", ""),
            citations=state.get("citations", []),
            strict=False,
        )
        return {
            "draft_answer": draft,
            "generation_ms": (perf_counter() - started_at) * 1000.0,
        }

    def enforce_citations(state: RagGraphState) -> RagGraphState:
        final_answer, degraded, warning = guard.enforce(
            query=state["query"],
            intent=state["intent"],
            context=state.get("context", ""),
            citations=state.get("citations", []),
            draft_answer=state.get("draft_answer", ""),
            generator=generator,
        )
        response: RagGraphState = {"final_answer": final_answer}
        if degraded:
            response["degraded_mode"] = True
        if warning:
            response["warning"] = warning
        return response

    graph = StateGraph(RagGraphState)
    graph.add_node("route_intent", route_intent)
    graph.add_node("retrieve", retrieve)
    graph.add_node("build_context", build_context)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("enforce_citations", enforce_citations)

    graph.add_edge(START, "route_intent")
    graph.add_edge("route_intent", "retrieve")
    graph.add_edge("retrieve", "build_context")
    graph.add_edge("build_context", "generate_answer")
    graph.add_edge("generate_answer", "enforce_citations")
    graph.add_edge("enforce_citations", END)
    return graph.compile()
