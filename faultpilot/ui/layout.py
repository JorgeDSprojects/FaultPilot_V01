"""Gradio layout composition for FaultPilot UI."""

from __future__ import annotations

from dataclasses import dataclass

import gradio as gr


TRACEABILITY_PLACEHOLDER = "### Traceability\n- Waiting for query"
SOURCES_PLACEHOLDER = "### Sources\n- Waiting for query"


@dataclass(frozen=True)
class LayoutHandles:
    chatbot: gr.Chatbot
    query_box: gr.Textbox
    manufacturer: gr.Dropdown
    equipment: gr.Dropdown
    send_button: gr.Button
    clear_button: gr.Button
    traceability_md: gr.Markdown
    sources_md: gr.Markdown
    traceability_open_default: bool


def _default_choice(options: list[str]) -> str | None:
    if not options:
        return None
    return options[0]


def build_layout(
    title: str,
    manufacturers: list[str],
    equipment: list[str],
    traceability_open: bool,
) -> tuple[gr.Blocks, LayoutHandles]:
    with gr.Blocks(title=title) as demo:
        gr.Markdown(f"## {title}\nIndustrial troubleshooting assistant")

        with gr.Row():
            with gr.Column(scale=7):
                chatbot = gr.Chatbot(label="Conversation", height=520)
                query_box = gr.Textbox(
                    label="Query",
                    placeholder="Type your OT question...",
                    lines=2,
                )
                with gr.Row():
                    send_button = gr.Button("Send", variant="primary")
                    clear_button = gr.Button("Clear")
                with gr.Row():
                    manufacturer_dd = gr.Dropdown(
                        choices=manufacturers,
                        value=_default_choice(manufacturers),
                        label="Manufacturer",
                    )
                    equipment_dd = gr.Dropdown(
                        choices=equipment,
                        value=_default_choice(equipment),
                        label="Equipment",
                    )

            with gr.Column(scale=3):
                with gr.Accordion("Traceability", open=traceability_open):
                    traceability_md = gr.Markdown(TRACEABILITY_PLACEHOLDER)
                    sources_md = gr.Markdown(SOURCES_PLACEHOLDER)

    handles = LayoutHandles(
        chatbot=chatbot,
        query_box=query_box,
        manufacturer=manufacturer_dd,
        equipment=equipment_dd,
        send_button=send_button,
        clear_button=clear_button,
        traceability_md=traceability_md,
        sources_md=sources_md,
        traceability_open_default=traceability_open,
    )
    return demo, handles
