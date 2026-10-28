# 02 · Architecture

> Decided items are marked **[decided]**. Items marked **[proposed]** are sensible defaults written for the build; change them if a better option shows up, and log the change in `15-decisions-log.md`.

## Pipeline

```
 camera(s) / phone stream / imported video        sensors, instrument logs (later)
            │                                              │
            ▼                                              ▼
 ┌─────────────────────── Python worker (owns the camera) ───────────────────────┐
 │ capture loop → frame-quality check → WATCHER (per vessel ROI, keyframe compare) │
 │        │ trigger / scheduled check-in / Continuous tick                          │
 │        ▼                                                                         │
 │ segment()  ── SAM 3.1 (Meta API) ──► masks per vessel/object                     │
 │        ▼                                                                         │
 │ MEASURE (code only): area, height, count, color, ± from noise floor, units      │
 │        ▼                                                                         │
 │ ANALYZE (code only): control vs treatment, curve fit, change points, stats      │
 │        ▼                                                                         │
 │ reason(tier) ── Muse Spark (routine) / Muse Wonder (deep) ──► JSON note         │
 │        ▼                                                                         │
 │ CLAIM CHECKER (code) ──► save note | reject & regenerate                         │
 │        ▼                                                                         │
 │ SQLite + files ──► SSE events ──► dashboard      ffmpeg ──► timelapse, reel      │
 │ Ax (next settings) · smart-plug rules (with limits) · ntfy alerts               │
 └──────────────────────────────────────────────────────────────────────────────────┘
            ▲ REST + SSE + MJPEG (localhost)
 ┌──────────┴──────────┐
 │ Next.js dashboard   │ setup wizard, live view, timeline, charts, notes, reports
 └─────────────────────┘
```

## Hard rules [decided]

1. **The LLM never computes numbers.** Area, height, count, color, rates, statistics are computed in Python. Models only interpret.
2. **Only two functions call models:** `segment()` (vision) and `reason()` (language). Nothing else imports a model client.
3. **Model names, base URLs and keys live in config/env**, never hard-coded.
4. **Prompts live in `prompts/`**, never inline.
5. **Every model call is logged:** model, tier, input/cached/output tokens, cost, latency.
6. **Evidence is never overwritten.** Four layers stored separately: observation → measurement/detection → AI explanation → researcher review.

## Adapters [decided]

```python
# config.py
REASONING_TIERS = {   # provider + model per tier (D-06, D-33)
    "routine": {"provider": "meta", "model": "muse-spark-1.3"},   # notes, checkpoints
    "deep":    {"provider": "meta", "model": "muse-wonder-1.0"},  # verdicts, critique, next run, report
}
# Optional later (open-weight bonus): {"provider": "baseten", "model": "meta-models/muse-spark-open-1026"}
PROVIDERS = {
    "meta":    {"base_url": "https://api.meta.ai/v1",         "key_env": "MODEL_API_KEY"},
    "baseten": {"base_url": "https://inference.baseten.co/v1", "key_env": "BASETEN_API_KEY"},
}
SEGMENT_BACKEND = "meta_api"       # or "local_sam_image" (fallback, see 10-hardware)
```

```python
# Every vision backend returns Argus's own format, so swapping models never breaks the rest.
@dataclass
class Track:
    id: int            # stable across frames
    label: str         # "foam", "seed", "colony"
    mask: np.ndarray   # bool H×W
    box: tuple         # x1, y1, x2, y2
    confidence: float | None

def segment(frame, prompt: str, vessel_roi=None) -> list[Track]: ...
def reason(prompt_parts, images=None, tier="routine", schema=None) -> dict: ...
```

- SAM 3.1 takes **one concept per request** (no "seed, root" lists). A recipe with two concepts makes two requests.
- In image mode, object IDs are kept stable by matching masks to the previous frame by overlap (IoU). In API video mode, SAM tracks IDs itself.

## Who sees what [decided]

| Part | Sees | How often |
| --- | --- | --- |
| Watcher (local, free) | Every frame, inside each vessel's region | Constantly |
| SAM 3.1 | Frames when triggered (or each Continuous tick) | On change / on rhythm |
| Measurement code | SAM masks over time | Every SAM run |
| Muse Spark / Wonder | **Measurements over time + 1–2 snapshots + locked plan + notes + running summary** | Only on meaningful events and checkpoints |

The reasoning model does **not** watch the video. Every frame is processed by the watcher and SAM; the model reads the numbers from all of them plus a before/after snapshot pair. Optional **short clip mode** (5–10 s MP4) for motion-heavy recipes (bubbling, mixing) because Muse Spark accepts video; costs more, so it's a per-recipe setting.

## Processes [proposed]

| Process | Tech | Job |
| --- | --- | --- |
| Worker | Python 3.12, FastAPI + uvicorn on `localhost:8000` | Owns cameras (a webcam often can't be opened by two programs at once on Windows), runs the pipeline, serves REST, SSE events and an MJPEG preview |
| Dashboard | Next.js + TypeScript | UI only; talks to the worker API. Never touches the camera or the database directly |
| Storage | SQLite (Python `sqlite3`) + files on disk | One writer (the worker) avoids locking problems |

## Storage sketch [proposed]

| Table | Key columns |
| --- | --- |
| `experiments` | id, recipe, plan_json (locked), plan_locked_at, mode, status |
| `vessels` | id, experiment_id, label, role (control/treatment/replicate), group, roi_polygon, position_index |
| `frames` | id, experiment_id, camera_id, ts, path, quality_flags |
| `measurements` | id, vessel_id, frame_id, ts, metric, value, unit, uncertainty, method_version |
| `events` | id, experiment_id, vessel_id, ts_start, ts_end, kind, source (rule/model), evidence_frame_ids |
| `notes` | id, experiment_id, ts, author (ai/researcher), tag (observation/intervention/question), body_json, model, status (draft/approved/dismissed) |
| `model_calls` | id, ts, function, model, tier, input_tokens, cached_tokens, output_tokens, cost_usd, latency_ms |
| `actions` | id, ts, device, command, reason, approved_by, result |
| `audit_chain` | batch_id, sha256(prev_hash + batch) |

Files: `data/<experiment>/frames/`, `keyframes/`, `clips/`, `exports/`.

## Repository layout [proposed]

```
C:\Projects\Argus\
├── CLAUDE.md                  ← always-loaded guide for Claude Code
├── THIRD_PARTY_NOTICES.md
├── .env.example  .gitignore
├── .claude\skills\            ← 7 reviewed skills (see 12-skills.md)
├── docs\knowledge-base\       ← this folder
├── prompts\                   ← system rules, deep critique, JSON schemas, recipe method cards
├── recipes\                   ← one YAML/JSON per experiment type
├── worker\                    ← Python: capture, watcher, segment, measure, analyze, reason, api
└── web\                       ← Next.js dashboard
```

## Live updates

The dashboard subscribes to worker **Server-Sent Events** (new measurement, event, note, action). Same pattern used in FoodLine DC.
