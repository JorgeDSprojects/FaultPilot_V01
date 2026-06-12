from __future__ import annotations

from dataclasses import dataclass, field

import gradio as gr
import pytest

from faultpilot.rag.openai_client import OpenAiTextGenerationError
from faultpilot.rag.schemas import Citation, RagAnswer, TraceabilitySnapshot
from faultpilot.ui.controllers import stream_chat_response


@dataclass
class _StubRagService:
    calls: list[tuple[str, object, object]] = field(default_factory=list)
    error: Exception | None = None
    answer_text: str = (
        "Line one. Line two. Source [ac_spindle_alarm_list.pdf:p.2] "
        "Additional details for chunked streaming updates."
    )

    def answer(self, query: str, filters=None, intent_override=None) -> RagAnswer:
        self.calls.append((query, filters, intent_override))
        if self.error is not None:
            raise self.error
        return RagAnswer(
            intent="alarm_lookup",
            answer_text=self.answer_text,
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
        intent_mode="Auto",
        rag_service_factory=None,
        api_key="sk-test",
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
    assert "Top grounded context" in first[1]
    assert "ac_spindle_alarm_list.pdf" in first[1]
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
        intent_mode="Auto",
        rag_service_factory=None,
        api_key="sk-test",
    )

    next(generator)

    _, filters, intent_override = rag_service.calls[0]
    assert filters.manufacturer is None
    assert filters.equipment is None
    assert intent_override is None


def test_stream_chat_response_passes_manual_intent_override() -> None:
    rag_service = _StubRagService()
    generator = stream_chat_response(
        rag_service=rag_service,
        query="AL-09",
        history=[],
        manufacturer="All",
        equipment="All",
        intent_mode="programming",
        rag_service_factory=None,
        api_key="sk-test",
    )

    next(generator)

    _, _, intent_override = rag_service.calls[0]
    assert intent_override == "programming"


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
        intent_mode="Auto",
        rag_service_factory=None,
        api_key=None,
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
        intent_mode="Auto",
        rag_service_factory=None,
        api_key="sk-test",
    )

    first = next(generator)
    payload = first[0]
    chatbot = gr.Chatbot()

    postprocessed = chatbot.postprocess(payload)

    assert postprocessed is not None


def test_stream_chat_response_missing_api_key_returns_guidance_without_backend_calls() -> None:
    rag_service = _StubRagService()
    factory_calls: list[str] = []

    def _factory(api_key: str) -> _StubRagService:
        factory_calls.append(api_key)
        return _StubRagService()

    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        rag_service_factory=_factory,
        api_key="   ",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert first[0][0] == {"role": "user", "content": "What is AL-09?"}
    assert first[0][1]["role"] == "assistant"
    assert "openai api key" in first[0][1]["content"].lower()
    assert "provide" in first[0][1]["content"].lower()
    assert first[1].startswith("### Traceability")
    assert "missing_api_key" in first[1]
    assert first[2].startswith("### Sources")
    assert "No grounded sources available" in first[2]
    assert first[3] == ""
    assert rag_service.calls == []
    assert factory_calls == []


def test_stream_chat_response_uses_factory_service_when_api_key_is_present() -> None:
    baseline_service = _StubRagService()
    provider_service = _StubRagService(answer_text="Provider answer.")
    captured_keys: list[str] = []

    def _factory(api_key: str) -> _StubRagService:
        captured_keys.append(api_key)
        return provider_service

    generator = stream_chat_response(
        rag_service=baseline_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        rag_service_factory=_factory,
        api_key="  sk-test  ",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert captured_keys == ["sk-test"]
    assert baseline_service.calls == []
    assert len(provider_service.calls) == 1
    assert first[0][1]["content"] == "Provider answer."


def test_stream_chat_response_factory_error_returns_stable_degraded_payload() -> None:
    rag_service = _StubRagService()

    def _factory(_api_key: str) -> _StubRagService:
        raise RuntimeError("factory exploded")

    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        rag_service_factory=_factory,
        api_key="sk-test",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert first[0][0] == {"role": "user", "content": "What is AL-09?"}
    assert first[0][1]["role"] == "assistant"
    assert "degraded response" in first[0][1]["content"].lower()
    assert "backend_error" in first[1]
    assert "Degraded" in first[1]
    assert "No grounded sources available" in first[2]
    assert first[3] == ""
    assert rag_service.calls == []


def test_stream_chat_response_openai_error_returns_stable_degraded_payload() -> None:
    rag_service = _StubRagService(error=OpenAiTextGenerationError("invalid API key"))
    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        rag_service_factory=None,
        api_key="sk-test",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert first[0][0] == {"role": "user", "content": "What is AL-09?"}
    assert first[0][1]["role"] == "assistant"
    assert "openai" in first[0][1]["content"].lower()
    assert "provider_error" in first[1]
    assert "Degraded" in first[1]
    assert "No grounded sources available" in first[2]
    assert first[3] == ""


def test_stream_chat_response_backend_error_returns_stable_degraded_payload() -> None:
    rag_service = _StubRagService(error=RuntimeError("backend exploded"))
    generator = stream_chat_response(
        rag_service=rag_service,
        query="What is AL-09?",
        history=[],
        manufacturer="Fanuc",
        equipment="A06B",
        intent_mode="Auto",
        rag_service_factory=None,
        api_key="sk-test",
    )

    first = next(generator)

    with pytest.raises(StopIteration):
        next(generator)

    assert first[0][0] == {"role": "user", "content": "What is AL-09?"}
    assert first[0][1]["role"] == "assistant"
    assert "degraded response" in first[0][1]["content"].lower()
    assert "backend_error" in first[1]
    assert "Degraded" in first[1]
    assert "No grounded sources available" in first[2]
    assert first[3] == ""
