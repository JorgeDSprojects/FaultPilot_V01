# Changelog

## 2026-06-09 - Hito 1: Setup + Parsers PDF (Bosch/Fanuc)

### Added
- Base package `faultpilot/` with ingestion domain modules.
- CLI `faultpilot-ingest` (`faultpilot.ingestion.cli`) for running Hito 1 pipeline.
- Chunk contract model (`ChunkRecord`) with normalization helpers.
- Fanuc parser for `ac_spindle_alarm_list.pdf`.
- Bosch parser for `Error_messages_CC_220107007331804.pdf` with table-oriented extraction.
- Ingestion pipeline orchestration to generate JSONL artifacts and manifest.
- Validation gate output `data/processed/validation_hito1.json`.

### Changed
- `pyproject.toml` updated with:
  - Python baseline `>=3.10`
  - PDF dependency `pdfplumber`
  - dev dependency `pytest`
  - package config for editable install and script entrypoints

### Generated Artifacts
- `data/processed/fanuc_ac_spindle_chunks.jsonl`
- `data/processed/bosch_cc220_chunks.jsonl`
- `data/processed/manifest_hito1.json`
- `data/processed/validation_hito1.json`

### Verification
- Unit tests for CLI, contract, parser logic, and pipeline utilities.
- End-to-end ingestion run over Bosch + Fanuc manuals with critical validation status `ok`.

## 2026-06-11 - Hito 2: Hybrid Retrieval Engine (BM25 + Dense + RRF + Reranker)

### Added
- Retrieval package under `faultpilot/retrieval/`:
  - `config.py` for typed settings loading.
  - `schemas.py` for retrieval request/response contracts.
  - `loaders.py` for JSONL chunk loading and deterministic chunk IDs.
  - `bm25_index.py` for sparse retrieval build/search plus persistence.
  - `vector_index.py` for dense retrieval with ChromaDB backend when available.
  - `fusion.py` for reciprocal rank fusion.
  - `reranker.py` for cross-encoder reranking.
  - `service.py` for hybrid orchestration.
  - `cli.py` for index/search commands.
- Retrieval config files:
  - `config/settings.yaml` with tunable knobs and route profiles.
  - `config/prompts.yaml` for system/response prompt templates.
- Retrieval test suite in `tests/retrieval/`.
- Hito 2 design and implementation plan docs in `Documentation/plan/`.

### Changed
- `pyproject.toml`:
  - Added dependencies: `pyyaml`, `rank-bm25`, `chromadb`, `sentence-transformers`.
  - Added CLI script entrypoint: `faultpilot-retrieval`.
- `uv.lock` updated after dependency resolution.

### Verification
- Full automated suite: `uv run python -m pytest tests -v` -> 23 passed.
- Retrieval index command executed successfully:
  - `uv run faultpilot-retrieval --settings config/settings.yaml index`
- Retrieval search smoke test executed:
  - `uv run faultpilot-retrieval --settings config/settings.yaml search --query "AL-09" --route alarm_lookup --manufacturer Fanuc`

## 2026-06-11 - Hito 3: Router + RAG Pipeline (LangGraph)

### Added
- Routing package under `faultpilot/routing/`:
  - `schemas.py` for routing contracts.
  - `local_classifier.py` for regex/keyword local intent detection.
  - `llm_classifier.py` for provider-agnostic LLM fallback classification.
  - `intent_router.py` for local-first routing policy with degraded fallback.
- RAG package under `faultpilot/rag/`:
  - `schemas.py` (`Citation`, `RagAnswer`).
  - `context_builder.py` for bounded context assembly.
  - `generator.py` for provider-agnostic answer generation adapter.
  - `postprocess.py` for citation guard and safe fallback response.
  - `state.py` for LangGraph state typing.
  - `graph.py` for graph composition (`route -> retrieve -> context -> generate -> guard`).
  - `service.py` for high-level `answer(...)` API.
- Test suites:
  - `tests/routing/` for local classifier and router fallback behavior.
  - `tests/rag/` for context builder, citation guard, and graph/service integration.
- Hito 3 design and implementation plans:
  - `Documentation/plan/2026-06-11-hito3-routing-rag-design.md`
  - `Documentation/plan/2026-06-11-hito3-routing-rag-implementation-plan.md`

### Changed
- `config/prompts.yaml`:
  - Added `route_intent`, `rag_answer`, and `rag_answer_strict_citations` templates.
- `config/settings.yaml`:
  - Extended `routing` with `local_first`, `llm_fallback_enabled`, and `default_intent`.
  - Added `rag` section with `max_context_chars` and `max_regeneration_attempts`.

### Verification
- Full automated suite: `uv run python -m pytest tests -v` -> 33 passed.

## 2026-06-11 - Hito 4: UI Integration (Gradio)

### Added
- UI module settings parser: `faultpilot/ui/settings.py`.
- UI settings tests: `tests/ui/test_settings.py`.
- Spaces runtime dependency manifest: `requirements.txt`.
- Training guide for UI integration and deployment:
  - `Documentation/Training/04_ui_integration_tutorial.md`

### Changed
- `config/settings.yaml` UI block now includes `traceability_open_default: false`.
- `README.md` now documents local execution and Hugging Face Spaces deployment.

### Verification
- `uv run python -m pytest tests/ui/test_settings.py -v`
- `uv run python -m pytest tests -v`

## 2026-06-12 - Compliance update: API key handling and deployment guidance

### Changed
- `README.md` now includes certification-focused sections:
  - Clear project description.
  - OpenAI API key guidance clarifying users paste the key in the UI each session (no required `OPENAI_API_KEY` env var/secret).
  - Explicit statement that the API key is user-supplied in the UI and not persistently stored by FaultPilot.
  - Quick cost estimate showing a `gpt-4o-mini` smoke run under $0.50.
  - Explicit optional functionalities list for non-blocking capabilities.
  - Hugging Face Spaces deployment guidance with a placeholder for the public Space URL.
- `faultpilot/ui/controllers.py` runtime behavior now enforces per-session UI API keys:
  - Empty keys return a stable degraded response with `missing_api_key` guidance.
  - Provider/backend exceptions return stable degraded payloads instead of bubbling errors to the UI stream.
- `faultpilot/ui/app.py` clear flow now resets conversation outputs and clears the API key textbox to reduce secret lifetime in-memory/UI state.
- Dependency policy documented and verified for deployment runtime:
  - `requirements.txt` is kept synchronized with `[project.dependencies]` in `pyproject.toml` for Spaces parity.

### Verification
- Executed `uv run pytest` -> 77 passed.
- Executed `uv run python scripts/test_stream.py` -> stream smoke output returned `chunk=1` with degraded fallback `missing_api_key`.
- Executed `uv run faultpilot-retrieval --settings config/settings.yaml search --query "AL-09" --route alarm_lookup --manufacturer Fanuc` -> returned `AL-09` matches from `ac_spindle_alarm_list.pdf`.
- Executed dependency-sync verification command `uv run python -c "import pathlib,re,sys,tomllib; py=tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')); deps={re.split(r'[<>=!~ ]', d.strip(), 1)[0] for d in py['project']['dependencies']}; req={re.split(r'[<>=!~ ]', l.strip(), 1)[0] for l in pathlib.Path('requirements.txt').read_text(encoding='utf-8').splitlines() if l.strip() and not l.lstrip().startswith('#')}; missing=sorted(deps-req); extra=sorted(req-deps); print('missing_in_requirements=', missing); print('extra_in_requirements=', extra); sys.exit(1 if missing or extra else 0)"` -> `missing_in_requirements=[]`, `extra_in_requirements=[]` (exit 0).
