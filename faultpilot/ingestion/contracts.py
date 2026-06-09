"""Data contracts and normalization helpers for ingestion chunks."""

from __future__ import annotations

from dataclasses import dataclass


def normalize_alarm_code(value: str | None) -> str | None:
    """Normalize alarm code casing and whitespace."""
    if value is None:
        return None

    normalized = value.strip().upper()
    return normalized or None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


@dataclass(frozen=True)
class ChunkRecord:
    """Canonical chunk record for PDF-derived troubleshooting content."""

    content: str
    alarm_code: str | None
    equipment: str
    manufacturer: str
    source_doc: str
    page: int
    category: str | None = None
    description: str | None = None
    language: str | None = None
    raw_table_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", _require_text(self.content, "content"))
        object.__setattr__(self, "alarm_code", normalize_alarm_code(self.alarm_code))
        object.__setattr__(self, "equipment", _require_text(self.equipment, "equipment"))
        object.__setattr__(
            self,
            "manufacturer",
            _require_text(self.manufacturer, "manufacturer"),
        )
        object.__setattr__(self, "source_doc", _require_text(self.source_doc, "source_doc"))

        if self.page <= 0:
            raise ValueError("page must be greater than 0")

        object.__setattr__(self, "category", _normalize_text(self.category))
        object.__setattr__(self, "description", _normalize_text(self.description))
        object.__setattr__(self, "language", _normalize_text(self.language))
        object.__setattr__(self, "raw_table_ref", _normalize_text(self.raw_table_ref))

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize the chunk to JSON-compatible dictionary."""
        return {
            "content": self.content,
            "alarm_code": self.alarm_code,
            "equipment": self.equipment,
            "manufacturer": self.manufacturer,
            "source_doc": self.source_doc,
            "page": self.page,
            "category": self.category,
            "description": self.description,
            "language": self.language,
            "raw_table_ref": self.raw_table_ref,
        }


def _require_text(value: str, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized
