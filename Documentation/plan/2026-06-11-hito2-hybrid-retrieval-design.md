# Hito 2 Design - Hybrid Retrieval (BM25 + Chroma + RRF + Reranker)

## Goal
Build a retrieval engine that combines exact code matching and semantic troubleshooting search for Bosch/Fanuc chunks produced in Hito 1.

## Scope
In scope:
- BM25 index and dense vector index (ChromaDB).
- Parallel retrieval and RRF fusion.
- Cross-encoder reranking over fused shortlist.
- Structured retrieval service API with filters.
- Externalized technical configuration through `config/settings.yaml`.

Out of scope:
- Query router implementation (Hito 3).
- Full Gradio integration (Hito 4).
- LLM response generation logic.

## Architecture

### Components
- `faultpilot/retrieval/loaders.py`: load JSONL chunks from `data/processed/`.
- `faultpilot/retrieval/bm25_index.py`: build/load BM25 index and query candidates.
- `faultpilot/retrieval/vector_index.py`: build/load Chroma collection and dense query.
- `faultpilot/retrieval/fusion.py`: Reciprocal Rank Fusion (RRF) and deduplication.
- `faultpilot/retrieval/reranker.py`: cross-encoder reranking for top-N fused docs.
- `faultpilot/retrieval/service.py`: orchestration entrypoint `hybrid_retrieve(...)`.
- `faultpilot/retrieval/schemas.py`: typed request/response contracts.
- `faultpilot/retrieval/cli.py`: index and search commands for local validation.

### Data Flow
1. Receive query and optional filters (`manufacturer`, `equipment`, `language`).
2. Run BM25 and dense retrieval in parallel.
3. Deduplicate by `chunk_id` and compute `rrf_score`.
4. Select top `top_n_rerank` candidates by RRF.
5. Rerank with cross-encoder using query-document pairs.
6. Return top `final_k` with source/page and score breakdown.

## Ranking Logic

### RRF Formula
For each candidate document:

`RRF(doc) = 1 / (k_rrf + rank_bm25) + 1 / (k_rrf + rank_dense)`

Notes:
- If a document is missing in one retriever list, only available rank contributes.
- `k_rrf=60` by default to smooth rank differences.

### Final Ordering
- Primary order: `rerank_score` (cross-encoder output).
- Secondary debugging attributes: `rrf_score`, `rank_bm25`, `rank_dense`, raw retriever scores.

## Retrieval Contracts

### Input
- `query: str`
- `filters: RetrievalFilters`
- `route: Literal["alarm_lookup", "troubleshooting", "programming"]`

### Output (per hit)
- `chunk_id`
- `content`
- `alarm_code`
- `equipment`
- `manufacturer`
- `source_doc`
- `page`
- `scores: {bm25, dense, rrf, rerank}`
- `ranks: {bm25_rank, dense_rank, fused_rank, final_rank}`

## Error Handling
- Missing BM25 index: fail fast with actionable message in index mode.
- Missing Chroma collection: fail fast with actionable message in index mode.
- Missing reranker model: degrade to RRF-only mode and return warning flag.
- Empty result after filters: return empty list (valid response, no exception).
- Timeout in one branch: continue with remaining branch and mark `degraded_mode=true`.

## Configuration Strategy

Two files are defined:
- `config/prompts.yaml`: prompts and system prompts only.
- `config/settings.yaml`: technical runtime/configuration values.

The retrieval engine must read all runtime knobs from `settings.yaml` and never hardcode these values in service logic.

## Proposed `config/settings.yaml`

