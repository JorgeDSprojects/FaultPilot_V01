from __future__ import annotations

from scripts.test_stream import run_stream_probe


def _state() -> tuple[list[dict[str, str]], str, str, str]:
    return ([{"role": "assistant", "content": "partial"}], "trace", "sources", "")


def test_run_stream_probe_returns_zero_when_first_chunk_within_threshold() -> None:
    clock = iter([10.0, 10.03, 10.06])

    exit_code = run_stream_probe(
        iter([_state(), _state()]),
        max_first_chunk_ms=100.0,
        now_fn=lambda: next(clock),
        logger=lambda _: None,
    )

    assert exit_code == 0


def test_run_stream_probe_fails_when_generator_yields_no_chunks() -> None:
    exit_code = run_stream_probe(
        iter(()),
        max_first_chunk_ms=100.0,
        now_fn=lambda: 0.0,
        logger=lambda _: None,
    )

    assert exit_code == 1


def test_run_stream_probe_fails_when_first_chunk_exceeds_threshold() -> None:
    clock = iter([0.0, 0.25])

    exit_code = run_stream_probe(
        iter([_state()]),
        max_first_chunk_ms=100.0,
        now_fn=lambda: next(clock),
        logger=lambda _: None,
    )

    assert exit_code == 1
