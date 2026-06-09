"""CLI entrypoint for ingestion workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from faultpilot.ingestion.pipeline import run_ingestion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="faultpilot-ingest")
    parser.add_argument(
        "--documents",
        nargs="+",
        choices=["bosch", "fanuc"],
        default=["bosch", "fanuc"],
        help="Documents to ingest.",
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Directory containing source PDF manuals.",
    )
    parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory where JSONL artifacts are written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate arguments and paths without running parsers.",
    )
    parser.add_argument(
        "--parser-version",
        default="0.1.0",
        help="Parser version written to manifest metadata.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)

    if not raw_dir.exists():
        parser.error(f"Raw directory does not exist: {raw_dir}")

    processed_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        return 0

    run_ingestion(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        documents=args.documents,
        parser_version=args.parser_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
