# Hito 2 Hybrid Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a configurable hybrid retrieval engine (BM25 + Chroma + RRF + reranker) for Bosch/Fanuc chunks from Hito 1.

**Architecture:** Split retrieval into focused modules: data loading, sparse index, dense index, fusion/reranking, and orchestration service. Keep all tuning parameters in `config/settings.yaml` and expose a CLI for indexing and search validation.

**Tech Stack:** Python 3.10+, PyYAML, rank-bm25, chromadb, sentence-transformers, pytest.

---

### Task 1: Config layer and schemas

**Files:**
- Create: `config/settings.yaml`
- Create: `config/prompts.yaml`
- Create: `faultpilot/retrieval/config.py`
- Create: `faultpilot/retrieval/schemas.py`
- Test: `tests/retrieval/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_settings_has_rrf_keys() -> None:
    settings = load_settings(Path("config/settings.yaml"))
    assert settings.retrieval.rrf_k == 60


def test_route_profile_override_alarm_lookup() -> None:
    settings = load_settings(Path("config/settings.yaml"))
    profile = settings.retrieval.profile_for_route("alarm_lookup")
    assert profile.bm25_k == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: faultpilot.retrieval.config`

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass(frozen=True)
class RetrievalSettings:
    bm25_k: int
    dense_k: int
    rrf_k: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/settings.yaml config/prompts.yaml faultpilot/retrieval/config.py faultpilot/retrieval/schemas.py tests/retrieval/test_config.py
git commit -m "feat: add retrieval configuration and schemas"
```

### Task 2: Chunk loader and chunk IDs

**Files:**
- Create: `faultpilot/retrieval/loaders.py`
- Test: `tests/retrieval/test_loaders.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_chunks_from_jsonl_directory(tmp_path: Path) -> None:
    chunks = load_chunks(tmp_path)
    assert chunks == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_loaders.py -v`
Expected: FAIL with `ModuleNotFoundError: faultpilot.retrieval.loaders`

- [ ] **Step 3: Write minimal implementation**

```python
def build_chunk_id(source_doc: str, page: int, alarm_code: str | None, content: str) -> str:
    return f"{source_doc}:{page}:{alarm_code or 'NA'}:{hash(content)}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_loaders.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add faultpilot/retrieval/loaders.py tests/retrieval/test_loaders.py
git commit -m "feat: add retrieval chunk loader"
```

### Task 3: BM25 index and query

**Files:**
- Create: `faultpilot/retrieval/bm25_index.py`
- Test: `tests/retrieval/test_bm25_index.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_bm25_search_returns_exact_alarm_first() -> None:
    idx = build_bm25_index(sample_chunks())
    hits = idx.search("AL-09", top_k=3)
    assert hits[0].alarm_code == "AL-09"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_bm25_index.py -v`
Expected: FAIL because build/search functions are missing

- [ ] **Step 3: Write minimal implementation**

```python
class Bm25Index:
    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_bm25_index.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add faultpilot/retrieval/bm25_index.py tests/retrieval/test_bm25_index.py
git commit -m "feat: add bm25 retrieval index"
```

### Task 4: RRF fusion and reranking interfaces

**Files:**
- Create: `faultpilot/retrieval/fusion.py`
- Create: `faultpilot/retrieval/reranker.py`
- Test: `tests/retrieval/test_fusion.py`
- Test: `tests/retrieval/test_reranker.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_rrf_prefers_documents_present_in_both_lists() -> None:
    fused = reciprocal_rank_fusion(bm25_hits(), dense_hits(), k=60)
    assert fused[0].chunk_id == "shared"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_fusion.py tests/retrieval/test_reranker.py -v`
Expected: FAIL with missing fusion/reranker functions

- [ ] **Step 3: Write minimal implementation**

```python
def reciprocal_rank_fusion(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_fusion.py tests/retrieval/test_reranker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add faultpilot/retrieval/fusion.py faultpilot/retrieval/reranker.py tests/retrieval/test_fusion.py tests/retrieval/test_reranker.py
git commit -m "feat: add rrf fusion and reranker adapter"
```

### Task 5: Hybrid retrieval service orchestration

**Files:**
- Create: `faultpilot/retrieval/service.py`
- Create: `faultpilot/retrieval/__init__.py`
- Test: `tests/retrieval/test_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_service_applies_route_profile_and_returns_final_k() -> None:
    service = HybridRetrievalService(...)
    result = service.hybrid_retrieve("AL-09", route="alarm_lookup")
    assert len(result.hits) <= result.meta.final_k
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_service.py -v`
Expected: FAIL with missing service module

- [ ] **Step 3: Write minimal implementation**

```python
class HybridRetrievalService:
    def hybrid_retrieve(self, query: str, route: str, filters: RetrievalFilters | None = None):
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add faultpilot/retrieval/service.py faultpilot/retrieval/__init__.py tests/retrieval/test_service.py
git commit -m "feat: add hybrid retrieval orchestration service"
```

### Task 6: Retrieval CLI and end-to-end validation

**Files:**
- Create: `faultpilot/retrieval/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/retrieval/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_cli_search_returns_zero_exit_code(tmp_path: Path) -> None:
    assert main(["search", "--query", "AL-09"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/retrieval/test_cli.py -v`
Expected: FAIL because CLI module does not exist

- [ ] **Step 3: Write minimal implementation**

```python
def main(argv: Sequence[str] | None = None) -> int:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/retrieval/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run full verification**

Run: `uv run python -m pytest tests -v`
Expected: PASS with 0 failures

- [ ] **Step 6: Commit**

```bash
git add faultpilot/retrieval/cli.py pyproject.toml tests/retrieval/test_cli.py
git commit -m "feat: add retrieval cli and hito2 test coverage"
```
