# Design - OpenAI API Key UI Compliance and Provider-Backed Generation

## 1. Context

FaultPilot already includes:
- RAG orchestration with routing, hybrid retrieval, and citation guard.
- Gradio UI with streaming chat and traceability panel.
- Hugging Face Spaces-compatible entrypoint (`app.py`) and dependency manifest.

Current compliance gaps for course certification are:
- The app does not require a real provider-backed LLM during chat generation.
- The UI does not include a field where the user can paste an API key.
- README lacks mandatory certification details (required keys, cost estimate, explicit optional features list).

User decisions captured during brainstorming:
- Provider scope for this iteration: OpenAI only.
- Default model: `gpt-4o-mini`.
- Behavior when key is missing: block answer generation and request API key in UI.

## 2. Goals and Non-Goals

### Goals
- Add a secure UI field for user-provided OpenAI API key.
- Use a real provider-backed LLM for answer generation when key is present.
- Block submission when key is missing and provide a clear UX message.
- Preserve existing retrieval/routing/citation behavior and streaming UX.
- Update README to satisfy certification requirements related to keys and cost transparency.

### Non-Goals
- No multi-provider support in this iteration (Gemini/Claude deferred).
- No persistent credential storage.
- No redesign of retrieval, routing, or ingestion logic.
- No feature expansion unrelated to certification closure.

## 3. Approaches Considered

### A. Inline key field in main UI (selected)
- Add password API key textbox in current layout and pass it through existing submit flow.
- Keep architecture changes minimal and directly auditable for certification.

### B. Startup modal or onboarding wizard
- Strong onboarding UX but introduces higher UI and state complexity.

### C. Immediate multi-provider selector
- Better long-term flexibility but higher implementation and test surface now.

Selected approach: **A** for fastest low-risk path to compliance.

## 4. High-Level Architecture

### 4.1 Components affected
- `faultpilot/ui/layout.py`: add key input component and expose handle.
- `faultpilot/ui/app.py`: include key in submit inputs and callback signature.
- `faultpilot/ui/controllers.py`: validate key presence and manage blocked path.
- `faultpilot/rag/generator.py`: keep provider-agnostic generator contract.
- New adapter module: `faultpilot/rag/openai_client.py` to implement `generate_text(prompt)`.
- Runtime wiring (`faultpilot/ui/runtime.py` and/or service factory) to supply provider-backed generator in request path.

### 4.2 Boundary rules
- UI owns credential intake and validation UX.
- RAG generator owns prompt construction and answer generation contract.
- Provider adapter owns OpenAI API invocation details and error normalization.
- Retrieval/routing modules remain untouched unless required by interface compatibility.

## 5. Detailed Design

### 5.1 UI and callback contracts
- Add `OpenAI API Key` textbox with `type="password"`.
- Add short helper text stating key is used in-memory only and not persisted.
- Extend `LayoutHandles` with `api_key_box`.
- Extend submit callback signature to accept `api_key`.
- Include `api_key_box` in `common_inputs` for both button click and Enter submit.

### 5.2 Controller behavior
- On submit, normalize query and API key.
- If query is empty: keep existing empty-query handling.
- If API key is missing:
  - return chat state with user-facing guidance to paste OpenAI key.
  - do not call retrieval/rag generation.
  - keep response contract stable (chat, traceability markdown, sources markdown, query box value).
- If API key exists:
  - build or obtain a provider-backed RAG service using OpenAI client.
  - execute current streaming behavior and traceability formatting.

### 5.3 OpenAI adapter
- Implement a small client class with `generate_text(prompt: str) -> str`.
- Default model: `gpt-4o-mini`.
- Request settings: deterministic low-cost defaults suitable for technical RAG answers.
- Normalize provider exceptions into controlled application-level errors to prevent raw stack traces in UI.

### 5.4 Runtime integration strategy
- Keep current retrieval and routing service construction.
- Make generator pluggable per request based on submitted key.
- Avoid global persistence of user key in config/env/state files.

## 6. Error Handling and Security

### 6.1 Error handling
- Missing key: blocking validation message in chat.
- Invalid key/auth error: clear user-facing authentication failure message.
- Rate limit/network/provider outage: controlled degraded message, no crash.
- All error paths preserve stable UI output tuple shape.

### 6.2 Security and privacy rules
- Never write user key to disk.
- Never include key in logs, traceability panel, exceptions, or test snapshots.
- Keep key lifetime request-scoped/in-memory only.
- README should instruct users to paste key in UI and avoid committing secrets.

## 7. Testing Strategy

### 7.1 Unit tests
- `tests/ui/test_layout.py`: verify API key component exists and is wired.
- `tests/ui/test_app_boot.py` and/or `tests/ui/test_controllers.py`:
  - missing key blocks provider call.
  - present key triggers provider-backed path.
  - output tuple remains stable.
- `tests/rag/test_openai_client.py` (new):
  - success path with mocked OpenAI response.
  - auth/rate limit error normalization.

### 7.2 Regression
- Full suite: `uv run pytest`.
- Keep existing streaming probe usable after changes.

## 8. README and Certification Compliance Updates

README must include:
- Project description and architecture summary.
- Required API keys section listing: `OpenAI API key`.
- Cost estimation section showing full demo usage can stay under `$0.50` with `gpt-4o-mini`.
- Explicit list of at least 5 optional features implemented in product.
- Clarification that keys are user-supplied in UI and not stored in repository.
- Hugging Face Spaces deployment instructions and public Space URL placeholder to fill after deployment.

## 9. Acceptance Criteria

- UI includes password input for OpenAI API key.
- Sending a query without key is blocked with clear guidance.
- Sending a query with valid key uses provider-backed generation (`gpt-4o-mini`).
- Key is not persisted or exposed in logs/output.
- Automated tests cover new key-gating and provider adapter behavior.
- README includes required keys, cost estimate (`<= $0.50` trial), and optional features list.

## 10. Risks and Mitigations

- Risk: OpenAI SDK/API interface differences across versions.
  - Mitigation: isolate provider calls in adapter and mock in tests.
- Risk: user confusion when key missing.
  - Mitigation: explicit blocking message and helper text near key input.
- Risk: accidental secret leakage via debug output.
  - Mitigation: strict no-log policy for key and test assertions for sanitized errors.
