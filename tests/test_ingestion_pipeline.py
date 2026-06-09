from pathlib import Path

from faultpilot.ingestion.contracts import ChunkRecord
from faultpilot.ingestion.pipeline import (
    build_manifest,
    validate_chunk_records,
    write_jsonl,
)


def test_write_jsonl_creates_one_line_per_chunk(tmp_path: Path) -> None:
    chunks = [
        ChunkRecord(
            content="AL-01 Motor Overheat",
            alarm_code="AL-01",
            equipment="A06B-6059-Hxxx",
            manufacturer="Fanuc",
            source_doc="ac_spindle_alarm_list.pdf",
            page=2,
        )
    ]

    output_path = tmp_path / "fanuc.jsonl"
    write_jsonl(output_path, chunks)

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "AL-01" in lines[0]


def test_validate_chunk_records_reports_critical_errors() -> None:
    chunks = [
        ChunkRecord(
            content="AL-01 Motor Overheat",
            alarm_code="AL-01",
            equipment="A06B-6059-Hxxx",
            manufacturer="Fanuc",
            source_doc="ac_spindle_alarm_list.pdf",
            page=2,
        )
    ]

    report = validate_chunk_records(chunks)
    assert report["critical_errors"] == 0


def test_build_manifest_contains_counts_and_warnings() -> None:
    manifest = build_manifest(
        fanuc_count=10,
        bosch_count=20,
        parser_version="0.1.0",
        warnings=[{"page": 88, "reason": "table parse fallback"}],
    )

    assert manifest["documents"]["fanuc"]["chunks"] == 10
    assert manifest["documents"]["bosch"]["chunks"] == 20
    assert manifest["warnings"][0]["page"] == 88
