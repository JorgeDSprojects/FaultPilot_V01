"""Chunk loaders for hybrid retrieval indexes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from faultpilot.retrieval.schemas import RetrievedChunk


def load_chunks(chunks_dir: Path) -> list[RetrievedChunk]:
    """Load all chunk JSONL files from processed directory."""
    if not chunks_dir.exists():
        return []

    chunks: list[RetrievedChunk] = []
    for file_path in sorted(chunks_dir.glob("*_chunks.jsonl")):
        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                row = json.loads(line)
                content = str(row["content"])
                alarm_code = row.get("alarm_code")
                equipment = str(row["equipment"])
                source_doc = str(row["source_doc"])
                page = int(row["page"])
                chunk_id = build_chunk_id(
                    source_doc=source_doc,
                    page=page,
                    equipment=equipment,
                    alarm_code=alarm_code,
                    content=content,
                )
                chunks.append(
                    RetrievedChunk(
                        chunk_id=chunk_id,
                        content=content,
                        alarm_code=alarm_code,
                        equipment=equipment,
                        manufacturer=str(row["manufacturer"]),
                        source_doc=source_doc,
                        page=page,
                        language=row.get("language"),
                    )
                )
    return chunks


def build_chunk_id(
    source_doc: str,
    page: int,
    equipment: str,
    alarm_code: str | None,
    content: str,
) -> str:
    """Build deterministic chunk id from provenance and content."""
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    code = alarm_code or "NA"
    equipment_digest = hashlib.sha1(equipment.encode("utf-8")).hexdigest()[:8]
    return f"{source_doc}:{page}:{equipment_digest}:{code}:{digest}"
