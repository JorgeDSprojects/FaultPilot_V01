# FaultPilot V01

## Project description

FaultPilot is an OT troubleshooting assistant for industrial maintenance teams.
It combines intent routing, hybrid retrieval (BM25 + dense + rerank), and citation-grounded answer generation in a Gradio UI designed for operator workflows.

## Run locally

```bash
uv sync
uv run python app.py
```

Optional settings override:

Windows PowerShell:

```powershell
$env:FAULTPILOT_SETTINGS_PATH = "path\\to\\settings.yaml"
uv run python app.py
```

Linux/macOS shell:

```bash
export FAULTPILOT_SETTINGS_PATH="path/to/settings.yaml"
uv run python app.py
```

## Required API keys

- Provider-backed grounded answer generation requires an OpenAI API key entered in the UI (`OpenAI API Key` password field).

Key handling statement:
- Each user supplies the key in the UI (`OpenAI API Key` password field) for the active session.
- FaultPilot uses the key in memory for request execution and does not store it in project files, repository config, or persistent application storage.

## Quick cost estimate (`gpt-4o-mini`)

- Certification smoke run example: 20 troubleshooting questions, each around <=1000 prompt tokens and <=500 completion tokens.
- Estimated total is well under **$0.50** with `gpt-4o-mini` (typically only a few cents, depending on prompt length and retries).

## Optional functionalities

- Manufacturer filter selector (for example `Fanuc`, `Bosch`, or `All`).
- Equipment dropdown selector to scope troubleshooting answers.
- Collapsible traceability panel with intent, confidence, and timing metadata.
- Sources panel listing evidence chunks used in each answer.
- Local settings override via `FAULTPILOT_SETTINGS_PATH`.
- Retrieval CLI smoke tests for route/manufacturer checks before UI deployment.

## Deploy on Hugging Face Spaces

1. Create a new Space with SDK set to `gradio`.
2. Keep `app.py` and `requirements.txt` at repository root.
3. Confirm Python runtime is `3.10+`.
4. The current runtime does not consume an `OPENAI_API_KEY` Space secret; users enter the key in the UI per session.
5. Push the repository and wait for the build to complete.

Public Space URL placeholder:
- `https://huggingface.co/spaces/<org-or-user>/<space-name>`

After each push, Spaces installs dependencies from `requirements.txt` and launches `app.py` automatically.

## Dependency sync rule

- Source of truth for runtime dependencies is `[project.dependencies]` in `pyproject.toml`.
- `requirements.txt` exists for Hugging Face Spaces compatibility and must stay in exact sync with `pyproject.toml` in every dependency-changing PR.
