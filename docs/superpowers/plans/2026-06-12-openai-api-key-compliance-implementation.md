# OpenAI API Key Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FaultPilot certification-compliant by adding a UI API key field, enforcing key-gated usage, and switching answer generation to a real OpenAI-backed LLM path.

**Architecture:** Keep retrieval/routing intact, add a small provider adapter (`faultpilot/rag/openai_client.py`), expose a runtime factory that builds API-key-scoped `RagPipelineService`, and wire Gradio callbacks to require a user key before generation. Update README with explicit certification sections (required key, sub-$0.50 cost estimate, optional features list).

**Tech Stack:** Python 3.10+, Gradio, OpenAI Python SDK, LangGraph, pytest, uv.

---

## Planned File Structure

### Create
- `faultpilot/rag/openai_client.py`
- `tests/rag/test_openai_client.py`

### Modify
- `pyproject.toml`
- `requirements.txt`
- `faultpilot/ui/runtime.py`
- `faultpilot/ui/layout.py`
- `faultpilot/ui/app.py`
- `faultpilot/ui/controllers.py`
- `tests/ui/test_runtime.py`
- `tests/ui/test_layout.py`
- `tests/ui/test_app_boot.py`
- `tests/ui/test_controllers.py`
- `README.md`
- `Documentation/changelog.md`

### Responsibility Boundaries
- `faultpilot/rag/openai_client.py`: provider invocation and provider error normalization only.
- `faultpilot/ui/runtime.py`: dependency wiring and API-key-scoped service factory.
- `faultpilot/ui/layout.py`: UI components only.
- `faultpilot/ui/app.py`: callback wiring only.
- `faultpilot/ui/controllers.py`: validation, flow control, and stable streaming outputs.
- `README.md`: certification-facing documentation and cost transparency.

---

### Task 1: Add OpenAI Provider Adapter and Dependency

**Files:**
- Create: `tests/rag/test_openai_client.py`
- Create: `faultpilot/rag/openai_client.py`
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing test**

```python
# tests/rag/test_openai_client.py
from __future__ import annotations

from types import SimpleNamespace

import pytest

from faultpilot.rag.openai_client import OpenAiTextGenerationClient, OpenAiTextGenerationError


class _FakeResponsesApi:
    def __init__(self, payload: object | None = None, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._payload


class _FakeOpenAiClient:
    def __init__(self, responses_api: _FakeResponsesApi) -> None:
        self.responses = responses_api


def test_openai_client_returns_text_and_uses_model_defaults() -> None:
    responses_api = _FakeResponsesApi(payload=SimpleNamespace(output_text="Grounded answer"))

    client = OpenAiTextGenerationClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    answer = client.generate_text("Intent: alarm_lookup")

    assert answer == "Grounded answer"
    assert len(responses_api.calls) == 1
    assert responses_api.calls[0]["model"] == "gpt-4o-mini"
    assert responses_api.calls[0]["temperature"] == 0.1


def test_openai_client_raises_when_provider_returns_empty_text() -> None:
    responses_api = _FakeResponsesApi(payload=SimpleNamespace(output_text="   "))

    client = OpenAiTextGenerationClient(
        api_key="sk-test",
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    with pytest.raises(OpenAiTextGenerationError, match="empty response"):
        client.generate_text("Intent: troubleshooting")


def test_openai_client_wraps_provider_failures() -> None:
    responses_api = _FakeResponsesApi(error=RuntimeError("401 Unauthorized"))

    client = OpenAiTextGenerationClient(
        api_key="sk-test",
        client_factory=lambda api_key: _FakeOpenAiClient(responses_api),
    )

    with pytest.raises(OpenAiTextGenerationError, match="OpenAI request failed"):
        client.generate_text("Intent: programming")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/rag/test_openai_client.py -v`
