# Fase 4 Gradio UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Gradio interface with safe streaming, traceability panel, and Hugging Face Spaces compatibility on top of the existing FaultPilot routing/retrieval/RAG backend.

**Architecture:** Keep backend domains (`routing`, `retrieval`, `rag`) unchanged as core business logic, and add a new `faultpilot/ui` boundary for layout, controllers, runtime wiring, and view-model formatting. Extend the RAG response contract with traceability metadata needed by UI, then wire a desktop-first two-column Gradio app that streams responses only after pre-yield stages complete.

**Tech Stack:** Python 3.10+, Gradio, LangGraph, pytest, uv, existing FaultPilot modules.

---

## Planned File Structure

### Create
- `faultpilot/ui/__init__.py`
- `faultpilot/ui/schemas.py`
- `faultpilot/ui/viewmodels.py`
- `faultpilot/ui/settings.py`
- `faultpilot/ui/runtime.py`
- `faultpilot/ui/controllers.py`
- `faultpilot/ui/layout.py`
- `faultpilot/ui/app.py`
- `app.py`
- `scripts/test_stream.py`
- `tests/ui/test_viewmodels.py`
- `tests/ui/test_settings.py`
- `tests/ui/test_runtime.py`
- `tests/ui/test_controllers.py`
- `tests/ui/test_layout.py`
- `tests/ui/test_app_boot.py`
- `requirements.txt`
- `Documentation/Training/04_ui_integration_tutorial.md`

### Modify
- `faultpilot/rag/schemas.py`
- `faultpilot/rag/state.py`
- `faultpilot/rag/graph.py`
- `faultpilot/rag/service.py`
- `tests/rag/test_graph_service.py`
- `config/settings.yaml`
- `pyproject.toml`
- `README.md`
- `Documentation/changelog.md`

### Responsibility Boundaries
- `faultpilot/ui/layout.py` only defines components and layout composition.
- `faultpilot/ui/controllers.py` only handles event flow, input validation, and streaming behavior.
- `faultpilot/ui/runtime.py` only constructs runtime dependencies and filter options.
- `faultpilot/ui/viewmodels.py` only formats traceability and sources for display.
- `faultpilot/rag/*` remains the backend contract owner; UI consumes `RagAnswer` without duplicating domain logic.

---

### Task 1: Extend RAG Contract With Traceability Metadata

**Files:**
- Modify: `faultpilot/rag/schemas.py`
- Modify: `faultpilot/rag/state.py`
- Modify: `faultpilot/rag/graph.py`
- Modify: `faultpilot/rag/service.py`
- Test: `tests/rag/test_graph_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/rag/test_graph_service.py
from faultpilot.rag.graph import build_rag_graph
from faultpilot.rag.service import RagPipelineService
from faultpilot.rag.schemas import Citation
from faultpilot.retrieval.schemas import RetrievalMeta, RetrievalResult, RetrievedChunk
from faultpilot.routing.schemas import RoutingDecision


class _StubRouter:
    def route(self, query: str) -> RoutingDecision:
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


def test_rag_pipeline_service_returns_traceability_metadata() -> None:
    graph = build_rag_graph(
        router=_StubRouter(),
        retrieval_service=_StubRetrievalService(),
        generator=_StubGenerator(),
        max_context_chars=1000,
    )
    service = RagPipelineService(graph)

    result = service.answer("What is AL-09?")

    assert result.intent == "alarm_lookup"
    assert result.traceability.routing_source == "local"
    assert result.traceability.intent_confidence == 0.9
    assert result.traceability.timing_ms["routing"] >= 0.0
    assert result.traceability.timing_ms["retrieval"] >= 0.0
    assert result.traceability.timing_ms["generation"] >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/rag/test_graph_service.py::test_rag_pipeline_service_returns_traceability_metadata -v`
Expected: FAIL because `RagAnswer` has no `traceability` field yet.

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/rag/schemas.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    source_doc: str
    page: int
    alarm_code: str | None = None


