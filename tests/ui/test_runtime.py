from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from faultpilot.retrieval.schemas import RetrievedChunk
from faultpilot.ui.runtime import build_ui_runtime, collect_filter_options


def _chunk(chunk_id: str, manufacturer: str, equipment: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        content="x",
        alarm_code=None,
        equipment=equipment,
        manufacturer=manufacturer,
        source_doc="doc.pdf",
        page=1,
    )


def test_collect_filter_options_sorts_unique_values() -> None:
    chunks = [
        _chunk("1", "Fanuc", "A06B"),
        _chunk("2", "Bosch", "CC220"),
        _chunk("3", "Fanuc", "CC220"),
    ]

    manufacturers, equipment = collect_filter_options(chunks)

    assert manufacturers == ["All", "Bosch", "Fanuc"]
    assert equipment == ["All", "A06B", "CC220"]


def test_collect_filter_options_accepts_generator_iterable() -> None:
    chunks = (
        _chunk(chunk_id, manufacturer, equipment)
        for chunk_id, manufacturer, equipment in [
            ("1", "Fanuc", "A06B"),
            ("2", "Bosch", "CC220"),
            ("3", "Bosch", "CC220"),
        ]
    )

    manufacturers, equipment = collect_filter_options(chunks)

    assert manufacturers == ["All", "Bosch", "Fanuc"]
    assert equipment == ["All", "A06B", "CC220"]