```yaml
# ============================================================
# FaultPilot — System Settings
# ============================================================

# --- Paths ---
paths:
  chunks_jsonl_dir: "data/processed"          # Directory containing parsed JSONL chunk files.
  chroma_db: "data/processed/chroma_db"       # Local persistence directory for Chroma collections.
  bm25_index: "data/processed/bm25_index.pkl" # Serialized BM25 index artifact path.
  raw_pdfs: "data/raw"                        # Source PDF directory used during ingestion/indexing.

# --- Embedding model ---
embeddings:
  model_name: "sentence-transformers/all-MiniLM-L6-v2" # Dense embedding model used for semantic retrieval.
  device: "cpu"                                        # Runtime device for embedding inference.
  normalize: true                                      # Whether to L2-normalize embeddings before indexing/querying.

# --- Reranker ---
reranker:
  enabled: true                                   # Enables cross-encoder reranking after hybrid fusion.
  model_name: "cross-encoder/ms-marco-MiniLM-L-6-v2" # Cross-encoder model used for final relevance ordering.
  max_length: 512                                 # Maximum token length per query-document pair.
  batch_size: 16                                  # Number of pairs processed per inference batch.
  device: "cpu"                                  # Runtime device for reranker inference.

# --- Retrieval pipeline (RRF-based) ---
retrieval:
  bm25_k: 40                   # Number of BM25 candidates retrieved before fusion.
  dense_k: 40                  # Number of dense candidates retrieved before fusion.
  rrf_k: 60                    # RRF constant controlling rank contribution smoothness.
  top_n_rerank: 25             # Number of fused candidates passed to reranker.
  final_k: 8                   # Number of final results returned to downstream pipeline.
  min_rrf_score: 0.0           # Minimum RRF score threshold to keep low-signal candidates.
  max_context_chars: 6000      # Max combined context length passed to generation stage.
  dedup_by: "chunk_id"         # Field used to deduplicate candidates across retrievers.

  route_profiles:
    alarm_lookup:
      bm25_k: 60               # Alarm route prioritizes exact sparse retrieval breadth.
      dense_k: 20              # Alarm route uses fewer dense candidates for precision.
      top_n_rerank: 30         # Alarm route reranks a wider shortlist before final cut.
    troubleshooting:
      bm25_k: 25               # Troubleshooting route keeps sparse branch lighter.
      dense_k: 60              # Troubleshooting route emphasizes semantic dense retrieval.
      top_n_rerank: 30         # Troubleshooting route reranks enough mixed evidence.
    programming:
      bm25_k: 20               # Programming route keeps sparse retrieval minimal.
      dense_k: 60              # Programming route relies on semantic recall from dense search.
      top_n_rerank: 25         # Programming route reranks a focused candidate subset.

# --- Indexing behavior ---
indexing:
  rebuild_on_start: false      # Rebuilds indexes at startup when true, otherwise reuses persisted artifacts.
  bm25_tokenizer: "simple"     # Tokenizer strategy used to build/query BM25 index.
  persist_manifest: true       # Writes indexing metadata manifest for traceability and audits.

# --- Query routing ---
routing:
  regex_first: true            # Applies cheap local regex routing before any model-based routing.
  ambiguous_threshold: 0.55    # Confidence threshold below which route is treated as ambiguous.

# --- Observability ---
observability:
  log_level: "INFO"            # Global logging verbosity level.
  trace_retrieval: true        # Logs intermediate retrieval stages and score traces.
  dump_debug_json: false       # Persists debug payloads to disk for offline inspection.

# --- Gradio UI defaults ---
ui:
  title: "FaultPilot — OT Troubleshooting Assistant" # Default Gradio app title.
  server_port: 7860                                  # Local server port for Gradio runtime.
  theme: "soft"                                      # Gradio visual theme preset.
  default_manufacturer: "All"                        # Default manufacturer filter selected in UI.
  show_score_breakdown: true                         # Displays BM25/Dense/RRF/Reranker score details in UI.
```

## Flags Planned for Later Phase
These controls are intentionally defined now but can be partially implemented after Hito 2 core is stable:
- `retrieval.min_rrf_score`
- `retrieval.max_context_chars`
- `observability.dump_debug_json`
- `routing.ambiguous_threshold`
- `ui.show_score_breakdown`

## Testing Strategy

### Unit Tests
- RRF score computation and rank-merging correctness.
- Deduplication policy over BM25+dense overlaps.
- Route profile override selection from settings.
- Settings parser validation and defaults.

### Integration Tests
- Build indexes from Hito 1 outputs.
- Query for exact alarm code (`AL-09`, `2641`) and verify expected high-rank results.
- Query troubleshooting symptoms and verify semantic retrieval contributes to final top-k.

### Contract/Quality Checks
- Every returned hit includes `source_doc` and `page`.
- `final_k` and route-specific limits are respected.
- Degraded mode paths still return traceable results.

## Success Criteria for Hito 2
- Hybrid retrieval service returns stable and traceable results for Bosch/Fanuc.
- RRF fusion is active and configurable through `settings.yaml`.
- Reranker improves ordering over fused candidates.
- All key retrieval parameters are externalized, no hardcoded knobs in retrieval orchestration.
