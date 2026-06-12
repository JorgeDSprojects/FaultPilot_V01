"""Alarm-code parsing and normalization helpers."""

from __future__ import annotations

import re

_ALARM_CODE_VALUE_RE = re.compile(r"^AL[\s\-]*(\d{1,2})(?:[\s\-]*(\d{1,2}))?$", re.IGNORECASE)
_ALARM_CODE_SEARCH_RE = re.compile(r"\bAL[\s\-]*(\d{1,2})(?:[\s\-]*(\d{1,2}))?\b", re.IGNORECASE)


def normalize_alarm_code(value: str | None) -> str | None:
    """Normalize alarm-code strings to canonical AL-XX format when possible."""
    if value is None:
        return None

    normalized = value.strip().upper()
    if not normalized:
        return None

    match = _ALARM_CODE_VALUE_RE.match(normalized)
    if match is None:
        return normalized

    return _canonical_alarm_code(match.group(1), match.group(2))


def extract_alarm_code(text: str | None) -> str | None:
    """Extract first AL alarm code from free-form text."""
    if text is None:
        return None
    match = _ALARM_CODE_SEARCH_RE.search(text)
    if match is None:
        return None
    return _canonical_alarm_code(match.group(1), match.group(2))


def _canonical_alarm_code(primary: str, secondary: str | None) -> str:
    left = f"{int(primary):02d}"
    if secondary is None:
        return f"AL-{left}"
    right = f"{int(secondary):02d}"
    return f"AL-{left}-{right}"
