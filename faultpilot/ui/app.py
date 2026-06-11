"""Gradio app assembly and callback wiring."""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.layout import build_layout
from faultpilot.ui.runtime import build_ui_runtime


def create_app() -> gr.Blocks:
    runtime = build_ui_runtime(Path("config/settings.yaml"))
    demo, handles = build_layout(
        title="FaultPilot - OT Troubleshooting Assistant",
        manufacturers=runtime.manufacturers,
        equipment=runtime.equipment,
        traceability_open=False,
    )

    def _on_submit(
        query: str,
        history: list[tuple[str, str]] | None,
        manufacturer: str | None,
        equipment: str | None,
    ):
        return stream_chat_response(
            rag_service=runtime.rag_service,
            query=query,
            history=history or [],
            manufacturer=manufacturer,
            equipment=equipment,
        )

    common_inputs = [
        handles.query_box,
        handles.chatbot,
        handles.manufacturer,
        handles.equipment,
    ]
    common_outputs = [
        handles.chatbot,
        handles.traceability_md,
        handles.sources_md,
        handles.query_box,
    ]

    with demo:
        handles.send_button.click(_on_submit, inputs=common_inputs, outputs=common_outputs)
        handles.query_box.submit(_on_submit, inputs=common_inputs, outputs=common_outputs)
        handles.clear_button.click(
            lambda: ([], "", "", ""),
            outputs=common_outputs,
        )

    return demo
