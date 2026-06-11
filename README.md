# FaultPilot V01

FaultPilot is an OT troubleshooting assistant that combines routing, hybrid retrieval, and citation-guarded RAG with a Gradio user interface.

## Run locally

```bash
uv sync
uv run python app.py
```

Optional settings override:

```bash
set FAULTPILOT_SETTINGS_PATH=path\to\settings.yaml
uv run python app.py
```

## Deploy on Hugging Face Spaces

- SDK: `gradio`
- App file: `app.py`
- Python: `3.10+`
- Runtime dependencies: `requirements.txt`

Recommended repository structure for Spaces:

1. Keep `app.py` at repository root.
2. Keep `requirements.txt` at repository root.
3. Commit `config/settings.yaml` with UI defaults.
4. Add `OPENAI_API_KEY` only if you later wire a provider-backed generator.

After each push, Spaces installs dependencies from `requirements.txt` and launches `app.py` automatically.
