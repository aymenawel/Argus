# Argus — guide for Claude Code

Argus is an AI lab partner that watches experiments through a webcam or USB microscope, measures change in real units, judges the researcher's hypothesis and suggests the next run (plan → watch → measure → judge → next run). Built solo by Aymen (team Argus Labs) for the **Meta Global AI Developer Hackathon**, Indie track, Push the Frontier. **Building period Oct 27 – Nov 4, 2026; submission due Nov 4, 9:00 PM ET.**

## Read before coding

- `docs/knowledge-base/README.md`: index of the knowledge base. Read `00`, `02` and `17` at the start of a session, then only the file for the task.
- Before adding a dependency: `docs/knowledge-base/11-tech-stack-and-libraries.md` (verified verdicts; some popular libraries are deliberately skipped).
- Before calling a Meta model: `docs/knowledge-base/04-models-and-api.md` (exact IDs, request shapes, limits).

## Non-negotiable rules

1. **The LLM never computes numbers.** Measurements, statistics and fits are Python code; models only interpret.
2. **Only `segment()` and `reason()` call models.** Model IDs, base URL and keys come from config/env.
3. **Prompts live in `prompts/`**; JSON output schemas in `prompts/schemas/`; every AI note passes the claim checker before saving.
4. **Log every model call** (model, tier, input/cached/output tokens, cost, latency).
5. **Never overwrite evidence:** observation → measurement → AI explanation → researcher review are separate records.
6. **Repo is public.** Never commit secrets; keys go in `.env` (git-ignored). Mirror new variables in `.env.example`.
7. **New work only.** Everything here is built during the hackathon; don't paste code from other projects.
8. **Safety:** no automatic hardware actions for flame, strong heat, pressure, hazardous chemicals or pathogens; hard limits on every device; no medical advice.
9. Use the vocabulary in `docs/knowledge-base/18-glossary.md`.

## Stack

Python 3.12 worker (OpenCV, scikit-image, numpy/scipy, statsmodels, uncertainties, Ax, ruptures, FastAPI) · Meta Model API via the `openai` SDK at `https://api.meta.ai/v1`: `muse-spark-1.3` (routine), `muse-wonder-1.0` (deep), `sam-3.1`, `muse-voice-transcribe-1.0`. The routine tier can run on Muse Spark Open via Baseten instead (`meta-models/muse-spark-open-1026`), switched in the app's Settings, falling back to `muse-spark-1.3` (D-77) · `meta-sam-parser` · SQLite + files · Next.js + TypeScript dashboard over SSE · ffmpeg CLI. Windows machine with a 4 GB GPU: SAM runs through the API.

## Where things go

`worker/` Python pipeline and API · `web/` Next.js UI · `recipes/` experiment types · `prompts/` model prompts and schemas · `docs/knowledge-base/` decisions and references · `.claude/skills/` reviewed skills (experimental-design, statistical-power, uncertainty-and-units, hypothesis-generation, scientific-critical-thinking, opencv, trackpy-particle-tracking).

## Keeping docs current

When you make or change a design decision, add a row to `docs/knowledge-base/15-decisions-log.md`. When you answer an item in `16-open-questions.md`, tick it and move the answer into the right file.
