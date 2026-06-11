# Hito 3 Design - Router + RAG Pipeline (LangGraph)

## Goal
Build FaultPilot's routing and grounded answer pipeline so each query is classified into the correct intent and answered with strict source/page traceability.

## Scope
In scope:
- Hybrid intent routing (`local regex first + LLM fallback`).
- LangGraph pipeline orchestration.
- Context injection from Hito 2 retrieval service.
- Citation guard to enforce source/page in final answer.

Out of scope:
- Final Gradio UI wiring (Hito 4).
- Streaming websocket hardening in UI layer (Hito 4 skill-specific).

## Architecture

### Routing Layer
- `faultpilot/routing/local_classifier.py`: cheap deterministic intent classifier.
- `faultpilot/routing/llm_classifier.py`: LLM fallback classifier for ambiguous queries.
- `faultpilot/routing/intent_router.py`: policy combining both classifiers.

### RAG Layer
- `faultpilot/rag/state.py`: typed graph state.
- `faultpilot/rag/context_builder.py`: builds bounded grounded context + citations.
- `faultpilot/rag/generator.py`: answer generation adapter (provider-agnostic client).
- `faultpilot/rag/postprocess.py`: citation guard and safety fallback.
- `faultpilot/rag/graph.py`: LangGraph nodes and transitions.
- `faultpilot/rag/service.py`: high-level `answer(...)` API.

## Graph Flow
1. `route_intent` -> classify query intent.
2. `retrieve` -> call `HybridRetrievalService` with route and filters.
3. `build_context` -> generate bounded context and citation objects.
4. `generate_answer` -> create draft answer from prompts + context.
5. `enforce_citations` -> verify answer includes source/page, regenerate once or return safe fallback.
6. `finalize` -> return structured response payload.

## Routing Policy
- Local classifier outputs `(intent, confidence, evidence)`.
- If `confidence >= routing.ambiguous_threshold`, accept local route.
- Else call LLM classifier.
- If LLM fails/timeouts, fallback to `troubleshooting` and mark degraded mode.

## Context and Citation Rules
- Use only retrieved evidence from Hito 2 result set.
- Build context up to `retrieval.max_context_chars`.
- Keep citation objects with `source_doc`, `page`, and optional `alarm_code`.
- Final answer must include at least one valid source/page reference from citations.

## Config Usage
- Reuse `config/settings.yaml` for routing threshold and context length.
- Extend `config/prompts.yaml` with:
  - `route_intent` prompt template.
  - `rag_answer` prompt template.
  - `rag_answer_strict_citations` prompt template.

## Testing Strategy

### Unit
- Local classifier intent detection for alarm/programming/troubleshooting.
- Router fallback behavior when local is ambiguous.
- Context builder truncation and citation extraction.
- Citation guard: valid answer pass, invalid answer fallback path.

### Integration
- End-to-end graph run with fake LLM client and fake retrieval service.
- Alarm code query returns `alarm_lookup` route and citation-rich answer.
- Ambiguous query triggers LLM fallback path.

## Success Criteria
- Router uses local-first with LLM fallback as approved.
- LangGraph pipeline returns structured answer with citations.
- If citations are missing, pipeline returns deterministic safe fallback.
- New tests cover routing and RAG flow, and full suite remains green.
