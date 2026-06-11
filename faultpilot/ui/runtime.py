"""Runtime wiring for Gradio UI dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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
class UiRuntimeConfig:
    chunks_jsonl_dir: Path
    bm25_index: Path
    chroma_db: Path
    embeddings_model_name: str
    reranker_model_name: str
    routing_ambiguous_threshold: float
    routing_local_first: bool
    rag_max_context_chars: int
    rag_max_regeneration_attempts: int

    @classmethod
    def from_settings(cls, raw_settings: dict[str, Any]) -> UiRuntimeConfig:
        paths = raw_settings["paths"]
        embeddings = raw_settings["embeddings"]
        reranker = raw_settings["reranker"]
        routing = raw_settings["routing"]
        rag = raw_settings["rag"]
        return cls(
            chunks_jsonl_dir=Path(paths["chunks_jsonl_dir"]),
            bm25_index=Path(paths["bm25_index"]),
            chroma_db=Path(paths["chroma_db"]),
            embeddings_model_name=str(embeddings["model_name"]),
            reranker_model_name=str(reranker["model_name"]),
            routing_ambiguous_threshold=float(routing["ambiguous_threshold"]),
            routing_local_first=bool(routing["local_first"]),
            rag_max_context_chars=int(rag["max_context_chars"]),
            rag_max_regeneration_attempts=int(rag["max_regeneration_attempts"]),
        )


@dataclass(frozen=True)
class UiRuntime:
    rag_service: RagPipelineService
    manufacturers: list[str]
    equipment: list[str]


def collect_filter_options(chunks: Iterable[RetrievedChunk]) -> tuple[list[str], list[str]]:
    manufacturers_raw: set[str] = set()
    equipment_raw: set[str] = set()
    for chunk in chunks:
        manufacturers_raw.add(chunk.manufacturer)
        equipment_raw.add(chunk.equipment)

    manufacturers = _with_all_prefix(manufacturers_raw)
    equipment = _with_all_prefix(equipment_raw)
    return manufacturers, equipment


def build_ui_runtime(settings_path: Path) -> UiRuntime:
    settings = load_settings(settings_path)
    config = UiRuntimeConfig.from_settings(settings.raw)

    chunks = load_chunks(config.chunks_jsonl_dir)
    manufacturers, equipment = collect_filter_options(chunks)

    sparse = _load_or_build_sparse_index(config.bm25_index, chunks)

    dense = build_dense_index(
        chunks,
        persist_dir=config.chroma_db,
        model_name=config.embeddings_model_name,
    )
    reranker = CrossEncoderReranker(model_name=config.reranker_model_name)
    retrieval = HybridRetrievalService(
        settings=settings,
        sparse_retriever=sparse,
        dense_retriever=dense,
        reranker=reranker,
    )

    router = IntentRouter(
        local_classifier=LocalIntentClassifier(),
        llm_classifier=_FallbackLlmClassifier(),
        ambiguous_threshold=config.routing_ambiguous_threshold,
        local_first=config.routing_local_first,
    )
    generator = RagAnswerGenerator(client=None)
    graph = build_rag_graph(
        router=router,
        retrieval_service=retrieval,
        generator=generator,
        max_context_chars=config.rag_max_context_chars,
        citation_guard=CitationGuard(
            max_regeneration_attempts=config.rag_max_regeneration_attempts
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


def _load_or_build_sparse_index(
    bm25_path: Path,
    chunks: list[RetrievedChunk],
):
    if not bm25_path.exists():
        return build_bm25_index(chunks)
    try:
        return load_bm25_index(bm25_path)
    except Exception:
        return build_bm25_index(chunks)
