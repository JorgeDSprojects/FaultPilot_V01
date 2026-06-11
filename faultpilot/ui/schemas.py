"""Schemas for UI inputs and state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiQuery:
    """Normalized query payload coming from UI controls."""

    text: str
    manufacturer: str | None = None
    equipment: str | None = None
