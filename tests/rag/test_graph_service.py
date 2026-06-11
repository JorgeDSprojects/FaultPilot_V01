from faultpilot.rag.graph import build_rag_graph
from faultpilot.rag.service import RagPipelineService
from faultpilot.rag.schemas import Citation
from faultpilot.retrieval.schemas import RetrievalMeta, RetrievalResult, RetrievedChunk
from faultpilot.routing.schemas import RoutingDecision


class _StubRouter:
    def __init__(self) -> None:
        self.calls = 0

    def route(self, query: str) -> RoutingDecision:
        self.calls += 1
        return RoutingDecision(intent="alarm_lookup", confidence=0.9, source="local")


class _StubRetrievalService:
    def hybrid_retrieve(self, query: str, route: str, filters=None) -> RetrievalResult:
        hit = RetrievedChunk(
            chunk_id="x",
            content="AL-09 Overheat of radiator",
            alarm_code="AL-09",
            equipment="A06B-6059-Hxxx",
            manufacturer="Fanuc",
            source_doc="ac_spindle_alarm_list.pdf",
            page=2,
        )
        return RetrievalResult(hits=(hit,), meta=RetrievalMeta(route=route, final_k=1))


class _StubGenerator:
    def generate(self, query: str, intent: str, context: str, citations: list[Citation], strict: bool = False) -> str:
        first = citations[0]
        return f"Use source [{first.source_doc}:p.{first.page}]"


def test_rag_pipeline_service_returns_structured_answer() -> None:
    router = _StubRouter()
    graph = build_rag_graph(
        router=router,
        retrieval_service=_StubRetrievalService(),
        generator=_StubGenerator(),
        max_context_chars=1000,
    )
    service = RagPipelineService(graph)

    result = service.answer("What is AL-09?")

    assert result.intent == "alarm_lookup"
    assert len(result.citations) == 1
    assert "ac_spindle_alarm_list.pdf" in result.answer_text
    assert result.traceability.routing_source == "local"
    assert result.traceability.intent_confidence == 0.9
    assert result.traceability.degraded_mode is False
    assert result.traceability.warning is None
    assert result.traceability.timing_ms["routing"] >= 0.0
    assert result.traceability.timing_ms["retrieval"] >= 0.0
    assert result.traceability.timing_ms["generation"] >= 0.0
    assert router.calls == 1


def test_rag_pipeline_service_supports_manual_intent_override() -> None:
    router = _StubRouter()
    graph = build_rag_graph(
        router=router,
        retrieval_service=_StubRetrievalService(),
        generator=_StubGenerator(),
        max_context_chars=1000,
    )
    service = RagPipelineService(graph)

    result = service.answer("Need PLC loop code", intent_override="programming")

    assert result.intent == "programming"
    assert result.traceability.routing_source == "manual_override"
    assert result.traceability.intent_confidence == 1.0
    assert router.calls == 0
