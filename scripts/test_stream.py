from __future__ import annotations

import argparse
import os
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterator

from faultpilot.ui.controllers import stream_chat_response
from faultpilot.ui.runtime import build_ui_runtime


def run_stream_probe(
    generator: Iterator[tuple[list[dict[str, str]], str, str, str]],
    max_first_chunk_ms: float,
    now_fn: Callable[[], float] = perf_counter,
    logger: Callable[[str], None] = print,
) -> int:
    started_at = now_fn()
    first_chunk_ms: float | None = None
    chunks_seen = 0

    for idx, state in enumerate(generator, start=1):
        if first_chunk_ms is None:
            first_chunk_ms = (now_fn() - started_at) * 1000.0
        chat, traceability, sources, _ = state
        last_message = chat[-1] if chat else {"content": ""}
        if isinstance(last_message, dict):
            assistant_text = str(last_message.get("content", ""))
        else:
            assistant_text = str(last_message[1]) if len(last_message) > 1 else ""
        logger(f"chunk={idx} assistant_len={len(assistant_text)}")
        if idx == 1:
            logger(traceability)
            logger(sources)
        chunks_seen += 1

    if chunks_seen == 0:
        logger("ERROR: stream produced no chunks")
        return 1

    logger(f"time_to_first_chunk_ms={first_chunk_ms:.1f}")
    if first_chunk_ms is not None and first_chunk_ms > max_first_chunk_ms:
        logger(
            "ERROR: first chunk exceeded threshold "
            f"({first_chunk_ms:.1f} ms > {max_first_chunk_ms:.1f} ms)"
        )
        return 1

    return 0


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