def test_build_ui_runtime_wires_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings = _build_settings(tmp_path)
    bm25_path = Path(settings.raw["paths"]["bm25_index"])
    chunks = [
        _chunk("1", "Fanuc", "A06B"),
        _chunk("2", "Bosch", "CC220"),
    ]

    calls: dict[str, object] = {}
    sparse = object()
    dense = object()
    graph = object()

    def fake_load_settings(path: Path):
        calls["settings_path"] = path
        return settings

    def fake_load_chunks(path: Path):
        calls["chunks_path"] = path
        return chunks

    def fake_build_bm25_index(loaded_chunks):
        calls["bm25_chunks"] = loaded_chunks
        return sparse

    def fake_load_bm25_index(path: Path):
        raise AssertionError(f"Should not load BM25 index from disk: {path}")

    def fake_build_dense_index(loaded_chunks, persist_dir: Path, model_name: str):
        calls["dense_chunks"] = loaded_chunks
        calls["dense_persist_dir"] = persist_dir
        calls["dense_model_name"] = model_name
        return dense

    class _FakeCrossEncoderReranker:
        def __init__(self, model_name: str) -> None:
            calls["reranker_model_name"] = model_name

    class _FakeHybridRetrievalService:
        def __init__(
            self,
            settings,
            sparse_retriever,
            dense_retriever,
            reranker,
        ) -> None:
            calls["retrieval_settings"] = settings
            calls["retrieval_sparse"] = sparse_retriever
            calls["retrieval_dense"] = dense_retriever
            calls["retrieval_reranker"] = reranker

    class _FakeLocalIntentClassifier:
        pass

    class _FakeIntentRouter:
        def __init__(
            self,
            local_classifier,
            llm_classifier,
            ambiguous_threshold: float,
            local_first: bool,
        ) -> None:
            calls["router_local_classifier"] = local_classifier
            calls["router_llm_classifier"] = llm_classifier
            calls["router_threshold"] = ambiguous_threshold
            calls["router_local_first"] = local_first

    class _FakeRagAnswerGenerator:
        def __init__(self, client) -> None:
            calls["generator_client"] = client

    class _FakeCitationGuard:
        def __init__(self, max_regeneration_attempts: int) -> None:
            calls["guard_attempts"] = max_regeneration_attempts

    def fake_build_rag_graph(
        router,
        retrieval_service,
        generator,
        max_context_chars: int,
        citation_guard,
    ):
        calls["graph_router"] = router
        calls["graph_retrieval_service"] = retrieval_service
        calls["graph_generator"] = generator
        calls["graph_max_context_chars"] = max_context_chars
        calls["graph_citation_guard"] = citation_guard
        return graph

    class _FakeRagPipelineService:
        def __init__(self, runtime_graph) -> None:
            calls["rag_graph"] = runtime_graph

    monkeypatch.setattr("faultpilot.ui.runtime.load_settings", fake_load_settings)
    monkeypatch.setattr("faultpilot.ui.runtime.load_chunks", fake_load_chunks)
    monkeypatch.setattr("faultpilot.ui.runtime.build_bm25_index", fake_build_bm25_index)
    monkeypatch.setattr("faultpilot.ui.runtime.load_bm25_index", fake_load_bm25_index)
    monkeypatch.setattr("faultpilot.ui.runtime.build_dense_index", fake_build_dense_index)
    monkeypatch.setattr("faultpilot.ui.runtime.CrossEncoderReranker", _FakeCrossEncoderReranker)
    monkeypatch.setattr(
        "faultpilot.ui.runtime.HybridRetrievalService",
        _FakeHybridRetrievalService,
    )
    monkeypatch.setattr("faultpilot.ui.runtime.LocalIntentClassifier", _FakeLocalIntentClassifier)
    monkeypatch.setattr("faultpilot.ui.runtime.IntentRouter", _FakeIntentRouter)
    monkeypatch.setattr("faultpilot.ui.runtime.RagAnswerGenerator", _FakeRagAnswerGenerator)
    monkeypatch.setattr("faultpilot.ui.runtime.CitationGuard", _FakeCitationGuard)
    monkeypatch.setattr("faultpilot.ui.runtime.build_rag_graph", fake_build_rag_graph)
    monkeypatch.setattr("faultpilot.ui.runtime.RagPipelineService", _FakeRagPipelineService)

    runtime = build_ui_runtime(settings_path)

    assert calls["settings_path"] == settings_path
    assert calls["chunks_path"] == Path(settings.raw["paths"]["chunks_jsonl_dir"])
    assert calls["bm25_chunks"] == chunks
    assert calls["dense_chunks"] == chunks
    assert calls["dense_persist_dir"] == Path(settings.raw["paths"]["chroma_db"])
    assert calls["dense_model_name"] == "dense-model"
    assert calls["reranker_model_name"] == "reranker-model"
    assert calls["retrieval_settings"] is settings
    assert calls["retrieval_sparse"] is sparse
    assert calls["retrieval_dense"] is dense
    assert isinstance(calls["router_local_classifier"], _FakeLocalIntentClassifier)
    llm_classifier = calls["router_llm_classifier"]
    assert hasattr(llm_classifier, "classify")
    first = llm_classifier.classify("What is AL-09?")  # type: ignore[union-attr]
    second = llm_classifier.classify("Different question")  # type: ignore[union-attr]
    assert first == second
    assert first.intent == "troubleshooting"
    assert first.confidence == 0.5
    assert first.evidence == "fallback_ui_classifier"
    assert calls["router_threshold"] == 0.42
    assert calls["router_local_first"] is True
    assert calls["generator_client"] is None
    assert calls["guard_attempts"] == 2
    assert calls["graph_max_context_chars"] == 1234
    assert calls["rag_graph"] is graph
    assert runtime.manufacturers == ["All", "Bosch", "Fanuc"]
    assert runtime.equipment == ["All", "A06B", "CC220"]


