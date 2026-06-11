from __future__ import annotations

from faultpilot.ui.settings import UiSettings, read_ui_settings


def test_read_ui_settings_applies_defaults() -> None:
    raw = {"ui": {"title": "FaultPilot"}}

    result = read_ui_settings(raw)

    assert isinstance(result, UiSettings)
    assert result.title == "FaultPilot"
    assert result.server_port == 7860
    assert result.theme == "soft"
    assert result.default_manufacturer == "All"
    assert result.default_intent_mode == "Auto"
    assert result.traceability_open_default is False


def test_read_ui_settings_uses_default_title_when_missing() -> None:
    raw = {"ui": {}}

    result = read_ui_settings(raw)

    assert result.title == "FaultPilot - OT Troubleshooting Assistant"
