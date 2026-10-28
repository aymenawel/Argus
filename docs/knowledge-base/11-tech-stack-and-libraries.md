# 11 · Tech stack and libraries (verified)

> Every entry from the earlier "Argus Build Resources" doc was re-checked on **Oct 27, 2026** against PyPI, GitHub or official docs, and judged on one question: **is using it better than writing it ourselves?** Verdicts: **USE** · **USE LATER** · **OPTIONAL** (only if a stated condition happens) · **BUILD** (write our own, it's small) · **SKIP** · **REFERENCE** (learn from the design, don't install).

## Runtime versions

- **Python 3.12** for the worker. Why: Ax needs ≥3.11, ruptures supports <3.14, the K-Dense skill scripts target ≥3.12. The machine had only 3.11/3.13/3.14, so **uv** (0.13.1, already installed) provides CPython 3.12.15; `worker/pyproject.toml` pins `>=3.12,<3.13` and `uv.lock` pins every version (D-45). Run with `uv run --env-file ../.env ...` from `worker/`.
- Node LTS (v24.13 installed) + Next.js + TypeScript for the dashboard.

### Installed and verified Oct 27

| Package | Version | Note |
| --- | --- | --- |
| `openai` | 3.40.0 | Responses API with `text`, `reasoning`, `prompt_cache_key`, `prompt_cache_retention`, `input_tokens.count`. No longer pulls in `httpx` |
| `meta-sam-parser` | 0.1.0 | Works with `AsyncOpenAI` streams; see `04` |
| `opencv-python` | 5.0.0 | ArUco detector included |
| `numpy` / `scipy` / `scikit-image` | 2.5.4 / 1.18.1 / 0.26.0 | — |
| `requests` | 2.34.2 | Used for the multipart voice upload (and ntfy later) |
| `ax-platform` | 1.3.1 (torch 2.14.1+cpu, botorch 0.18.1) | Installs on Windows + 3.12 in ~45 s. Default strategy Center → Sobol → BoTorch ("MBM"); `attach_trial` + `complete_trial` on finished vessels skips the random start (verified: 6 attached trials → next batch came from MBM). `configure_optimization(objective=..., outcome_constraints=["sprouted_pct >= 80"])` works |
| ffmpeg | 9.0.2 (gyan.dev build, on PATH) | `imageio-ffmpeg` dropped; worker checks for ffmpeg at startup |
| `pytest`, `ruff` (dev only) | 9.2.0, 0.17.3 | Tests and lint/format, as asked in the build brief. Config in `worker/pyproject.toml` (line length 120) |

## Core stack

| Layer | Choice | Verdict | Why |
| --- | --- | --- | --- |
| Model client | `openai` Python SDK → `https://api.meta.ai/v1` | USE | Meta's API is OpenAI-SDK compatible; docs use the Responses API |
| SAM output parsing | `meta-sam-parser` (official, Python ≥3.10, no dependencies, SAM License) | USE | SAM returns a custom streamed text grammar; the official parser decodes masks to raster/RLE and builds box/point prompts. Writing our own would cost hours for no gain |
| SAM in the browser | `@meta-sam/react`, `graphics`, `video` (npm, same repo) | OPTIONAL | Only if drawing live masks in React gets fiddly; otherwise the worker sends overlay images |
| Capture, watcher, drawing | `opencv-python` | USE | Camera I/O, color stats, ArUco, drawing overlays |
| Image metrics | `scikit-image` | USE | SSIM, regionprops, skeletonize |
| Math | `numpy`, `scipy` | USE | Curve fitting with covariance, Latin hypercube (`scipy.stats.qmc`) |
| Statistics | `statsmodels` | USE | t-tests/ANOVA, power analysis |
| Uncertainty | `uncertainties` | USE | ± propagation on every number |
| Units | `pint` | OPTIONAL | Nice but adds friction; unit-suffixed column names are enough for the hackathon |
| Next-run suggestions | **Ax** (`ax-platform` 1.3.1, Jun 2026, MIT, Python ≥3.11; Bayesian optimization on BoTorch/PyTorch) | USE | Bayesian optimization is not something to write from scratch, and it's Meta tech. Install it on day 1–2 to catch Windows/PyTorch issues early |
| Change points | `ruptures` 1.1.10 (BSD-2, Python <3.14) | USE (Should) | Phase detection (lag/growth/plateau); small dependency, offline detection on the series so far is fine |
| Worker API | FastAPI + uvicorn | USE [proposed] | REST + SSE + MJPEG from one process that owns the camera |
| Storage | SQLite (stdlib `sqlite3`) + files | USE | Single writer, zero setup |
| Dashboard | Next.js + TypeScript, Server-Sent Events | USE | Same pattern as FoodLine DC |
| Video (timelapse, reel, clips) | **ffmpeg binary called with `subprocess`**; ffmpeg 9.0.2 already on PATH (`winget install Gyan.FFmpeg` on a new machine). `imageio-ffmpeg` not needed (D-45) | USE | See ffmpeg-python below |
| Alerts | ntfy via `requests.post` | USE (Should) | One HTTP call; free apps; topic name acts as a password |
| Smart plug | Shelly local HTTP RPC (our own ~15 lines) **or** `python-kasa` 0.12.0 (GPL-3.0+) | BUILD / OPTIONAL | See `10-hardware-and-control.md` |

## Changed or dropped after verification