def test_build_ui_runtime_loads_persisted_bm25_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings = _build_settings(tmp_path)
    bm25_path = Path(settings.raw["paths"]["bm25_index"])
    bm25_path.write_bytes(b"persisted")
    chunks = [_chunk("1", "Fanuc", "A06B")]

    calls: dict[str, object] = {"loaded": False, "built": False, "retrieval_sparse": None}
    loaded_sparse = object()

    monkeypatch.setattr("faultpilot.ui.runtime.load_settings", lambda _: settings)
    monkeypatch.setattr("faultpilot.ui.runtime.load_chunks", lambda _: chunks)
    monkeypatch.setattr(
        "faultpilot.ui.runtime.load_bm25_index",
        lambda path: calls.__setitem__("loaded", path) or loaded_sparse,
    )
    monkeypatch.setattr(
        "faultpilot.ui.runtime.build_bm25_index",
        lambda _: calls.__setitem__("built", True),
    )
    monkeypatch.setattr("faultpilot.ui.runtime.build_dense_index", lambda *args, **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.CrossEncoderReranker", lambda **kwargs: object())
    monkeypatch.setattr(
        "faultpilot.ui.runtime.HybridRetrievalService",
        lambda **kwargs: calls.__setitem__("retrieval_sparse", kwargs["sparse_retriever"]) or object(),
    )
    monkeypatch.setattr("faultpilot.ui.runtime.LocalIntentClassifier", lambda: object())
    monkeypatch.setattr("faultpilot.ui.runtime.IntentRouter", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.RagAnswerGenerator", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.CitationGuard", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.build_rag_graph", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.RagPipelineService", lambda *args: object())

    build_ui_runtime(settings_path)

    assert calls["loaded"] == bm25_path
    assert calls["built"] is False
    assert calls["retrieval_sparse"] is loaded_sparse


def test_build_ui_runtime_rebuilds_bm25_index_when_corrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "settings.yaml"
    settings = _build_settings(tmp_path)
    bm25_path = Path(settings.raw["paths"]["bm25_index"])
    bm25_path.write_bytes(b"corrupted")
    chunks = [_chunk("1", "Fanuc", "A06B")]

    rebuilt_sparse = object()
    calls: dict[str, object] = {
        "loaded": False,
        "built_with": None,
        "retrieval_sparse": None,
    }

    monkeypatch.setattr("faultpilot.ui.runtime.load_settings", lambda _: settings)
    monkeypatch.setattr("faultpilot.ui.runtime.load_chunks", lambda _: chunks)

    def fake_load_bm25_index(path: Path):
        calls["loaded"] = path
        raise ValueError("corrupted index")

    monkeypatch.setattr("faultpilot.ui.runtime.load_bm25_index", fake_load_bm25_index)
    monkeypatch.setattr(
        "faultpilot.ui.runtime.build_bm25_index",
        lambda loaded_chunks: calls.__setitem__("built_with", loaded_chunks) or rebuilt_sparse,
    )
    monkeypatch.setattr("faultpilot.ui.runtime.build_dense_index", lambda *args, **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.CrossEncoderReranker", lambda **kwargs: object())
    monkeypatch.setattr(
        "faultpilot.ui.runtime.HybridRetrievalService",
        lambda **kwargs: calls.__setitem__("retrieval_sparse", kwargs["sparse_retriever"]) or object(),
    )
    monkeypatch.setattr("faultpilot.ui.runtime.LocalIntentClassifier", lambda: object())
    monkeypatch.setattr("faultpilot.ui.runtime.IntentRouter", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.RagAnswerGenerator", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.CitationGuard", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.build_rag_graph", lambda **kwargs: object())
    monkeypatch.setattr("faultpilot.ui.runtime.RagPipelineService", lambda *args: object())

    build_ui_runtime(settings_path)

    assert calls["loaded"] == bm25_path
    assert calls["built_with"] == chunks
    assert calls["retrieval_sparse"] is rebuilt_sparse


def _build_settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        raw={
            "paths": {
                "chunks_jsonl_dir": str(tmp_path / "processed"),
                "bm25_index": str(tmp_path / "bm25_index.pkl"),
                "chroma_db": str(tmp_path / "chroma_db"),
            },
            "embeddings": {"model_name": "dense-model"},
            "reranker": {"model_name": "reranker-model"},
            "routing": {"ambiguous_threshold": 0.42, "local_first": True},
            "rag": {"max_context_chars": 1234, "max_regeneration_attempts": 2},
        }
    )