@dataclass(frozen=True)
class TraceabilitySnapshot:
    routing_source: str
    intent_confidence: float
    degraded_mode: bool
    warning: str | None
    timing_ms: dict[str, float]


@dataclass(frozen=True)
class RagAnswer:
    intent: str
    answer_text: str
    citations: tuple[Citation, ...]
    degraded_mode: bool
    warnings: tuple[str, ...]
    traceability: TraceabilitySnapshot
```

```python
# faultpilot/rag/state.py
from typing import TypedDict


class RagGraphState(TypedDict, total=False):
    query: str
    filters: object
    intent: str
    intent_confidence: float
    routing_source: str
    degraded_mode: bool
    warning: str | None
    retrieval_result: object
    context: str
    citations: list[object]
    draft_answer: str
    final_answer: str
    routing_ms: float
    retrieval_ms: float
    generation_ms: float
```

```python
# faultpilot/rag/graph.py
from time import perf_counter


def route_intent(state):
    start = perf_counter()
    decision = router.route(state["query"])
    return {
        "intent": decision.intent,
        "intent_confidence": decision.confidence,
        "routing_source": decision.source,
        "degraded_mode": decision.degraded_mode,
        "warning": decision.warning,
        "routing_ms": (perf_counter() - start) * 1000,
    }


def retrieve(state):
    start = perf_counter()
    filters = state.get("filters", RetrievalFilters())
    result = retrieval_service.hybrid_retrieve(
        query=state["query"],
        route=state["intent"],
        filters=filters,
    )
    return {
        "retrieval_result": result,
        "retrieval_ms": (perf_counter() - start) * 1000,
    }


def generate_answer(state):
    start = perf_counter()
    draft = generator.generate(
        query=state["query"],
        intent=state["intent"],
        context=state.get("context", ""),
        citations=state.get("citations", []),
        strict=False,
    )
    return {
        "draft_answer": draft,
        "generation_ms": (perf_counter() - start) * 1000,
    }
```

```python
# faultpilot/rag/service.py
from faultpilot.rag.schemas import RagAnswer, TraceabilitySnapshot


class RagPipelineService:
    def __init__(self, graph) -> None:
        self._graph = graph

    def answer(self, query: str, filters=None) -> RagAnswer:
        state = {"query": query, "filters": filters}
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/rag/test_graph_service.py -v`
Expected: PASS for graph service tests.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/rag/schemas.py faultpilot/rag/state.py faultpilot/rag/graph.py faultpilot/rag/service.py tests/rag/test_graph_service.py
git commit -m "feat: add rag traceability metadata contract"
```

---

### Task 2: Add UI Schemas and ViewModels

**Files:**
- Create: `faultpilot/ui/__init__.py`
- Create: `faultpilot/ui/schemas.py`
- Create: `faultpilot/ui/viewmodels.py`
- Test: `tests/ui/test_viewmodels.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_viewmodels.py
from faultpilot.rag.schemas import Citation, TraceabilitySnapshot
from faultpilot.ui.viewmodels import format_sources_markdown, format_traceability_markdown


def test_format_sources_markdown_includes_doc_and_page() -> None:
    markdown = format_sources_markdown(
        (
            Citation(source_doc="ac_spindle_alarm_list.pdf", page=2),
            Citation(source_doc="bosch_cc220_manual.pdf", page=14),
        )
    )

    assert "ac_spindle_alarm_list.pdf" in markdown
    assert "p.2" in markdown
    assert "bosch_cc220_manual.pdf" in markdown


def test_format_traceability_markdown_includes_timing_blocks() -> None:
    snapshot = TraceabilitySnapshot(
        routing_source="local",
        intent_confidence=0.87,
        degraded_mode=False,
        warning=None,
        timing_ms={"routing": 5.0, "retrieval": 120.0, "generation": 80.0},
    )

    markdown = format_traceability_markdown(intent="alarm_lookup", snapshot=snapshot)

    assert "alarm_lookup" in markdown
    assert "local" in markdown
    assert "120.0 ms" in markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/ui/test_viewmodels.py -v`