| Item (from the old doc) | New verdict | Reason |
| --- | --- | --- |
| `ffmpeg-python` | **SKIP** | Last release 0.2.0 in **July 2019**; unmaintained. Call the ffmpeg CLI directly |
| PyAV | SKIP for now | Works, but the CLI is simpler for cutting and concatenating clips |
| `go2rtc` (MIT) | **SKIP** | The worker already owns the camera; a second process would fight for it. Serve MJPEG from the worker; read phone streams with `cv2.VideoCapture(url)` |
| `supervision` (0.31.2, MIT, active) | **SKIP** | Our needs are small: drawing masks/labels is ~20 lines of OpenCV; SAM video returns IDs; image mode uses simple IoU matching. Not worth another dependency |
| Ax code using `ax.service.ax_client.AxClient` | **Replace** | Ax 1.x API is `ax.api.client.Client` (example below) |
| DINOv2-small confirmation (`facebook/dinov2-small`, 22M params, Apache-2.0) | OPTIONAL | Only if the watcher shows false triggers in testing |
| PlantCV (4.11.3, MPL-2.0) | OPTIONAL | Basic plant metrics from SAM masks are a few lines. Use PlantCV only for ColorChecker detection/correction or advanced morphology |
| `pydoe` | OPTIONAL | Full factorial = `itertools.product`, LHS = `scipy.stats.qmc`. Pull in pydoe only for fractional factorial, Plackett-Burman, central composite or Box-Behnken. (Per the experimental-design skill, pyDOE3 was archived in May 2026 and development returned to `pydoe`; the skill's scripts target `pydoe==1.5.0`) |
| Self-hosted SAM (`facebookresearch/sam3` + gated `facebook/sam3.1` weights) | SKIP (fallback only) | API covers it; 4 GB GPU can't do video tracking |
| `trackpy`, `Cellpose` | USE LATER | Only if the demo includes particles or cells |
| MiTemperature2 | SKIP on Windows | Documented for Linux only (BlueZ tooling); use `bleak` later |
| `colour-checker-detection` (BSD-3; YOLO script AGPL) | USE LATER / optional | Only with a real ColorChecker |
| OpenPIV (GPL-3), OpenCFU (GPL-3), ToxTrac (GPL-3), Tracker | REFERENCE | Borrow methods; bundling GPL code would force Argus to GPL |
| eLabFTW Python API, RO-Crate | USE LATER | Export features after the hackathon |
| PyLabRobot (MIT) | FUTURE | Robot control (Opentrons OT-2, Hamilton, Tecan, plate readers) |
| Frigate NVR | REFERENCE | Same "cheap motion gate → expensive model" design. Borrow: events with start/end, best snapshot per event, pre/post-event footage, retention rules |
| `sparks-baird/self-driving-lab-demo` (MIT) | REFERENCE | Low-cost closed-loop lab (<$100 light demo); compares grid search, random search and Bayesian optimization. Good pitch material |
| Community skills collection "josephtr1285/skills" | **DROPPED** | Could not verify quality or origin |
| "K-Dense-AI/claude-scientific-skills (75 skills)" | **CORRECTED** | Repo is now `K-Dense-AI/scientific-agent-skills` (177 skills) |
| "jaechang-hits/scicraft" | **CORRECTED** | Repo is `jaechang-hits/SciAgent-Skills` |

## Ax 1.x example (verified against the current quickstart)

```python
from ax.api.client import Client
from ax.api.configs import RangeParameterConfig

client = Client()
client.configure_experiment(
    name="yeast_foam",
    parameters=[
        RangeParameterConfig(name="temp_c",  bounds=(20.0, 45.0), parameter_type="float"),
        RangeParameterConfig(name="sugar_g", bounds=(5.0, 20.0),  parameter_type="float"),
    ],
)
client.configure_optimization(objective="foam_mm")      # maximize; use "-1 * x" to minimize

trials = client.get_next_trials(max_trials=6)            # 6 vessels → 6 trials in parallel
for trial_index, params in trials.items():
    ...                                                  # Argus runs and measures this vessel
    client.complete_trial(trial_index=trial_index, raw_data={"foam_mm": 39.0})

best = client.get_best_parameterization()
```

Limits: needs **one number** to optimize; suggestions mean little before 2–3 completed rounds; best with 2–5 variables. For the demo, use short runs (10–30 min) so 3–5 rounds fit. Muse explains each pick in plain words; Ax picks the numbers.

## Licenses to respect

| Item | License | Meaning for Argus (public repo) |
| --- | --- | --- |
| SAM 3.1, meta-sam | SAM License | Fine to use via API/parser; read terms before redistributing weights |
| Meta cookbook | MIT | Copy patterns freely with attribution |
| Ax, BoTorch | MIT | Fine |
| PlantCV | MPL-2.0 | Fine to use; changes to PlantCV files must stay open |
| python-kasa, OpenPIV, OpenCFU, ToxTrac | GPL-3.0 | Keep optional/separate or reimplement the method |
| Installed skills | MIT / CC BY 4.0 | Attribution in `THIRD_PARTY_NOTICES.md` |
| what-if-oracle skill | CC BY-NC-SA 4.0 | Not copied or adapted |

## Install [decided, D-45]

```bash
cd worker
uv sync                       # Python 3.12 + locked versions from uv.lock
uv run --env-file ../.env python -m probes.sam
```

Add packages with `uv add <name>` (only ones with a USE verdict here, or after approval); `uv.lock` is committed. `uv export > requirements.txt` if a plain list is ever needed.
