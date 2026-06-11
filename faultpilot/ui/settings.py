"""Typed UI settings extraction from raw config payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_TITLE = "FaultPilot - OT Troubleshooting Assistant"
DEFAULT_SERVER_PORT = 7860
DEFAULT_THEME = "soft"
DEFAULT_MANUFACTURER = "All"


@dataclass(frozen=True)
class UiSettings:
    title: str
    server_port: int
    theme: str
    default_manufacturer: str
    traceability_open_default: bool


def read_ui_settings(raw: dict[str, Any]) -> UiSettings:
    ui = raw.get("ui")
    if not isinstance(ui, dict):
        ui = {}

    title = ui.get("title") or DEFAULT_TITLE
    return UiSettings(
        title=str(title),
        server_port=int(ui.get("server_port", DEFAULT_SERVER_PORT)),
        theme=str(ui.get("theme", DEFAULT_THEME)),
        default_manufacturer=str(ui.get("default_manufacturer", DEFAULT_MANUFACTURER)),
        traceability_open_default=bool(ui.get("traceability_open_default", False)),
    )
