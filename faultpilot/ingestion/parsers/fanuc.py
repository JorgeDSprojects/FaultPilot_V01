"""Parser for Fanuc AC spindle alarm manuals."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from faultpilot.ingestion.contracts import ChunkRecord

FANUC_MANUAL_FILENAME = "ac_spindle_alarm_list.pdf"

_EQUIPMENT_PATTERN = re.compile(r"Alarm List for\s+(.+)$", re.IGNORECASE)
_AL_CODE_PATTERN = re.compile(r"^(AL-\d{2}(?:-\d{2})?)\s+(.+)$")
_NUMERIC_CODE_PATTERN = re.compile(r"^(\d{1,2})\s+(?:o\s+)*(.+)$", re.IGNORECASE)


def extract_fanuc_chunks_from_lines(lines: list[str], page_number: int) -> list[ChunkRecord]:
    """Extract normalized Fanuc chunks from text lines for one page."""
    equipment = "A06B-unknown"
    chunks: list[ChunkRecord] = []

    for raw_line in lines:
        line = " ".join(raw_line.split())
        if not line:
            continue

        equipment_match = _EQUIPMENT_PATTERN.search(line)
        if equipment_match:
            equipment = equipment_match.group(1).strip()
            continue

        al_code_match = _AL_CODE_PATTERN.match(line)
        if al_code_match:
            alarm_code = al_code_match.group(1)
            meaning = al_code_match.group(2)
            chunks.append(
                _build_fanuc_chunk(
                    alarm_code=alarm_code,
                    meaning=meaning,
                    equipment=equipment,
                    page_number=page_number,
                )
            )
            continue

        numeric_code_match = _NUMERIC_CODE_PATTERN.match(line)
        if numeric_code_match:
            number = int(numeric_code_match.group(1))
            if number <= 0 or number > 99:
                continue
            alarm_code = f"AL-{number:02d}"
            meaning = numeric_code_match.group(2)
            chunks.append(
                _build_fanuc_chunk(
                    alarm_code=alarm_code,
                    meaning=meaning,
                    equipment=equipment,
                    page_number=page_number,
                )
            )

    return _deduplicate_by_code(chunks)


def parse_fanuc_pdf(pdf_path: Path) -> list[ChunkRecord]:
    """Parse Fanuc AC spindle PDF into chunk records."""
    records: list[ChunkRecord] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            records.extend(extract_fanuc_chunks_from_lines(text.splitlines(), page_number))
    return records


def _build_fanuc_chunk(
    alarm_code: str,
    meaning: str,
    equipment: str,
    page_number: int,
) -> ChunkRecord:
    content = f"{alarm_code} {meaning}".strip()
    return ChunkRecord(
        content=content,
        alarm_code=alarm_code,
        equipment=equipment,
        manufacturer="Fanuc",
        source_doc=FANUC_MANUAL_FILENAME,
        page=page_number,
        category="alarm",
        description=meaning,
        language="en",
        raw_table_ref=f"page_{page_number}",
    )


def _deduplicate_by_code(chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    seen: set[tuple[str | None, str]] = set()
    deduped: list[ChunkRecord] = []
    for chunk in chunks:
        key = (chunk.alarm_code, chunk.equipment)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped
