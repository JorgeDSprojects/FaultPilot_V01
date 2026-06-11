"""Runtime wiring for Gradio UI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from faultpilot.rag.generator import RagAnswerGenerator
from faultpilot.rag.graph import build_rag_graph
from faultpilot.rag.postprocess import CitationGuard
from faultpilot.rag.service import RagPipelineService
from faultpilot.retrieval.bm25_index import build_bm25_index, load_bm25_index
from faultpilot.retrieval.config import load_settings
from faultpilot.retrieval.loaders import load_chunks
from faultpilot.retrieval.reranker import CrossEncoderReranker
from faultpilot.retrieval.schemas import RetrievedChunk
from faultpilot.retrieval.service import HybridRetrievalService
from faultpilot.retrieval.vector_index import build_dense_index
from faultpilot.routing.intent_router import IntentRouter
from faultpilot.routing.local_classifier import LocalIntentClassifier
from faultpilot.routing.schemas import IntentClassification


class _FallbackLlmClassifier:
    """Deterministic fallback classifier used by UI runtime."""

    def classify(self, query: str) -> IntentClassification:
        return IntentClassification(
            intent="troubleshooting",
            confidence=0.5,
            source="fallback",
            evidence="fallback_ui_classifier",
        )


@dataclass(frozen=True)
class UiRuntime:
    rag_service: RagPipelineService
    manufacturers: list[str]
    equipment: list[str]


def collect_filter_options(chunks: Iterable[RetrievedChunk]) -> tuple[list[str], list[str]]:
    manufacturers = _with_all_prefix(chunk.manufacturer for chunk in chunks)
    equipment = _with_all_prefix(chunk.equipment for chunk in chunks)
    return manufacturers, equipment


def build_ui_runtime(settings_path: Path) -> UiRuntime:
    settings = load_settings(settings_path)
    raw_paths = settings.raw["paths"]
    chunks = load_chunks(Path(raw_paths["chunks_jsonl_dir"]))
    manufacturers, equipment = collect_filter_options(chunks)

    bm25_path = Path(raw_paths["bm25_index"])
    sparse = load_bm25_index(bm25_path) if bm25_path.exists() else build_bm25_index(chunks)

    dense = build_dense_index(
        chunks,
        persist_dir=Path(raw_paths["chroma_db"]),
        model_name=str(settings.raw["embeddings"]["model_name"]),
    )
    reranker = CrossEncoderReranker(model_name=str(settings.raw["reranker"]["model_name"]))
    retrieval = HybridRetrievalService(
        settings=settings,
        sparse_retriever=sparse,
        dense_retriever=dense,
        reranker=reranker,
    )

    router = IntentRouter(
        local_classifier=LocalIntentClassifier(),
        llm_classifier=_FallbackLlmClassifier(),
        ambiguous_threshold=float(settings.raw["routing"]["ambiguous_threshold"]),
        local_first=bool(settings.raw["routing"]["local_first"]),
    )
    generator = RagAnswerGenerator(client=None)
    graph = build_rag_graph(
        router=router,
        retrieval_service=retrieval,
        generator=generator,
        max_context_chars=int(settings.raw["rag"]["max_context_chars"]),
        citation_guard=CitationGuard(
            max_regeneration_attempts=int(settings.raw["rag"]["max_regeneration_attempts"])
        ),
    )

    return UiRuntime(
        rag_service=RagPipelineService(graph),
        manufacturers=manufacturers,
        equipment=equipment,
    )


def _with_all_prefix(values: Iterable[str]) -> list[str]:
    unique_sorted = sorted({value.strip() for value in values if value and value.strip()})
    return ["All", *unique_sorted]
