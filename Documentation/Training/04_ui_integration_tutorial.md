# 04 - UI integration tutorial (Gradio + Spaces)

## Objective
Hito 4 turns the routing and RAG backend into an operator-facing interface.
The goal is to keep UX simple for OT teams while preserving technical traceability.

---

## Why this integration exists

### 1) Keep orchestration logic outside the view layer
The UI should not know how routing or retrieval works internally.
It only calls a streaming controller and renders:
- chat history,
- traceability metadata,
- source references.

This keeps the backend testable and lets us evolve the graph without rewriting UI components.

### 2) Keep traceability visible but not noisy
Operators need evidence (intent, sources, timing), but the main conversation must remain readable.
The Traceability panel is collapsed by default (`traceability_open_default: false`) and expanded only when needed.

### 3) Keep deployment friction low
`app.py` is a Spaces-ready entrypoint and `requirements.txt` contains runtime dependencies.
This allows direct deployment to Hugging Face Spaces without extra packaging steps.

---

## Architecture handoff (backend -> UI)

1. `faultpilot.ui.runtime.build_ui_runtime(...)` builds service dependencies.
2. `faultpilot.ui.layout.build_layout(...)` creates Gradio components.
3. `faultpilot.ui.controllers.stream_chat_response(...)` streams answer chunks.
4. `faultpilot.ui.app.create_app(...)` wires callbacks and exports `gr.Blocks`.
5. Root `app.py` exposes `demo` for local run and Spaces runtime.

This separation prevents tight coupling between transport/UI and domain logic.

---

## How to run locally

```bash
uv sync
uv run python app.py
```

Open the URL printed by Gradio (usually `http://127.0.0.1:7860`).

Optional custom settings file:

```bash
set FAULTPILOT_SETTINGS_PATH=path\to\settings.yaml
uv run python app.py
```

---

## How to deploy on Hugging Face Spaces

1. Create a new Space with SDK set to `gradio`.
2. Push this repository with `app.py` and `requirements.txt` at root.
3. Confirm Python version is `3.10+`.
4. Add secrets only when needed (for example `OPENAI_API_KEY` if external LLM generation is enabled later).
5. Wait for the Space build to complete and verify the UI loads.

Spaces will install dependencies from `requirements.txt` and start `app.py` automatically.

---

## Verification checklist

- UI launches successfully from `uv run python app.py`.
- Traceability accordion starts collapsed.
- Messages stream incrementally and keep chat history state.
- Sources and traceability blocks update on each response.
- `uv run python -m pytest tests -v` passes before deployment.
