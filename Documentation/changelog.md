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
