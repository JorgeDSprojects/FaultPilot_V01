from __future__ import annotations

import gradio as gr

from faultpilot.ui.layout import build_layout


def test_build_layout_has_traceability_collapsed_default() -> None:
    demo, handles = build_layout(
        title="FaultPilot",
        theme="soft",
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
        default_manufacturer="Fanuc",
        traceability_open=False,
        default_intent_mode="Auto",
    )

    assert isinstance(demo, gr.Blocks)
    assert handles.traceability_open_default is False


def test_build_layout_returns_core_components() -> None:
    _, handles = build_layout(
        title="FaultPilot",
        theme="soft",
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
        default_manufacturer="Fanuc",
        traceability_open=False,
        default_intent_mode="Auto",
    )

    assert isinstance(handles.chatbot, gr.Chatbot)
    assert isinstance(handles.query_box, gr.Textbox)
    assert isinstance(handles.manufacturer, gr.Dropdown)
    assert isinstance(handles.equipment, gr.Dropdown)
    assert isinstance(handles.send_button, gr.Button)
    assert isinstance(handles.clear_button, gr.Button)
    assert isinstance(handles.intent_mode, gr.Dropdown)
    assert isinstance(handles.traceability_md, gr.Markdown)
    assert isinstance(handles.sources_md, gr.Markdown)
