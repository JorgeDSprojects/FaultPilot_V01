"""Dense retrieval adapter with optional ChromaDB backend."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

from faultpilot.retrieval.schemas import RetrievedChunk, RetrievalFilters

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-]+")


class DenseVectorIndex:
    """Dense retriever over chunk content."""

    def __init__(
        self,
        chunks: list[RetrievedChunk],
        embeddings: list[list[float]] | None,
        query_embedder=None,
        collection=None,
    ) -> None:
        self._chunks = chunks
        self._embeddings = embeddings
        self._query_embedder = query_embedder
        self._collection = collection
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self._token_sets = [set(_tokenize(chunk.content)) for chunk in chunks]

    def search(
        self,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        """Return top-k dense matches with score annotations."""
        if not self._chunks:
            return []

        if self._collection is not None and self._query_embedder is not None:
            return self._search_chroma(query, top_k, filters)
        return self._search_in_memory(query, top_k, filters)

    def _search_chroma(
        self,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None,
    ) -> list[RetrievedChunk]:
        query_vector = self._embed_query(query)
        where = _build_chroma_where(filters)
        kwargs = {"query_embeddings": [query_vector], "n_results": top_k}
        if where is not None:
            kwargs["where"] = where

        result = self._collection.query(**kwargs)
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        output: list[RetrievedChunk] = []
        for rank, (chunk_id, distance) in enumerate(zip(ids, distances), start=1):
            chunk = self._chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            dense_score = 1.0 / (1.0 + float(distance))
            output.append(
                replace(
                    chunk,
                    scores={**chunk.scores, "dense": dense_score},
                    ranks={**chunk.ranks, "dense_rank": rank},
                )
            )
        return output

    def _search_in_memory(
        self,
        query: str,
        top_k: int,
        filters: RetrievalFilters | None,
    ) -> list[RetrievedChunk]:
        if self._embeddings is not None:
            query_vector = self._embed_query(query)
            scores = [_cosine(query_vector, vector) for vector in self._embeddings]
        else:
            query_tokens = set(_tokenize(query))
            scores = [_token_overlap(query_tokens, tokens) for tokens in self._token_sets]

        ranked_ids = sorted(
            range(len(self._chunks)),
            key=lambda idx: scores[idx],
            reverse=True,
        )

        output: list[RetrievedChunk] = []
        rank = 1
        for idx in ranked_ids:
            if scores[idx] <= 0:
                continue
            chunk = self._chunks[idx]
            if not _matches_filters(chunk, filters):
                continue
            output.append(
                replace(
                    chunk,
                    scores={**chunk.scores, "dense": float(scores[idx])},
                    ranks={**chunk.ranks, "dense_rank": rank},
                )
            )
            rank += 1
            if len(output) >= top_k:
                break
        return output

    def _embed_query(self, query: str) -> list[float]:
        if self._query_embedder is None:
            return []
        vector = self._query_embedder([query], normalize_embeddings=True)[0]
        return vector.tolist()


def build_dense_index(
    chunks: list[RetrievedChunk],
    persist_dir: Path | None = None,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> DenseVectorIndex:
    """Build dense retriever and persist to Chroma when available."""
    embeddings, query_embedder = _maybe_embed_chunks(chunks, model_name)
    collection = None

    if persist_dir is not None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        collection = _maybe_build_chroma_collection(
            persist_dir=persist_dir,
            chunks=chunks,
            embeddings=embeddings,
        )

    return DenseVectorIndex(
        chunks=chunks,
        embeddings=embeddings,
        query_embedder=query_embedder,
        collection=collection,
    )


def _maybe_embed_chunks(
    chunks: list[RetrievedChunk],
    model_name: str,
) -> tuple[list[list[float]] | None, object | None]:
    if not chunks:
        return [], None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None, None

    model = SentenceTransformer(model_name)
    vectors = model.encode([chunk.content for chunk in chunks], normalize_embeddings=True)
    return [vector.tolist() for vector in vectors], model.encode


def _maybe_build_chroma_collection(
    persist_dir: Path,
    chunks: list[RetrievedChunk],
    embeddings: list[list[float]] | None,
):
    if embeddings is None:
        return None
    try:
        import chromadb
    except ImportError:
        return None

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection("faultpilot_hito2")

    existing_ids = collection.get().get("ids", [])
    if existing_ids:
        collection.delete(ids=existing_ids)

    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=[chunk.content for chunk in chunks],
        metadatas=[
            {
                "manufacturer": chunk.manufacturer,
                "equipment": chunk.equipment,
                "language": chunk.language or "",
                "source_doc": chunk.source_doc,
                "page": chunk.page,
            }
            for chunk in chunks
        ],
        embeddings=embeddings,
    )
    return collection


def _build_chroma_where(filters: RetrievalFilters | None):
    if filters is None:
        return None
    clauses = []
    if filters.manufacturer:
        clauses.append({"manufacturer": filters.manufacturer})
    if filters.equipment:
        clauses.append({"equipment": filters.equipment})
    if filters.language:
        clauses.append({"language": filters.language})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in _TOKEN_PATTERN.findall(value)]


def _token_overlap(query_tokens: set[str], doc_tokens: set[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    return len(query_tokens & doc_tokens) / len(query_tokens)


def _matches_filters(chunk: RetrievedChunk, filters: RetrievalFilters | None) -> bool:
    if filters is None:
        return True
    if filters.manufacturer and chunk.manufacturer != filters.manufacturer:
        return False
    if filters.equipment and chunk.equipment != filters.equipment:
        return False
    if filters.language and chunk.language != filters.language:
        return False
    return True
