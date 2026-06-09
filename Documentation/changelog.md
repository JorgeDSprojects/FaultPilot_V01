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
