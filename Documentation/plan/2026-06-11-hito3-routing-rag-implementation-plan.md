# Hito 3 Routing + RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement intent routing and LangGraph-based grounded answer generation with strict source/page citations.

**Architecture:** Add a routing domain (local + LLM fallback), add a RAG domain orchestrated by LangGraph, and integrate it with the existing Hito 2 retrieval service. Keep provider calls injectable for testing and runtime key management.

**Tech Stack:** Python 3.10+, LangGraph, LangChain core patterns, pytest.

---

### Task 1: Routing contracts and local classifier

**Files:**
- Create: `faultpilot/routing/schemas.py`
- Create: `faultpilot/routing/local_classifier.py`
- Test: `tests/routing/test_local_classifier.py`

- [ ] **Step 1: Write failing tests for alarm/programming/troubleshooting classification**
- [ ] **Step 2: Run `uv run python -m pytest tests/routing/test_local_classifier.py -v` and confirm FAIL**
- [ ] **Step 3: Implement minimal routing schemas + local regex classifier**
- [ ] **Step 4: Re-run the same test command and confirm PASS**
- [ ] **Step 5: Commit**

```bash
git add faultpilot/routing/schemas.py faultpilot/routing/local_classifier.py tests/routing/test_local_classifier.py
git commit -m "feat: add local intent classifier"
```

### Task 2: LLM classifier fallback and intent router

**Files:**
- Create: `faultpilot/routing/llm_classifier.py`
- Create: `faultpilot/routing/intent_router.py`
- Create: `faultpilot/routing/__init__.py`
- Test: `tests/routing/test_intent_router.py`

- [ ] **Step 1: Write failing tests for ambiguous query fallback and failure degradation**
- [ ] **Step 2: Run `uv run python -m pytest tests/routing/test_intent_router.py -v` and confirm FAIL**
- [ ] **Step 3: Implement router policy (`local first`, threshold, llm fallback, degraded mode)**
- [ ] **Step 4: Re-run same test command and confirm PASS**
- [ ] **Step 5: Commit**

```bash
git add faultpilot/routing/llm_classifier.py faultpilot/routing/intent_router.py faultpilot/routing/__init__.py tests/routing/test_intent_router.py
git commit -m "feat: add hybrid intent router with llm fallback"
```

### Task 3: Context builder and citation guard

**Files:**
- Create: `faultpilot/rag/schemas.py`
- Create: `faultpilot/rag/context_builder.py`
- Create: `faultpilot/rag/postprocess.py`
- Test: `tests/rag/test_context_builder.py`
- Test: `tests/rag/test_citation_guard.py`

- [ ] **Step 1: Write failing tests for context truncation and citation enforcement**
- [ ] **Step 2: Run `uv run python -m pytest tests/rag/test_context_builder.py tests/rag/test_citation_guard.py -v` and confirm FAIL**
- [ ] **Step 3: Implement context builder and citation guard fallback behavior**
- [ ] **Step 4: Re-run same command and confirm PASS**
- [ ] **Step 5: Commit**

```bash
git add faultpilot/rag/schemas.py faultpilot/rag/context_builder.py faultpilot/rag/postprocess.py tests/rag/test_context_builder.py tests/rag/test_citation_guard.py
git commit -m "feat: add rag context builder and citation guard"
```

### Task 4: LangGraph pipeline and service API

**Files:**
- Create: `faultpilot/rag/state.py`
- Create: `faultpilot/rag/generator.py`
- Create: `faultpilot/rag/graph.py`
- Create: `faultpilot/rag/service.py`
- Create: `faultpilot/rag/__init__.py`
- Test: `tests/rag/test_graph_service.py`

- [ ] **Step 1: Write failing integration-style test for graph run and final response shape**
- [ ] **Step 2: Run `uv run python -m pytest tests/rag/test_graph_service.py -v` and confirm FAIL**
- [ ] **Step 3: Implement graph nodes (`route`, `retrieve`, `build_context`, `generate`, `guard`) and service wrapper**
- [ ] **Step 4: Re-run same command and confirm PASS**
- [ ] **Step 5: Commit**

```bash
git add faultpilot/rag/state.py faultpilot/rag/generator.py faultpilot/rag/graph.py faultpilot/rag/service.py faultpilot/rag/__init__.py tests/rag/test_graph_service.py
git commit -m "feat: add langgraph rag pipeline service"
```

### Task 5: Config/prompt updates, docs, full verification

**Files:**
- Modify: `config/prompts.yaml`
- Modify: `config/settings.yaml`
- Modify: `Documentation/changelog.md`
- Create: `Documentation/Training/03_routing_rag_tutorial.md`

- [ ] **Step 1: Add routing and RAG prompt templates in `config/prompts.yaml`**
- [ ] **Step 2: Add/confirm routing and rag control flags in `config/settings.yaml`**
- [ ] **Step 3: Update changelog and training tutorial**
- [ ] **Step 4: Run full suite and confirm green**

Run: `uv run python -m pytest tests -v`
Expected: PASS with 0 failures

- [ ] **Step 5: Commit**

```bash
git add config/prompts.yaml config/settings.yaml Documentation/changelog.md Documentation/Training/03_routing_rag_tutorial.md
git commit -m "docs: add hito 3 routing rag documentation"
```
