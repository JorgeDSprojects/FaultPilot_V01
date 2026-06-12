"""Gradio app assembly and callback wiring."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import gradio as gr

from faultpilot.ui.controllers import ChatMessage, stream_chat_response
from faultpilot.ui.layout import build_layout
from faultpilot.ui.runtime import build_ui_runtime


SETTINGS_PATH_ENV = "FAULTPILOT_SETTINGS_PATH"
SERVER_PORT_ATTR = "faultpilot_server_port"
THEME_ATTR = "faultpilot_theme"


def resolve_settings_path(settings_path: str | Path | None = None) -> Path:
    if settings_path is not None:
        return Path(settings_path).expanduser().resolve()

    env_value = os.getenv(SETTINGS_PATH_ENV)
    if env_value:
        return Path(env_value).expanduser().resolve()

    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "config" / "settings.yaml").resolve()


def create_app(settings_path: str | Path | None = None) -> gr.Blocks:
    runtime = build_ui_runtime(resolve_settings_path(settings_path))
    demo, handles = build_layout(
        title=runtime.ui_settings.title,
        theme=runtime.ui_settings.theme,
        manufacturers=runtime.manufacturers,
        equipment=runtime.equipment,
        default_manufacturer=runtime.ui_settings.default_manufacturer,
        traceability_open=runtime.ui_settings.traceability_open_default,
        default_intent_mode=runtime.ui_settings.default_intent_mode,
    )
    setattr(demo, SERVER_PORT_ATTR, runtime.ui_settings.server_port)
    setattr(demo, THEME_ATTR, runtime.ui_settings.theme)

    def _on_submit(
        query: str,
        history: list[ChatMessage] | None,
        manufacturer: str | None,
        equipment: str | None,
        intent_mode: str | None,
        api_key: str | None,
    ) -> Iterator[tuple[list[ChatMessage], str, str, str]]:
        yield from stream_chat_response(
            rag_service=runtime.rag_service,
            rag_service_factory=runtime.rag_service_factory,
            query=query,
            history=history or [],
            manufacturer=manufacturer,
            equipment=equipment,
            intent_mode=intent_mode,
            api_key=api_key,
        )

    common_inputs = [
        handles.query_box,
        handles.chatbot,
        handles.manufacturer,
        handles.equipment,
        handles.intent_mode,
        handles.api_key_box,
    ]
    common_outputs = [
        handles.chatbot,
        handles.traceability_md,
        handles.sources_md,
        handles.query_box,
    ]
    clear_outputs = [*common_outputs, handles.api_key_box]

    with demo:
        handles.send_button.click(_on_submit, inputs=common_inputs, outputs=common_outputs)
        handles.query_box.submit(_on_submit, inputs=common_inputs, outputs=common_outputs)
        handles.clear_button.click(
            lambda: ([], "", "", "", ""),
            outputs=clear_outputs,
        )

    return demo
