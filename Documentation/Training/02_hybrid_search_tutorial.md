# 02 - Hybrid retrieval tutorial (BM25 + Dense + RRF + Reranker)

## Objective
In Hito 2 we built FaultPilot's retrieval core so the system can answer both:
- exact alarm/code lookups (`AL-09`, `2641`), and
- semantic troubleshooting questions (symptom-based queries).

The implementation now combines sparse retrieval, dense retrieval, rank fusion, and reranking in one configurable service.

---

## Decision 1 - Externalized settings (`config/settings.yaml`)

**El Problema:**
Hardcoded retrieval constants make tuning slow and risky when testing route behavior (`alarm_lookup` vs `troubleshooting`).

**Alternativas Evaluadas:**
- Inline constants in Python modules.
- Environment variables only.
- YAML settings file with typed loader.

**La Decision:**
Use `config/settings.yaml` as the single source of technical knobs and load it with a typed config layer.

**Implementación:**
```python
settings = load_settings(Path("config/settings.yaml"))
profile = settings.retrieval.profile_for_route("alarm_lookup")
```

---

## Decision 2 - Sparse retrieval with BM25

**El Problema:**
Alarm-code queries need exact lexical matching that dense-only retrieval can miss.

**Alternativas Evaluadas:**
- Dense-only retrieval.
- Regex-only retrieval.
- BM25 + semantic dense branch.

**La Decision:**
Implement a BM25 index (`faultpilot/retrieval/bm25_index.py`) as the sparse branch for precision on codes and exact terms.

**Implementación:**
```python
index = build_bm25_index(chunks)
hits = index.search("AL-09", top_k=40, filters=filters)
```

---

## Decision 3 - Dense retrieval with Chroma fallback strategy

**El Problema:**
Troubleshooting queries often share meaning, not exact vocabulary.

**Alternativas Evaluadas:**
- Sparse-only retrieval.
- Dense in-memory only.
- Dense with persisted Chroma backend, fallback when unavailable.

**La Decision:**
Implement `vector_index.py` with Chroma persistence when available, and a deterministic fallback path for local resilience.

**Implementación:**
```python
dense = build_dense_index(chunks, persist_dir=Path("data/processed/chroma_db"))
hits = dense.search("panel transfer fault", top_k=40, filters=filters)
```

---

## Decision 4 - Fusion with RRF

**El Problema:**
Sparse and dense scores are not directly comparable; score-sum calibration is brittle across corpora.

**Alternativas Evaluadas:**
- Weighted score sum.
- Max-score winner-take-all.
- Reciprocal Rank Fusion (RRF).

**La Decision:**
Fuse rankings with RRF because it is robust to score scale differences and works well with mixed retrieval signals.

**Implementación:**
```python
fused = reciprocal_rank_fusion(bm25_hits=bm25_hits, dense_hits=dense_hits, k=60)
```

---

## Decision 5 - Final reranking with cross-encoder

**El Problema:**
After fusion, top candidates can still have near-ties where contextual relevance is unclear.

**Alternativas Evaluadas:**
- Keep fused order as final output.
- Rule-based tie breaking.
- Cross-encoder reranking on top-N candidates.

**La Decision:**
Use cross-encoder reranking on a bounded shortlist (`top_n_rerank`) to improve final ordering quality.

**Implementación:**
```python
reranked = reranker.rerank(query=query, hits=fused_hits, top_n=profile.top_n_rerank)
```

---

## Decision 6 - Orchestrated service boundary

**El Problema:**
Without a dedicated service boundary, BM25, dense, fusion, and reranker logic leak into CLI/UI layers.

**Alternativas Evaluadas:**
- Keep orchestration inside CLI.
- Spread logic across retriever modules.
- Single hybrid service entrypoint.

**La Decision:**
Create `HybridRetrievalService` as the integration boundary for Hito 2.

**Implementación:**
```python
service = HybridRetrievalService(settings, sparse, dense, reranker)
result = service.hybrid_retrieve("AL-09", route="alarm_lookup", filters=filters)
```

---

## Operational commands

Build indexes:
```bash
uv run faultpilot-retrieval --settings config/settings.yaml index
```

Run a query:
```bash
uv run faultpilot-retrieval --settings config/settings.yaml search --query "AL-09" --route alarm_lookup --manufacturer Fanuc
```

Run tests:
```bash
uv run python -m pytest tests -v
```

---

## Current limits and next iteration notes
- Dense search currently supports robust fallback behavior; route-aware optimization can be expanded in Hito 3.
- Retrieval outputs include traceability (`source_doc`, `page`), ready for RAG injection.
- Flags such as `min_rrf_score`, `max_context_chars`, and debug dump controls are already defined in settings for progressive activation.
