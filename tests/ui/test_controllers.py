from __future__ import annotations

from dataclasses import dataclass, field

import gradio as gr
import pytest

from faultpilot.rag.schemas import Citation, RagAnswer, TraceabilitySnapshot
from faultpilot.ui.controllers import stream_chat_response


@dataclass
class _StubRagService:
    calls: list[tuple[str, object]] = field(default_factory=list)

    def answer(self, query: str, filters=None) -> RagAnswer:
        self.calls.append((query, filters))
        return RagAnswer(
            intent="alarm_lookup",
            answer_text=(
                "Line one. Line two. Source [ac_spindle_alarm_list.pdf:p.2] "
                "Additional details for chunked streaming updates."
            ),
            citations=(Citation(source_doc="ac_spindle_alarm_list.pdf", page=2),),
            degraded_mode=False,
            warnings=(),
            traceability=TraceabilitySnapshot(
                routing_source="local",
                intent_confidence=0.92,
                degraded_mode=False,
                warning=None,
                timing_ms={"routing": 1.0, "retrieval": 2.0, "generation": 3.0},
            ),
        )


def test_stream_chat_response_yields_independent_incremental_snapshots() -> None:
    rag_service = _StubRagService()
    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
    )

    first = next(generator)
    first_chat = first[0]
    first_text = first_chat[1]["content"]

    second = next(generator)
    second_chat = second[0]
    second_text = second_chat[1]["content"]

    assert len(first) == 4
    assert len(first_chat) == 2
    assert first_chat[0]["role"] == "user"
    assert first_chat[0]["content"] == "What is AL-09?"
    assert first_chat[1]["role"] == "assistant"
    assert len(first_text) > 0
    assert second_text.startswith(first_text)
    assert len(second_text) > len(first_text)
    assert first_chat is not second_chat
    assert first_chat[1]["content"] == first_text
    assert first[1] == second[1]
    assert first[2] == second[2]
    assert first[1].startswith("### Traceability")
    assert first[2].startswith("### Sources")
    assert first[3] == ""

    lengths = [len(first_text), len(second_text)]
    lengths.extend(len(state[0][1]["content"]) for state in generator)
    assert lengths == sorted(lengths)
    assert len(set(lengths)) == len(lengths)
    assert len(rag_service.calls) == 1


def test_stream_chat_response_normalizes_all_filters_to_none() -> None:
    rag_service = _StubRagService()
    generator = stream_chat_response(
        rag_service=rag_service,
        query="AL-09",
        history=[],
        manufacturer="All",
        equipment="  All  ",
    )

    next(generator)

    _, filters = rag_service.calls[0]
    assert filters.manufacturer is None
    assert filters.equipment is None


def test_stream_chat_response_empty_query_returns_validation_state() -> None:
    rag_service = _StubRagService()
    history = [
        {"role": "user", "content": "old q"},
        {"role": "assistant", "content": "old a"},
    ]
    generator = stream_chat_response(
        rag_service=rag_service,
        query="   ",
        history=history,
        manufacturer="Fanuc",
        equipment="A06B",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert first[0] == history
    assert "Empty query" in first[1]
    assert first[2].startswith("### Sources")
    assert first[3] == ""
    assert rag_service.calls == []


def test_stream_chat_response_payload_is_chatbot_postprocess_compatible() -> None:
    rag_service = _StubRagService()
    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
    )

    first = next(generator)
    payload = first[0]
    chatbot = gr.Chatbot()

    postprocessed = chatbot.postprocess(payload)

    assert postprocessed is not None
