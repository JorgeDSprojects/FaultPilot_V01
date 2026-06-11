# Fase 4 Design - Gradio UI Integration and Streaming

## 1. Context

FaultPilot already has the backend pipeline implemented:
- Ingestion (Hito 1)
- Hybrid retrieval with RRF (Hito 2)
- Intent routing plus RAG orchestration (Hito 3)

Fase 4 focuses on building the Gradio frontend and validating stable streaming behavior.

User decisions captured during brainstorming:
- Scope: Intermedio
- Layout: two columns
- Traceability panel: collapsed by default
- Responsiveness: desktop-first with safe mobile fallback
- Target deployment: Hugging Face Spaces
- Communication: Spanish text, code in English

## 2. Goals and Non-Goals

### Goals
- Build a professional, clean, readable Gradio UI for OT usage.
- Connect UI to existing routing/retrieval/rag services without duplicating backend logic.
- Provide stable token streaming in chat responses.
- Expose a traceability panel with intent, confidence, fallback status, timing, and top context chunks.
- Ensure every final answer includes source citations.
- Keep local run and Hugging Face Spaces deployment compatible.

### Non-Goals
- No redesign of retrieval, routing, or RAG algorithms.
- No advanced analytics dashboard in this phase.
- No multi-user auth or persistent user sessions.
- No dark, decorative, or technical-heavy visual theme.

## 3. Recommended Approach

Selected approach: **B - modular UI by layers**.

Reasoning:
- Faster future iteration than a monolithic `app.py`.
- Better testability for callbacks and streaming.
- Keeps boundaries explicit between presentation, orchestration, and domain services.

## 4. High-Level Architecture

### 4.1 Modules
- `app.py`: entrypoint for local run and Hugging Face Spaces.
- `faultpilot/ui/layout.py`: builds all Gradio components and layout containers.
- `faultpilot/ui/controllers.py`: handles submit/clear/toggle events and streaming generators.
- `faultpilot/ui/viewmodels.py`: formats backend outputs for UI display blocks.
- `faultpilot/ui/theme.py` (optional helper): CSS string and palette constants.

### 4.2 Existing Service Dependencies
- `faultpilot.routing.intent_router.IntentRouter`
- `faultpilot.retrieval.service.HybridRetrievalService`
- `faultpilot.rag.service.RagPipelineService`

The UI layer depends on these services through stable input/output contracts.

## 5. UI Layout and UX

### 5.1 Screen Structure (Desktop-first)
- Left column (~70%):
  - Header (`FaultPilot`, short subtitle, compact status badge)
  - `gr.Chatbot`
  - Input row (`gr.Textbox`, `Send`, `Clear`)
  - Filter row (`Manufacturer`, `Equipment`, `Intent mode`)
- Right column (~30%):
  - `Traceability` accordion collapsed by default
  - Routing card: intent, confidence, fallback
  - Timing card: routing/retrieval/generation durations
  - Context card: top chunks with source metadata

### 5.2 Mobile Fallback
- Two columns stack vertically.
- Traceability remains collapsed by default and moves below chat.
- Input controls remain visible and simple (no dense toolbar behavior).

### 5.3 Visual Rules
- Neutral light palette (white/gray/corporate blue).
- High contrast text and buttons for factory-floor readability.
- No technical background patterns, binary textures, or overloaded iconography.

## 6. Data Flow and Streaming Model

### 6.1 Request Lifecycle
1. User submits query and filters.
2. Controller validates query and prepares request context.
3. Pre-yield pipeline (blocking stage):
   - route intent
   - run hybrid retrieval
   - build grounded context with sources
4. Start streaming generator only after pre-yield stage is complete.
5. Yield response increments to `gr.Chatbot`.
6. On completion, update traceability panel with final metadata.

### 6.2 Streaming Safety Rule
To comply with `gradio-stream-isolation`:
- Implement terminal-only validation first in `scripts/test_stream.py`.
- Confirm generator emits incremental chunks and finishes cleanly.
- Reuse the same generator contract inside Gradio callback.

This isolates yield behavior before websocket UI integration.

## 7. Error Handling Strategy

- Empty query: return inline validation message, no backend call.
- Router fallback errors: default to `troubleshooting_general` and log event.
- Retrieval returns no chunks: return safe assistant response with explicit "no evidence found" plus guidance.
- LLM/generation exception: show controlled user-facing error, keep app alive, preserve conversation state.
- Traceability panel always receives a consistent payload shape, even in degraded mode.

## 8. Testing Strategy

### 8.1 Unit and Integration Tests
- `tests/ui/test_layout.py`: smoke checks for component creation and IDs.
- `tests/ui/test_controllers.py`: submit lifecycle and state transitions.
- `tests/ui/test_streaming.py`: multiple yields, termination, and citation suffix presence.
- `tests/ui/test_viewmodels.py`: formatting contracts for traceability blocks.

### 8.2 Streaming Isolation Script
- `scripts/test_stream.py`:
  - Calls the same pipeline entry used by UI generator.
  - Prints incremental chunks to terminal.
  - Confirms no blocking behavior before first token.

### 8.3 Regression Guard
- Run full project test suite after adding UI tests:
  - `uv run python -m pytest tests -v`

## 9. Hugging Face Spaces Deployment Design

- Entry point remains `app.py`.
- Export app object as `demo = create_app()` and run via `demo.launch()`.
- Use environment variables for secrets (`OPENAI_API_KEY`, etc.).
- Keep config lookup relative to repo root.
- Update `requirements.txt` with any new UI/runtime dependencies.
- Add README section for local run and Spaces settings.

## 10. Acceptance Criteria for Fase 4

- App boots locally and in Hugging Face Spaces.
- Chat responds with visible token streaming.
- Traceability panel is present, collapsed by default, and updates each query.
- Final answers include source references.
- UI remains clean and readable on desktop and usable on mobile.

## 11. Implementation Boundaries

- UI code must not modify business logic in routing/retrieval/rag domains.
- Any backend API mismatch discovered during integration should be solved via adapters in `ui/controllers.py` or small typed schema bridges, not ad-hoc patches across domains.
- Keep state shape explicit and typed to reduce callback ambiguity.

## 12. Risks and Mitigations

- Risk: delayed first token due to heavy pre-yield stage.
  - Mitigation: keep pre-yield minimal and measure timing in traceability block.
- Risk: websocket stalls from incorrect generator pattern.
  - Mitigation: mandatory `scripts/test_stream.py` validation before UI hookup.
- Risk: cluttered UX from too much debugging data.
  - Mitigation: keep traceability hidden by default and summarized.
