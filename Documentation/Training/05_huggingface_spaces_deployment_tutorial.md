# 05 - Hugging Face Spaces deployment tutorial (step by step)

## Objective
Deploy FaultPilot V01 in a public Hugging Face Space, keeping course compliance:
- app available for reviewers,
- user-provided OpenAI API key in UI,
- no secrets committed in repository.

---

## Step 0 - Pre-flight checklist (before opening Spaces)

**El Problema:**
Many Space build failures happen before deployment because the repo is not ready.

**Alternativas Evaluadas:**
- Push immediately and debug in production.
- Validate locally first, then deploy.

**La Decision:**
Validate locally first and deploy only from a green baseline.

**Implementacion:**
```bash
uv sync
uv run pytest
uv run python app.py
```

Expected:
- tests pass,
- app starts,
- UI shows `OpenAI API Key` input.

---

## Step 1 - Create the Space

**El Problema:**
Wrong Space settings (SDK/hardware/visibility) break startup or certification review.

**Alternativas Evaluadas:**
- Docker Space (more control, more complexity).
- Gradio Space (simpler and aligned with current project).

**La Decision:**
Create a **Gradio** Space.

**Implementacion:**
1. Go to `https://huggingface.co/new-space`.
2. Owner: your personal account or org.
3. Space name: for example `faultpilot-v01`.
4. SDK: `Gradio`.
5. Visibility: `Public` (required for course review).
6. Hardware: `CPU Basic` is enough for this version.
7. Click **Create Space**.

---

## Step 2 - Connect code to the Space

**El Problema:**
Spaces needs repository root files in the right place to auto-build correctly.

**Alternativas Evaluadas:**
- Upload files manually in web UI.
- Sync from GitHub repository.

**La Decision:**
Use GitHub sync (recommended), keep manual upload only as fallback.

**Implementacion:**
1. In the Space page, open **Settings -> Repository secrets and variables** (optional here).
2. In **Settings -> Linked repositories**, connect your GitHub repo.
Sí, correcto: en muchas cuentas ese menú de Linked repositories ya no aparece (o cambió de sitio).  
No te preocupes: hay una forma 100% fiable de desplegar igual.
Hazlo por git push al repo del Space:
# En tu repo local
git remote add hf-space https://huggingface.co/spaces/jmartinezsegulagrp/faultpilot-v01

https://huggingface.co/spaces/<TU_USUARIO_HF>/<NOMBRE_DEL_SPACE>
https://huggingface.co/spaces/jmartinezsegulagrp/faultpilot-v01
# Empuja tu rama main al Space
git push hf-space main
Cuando pida credenciales:
- Username: tu usuario de Hugging Face
- Password: tu HF Token (no tu password normal)
Luego:
1. Abre tu Space en HF.
2. Ve a Build logs.
3. Espera a Running.
4. Prueba la app (sin key debe pedir key; con key debe responder).
Si te da error por tamaño de archivos al hacer push, te paso el flujo con Git LFS en 2 comandos extra.


4. Confirm these files exist at repo root:
   - `app.py`
   - `requirements.txt`
   - `config/settings.yaml`
5. Push latest `main` branch to GitHub.
6. Wait for Space auto-build.

Fallback (manual):
- Use `git` with the Space URL and push current repo contents.

---

## Step 3 - Runtime configuration and secrets

**El Problema:**
Many apps fail certification by forcing backend secrets or storing user keys.

**Alternativas Evaluadas:**
- Store provider key as `OPENAI_API_KEY` Space secret.
- Ask user to paste key in UI each session.

**La Decision:**
Use UI-based key input per session (current FaultPilot behavior).

**Implementacion:**
- Do **not** commit API keys.
- Space secret `OPENAI_API_KEY` is **not required** for current runtime path.
- User enters key in the `OpenAI API Key` field in the app.
- Key is used in-memory and not persisted by FaultPilot.

---

## Step 4 - Verify the deployed app in Space

**El Problema:**
Space build success does not guarantee functional compliance.

**Alternativas Evaluadas:**
- Quick visual check only.
- Functional checklist with real query flow.

**La Decision:**
Run a functional checklist.

**Implementacion:**
After Space is `Running`, validate:
1. UI loads and shows chat + traceability panel.
2. `OpenAI API Key` input is visible.
3. Send query without key -> app blocks and asks for key.
4. Paste valid key, send query -> answer streams and shows sources.
5. Traceability block updates with intent/source/timing.

Suggested smoke queries:
- `AL-09`
- `What does error 116 mean in Bosch CC220?`

---

## Step 5 - Add Space URL to README

**El Problema:**
Reviewers need one direct public link.

**Alternativas Evaluadas:**
- Keep placeholder URL.
- Replace with final public Space URL.

**La Decision:**
Replace placeholder with real URL after first successful deploy.

**Implementacion:**
Update `README.md`:
- Find `Space URL: <ADD_YOUR_PUBLIC_SPACE_URL_HERE>`
- Replace with your real Space link, for example:
  - `Space URL: https://huggingface.co/spaces/<user>/faultpilot-v01`

Commit and push.

---

## Common issues and quick fixes

### 1) Build fails on dependencies
- Re-check `requirements.txt` and `pyproject.toml` sync.
- Verify `openai` dependency is present in both.

### 2) Space starts but query fails immediately
- Check if user entered API key in UI.
- Verify key has active billing/quota.

### 3) Slow first response
- First run may download model artifacts.
- Retry after warm-up.

### 4) No retrieval results
- Confirm `data/processed/*.jsonl` and retrieval artifacts are in repo.

---

## Final certification checklist

- Public Space URL works without login.
- README includes required key list and cost estimate (`<= $0.50` trial usage).
- README lists at least 5 optional functionalities implemented.
- API keys are not committed.
- App behavior matches course constraints.
