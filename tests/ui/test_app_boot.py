from __future__ import annotations

from dataclasses import dataclass
import importlib
import sys
from types import SimpleNamespace

import gradio as gr

from faultpilot.ui.app import create_app


def test_create_app_returns_blocks(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_ui_runtime(_settings_path):
        captured["settings_path"] = _settings_path
        return SimpleNamespace(
            rag_service=object(),
            manufacturers=["All", "Fanuc"],
            equipment=["All", "A06B"],
        )

    monkeypatch.setattr("faultpilot.ui.app.build_ui_runtime", fake_build_ui_runtime)

    app = create_app()

    assert isinstance(app, gr.Blocks)
    assert captured["settings_path"].name == "settings.yaml"


@dataclass
class _CallRecord:
    fn: object
    inputs: list[object]
    outputs: list[object]


class _FakeButton:
    def __init__(self) -> None:
        self.calls: list[_CallRecord] = []

    def click(self, fn, inputs=None, outputs=None):
        self.calls.append(_CallRecord(fn=fn, inputs=inputs or [], outputs=outputs or []))


class _FakeTextbox:
    def __init__(self) -> None:
        self.calls: list[_CallRecord] = []

    def submit(self, fn, inputs=None, outputs=None):
        self.calls.append(_CallRecord(fn=fn, inputs=inputs or [], outputs=outputs or []))


class _FakeDemo:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_create_app_wires_submit_send_and_clear(monkeypatch) -> None:
    fake_runtime = SimpleNamespace(
        rag_service=object(),
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
    )
    fake_stream_result = iter([([("q", "a")], "trace", "sources", "")])
    captured_stream_call: dict[str, object] = {}

    chatbot = object()
    query_box = _FakeTextbox()
    manufacturer = object()
    equipment = object()
    send_button = _FakeButton()
    clear_button = _FakeButton()
    traceability_md = object()
    sources_md = object()
    fake_handles = SimpleNamespace(
        chatbot=chatbot,
        query_box=query_box,
        manufacturer=manufacturer,
        equipment=equipment,
        send_button=send_button,
        clear_button=clear_button,
        traceability_md=traceability_md,
        sources_md=sources_md,
        traceability_open_default=False,
    )
    fake_demo = _FakeDemo()
    captured_layout_call: dict[str, object] = {}

    captured_settings_path: dict[str, object] = {}

    def fake_build_ui_runtime(_settings_path):
        captured_settings_path["path"] = _settings_path
        return fake_runtime

    def fake_build_layout(*, title, manufacturers, equipment, traceability_open):
        captured_layout_call["title"] = title
        captured_layout_call["manufacturers"] = manufacturers
        captured_layout_call["equipment"] = equipment
        captured_layout_call["traceability_open"] = traceability_open
        return fake_demo, fake_handles

    def fake_stream_chat_response(**kwargs):
        captured_stream_call.update(kwargs)
        return fake_stream_result

    monkeypatch.setattr("faultpilot.ui.app.build_ui_runtime", fake_build_ui_runtime)
    monkeypatch.setattr("faultpilot.ui.app.build_layout", fake_build_layout)
    monkeypatch.setattr("faultpilot.ui.app.stream_chat_response", fake_stream_chat_response)

    demo = create_app()

    assert demo is fake_demo
    assert captured_layout_call["traceability_open"] is False
    assert captured_layout_call["manufacturers"] == fake_runtime.manufacturers
    assert captured_layout_call["equipment"] == fake_runtime.equipment

    assert len(send_button.calls) == 1
    assert len(query_box.calls) == 1
    assert len(clear_button.calls) == 1

    send_call = send_button.calls[0]
    submit_call = query_box.calls[0]
    clear_call = clear_button.calls[0]

    assert send_call.inputs == [query_box, chatbot, manufacturer, equipment]
    assert send_call.outputs == [chatbot, traceability_md, sources_md, query_box]
    assert submit_call.inputs == [query_box, chatbot, manufacturer, equipment]
    assert submit_call.outputs == [chatbot, traceability_md, sources_md, query_box]
    assert clear_call.outputs == [chatbot, traceability_md, sources_md, query_box]

    stream_result = send_call.fn(
        "AL-09",
        [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "state"},
        ],
        "Fanuc",
        "A06B",
    )
    assert stream_result is fake_stream_result
    assert captured_stream_call == {
        "rag_service": fake_runtime.rag_service,
        "query": "AL-09",
        "history": [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "state"},
        ],
        "manufacturer": "Fanuc",
        "equipment": "A06B",
    }
    assert captured_settings_path["path"].name == "settings.yaml"

    assert clear_call.fn() == ([], "", "", "")


def test_root_app_module_exports_demo(monkeypatch) -> None:
    sentinel = object()
    sys.modules.pop("app", None)
    monkeypatch.setattr("faultpilot.ui.app.create_app", lambda: sentinel)

    module = importlib.import_module("app")

    assert module.demo is sentinel


def test_create_app_uses_explicit_settings_path_from_non_repo_cwd(
    monkeypatch,
    tmp_path,
) -> None:
    explicit_settings = (tmp_path / "custom-settings.yaml").resolve()
    explicit_settings.write_text("ui:\n  title: FaultPilot\n", encoding="utf-8")

    fake_runtime = SimpleNamespace(
        rag_service=object(),
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
    )
    captured: dict[str, object] = {}

    def fake_build_ui_runtime(settings_path):
        captured["settings_path"] = settings_path
        return fake_runtime

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("faultpilot.ui.app.build_ui_runtime", fake_build_ui_runtime)
    monkeypatch.setattr("faultpilot.ui.app.build_layout", lambda **kwargs: (_FakeDemo(), SimpleNamespace(
        chatbot=object(),
        query_box=_FakeTextbox(),
        manufacturer=object(),
        equipment=object(),
        send_button=_FakeButton(),
        clear_button=_FakeButton(),
        traceability_md=object(),
        sources_md=object(),
        traceability_open_default=False,
    )))
    monkeypatch.setattr(
        "faultpilot.ui.app.stream_chat_response",
        lambda **kwargs: iter([([], "", "", "")]),
    )

    create_app(settings_path=explicit_settings)

    assert captured["settings_path"] == explicit_settings


def test_create_app_uses_env_settings_path_when_not_explicit(monkeypatch, tmp_path) -> None:
    env_settings = (tmp_path / "env-settings.yaml").resolve()
    env_settings.write_text("ui:\n  title: FaultPilot\n", encoding="utf-8")

    fake_runtime = SimpleNamespace(
        rag_service=object(),
        manufacturers=["All", "Fanuc"],
        equipment=["All", "A06B"],
    )
    captured: dict[str, object] = {}

    def fake_build_ui_runtime(settings_path):
        captured["settings_path"] = settings_path
        return fake_runtime

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FAULTPILOT_SETTINGS_PATH", str(env_settings))
    monkeypatch.setattr("faultpilot.ui.app.build_ui_runtime", fake_build_ui_runtime)
    monkeypatch.setattr("faultpilot.ui.app.build_layout", lambda **kwargs: (_FakeDemo(), SimpleNamespace(
        chatbot=object(),
        query_box=_FakeTextbox(),
        manufacturer=object(),
        equipment=object(),
        send_button=_FakeButton(),
        clear_button=_FakeButton(),
        traceability_md=object(),
        sources_md=object(),
        traceability_open_default=False,
    )))
    monkeypatch.setattr(
        "faultpilot.ui.app.stream_chat_response",
        lambda **kwargs: iter([([], "", "", "")]),
    )

    create_app()

    assert captured["settings_path"] == env_settings
