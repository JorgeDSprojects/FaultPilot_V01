"""Utilities to validate streamed UI output behavior."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Iterator


def run_stream_probe(
    generator: Iterator[tuple[list[dict[str, str]], str, str, str]],
    max_first_chunk_ms: float,
    now_fn: Callable[[], float] = perf_counter,
    logger: Callable[[str], None] = print,
) -> int:
    """Validate streamed output emits first chunk within threshold."""
    started_at = now_fn()
    first_chunk_ms: float | None = None
    chunks_seen = 0

    for idx, state in enumerate(generator, start=1):
        if first_chunk_ms is None:
            first_chunk_ms = (now_fn() - started_at) * 1000.0
        chat, traceability, sources, _ = state
        last_message = chat[-1] if chat else {"content": ""}
        assistant_text = str(last_message.get("content", ""))
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
