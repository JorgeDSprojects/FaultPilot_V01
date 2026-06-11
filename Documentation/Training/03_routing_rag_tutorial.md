# 03 - Routing + RAG pipeline tutorial (LangGraph)

## Objective
Hito 3 adds the decision and generation layer on top of Hito 2 retrieval:
- classify user intent reliably,
- inject grounded context,
- generate an answer,
- enforce source/page citations before returning output.

This phase is implemented with a LangGraph pipeline and provider-agnostic adapters.

---

## Decision 1 - Local-first router with LLM fallback

**El Problema:**
Intent classification must be fast and cheap for clear queries, but still robust for ambiguous language.

**Alternativas Evaluadas:**
- LLM-only classification.
- Local regex-only classification.
- Local-first + LLM fallback.

**La Decisión:**
Use local-first routing and call LLM only when confidence is below threshold.

**Implementación:**
```python
decision = router.route(query)
if decision.source == "local":
    ...
elif decision.source == "llm":
    ...
```

---

## Decision 2 - Dedicated routing domain

**El Problema:**
Embedding routing logic directly inside RAG orchestration would couple concerns and make testing harder.

**Alternativas Evaluadas:**
- Keep routing inside graph nodes only.
- Split routing into separate domain package.

**La Decisión:**
Create `faultpilot/routing/` with explicit contracts and policy.

**Implementación:**
```python
class IntentRouter:
    def route(self, query: str) -> RoutingDecision:
        ...
```

---

## Decision 3 - LangGraph orchestration for RAG

**El Problema:**
The pipeline has multiple dependent phases (route, retrieve, context, generate, guard). Linear scripts become fragile as behavior grows.

**Alternativas Evaluadas:**
- Plain sequential service only.
- LangGraph with typed state transitions.

**La Decisión:**
Use LangGraph for explicit node boundaries and state transitions.

**Implementación:**
```python
graph.add_edge("route_intent", "retrieve")
graph.add_edge("retrieve", "build_context")
graph.add_edge("build_context", "generate_answer")
graph.add_edge("generate_answer", "enforce_citations")
```

---

## Decision 4 - Citation guard as mandatory gate

**El Problema:**
Project requirements require exact traceability (`source_doc` and `page`). A plain generation step can omit citations.

**Alternativas Evaluadas:**
- Trust generator prompt only.
- Post-process answer and enforce citations.

**La Decisión:**
Add `CitationGuard` after generation:
1. validate citations,
2. regenerate once with strict prompt,
3. fallback to safe response if still invalid.

**Implementación:**
```python
final_answer, degraded, warning = guard.enforce(
    query=query,
    intent=intent,
    context=context,
    citations=citations,
    draft_answer=draft,
    generator=generator,
)
```

---

## Decision 5 - Provider-agnostic generation interface

**El Problema:**
OpenAI/Gemini/Anthropic provider choice should be runtime-configurable, not hardcoded in pipeline logic.

**Alternativas Evaluadas:**
- Provider-specific calls inside graph node.
- Adapter protocol for generation client.

**La Decisión:**
Use an abstract generation client with deterministic fallback for tests and offline behavior.

**Implementación:**
```python
class TextGenerationClient(Protocol):
    def generate_text(self, prompt: str) -> str: ...
```

---

## Test strategy applied
- `tests/routing/test_local_classifier.py`
- `tests/routing/test_intent_router.py`
- `tests/rag/test_context_builder.py`
- `tests/rag/test_citation_guard.py`
- `tests/rag/test_graph_service.py`

Verification command:
```bash
uv run python -m pytest tests -v
```

Result in this phase: **33 passed**.

---

## Next phase handoff
Hito 3 delivers a structured answer service with mandatory citations.
Hito 4 can now focus on Gradio integration and streaming stability using the already-defined RAG service boundary.
