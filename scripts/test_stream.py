from __future__ import annotations

from pathlib import Path

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.runtime import build_ui_runtime


def main() -> int:
    runtime = build_ui_runtime(Path("config/settings.yaml"))
    generator = stream_chat_response(
        rag_service=runtime.rag_service,
        query="AL-09",
        history=[],
        manufacturer="All",
        equipment="All",
    )

    for idx, state in enumerate(generator, start=1):
        chat, traceability, sources, _ = state
        last_message = chat[-1] if chat else {"content": ""}
        if isinstance(last_message, dict):
            assistant_text = str(last_message.get("content", ""))
        else:
            assistant_text = str(last_message[1]) if len(last_message) > 1 else ""
        print(f"chunk={idx} assistant_len={len(assistant_text)}")
        if idx == 1:
            print(traceability)
            print(sources)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
