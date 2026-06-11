"""CLI commands for Hito 2 retrieval indexing and search."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from faultpilot.retrieval.bm25_index import build_bm25_index, save_bm25_index
from faultpilot.retrieval.config import FaultPilotSettings, load_settings
from faultpilot.retrieval.loaders import load_chunks
from faultpilot.retrieval.reranker import CrossEncoderReranker
from faultpilot.retrieval.schemas import RetrievalFilters
from faultpilot.retrieval.service import HybridRetrievalService
from faultpilot.retrieval.vector_index import build_dense_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="faultpilot-retrieval")
    parser.add_argument(
        "--settings",
        default="config/settings.yaml",
        help="Path to settings YAML file.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    index_cmd = sub.add_parser("index", help="Build sparse/dense retrieval artifacts.")
    index_cmd.add_argument("--dry-run", action="store_true", help="Validate configuration only.")

    search_cmd = sub.add_parser("search", help="Run one hybrid retrieval query.")
    search_cmd.add_argument("--query", required=True, help="Search query text.")
    search_cmd.add_argument("--route", default="troubleshooting", help="Route profile to apply.")
    search_cmd.add_argument("--manufacturer", default=None, help="Optional manufacturer filter.")
    search_cmd.add_argument("--equipment", default=None, help="Optional equipment filter.")
    search_cmd.add_argument("--language", default=None, help="Optional language filter.")
    search_cmd.add_argument("--dry-run", action="store_true", help="Validate arguments only.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = load_settings(Path(args.settings))

    if args.command == "index":
        return _run_index(settings=settings, dry_run=args.dry_run)
    if args.command == "search":
        return _run_search(
            settings=settings,
            query=args.query,
            route=args.route,
            manufacturer=args.manufacturer,
            equipment=args.equipment,
            language=args.language,
            dry_run=args.dry_run,
        )
    parser.error(f"Unsupported command: {args.command}")
    return 2


def _run_index(settings: FaultPilotSettings, dry_run: bool) -> int:
    if dry_run:
        return 0

    paths = settings.raw["paths"]
    chunks = load_chunks(Path(paths["chunks_jsonl_dir"]))
    sparse = build_bm25_index(chunks)
    save_bm25_index(Path(paths["bm25_index"]), sparse)
    build_dense_index(chunks, persist_dir=Path(paths["chroma_db"]))
    return 0


def _run_search(
    settings: FaultPilotSettings,
    query: str,
    route: str,
    manufacturer: str | None,
    equipment: str | None,
    language: str | None,
    dry_run: bool,
) -> int:
    if dry_run:
        return 0

    paths = settings.raw["paths"]
    chunks = load_chunks(Path(paths["chunks_jsonl_dir"]))
    sparse = build_bm25_index(chunks)
    dense = build_dense_index(chunks, persist_dir=Path(paths["chroma_db"]))
    reranker = CrossEncoderReranker(model_name=settings.raw["reranker"]["model_name"])
    service = HybridRetrievalService(settings, sparse, dense, reranker)

    filters = RetrievalFilters(
        manufacturer=manufacturer,
        equipment=equipment,
        language=language,
    )
    result = service.hybrid_retrieve(query=query, route=route, filters=filters)
    for hit in result.hits:
        print(f"[{hit.source_doc}:{hit.page}] {hit.content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
