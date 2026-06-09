"""Parser for Bosch CC220/320 error manual."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from faultpilot.ingestion.contracts import ChunkRecord

BOSCH_MANUAL_FILENAME = "Error_messages_CC_220107007331804.pdf"

_CODE_PATTERN = re.compile(r"\b(\d{3,5})\b")
_CONTROL_CHARS_PATTERN = re.compile(r"\(cid:\d+\)")
_NOISE_CLUSTER_PATTERN = re.compile(r"(?:\bÁ\b\s*){2,}")
_NOISE_REPEAT_PATTERN = re.compile(r"Á{2,}")


def parse_bosch_pdf(pdf_path: Path) -> tuple[list[ChunkRecord], list[dict[str, int | str]]]:
    """Parse Bosch PDF into chunks and list of low-confidence pages."""
    records: list[ChunkRecord] = []
    warnings: list[dict[str, int | str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            if not tables:
                continue

            parsed_any = False
            for table_index, table in enumerate(tables, start=1):
                if not _is_error_cause_table(table):
                    continue

                for row_index, row in enumerate(table[1:], start=1):
                    chunk = parse_bosch_error_row(
                        row=row,
                        page_number=page_number,
                        row_index=row_index,
                        table_index=table_index,
                    )
                    if chunk is not None:
                        records.append(chunk)
                        parsed_any = True

            if not parsed_any and page_number >= 40:
                warnings.append(
                    {
                        "page": page_number,
                        "reason": "No parseable ERROR CAUSE/REMEDY rows",
                    }
                )

    return records, warnings


def parse_bosch_error_row(
    row: list[str | None],
    page_number: int,
    row_index: int,
    table_index: int | None = None,
) -> ChunkRecord | None:
    """Parse one Bosch table row into a ChunkRecord."""
    if len(row) < 2:
        return None

    cause_cell = _clean_text(row[0])
    remedy_cell = _clean_text(row[1])

    if not cause_cell and not remedy_cell:
        return None

    alarm_code, title = _extract_code_and_title(cause_cell)
    if not title:
        title = cause_cell

    content_parts = [part for part in [title, remedy_cell] if part]
    if not content_parts:
        return None

    description = cause_cell if cause_cell else None
    raw_ref = f"table_{table_index}_row_{row_index}" if table_index is not None else f"row_{row_index}"
    return ChunkRecord(
        content="\n".join(content_parts),
        alarm_code=alarm_code,
        equipment="CC220/320",
        manufacturer="Bosch",
        source_doc=BOSCH_MANUAL_FILENAME,
        page=page_number,
        category="error",
        description=description,
        language="en",
        raw_table_ref=raw_ref,
    )


def _extract_code_and_title(cause_cell: str) -> tuple[str | None, str]:
    code_match = _CODE_PATTERN.search(cause_cell)
    if code_match is None:
        title = cause_cell.lstrip("> ")
        return None, title

    alarm_code = code_match.group(1)
    title = cause_cell[code_match.start() :]
    return alarm_code, title


def _is_error_cause_table(table: list[list[str | None]]) -> bool:
    if not table:
        return False
    header = " ".join(_clean_text(cell) for cell in table[0] if cell)
    return "ERROR CAUSE" in header.upper() and "ERROR REMEDY" in header.upper()


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = _CONTROL_CHARS_PATTERN.sub(" ", value)
    cleaned = cleaned.replace("�", " ")
    cleaned = cleaned.replace("Á", " ")
    cleaned = cleaned.replace("cid", " ")
    cleaned = _NOISE_CLUSTER_PATTERN.sub(" ", cleaned)
    cleaned = _NOISE_REPEAT_PATTERN.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()