Expected: FAIL with module import errors (`faultpilot.ui` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/ui/__init__.py
"""UI package for FaultPilot Gradio integration."""
```

```python
# faultpilot/ui/schemas.py
from dataclasses import dataclass


@dataclass(frozen=True)
class UiQuery:
    text: str
    manufacturer: str | None
    equipment: str | None
```

```python
# faultpilot/ui/viewmodels.py
from faultpilot.rag.schemas import Citation, TraceabilitySnapshot


def format_sources_markdown(citations: tuple[Citation, ...]) -> str:
    if not citations:
        return "### Sources\n- No grounded sources available"
    lines = ["### Sources"]
    for citation in citations:
        lines.append(f"- `{citation.source_doc}` (p.{citation.page})")
    return "\n".join(lines)


def format_traceability_markdown(intent: str, snapshot: TraceabilitySnapshot) -> str:
    return (
        "### Traceability\n"
        f"- Intent: `{intent}`\n"
        f"- Router source: `{snapshot.routing_source}`\n"
        f"- Confidence: `{snapshot.intent_confidence:.2f}`\n"
        f"- Routing: `{snapshot.timing_ms['routing']:.1f} ms`\n"
        f"- Retrieval: `{snapshot.timing_ms['retrieval']:.1f} ms`\n"
        f"- Generation: `{snapshot.timing_ms['generation']:.1f} ms`"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/ui/test_viewmodels.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/ui/__init__.py faultpilot/ui/schemas.py faultpilot/ui/viewmodels.py tests/ui/test_viewmodels.py
git commit -m "feat: add ui viewmodels for traceability and sources"
```

---

### Task 3: Build UI Runtime Wiring and Filter Options

**Files:**
- Create: `faultpilot/ui/runtime.py`
- Test: `tests/ui/test_runtime.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_runtime.py
from faultpilot.retrieval.schemas import RetrievedChunk
from faultpilot.ui.runtime import collect_filter_options


def test_collect_filter_options_sorts_unique_values() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            content="x",
            alarm_code=None,
            equipment="A06B",
            manufacturer="Fanuc",
            source_doc="a.pdf",
            page=1,
        ),
        RetrievedChunk(
            chunk_id="2",
            content="y",
            alarm_code=None,
            equipment="CC220",
            manufacturer="Bosch",
            source_doc="b.pdf",
            page=2,
        ),
    ]

    manufacturers, equipment = collect_filter_options(chunks)

    assert manufacturers == ["All", "Bosch", "Fanuc"]
    assert equipment == ["All", "A06B", "CC220"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/ui/test_runtime.py -v`
Expected: FAIL because `faultpilot.ui.runtime` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/ui/runtime.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faultpilot.rag.generator import RagAnswerGenerator
from faultpilot.rag.graph import build_rag_graph
from faultpilot.rag.postprocess import CitationGuard
from faultpilot.rag.service import RagPipelineService
from faultpilot.retrieval.bm25_index import build_bm25_index, load_bm25_index
from faultpilot.retrieval.cli import load_settings
from faultpilot.retrieval.loaders import load_chunks
from faultpilot.retrieval.reranker import CrossEncoderReranker
from faultpilot.retrieval.service import HybridRetrievalService
from faultpilot.retrieval.vector_index import build_dense_index
from faultpilot.routing.intent_router import IntentRouter
from faultpilot.routing.local_classifier import LocalIntentClassifier
from faultpilot.routing.schemas import IntentClassification


class _FallbackLlmClassifier:
    def classify(self, query: str) -> IntentClassification:
        return IntentClassification(
            intent="troubleshooting",
            confidence=0.5,
            source="llm",
            evidence="fallback_ui_classifier",
        )


@dataclass(frozen=True)
class UiRuntime:
    rag_service: RagPipelineService
    manufacturers: list[str]
    equipment: list[str]


def collect_filter_options(chunks) -> tuple[list[str], list[str]]:
    manufacturers = sorted({chunk.manufacturer for chunk in chunks})
    equipment = sorted({chunk.equipment for chunk in chunks})
    return ["All", *manufacturers], ["All", *equipment]


def build_ui_runtime(settings_path: Path) -> UiRuntime:
    settings = load_settings(settings_path)
    chunks = load_chunks(Path(settings.raw["paths"]["chunks_jsonl_dir"]))
    manufacturers, equipment = collect_filter_options(chunks)

    bm25_path = Path(settings.raw["paths"]["bm25_index"])
    sparse = load_bm25_index(bm25_path) if bm25_path.exists() else build_bm25_index(chunks)
    dense = build_dense_index(
        chunks,
        persist_dir=Path(settings.raw["paths"]["chroma_db"]),
        model_name=settings.raw["embeddings"]["model_name"],
    )
    reranker = CrossEncoderReranker(model_name=settings.raw["reranker"]["model_name"])
    retrieval = HybridRetrievalService(settings=settings, sparse_retriever=sparse, dense_retriever=dense, reranker=reranker)
    router = IntentRouter(
        local_classifier=LocalIntentClassifier(),
        llm_classifier=_FallbackLlmClassifier(),
        ambiguous_threshold=float(settings.raw["routing"]["ambiguous_threshold"]),
        local_first=bool(settings.raw["routing"]["local_first"]),
    )
    generator = RagAnswerGenerator(client=None)
    graph = build_rag_graph(
        router=router,
        retrieval_service=retrieval,
        generator=generator,
        max_context_chars=int(settings.raw["rag"]["max_context_chars"]),
        citation_guard=CitationGuard(
            max_regeneration_attempts=int(settings.raw["rag"]["max_regeneration_attempts"])
        ),
    )
    return UiRuntime(
        rag_service=RagPipelineService(graph),
        manufacturers=manufacturers,
        equipment=equipment,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/ui/test_runtime.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/ui/runtime.py tests/ui/test_runtime.py
git commit -m "feat: add ui runtime wiring and filter options"
```

---

### Task 4: Implement Streaming Controllers and Isolation Script

**Files:**
- Create: `faultpilot/ui/controllers.py`
- Create: `scripts/test_stream.py`
- Test: `tests/ui/test_controllers.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_controllers.py
from dataclasses import dataclass

from faultpilot.rag.schemas import Citation, RagAnswer, TraceabilitySnapshot
from faultpilot.ui.controllers import stream_chat_response


@dataclass
class _StubRagService:
    def answer(self, query: str, filters=None) -> RagAnswer:
        return RagAnswer(
            intent="alarm_lookup",
            answer_text="Line one. Line two. Source [ac_spindle_alarm_list.pdf:p.2]",
            citations=(Citation(source_doc="ac_spindle_alarm_list.pdf", page=2),),
            degraded_mode=False,
            warnings=(),
            traceability=TraceabilitySnapshot(
                routing_source="local",
                intent_confidence=0.92,
                degraded_mode=False,
                warning=None,
                timing_ms={"routing": 1.0, "retrieval": 2.0, "generation": 3.0},
            ),
        )


def test_stream_chat_response_yields_multiple_updates() -> None:
    history = []
    gen = stream_chat_response(
        rag_service=_StubRagService(),
        query="What is AL-09?",
        history=history,
        manufacturer="Fanuc",
        equipment="A06B",
    )

    first = next(gen)
    second = next(gen)

    assert len(first[0]) == 1
    assert first[0][0][0] == "What is AL-09?"
    assert len(second[0][0][1]) >= len(first[0][0][1])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/ui/test_controllers.py -v`
Expected: FAIL because `faultpilot.ui.controllers` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/ui/controllers.py
from __future__ import annotations

from typing import Iterator

from faultpilot.retrieval.schemas import RetrievalFilters
from faultpilot.ui.viewmodels import format_sources_markdown, format_traceability_markdown


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value == "All":
        return None
    return value


def _chunk_text(value: str, size: int = 32) -> list[str]:
    if not value:
        return [""]
    return [value[i : i + size] for i in range(0, len(value), size)]


def stream_chat_response(
    rag_service,
    query: str,
    history: list[tuple[str, str]],
    manufacturer: str | None,
    equipment: str | None,
) -> Iterator[tuple[list[tuple[str, str]], str, str, str]]:
    clean_query = query.strip()
    if not clean_query:
        yield history, "### Traceability\n- Empty query", "### Sources\n- N/A", ""
        return

    filters = RetrievalFilters(
        manufacturer=_normalize_filter(manufacturer),
        equipment=_normalize_filter(equipment),
    )
    answer = rag_service.answer(clean_query, filters=filters)
    traceability_md = format_traceability_markdown(answer.intent, answer.traceability)
    sources_md = format_sources_markdown(answer.citations)

    chat = [*history, (clean_query, "")]
    assistant_text = ""
    for piece in _chunk_text(answer.answer_text):
        assistant_text += piece
        chat[-1] = (clean_query, assistant_text)
        yield chat, traceability_md, sources_md, ""
```

```python
# scripts/test_stream.py
from pathlib import Path

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.runtime import build_ui_runtime


def main() -> int:
    runtime = build_ui_runtime(Path("config/settings.yaml"))
    generator = stream_chat_response(
        rag_service=runtime.rag_service,
        query="AL-09",
        history=[],
        manufacturer="All",
        equipment="All",
    )
    for idx, state in enumerate(generator, start=1):
        chat, traceability, sources, _ = state
        print(f"chunk={idx} assistant_len={len(chat[-1][1])}")
        if idx == 1:
            print(traceability)
            print(sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and stream isolation check**

Run: `uv run python -m pytest tests/ui/test_controllers.py -v`
Expected: PASS.

Run: `uv run python scripts/test_stream.py`
Expected: multiple `chunk=` lines printed and process exits with code 0.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/ui/controllers.py scripts/test_stream.py tests/ui/test_controllers.py
git commit -m "feat: add ui streaming controller with terminal isolation test"
```

---

### Task 5: Build Gradio Layout and App Entrypoints

**Files:**
- Create: `faultpilot/ui/layout.py`
- Create: `faultpilot/ui/app.py`
- Create: `app.py`
- Modify: `pyproject.toml`
- Create: `tests/ui/test_layout.py`
- Create: `tests/ui/test_app_boot.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_layout.py
from faultpilot.ui.layout import build_layout


def test_build_layout_has_traceability_collapsed_default() -> None:
    _, handles = build_layout(
        title="FaultPilot",
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
        traceability_open=False,
    )

    assert handles.traceability_open_default is False


# tests/ui/test_app_boot.py
from faultpilot.ui.app import create_app


def test_create_app_returns_blocks() -> None:
    app = create_app()
    assert app is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/ui/test_layout.py tests/ui/test_app_boot.py -v`
Expected: FAIL because app/layout modules do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/ui/layout.py
from __future__ import annotations

from dataclasses import dataclass

import gradio as gr


@dataclass(frozen=True)
class LayoutHandles:
    chatbot: gr.Chatbot
    query_box: gr.Textbox
    manufacturer: gr.Dropdown
    equipment: gr.Dropdown
    send_button: gr.Button
    clear_button: gr.Button
    traceability_md: gr.Markdown
    sources_md: gr.Markdown
    traceability_open_default: bool


def build_layout(title: str, manufacturers: list[str], equipment: list[str], traceability_open: bool):
    with gr.Blocks(title=title) as demo:
        gr.Markdown(f"## {title}\nIndustrial troubleshooting assistant")
        with gr.Row():
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(label="Conversation", height=520)
                query_box = gr.Textbox(label="Query", placeholder="Type your OT question...")
                with gr.Row():
                    manufacturer_dd = gr.Dropdown(choices=manufacturers, value="All", label="Manufacturer")
                    equipment_dd = gr.Dropdown(choices=equipment, value="All", label="Equipment")
                with gr.Row():
                    send_button = gr.Button("Send", variant="primary")
                    clear_button = gr.Button("Clear")
            with gr.Column(scale=3):
                with gr.Accordion("Traceability", open=traceability_open):
                    traceability_md = gr.Markdown("### Traceability\n- Waiting for query")
                    sources_md = gr.Markdown("### Sources\n- Waiting for query")

    handles = LayoutHandles(
        chatbot=chatbot,
        query_box=query_box,
        manufacturer=manufacturer_dd,
        equipment=equipment_dd,
        send_button=send_button,
        clear_button=clear_button,
        traceability_md=traceability_md,
        sources_md=sources_md,
        traceability_open_default=traceability_open,
    )
    return demo, handles
```

```python
# faultpilot/ui/app.py
from __future__ import annotations

from pathlib import Path

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.layout import build_layout
from faultpilot.ui.runtime import build_ui_runtime


def create_app():
    runtime = build_ui_runtime(Path("config/settings.yaml"))
    demo, handles = build_layout(
        title="FaultPilot - OT Troubleshooting Assistant",
        manufacturers=runtime.manufacturers,
        equipment=runtime.equipment,
        traceability_open=False,
    )

    def _on_submit(query, history, manufacturer, equipment):
        return stream_chat_response(
            rag_service=runtime.rag_service,
            query=query,
            history=history or [],
            manufacturer=manufacturer,
            equipment=equipment,
        )

    handles.send_button.click(
        _on_submit,
        inputs=[handles.query_box, handles.chatbot, handles.manufacturer, handles.equipment],
        outputs=[handles.chatbot, handles.traceability_md, handles.sources_md, handles.query_box],
    )
    handles.query_box.submit(
        _on_submit,
        inputs=[handles.query_box, handles.chatbot, handles.manufacturer, handles.equipment],
        outputs=[handles.chatbot, handles.traceability_md, handles.sources_md, handles.query_box],
    )
    handles.clear_button.click(lambda: ([], "", "", ""), outputs=[handles.chatbot, handles.traceability_md, handles.sources_md, handles.query_box])
    return demo
```

```python
# app.py
import os

from faultpilot.ui.app import create_app

demo = create_app()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
```

```toml
# pyproject.toml
[project]
dependencies = [
    "langchain>=1.3.4",
    "pdfplumber>=0.11.8",
    "pyyaml>=6.0.2",
    "rank-bm25>=0.2.2",
    "chromadb>=1.0.20",
    "sentence-transformers>=5.1.0",
    "gradio>=5.0.0",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/ui/test_layout.py tests/ui/test_app_boot.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/ui/layout.py faultpilot/ui/app.py app.py pyproject.toml tests/ui/test_layout.py tests/ui/test_app_boot.py
git commit -m "feat: add gradio layout and app entrypoint"
```

---

### Task 6: Settings, Deployment Artifacts, and Documentation

**Files:**
- Create: `faultpilot/ui/settings.py`
- Create: `tests/ui/test_settings.py`
- Modify: `config/settings.yaml`
- Create: `requirements.txt`
- Modify: `README.md`
- Modify: `Documentation/changelog.md`
- Create: `Documentation/Training/04_ui_integration_tutorial.md`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ui/test_settings.py
from faultpilot.ui.settings import UiSettings, read_ui_settings


def test_read_ui_settings_applies_defaults() -> None:
    raw = {"ui": {"title": "FaultPilot"}}

    result = read_ui_settings(raw)

    assert isinstance(result, UiSettings)
    assert result.title == "FaultPilot"
    assert result.traceability_open_default is False
    assert result.server_port == 7860
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/ui/test_settings.py -v`
Expected: FAIL because `faultpilot.ui.settings` does not exist.

- [ ] **Step 3: Write minimal implementation and config/deploy docs**

```python
# faultpilot/ui/settings.py
from dataclasses import dataclass


@dataclass(frozen=True)
class UiSettings:
    title: str
    server_port: int
    theme: str
    default_manufacturer: str
    traceability_open_default: bool


def read_ui_settings(raw: dict) -> UiSettings:
    ui = raw.get("ui", {})
    return UiSettings(
        title=str(ui.get("title", "FaultPilot - OT Troubleshooting Assistant")),
        server_port=int(ui.get("server_port", 7860)),
        theme=str(ui.get("theme", "soft")),
        default_manufacturer=str(ui.get("default_manufacturer", "All")),
        traceability_open_default=bool(ui.get("traceability_open_default", False)),
    )
```

```yaml
# config/settings.yaml (ui section)
ui:
  title: "FaultPilot — OT Troubleshooting Assistant"
  server_port: 7860
  theme: "soft"
  default_manufacturer: "All"
  show_score_breakdown: true
  traceability_open_default: false
```

```txt
# requirements.txt
gradio>=5.0.0
langchain>=1.3.4
pdfplumber>=0.11.8
pyyaml>=6.0.2
rank-bm25>=0.2.2
chromadb>=1.0.20
sentence-transformers>=5.1.0
```

```markdown
# README.md
## Run locally

```bash
uv sync
uv run python app.py
```

## Hugging Face Spaces

- SDK: Gradio
- App file: `app.py`
- Python: `3.10+`
- Required secrets:
  - `OPENAI_API_KEY` (optional, only if external LLM client is added later)
```

```markdown
# Documentation/Training/04_ui_integration_tutorial.md
# 04 UI Integration Tutorial

1. Why we isolate streaming in terminal before UI.
2. How Gradio callbacks map to routing/retrieval/rag service boundaries.
3. How traceability metadata is surfaced to operators.
4. How to deploy on Hugging Face Spaces safely.
```

```markdown
# Documentation/changelog.md (append)
## 2026-06-11 - Hito 4 UI integration
- Added modular Gradio UI package under `faultpilot/ui`.
- Added streaming controllers with pre-yield isolation test script.
- Added traceability panel with intent/timing/source information.
- Added Spaces-ready `app.py` entrypoint and deployment docs.
```

- [ ] **Step 4: Run tests and regression suite**

Run: `uv run python -m pytest tests/ui/test_settings.py -v`
Expected: PASS.

Run: `uv run python -m pytest tests -v`
Expected: PASS for full test suite.

- [ ] **Step 5: Commit**

```bash
git add faultpilot/ui/settings.py tests/ui/test_settings.py config/settings.yaml requirements.txt README.md Documentation/changelog.md Documentation/Training/04_ui_integration_tutorial.md
git commit -m "docs: finalize fase 4 ui deployment and training artifacts"
```

---

## Final Verification Checklist

- [ ] Run: `uv run python -m pytest tests -v`
- [ ] Run: `uv run python scripts/test_stream.py`
- [ ] Run: `uv run python app.py`
- [ ] Manually verify:
  - [ ] Two-column desktop layout appears correctly.
  - [ ] Traceability accordion is collapsed by default.
  - [ ] Chat streams incrementally (not one-shot full text).
  - [ ] Sources block appears every response.

---

## Spec Coverage Self-Review

1. **UI modular architecture:** Covered by Tasks 2, 3, 4, 5.
2. **Two-column clean visual layout:** Covered by Task 5.
3. **Collapsed traceability panel:** Covered by Task 5 + Task 6 settings.
4. **Pre-yield then streaming behavior:** Covered by Task 4.
5. **Intent/confidence/fallback/timing in traceability:** Covered by Task 1 + Task 2 + Task 4.
6. **Hugging Face Spaces readiness:** Covered by Tasks 5 and 6.
7. **Training/changelog updates:** Covered by Task 6.

No unresolved placeholders remain in this plan.
