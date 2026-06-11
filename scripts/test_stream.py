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
        print(f"chunk={idx} assistant_len={len(chat[-1][1])}")
        if idx == 1:
            print(traceability)
            print(sources)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
