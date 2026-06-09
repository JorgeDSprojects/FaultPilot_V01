"""Ingestion pipeline orchestration for Hito 1."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from faultpilot.ingestion.contracts import ChunkRecord
from faultpilot.ingestion.parsers import parse_bosch_pdf, parse_fanuc_pdf

FANUC_INPUT = "ac_spindle_alarm_list.pdf"
BOSCH_INPUT = "Error_messages_CC_220107007331804.pdf"

FANUC_OUTPUT = "fanuc_ac_spindle_chunks.jsonl"
BOSCH_OUTPUT = "bosch_cc220_chunks.jsonl"


def run_ingestion(
    raw_dir: Path,
    processed_dir: Path,
    documents: Iterable[str],
    parser_version: str = "0.1.0",
) -> dict[str, object]:
    """Execute ingestion pipeline for selected manuals."""
    selected_documents = set(documents)
    warnings: list[dict[str, int | str]] = []

    fanuc_chunks: list[ChunkRecord] = []
    if "fanuc" in selected_documents:
        fanuc_path = raw_dir / FANUC_INPUT
        if not fanuc_path.exists():
            raise FileNotFoundError(f"Missing Fanuc manual: {fanuc_path}")
        fanuc_chunks = parse_fanuc_pdf(fanuc_path)
        write_jsonl(processed_dir / FANUC_OUTPUT, fanuc_chunks)

    bosch_chunks: list[ChunkRecord] = []
    if "bosch" in selected_documents:
        bosch_path = raw_dir / BOSCH_INPUT
        if not bosch_path.exists():
            raise FileNotFoundError(f"Missing Bosch manual: {bosch_path}")
        bosch_chunks, bosch_warnings = parse_bosch_pdf(bosch_path)
        warnings.extend(bosch_warnings)
        write_jsonl(processed_dir / BOSCH_OUTPUT, bosch_chunks)

    all_chunks = fanuc_chunks + bosch_chunks
    validation_report = validate_chunk_records(all_chunks)
    validation_path = processed_dir / "validation_hito1.json"
    write_json(validation_path, validation_report)

    manifest = build_manifest(
        fanuc_count=len(fanuc_chunks),
        bosch_count=len(bosch_chunks),
        parser_version=parser_version,
        warnings=warnings,
    )
    manifest["validation_report"] = validation_report
    write_json(processed_dir / "manifest_hito1.json", manifest)
    return manifest


def write_jsonl(path: Path, chunks: Iterable[ChunkRecord]) -> None:
    """Write chunk records to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write dictionary payload as JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def validate_chunk_records(chunks: Iterable[ChunkRecord]) -> dict[str, object]:
    """Run critical validation rules on generated chunks."""
    checks = {
        "missing_manufacturer": 0,
        "missing_source_doc": 0,
        "invalid_page": 0,
        "missing_equipment": 0,
    }

    total = 0
    for chunk in chunks:
        total += 1
        if not chunk.manufacturer:
            checks["missing_manufacturer"] += 1
        if not chunk.source_doc:
            checks["missing_source_doc"] += 1
        if chunk.page <= 0:
            checks["invalid_page"] += 1
        if not chunk.equipment:
            checks["missing_equipment"] += 1

    critical_errors = sum(checks.values())
    return {
        "checked_chunks": total,
        "critical_errors": critical_errors,
        "checks": checks,
        "status": "ok" if critical_errors == 0 else "failed",
    }


def build_manifest(
    fanuc_count: int,
    bosch_count: int,
    parser_version: str,
    warnings: list[dict[str, int | str]],
) -> dict[str, object]:
    """Build manifest payload for Hito 1 output artifacts."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parser_version": parser_version,
        "documents": {
            "fanuc": {
                "source": FANUC_INPUT,
                "output": FANUC_OUTPUT,
                "chunks": fanuc_count,
            },
            "bosch": {
                "source": BOSCH_INPUT,
                "output": BOSCH_OUTPUT,
                "chunks": bosch_count,
            },
        },
        "warnings": warnings,
    }