Expected: FAIL with `ModuleNotFoundError` because `faultpilot.rag.openai_client` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# faultpilot/rag/openai_client.py
"""OpenAI text generation adapter for FaultPilot RAG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class _ResponsesApi(Protocol):
    def create(self, **kwargs):
        raise NotImplementedError


class _OpenAiClientProtocol(Protocol):
    responses: _ResponsesApi


ClientFactory = Callable[[str], _OpenAiClientProtocol]


class OpenAiTextGenerationError(RuntimeError):
    """Raised when OpenAI generation fails or returns unusable output."""


def _default_client_factory(api_key: str) -> _OpenAiClientProtocol:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency contract
        raise RuntimeError(
            "openai dependency is required for provider-backed generation."
        ) from exc
    return OpenAI(api_key=api_key)


@dataclass(frozen=True)
class OpenAiTextGenerationClient:
    """Minimal adapter implementing RagAnswerGenerator TextGenerationClient protocol."""

    api_key: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_output_tokens: int = 450
    client_factory: ClientFactory = _default_client_factory

    def generate_text(self, prompt: str) -> str:
        client = self.client_factory(self.api_key)
        try:
            response = client.responses.create(
                model=self.model,
                input=prompt,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            )
        except Exception as exc:
            raise OpenAiTextGenerationError(
                "OpenAI request failed. Check API key, quota, or connectivity."
            ) from exc

        output = getattr(response, "output_text", "")
        if not isinstance(output, str) or not output.strip():
            raise OpenAiTextGenerationError("OpenAI returned an empty response.")
        return output.strip()
```

- [ ] **Step 4: Add runtime dependency manifests**

```toml
# pyproject.toml (append in [project].dependencies)
dependencies = [
    "langchain>=1.3.4",
    "pdfplumber>=0.11.8",
    "pyyaml>=6.0.2",
    "rank-bm25>=0.2.2",
    "chromadb>=1.0.20",
    "sentence-transformers>=5.1.0",
    "gradio>=5.0.0",
    "openai>=1.55.0",
]
```

```txt
# requirements.txt
# Source of truth: [project.dependencies] in pyproject.toml.
# Keep this file in exact sync for Hugging Face Spaces deployments.
gradio>=5.0.0
langchain>=1.3.4
openai>=1.55.0
pdfplumber>=0.11.8
pyyaml>=6.0.2
rank-bm25>=0.2.2
chromadb>=1.0.20
sentence-transformers>=5.1.0
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/rag/test_openai_client.py -v`
Expected: all tests PASS.

```bash
git add tests/rag/test_openai_client.py faultpilot/rag/openai_client.py pyproject.toml requirements.txt
git commit -m "feat(rag): add OpenAI generation adapter"
```

---

### Task 2: Expose API-Key-Scoped RAG Service Factory in UI Runtime

**Files:**
- Modify: `faultpilot/ui/runtime.py`
- Modify: `tests/ui/test_runtime.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ui/test_runtime.py (append test)
def test_build_openai_rag_service_wires_provider_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from faultpilot.ui import runtime as runtime_module

    calls: dict[str, object] = {}

    class _FakeOpenAiClient:
        def __init__(self, api_key: str, model: str) -> None:
            calls["api_key"] = api_key
            calls["model"] = model

    class _FakeGenerator:
        def __init__(self, client) -> None:
            calls["generator_client"] = client

    class _FakeCitationGuard:
        def __init__(self, max_regeneration_attempts: int) -> None:
            calls["guard_attempts"] = max_regeneration_attempts

    graph_sentinel = object()

    def fake_build_rag_graph(**kwargs):
        calls["graph_kwargs"] = kwargs
        return graph_sentinel

    class _FakeRagPipelineService:
        def __init__(self, graph) -> None:
            calls["graph"] = graph

    monkeypatch.setattr(runtime_module, "OpenAiTextGenerationClient", _FakeOpenAiClient)
    monkeypatch.setattr(runtime_module, "RagAnswerGenerator", _FakeGenerator)
    monkeypatch.setattr(runtime_module, "CitationGuard", _FakeCitationGuard)
    monkeypatch.setattr(runtime_module, "build_rag_graph", fake_build_rag_graph)
    monkeypatch.setattr(runtime_module, "RagPipelineService", _FakeRagPipelineService)

    router = object()
    retrieval_service = object()
    runtime_module.build_openai_rag_service(
        router=router,
        retrieval_service=retrieval_service,
        api_key="sk-test",
        max_context_chars=1234,
        max_regeneration_attempts=2,
        model_name="gpt-4o-mini",
    )

    assert calls["api_key"] == "sk-test"
    assert calls["model"] == "gpt-4o-mini"
    assert calls["graph"] is graph_sentinel
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ui/test_runtime.py::test_build_openai_rag_service_wires_provider_client -v`
Expected: FAIL because `build_openai_rag_service` is not defined.

- [ ] **Step 3: Implement runtime helper and factory exposure**

```python
# faultpilot/ui/runtime.py (key additions)
from typing import Any, Callable, Iterable

from faultpilot.rag.openai_client import OpenAiTextGenerationClient

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def build_openai_rag_service(
    router,
    retrieval_service,
    api_key: str,
    max_context_chars: int,
    max_regeneration_attempts: int,
    model_name: str = DEFAULT_OPENAI_MODEL,
) -> RagPipelineService:
    generator = RagAnswerGenerator(
        client=OpenAiTextGenerationClient(api_key=api_key, model=model_name)
    )
    graph = build_rag_graph(
        router=router,
        retrieval_service=retrieval_service,
        generator=generator,
        max_context_chars=max_context_chars,
        citation_guard=CitationGuard(max_regeneration_attempts=max_regeneration_attempts),
    )
    return RagPipelineService(graph)


@dataclass(frozen=True)
class UiRuntime:
    rag_service: RagPipelineService
    rag_service_factory: Callable[[str], RagPipelineService]
    manufacturers: list[str]
    equipment: list[str]
    ui_settings: UiSettings


def build_ui_runtime(settings_path: Path) -> UiRuntime:
    settings = load_settings(settings_path)
    config = UiRuntimeConfig.from_settings(settings.raw)
    ui_settings = read_ui_settings(settings.raw)

    chunks = load_chunks(config.chunks_jsonl_dir)
    manufacturers, equipment = collect_filter_options(chunks)

    sparse = _load_or_build_sparse_index(config.bm25_index, chunks)

    dense = build_dense_index(
        chunks,
        persist_dir=config.chroma_db,
        model_name=config.embeddings_model_name,
    )
    reranker = CrossEncoderReranker(model_name=config.reranker_model_name)
    retrieval = HybridRetrievalService(
        settings=settings,
        sparse_retriever=sparse,
        dense_retriever=dense,
        reranker=reranker,
    )

    router = IntentRouter(
        local_classifier=LocalIntentClassifier(),
        llm_classifier=_FallbackLlmClassifier(),
        ambiguous_threshold=config.routing_ambiguous_threshold,
        local_first=config.routing_local_first,
    )

    generator = RagAnswerGenerator(client=None)
    graph = build_rag_graph(
        router=router,
        retrieval_service=retrieval,
        generator=generator,
        max_context_chars=config.rag_max_context_chars,
        citation_guard=CitationGuard(
            max_regeneration_attempts=config.rag_max_regeneration_attempts
        ),
    )

    baseline_rag_service = RagPipelineService(graph)

    def rag_service_factory(api_key: str) -> RagPipelineService:
        return build_openai_rag_service(
            router=router,
            retrieval_service=retrieval,
            api_key=api_key,
            max_context_chars=config.rag_max_context_chars,
            max_regeneration_attempts=config.rag_max_regeneration_attempts,
            model_name=DEFAULT_OPENAI_MODEL,
        )

    return UiRuntime(
        rag_service=baseline_rag_service,
        rag_service_factory=rag_service_factory,
        manufacturers=manufacturers,
        equipment=equipment,
        ui_settings=ui_settings,
    )
```

- [ ] **Step 4: Strengthen runtime wiring assertion**

```python
# tests/ui/test_runtime.py (inside test_build_ui_runtime_wires_dependencies)
assert callable(runtime.rag_service_factory)
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/ui/test_runtime.py -v`
Expected: all runtime tests PASS.

```bash
git add faultpilot/ui/runtime.py tests/ui/test_runtime.py
git commit -m "feat(ui): add API-key scoped rag service factory"
```

---

### Task 3: Add OpenAI API Key Input to Gradio Layout and App Wiring

**Files:**
- Modify: `faultpilot/ui/layout.py`
- Modify: `faultpilot/ui/app.py`
- Modify: `tests/ui/test_layout.py`
- Modify: `tests/ui/test_app_boot.py`

- [ ] **Step 1: Write failing UI tests**

```python
# tests/ui/test_layout.py (append assertions)
def test_build_layout_exposes_api_key_box() -> None:
    _, handles = build_layout(
        title="FaultPilot",
        theme="soft",
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
        default_manufacturer="Fanuc",
        traceability_open=False,
        default_intent_mode="Auto",
    )

    assert isinstance(handles.api_key_box, gr.Textbox)
    assert handles.api_key_box.type == "password"
```

```python
# tests/ui/test_app_boot.py (update wiring expectations in test_create_app_wires_submit_send_and_clear)
api_key_box = object()
fake_handles = SimpleNamespace(
    chatbot=chatbot,
    query_box=query_box,
    manufacturer=manufacturer,
    equipment=equipment,
    intent_mode=intent_mode,
    api_key_box=api_key_box,
    send_button=send_button,
    clear_button=clear_button,
    traceability_md=traceability_md,
    sources_md=sources_md,
    traceability_open_default=False,
)

assert send_call.inputs == [query_box, chatbot, manufacturer, equipment, intent_mode, api_key_box]
assert submit_call.inputs == [query_box, chatbot, manufacturer, equipment, intent_mode, api_key_box]

stream_states = list(
    send_call.fn(
        "AL-09",
        [{"role": "user", "content": "old"}, {"role": "assistant", "content": "state"}],
        "Fanuc",
        "A06B",
        "Auto",
        "sk-test",
    )
)

assert captured_stream_call["api_key"] == "sk-test"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/ui/test_layout.py tests/ui/test_app_boot.py::test_create_app_wires_submit_send_and_clear -v`
Expected: FAIL because `api_key_box` is not present yet.

- [ ] **Step 3: Implement layout and app wiring**

```python
# faultpilot/ui/layout.py (key additions)
@dataclass(frozen=True)
class LayoutHandles:
    chatbot: gr.Chatbot
    query_box: gr.Textbox
    manufacturer: gr.Dropdown
    equipment: gr.Dropdown
    send_button: gr.Button
    clear_button: gr.Button
    intent_mode: gr.Dropdown
    api_key_box: gr.Textbox
    traceability_md: gr.Markdown
    sources_md: gr.Markdown
    traceability_open_default: bool


def build_layout(
    title: str,
    theme: str,
    manufacturers: list[str],
    equipment: list[str],
    default_manufacturer: str,
    traceability_open: bool,
    default_intent_mode: str,
) -> tuple[gr.Blocks, LayoutHandles]:
    with gr.Blocks(title=title) as demo:
        gr.Markdown(f"## {title}\nIndustrial troubleshooting assistant")
        gr.Markdown("Paste your OpenAI API key below. The key is used in-memory only and is not stored.")

        with gr.Row():
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(label="Conversation", height=520)
                query_box = gr.Textbox(label="Query", placeholder="Type your OT question", lines=2)
                api_key_box = gr.Textbox(
                    label="OpenAI API Key",
                    placeholder="sk-your-key-here",
                    type="password",
                    lines=1,
                )
                with gr.Row():
                    send_button = gr.Button("Send", variant="primary")
                    clear_button = gr.Button("Clear")
                with gr.Row():
                    manufacturer_dd = gr.Dropdown(
                        choices=manufacturers,
                        value=_resolve_choice(manufacturers, default_manufacturer),
                        label="Manufacturer",
                    )
                    equipment_dd = gr.Dropdown(
                        choices=equipment,
                        value=_default_choice(equipment),
                        label="Equipment",
                    )
                    intent_mode_dd = gr.Dropdown(
                        choices=INTENT_MODE_CHOICES,
                        value=_resolve_choice(INTENT_MODE_CHOICES, default_intent_mode),
                        label="Intent mode",
                    )

            with gr.Column(scale=3):
                with gr.Accordion("Traceability", open=traceability_open):
                    traceability_md = gr.Markdown(TRACEABILITY_PLACEHOLDER)
                    sources_md = gr.Markdown(SOURCES_PLACEHOLDER)

    handles = LayoutHandles(
        chatbot=chatbot,
        query_box=query_box,
        manufacturer=manufacturer_dd,
        equipment=equipment_dd,
        send_button=send_button,
        clear_button=clear_button,
        intent_mode=intent_mode_dd,
        api_key_box=api_key_box,
        traceability_md=traceability_md,
        sources_md=sources_md,
        traceability_open_default=traceability_open,
    )
```

```python
# faultpilot/ui/app.py (key additions)
def create_app(settings_path: str | Path | None = None) -> gr.Blocks:
    runtime = build_ui_runtime(resolve_settings_path(settings_path))
    demo, handles = build_layout(
        title=runtime.ui_settings.title,
        theme=runtime.ui_settings.theme,
        manufacturers=runtime.manufacturers,
        equipment=runtime.equipment,
        default_manufacturer=runtime.ui_settings.default_manufacturer,
        traceability_open=runtime.ui_settings.traceability_open_default,
        default_intent_mode=runtime.ui_settings.default_intent_mode,
    )

    def _on_submit(
        query: str,
        history: list[ChatMessage] | None,
        manufacturer: str | None,
        equipment: str | None,
        intent_mode: str | None,
        api_key: str | None,
    ) -> Iterator[tuple[list[ChatMessage], str, str, str]]:
        yield from stream_chat_response(
            rag_service=runtime.rag_service,
            rag_service_factory=runtime.rag_service_factory,
            query=query,
            history=history or [],
            manufacturer=manufacturer,
            equipment=equipment,
            intent_mode=intent_mode,
            api_key=api_key,
        )

    common_inputs = [
        handles.query_box,
        handles.chatbot,
        handles.manufacturer,
        handles.equipment,
        handles.intent_mode,
        handles.api_key_box,
    ]
```

- [ ] **Step 4: Align test doubles for new handle field**

```python
# tests/ui/test_app_boot.py
fake_handles = SimpleNamespace(
    chatbot=chatbot,
    query_box=query_box,
    manufacturer=manufacturer,
    equipment=equipment,
    intent_mode=intent_mode,
    api_key_box=api_key_box,
    send_button=send_button,
    clear_button=clear_button,
    traceability_md=traceability_md,
    sources_md=sources_md,
    traceability_open_default=False,
)
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/ui/test_layout.py tests/ui/test_app_boot.py -v`
Expected: PASS for updated layout and wiring tests.

```bash
git add faultpilot/ui/layout.py faultpilot/ui/app.py tests/ui/test_layout.py tests/ui/test_app_boot.py
git commit -m "feat(ui): add OpenAI API key input and callback wiring"
```

---

### Task 4: Enforce API Key Gate and Provider Error Handling in Streaming Controller

**Files:**
- Modify: `faultpilot/ui/controllers.py`
- Modify: `tests/ui/test_controllers.py`

- [ ] **Step 1: Write failing controller tests**

```python
# tests/ui/test_controllers.py (append tests)
def test_stream_chat_response_blocks_when_api_key_missing() -> None:
    rag_service = _StubRagService()
    generator = stream_chat_response(
        rag_service=rag_service,
        rag_service_factory=None,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        api_key="   ",
    )

    state = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert "OpenAI API key" in state[0][-1]["content"]
    assert rag_service.calls == []


def test_stream_chat_response_uses_factory_when_api_key_present() -> None:
    base_service = _StubRagService()
    provider_service = _StubRagService()
    captured: dict[str, str] = {}

    def _factory(api_key: str):
        captured["api_key"] = api_key
        return provider_service

    generator = stream_chat_response(
        rag_service=base_service,
        rag_service_factory=_factory,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        api_key="sk-live",
    )

    next(generator)

    assert captured["api_key"] == "sk-live"
    assert len(provider_service.calls) == 1
    assert base_service.calls == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/ui/test_controllers.py::test_stream_chat_response_blocks_when_api_key_missing tests/ui/test_controllers.py::test_stream_chat_response_uses_factory_when_api_key_present -v`
Expected: FAIL because `stream_chat_response` does not accept `api_key` / `rag_service_factory` yet.

- [ ] **Step 3: Implement controller key gate and factory dispatch**

```python
# faultpilot/ui/controllers.py (key additions)
from typing import Callable, Iterator, Literal, Protocol, TypedDict

from faultpilot.rag.openai_client import OpenAiTextGenerationError


def _normalize_api_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def stream_chat_response(
    rag_service: RagServiceProtocol,
    query: str,
    history: list[ChatMessage],
    manufacturer: str | None,
    equipment: str | None,
    intent_mode: str | None,
    api_key: str | None,
    rag_service_factory: Callable[[str], RagServiceProtocol] | None = None,
) -> Iterator[tuple[list[ChatMessage], str, str, str]]:
    clean_query = query.strip()
    if not clean_query:
        yield [*history], "### Traceability\n- Empty query", "### Sources\n- N/A", ""
        return

    clean_api_key = _normalize_api_key(api_key)
    if clean_api_key is None:
        yield (
            [
                *history,
                {"role": "user", "content": clean_query},
                {
                    "role": "assistant",
                    "content": "Add your OpenAI API key to continue. Paste it in the OpenAI API Key field.",
                },
            ],
            "### Traceability\n- Missing OpenAI API key",
            "### Sources\n- No grounded sources available",
            "",
        )
        return

    active_service = rag_service_factory(clean_api_key) if rag_service_factory else rag_service
    filters = RetrievalFilters(
        manufacturer=_normalize_filter(manufacturer),
        equipment=_normalize_filter(equipment),
    )
    intent_override = _normalize_intent_override(intent_mode)

    conversation_prefix: list[ChatMessage] = [
        *history,
        {"role": "user", "content": clean_query},
    ]

    try:
        answer = active_service.answer(
            clean_query,
            filters=filters,
            intent_override=intent_override,
        )
    except OpenAiTextGenerationError:
        yield (
            [
                *conversation_prefix,
                {
                    "role": "assistant",
                    "content": "OpenAI request failed. Verify your API key and available balance, then retry.",
                },
            ],
            "### Traceability\n- Warning: `openai_request_failed`",
            "### Sources\n- No grounded sources available",
            "",
        )
        return
    except Exception:
        fallback_snapshot = TraceabilitySnapshot(
            routing_source="fallback",
            intent_confidence=0.0,
            degraded_mode=True,
            warning="backend_error",
            timing_ms={"routing": 0.0, "retrieval": 0.0, "generation": 0.0},
        )
        traceability_md = format_traceability_markdown(
            intent="troubleshooting",
            snapshot=fallback_snapshot,
            citations=(),
        )
        sources_md = format_sources_markdown(())
        yield (
            [
                *conversation_prefix,
                {
                    "role": "assistant",
                    "content": "Backend unavailable. Returning degraded response with no grounded context.",
                },
            ],
            traceability_md,
            sources_md,
            "",
        )
        return
```

- [ ] **Step 4: Update existing test invocations for new signature**

```python
# tests/ui/test_controllers.py (apply to existing calls)
generator = stream_chat_response(
    rag_service=rag_service,
    rag_service_factory=None,
    query="What is AL-09?",
    history=[],
    manufacturer="Fanuc",
    equipment="A06B",
    intent_mode="Auto",
    api_key="sk-test",
)
```

- [ ] **Step 5: Run tests and commit**

Run: `uv run pytest tests/ui/test_controllers.py -v`
Expected: PASS for all controller tests.

```bash
git add faultpilot/ui/controllers.py tests/ui/test_controllers.py
git commit -m "feat(ui): enforce OpenAI API key gating in stream controller"
```

---

### Task 5: Stabilize Root App Import Regression Test

**Files:**
- Modify: `tests/ui/test_app_boot.py`

- [ ] **Step 1: Run current failing regression test**

Run: `uv run pytest tests/ui/test_app_boot.py::test_root_app_module_exports_demo -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 2: Patch test to import root `app.py` deterministically**

```python
# tests/ui/test_app_boot.py (imports)
from pathlib import Path


def test_root_app_module_exports_demo(monkeypatch) -> None:
    sentinel = object()
    sys.modules.pop("app", None)
    monkeypatch.setattr("faultpilot.ui.app.create_app", lambda: sentinel)

    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(repo_root))

    module = importlib.import_module("app")

    assert module.demo is sentinel
```

- [ ] **Step 3: Verify regression test passes**

Run: `uv run pytest tests/ui/test_app_boot.py::test_root_app_module_exports_demo -v`
Expected: PASS.

- [ ] **Step 4: Verify full app boot tests still pass**

Run: `uv run pytest tests/ui/test_app_boot.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_app_boot.py
git commit -m "test(ui): stabilize root app import in pytest"
```

---

### Task 6: Update README for Certification Requirements and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `Documentation/changelog.md`

- [ ] **Step 1: Rewrite README with required certification sections**

```markdown
# FaultPilot V01

FaultPilot is an OT troubleshooting assistant that combines intent routing, hybrid retrieval, and citation-guarded RAG.

## Key Features
- Streaming responses in Gradio chat.
- Query routing (`alarm_lookup`, `troubleshooting`, `programming`).
- Hybrid retrieval (BM25 + dense + RRF).
- Cross-encoder reranker.
- Metadata filtering by manufacturer and equipment.
- Citation-guard post-processing.
- PDF ingestion pipeline for Bosch/Fanuc manuals.

## Required API Keys
- OpenAI API key (pasted by user in UI field `OpenAI API Key`).

FaultPilot does not store API keys in files, config, or repository history.

## Quick Cost Estimate (OpenAI)
Using default model `gpt-4o-mini`, a typical demo session (5-8 short queries, each with compact grounded context and concise answers) is expected to stay below **$0.50** total.

## Run Locally
```bash
uv sync
uv run python app.py
```

## Hugging Face Spaces Deployment
- SDK: `gradio`
- App file: `app.py`
- Runtime dependencies: `requirements.txt`
- Space URL: `<ADD_YOUR_PUBLIC_SPACE_URL_HERE>`

## Optional Course Functionalities Implemented
1. Streaming responses.
2. Domain-specific app (industrial OT troubleshooting).
3. Hybrid search.
4. Reranker.
5. Metadata filtering.
6. Query routing.
7. Data ingestion from PDFs.
```

- [ ] **Step 2: Update changelog entry for compliance milestone**

```markdown
## 2026-06-12 - Certification Compliance: OpenAI Key UX + Provider Generation

### Added
- OpenAI adapter for provider-backed text generation.
- UI API key field (`OpenAI API Key`) with in-memory usage policy.
- Runtime factory for API-key-scoped RAG service creation.

### Changed
- Stream controller now blocks generation when API key is missing.
- README now documents required API keys, cost estimate, and optional features implemented.

### Verification
- `uv run pytest`
- `uv run python scripts/test_stream.py`
```

- [ ] **Step 3: Run full verification suite**

Run: `uv run pytest`
Expected: full test suite PASS.

Run: `uv run python scripts/test_stream.py`
Expected: streaming probe returns success (exit code 0), first chunk under configured threshold.

Run: `uv run faultpilot-retrieval --settings config/settings.yaml search --query "AL-09" --route alarm_lookup --manufacturer Fanuc`
Expected: grounded hits printed from Fanuc source.

- [ ] **Step 4: Review dependency sync and git status**

Run: `uv run python -c "import tomllib, pathlib; p=pathlib.Path('pyproject.toml'); deps=tomllib.loads(p.read_text())['project']['dependencies']; req=pathlib.Path('requirements.txt').read_text().splitlines(); print('openai>=1.55.0' in deps, any('openai>=1.55.0' in line for line in req))"`
Expected: `True True`.

Run: `git status --short`
Expected: only intended files changed.

- [ ] **Step 5: Commit**

```bash
git add README.md Documentation/changelog.md
git commit -m "docs: add certification compliance and cost transparency"
```

---

## Spec Coverage Check

- UI API key element: covered by Task 3.
- Missing-key blocking path: covered by Task 4.
- Provider-backed OpenAI generation with `gpt-4o-mini`: covered by Tasks 1 and 2.
- Stable error handling/security posture: covered by Task 4 and adapter in Task 1.
- README compliance sections (required key, cost, optional features): covered by Task 6.
- Regression stability (`test_root_app_module_exports_demo`): covered by Task 5.

## Placeholder Scan

- No deferred implementation placeholders remain.
- Every code-change step includes concrete code and exact commands.

## Type and Interface Consistency

- Controller signature uses `api_key` + `rag_service_factory` consistently across app wiring and tests.
- Runtime exposes `rag_service_factory` and keeps existing `rag_service` for compatibility.
- OpenAI adapter keeps `generate_text(prompt)` contract expected by `RagAnswerGenerator`.
