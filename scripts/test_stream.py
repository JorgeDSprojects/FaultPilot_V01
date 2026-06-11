from __future__ import annotations

import argparse
import os
from pathlib import Path

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.runtime import build_ui_runtime
from faultpilot.ui.stream_probe import run_stream_probe


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe UI streaming latency and chunk output")
    parser.add_argument(
        "--max-first-chunk-ms",
        type=float,
        default=float(os.getenv("FAULTPILOT_MAX_FIRST_CHUNK_MS", "5000")),
        help="Fail when time-to-first-chunk exceeds this threshold in milliseconds",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runtime = build_ui_runtime(Path("config/settings.yaml"))
    generator = stream_chat_response(
        rag_service=runtime.rag_service,
        query="AL-09",
        history=[],
        manufacturer="All",
        equipment="All",
        intent_mode="Auto",
    )

    return run_stream_probe(generator, max_first_chunk_ms=args.max_first_chunk_ms)


if __name__ == "__main__":
    raise SystemExit(main())
