# Argus: design spec

> Written Oct 28, 2026 from the knowledge base (`docs/knowledge-base/`) and the decisions approved in this session (D-36 to D-50). The knowledge base stays the source of truth for facts, prices and verified library verdicts; this spec says **what we build and how the parts fit**. The implementation plan (next document) turns it into ordered tasks.
>
> UI reference: the design canvas at https://claude.ai/artifact/2JeEMitFwx3e3egzNbptwg (v2 "soft instrument"). All numbers on it are sample data.

## 1. Goal and what "done" means

Argus is an AI lab partner that runs a closed experiment loop on a desk: **plan → watch → measure → judge → next run**. A webcam or imported video goes in; calibrated measurements with ±, checked AI notes, a four-level verdict and the next batch of settings come out.

Done for the hackathon (submission Wed Nov 4, 9:00 PM ET) means:

1. A researcher can set up an experiment, run it live or import a recording, watch it with synced video, timeline, notes and views, get a verdict and a next-run batch, and export a report and a public replay link, **end to end on real data**.
2. Two real experiments have gone through Argus: the multi-day germination recording (imported) and one fast live experiment with at least two Ax rounds.
3. A validation table with real numbers (length accuracy, staged events caught, claim-checker rejections).
4. Public repo with README, a 3-minute video, and a public replay page judges can open without hardware.

Scoring weights to optimize for: Impact 30%, Use of Meta AI tooling 25%, Demo 25%, Technical depth 20% (`01`).

## 2. Scope

**Must (M1–M13, `07-features.md`):** setup wizard with measurement preview · Argus Card calibration · multi-vessel tracking · 3 recipes (seed germination, colour-change reaction, foam/growth height) · measurements with ± · curve fit and time-to-target · structured notes with claim checker · four-level verdict with rivals and critique · timelapse with synced overlay · Ax next run, batched · import video · public replay page · view catalog with AI-picked views.

**Should (only if Musts are on track by Nov 1):** voice notes (cheap, likely in), report PDF/CSV/run record (likely in, the Report screen needs them), phone alerts via ntfy, Ask Argus chat, DOE planner and replicate calculator.

**Out:** smart-plug control (D-44), sensors, robots, local SAM, Muse Spark Open on Baseten (D-33), RO-Crate and eLabFTW exports.

## 3. Architecture (D-48)

```
camera / imported video ──► Python worker (FastAPI, localhost:8000) ──REST + SSE + MJPEG──► Next.js app (localhost:3000)
                              owns cameras, pipeline, SQLite, files,                         UI only
                              every model call                                              │
                                                                                            └─ same app on Vercel with
                                                                                               ARGUS_PUBLIC_REPLAY=1:
                                                                                               /replay/<run> from a bundle
```

- **One command** (`uv run argus dev`) starts the worker and `next dev`.
- **Three source modes, always labeled** in the title row and on the video:
  - **LIVE:** a camera through the live pipeline.
  - **IMPORTED:** a video file or photo folder through the same pipeline, faster than real time, with a progress readout.
  - **REPLAY:** a finished run's stored results played back on the timeline. No model calls; nothing is recomputed.
- **One clock.** Every record carries `t`, the real seconds since the run's start. The UI playhead, video, masks, charts and notes all key off `t`; each video proxy has an index mapping its frames to `t`.
- **Public replay.** Deploy the same Next.js app to Vercel with `ARGUS_PUBLIC_REPLAY=1`. Middleware allows only `/replay/*`, and those pages read a run bundle (§9.3) from `public/runs/<run_id>/` instead of the worker. If the video proxy is too big for a static file, it goes to Vercel Blob or a GitHub release.

### 3.1 Repository layout

```
worker/
  argus/
    config.py            settings from env (pydantic), model tiers, prices, caps
    domain.py            pydantic types shared by every module (§5)
    capture/             sources (webcam DirectShow MJPEG, video files, photo folder), frame-quality gate
    watcher/             ROI keyframe compare (SSIM + Lab stats), debounce, cooldown, check-in, presets
    segment/             segment(): SAM 3.1 image and video, meta-sam-parser, IoU tracking, mask → simplified outline
    calibration/         card (done), card detection → homography and mm/px ±, print-scale check, colour reference, drift
    measure/             metrics (area, height, skeleton length, count, Lab colour and ΔE), noise floor, ± propagation
    analyze/             fits with CIs, events and onsets, change points, group stats, dose response, censoring,
                         derived numbers with IDs, verdict ceiling
    reason/              reason(): Responses API, tiers, prompt assembly from prompts/, cache keys, cost log, spend cap
    claims/              claim checker and the renderer that turns {ref} tokens into "4.6 ± 1.2 mm"
    views/               view catalog (ids, needs, params) and selection (Muse pick → validate → defaults)
    optimize/            Ax loop: attach finished vessels, constraints, batch suggestions
    media/               ffmpeg: proxy video, thumbnails, timelapse with overlay, highlights reel
    pipeline/            run orchestration for LIVE and IMPORTED, job queue
    storage/             SQLite (WAL, one writer), schema, repositories, file store, audit chain, run bundle export
    api/                 FastAPI routes, SSE broker with event IDs, MJPEG stream
    recipes/             TOML loader and validation
    cli.py               argus dev | import | export-bundle | card
  tests/   probes/
recipes/                 seed-germination.toml, colour-reaction.toml, foam-height.toml, general.toml
prompts/                 system/, deep/, recipes/<id>/method.md, setup/, schemas/
web/                     Next.js (App Router, TypeScript strict)
  app/                   experiments, experiments/[id]/(run|results|next|report|setup), views, settings, replay/[runId]
  components/            shell, frame, timeline, feed, readouts, verdict, evidence chip, views/*, charts/*
  lib/                   typed API client, RunSource (live | bundle), playhead store, number formatting
  styles/tokens.css      from the canvas's argus.css
assets/argus-card/       printable card (done)
```

## 4. Pipeline

### 4.1 LIVE

1. A capture thread reads the camera (DirectShow, MJPEG requested before the size, properties read back and recorded as locked / not locked / unknown).
2. The **frame-quality gate** rejects blurred, over-exposed and occluded frames and logs them. A hand in frame becomes a likely-intervention event.
3. The **watcher** compares each vessel's ROI with that vessel's last analyzed frame (SSIM plus Lab mean and spread, light-normalized). It triggers on change, with debounce, cooldown and scheduled check-ins. In **Continuous** mode it ticks on a rhythm instead; **Hybrid** switches between the two.
4. On trigger: `segment()` in image mode, one call per concept, on the full frame. Detections are assigned to vessels by ROI and matched to existing tracks by IoU.
5. Measurements are computed (§6), then derived numbers and events are updated.
6. `reason()` runs on events and at checkpoints only (rate-limited), then claims are checked and the result is stored.
7. Every record is stored and pushed to the UI over SSE.

### 4.2 IMPORTED

1. The researcher gives the files (in order; split MP4s are fine), the start time and the time-scale factor (e.g. ×600). Argus builds a frame index from video time to `t`.
2. Argus samples at the recipe's analysis step (default **one frame per 5 real minutes** for slow runs; every frame for fast runs) (D-38).
3. The quality gate runs on the sampled frames. The watcher runs over all frames (it's cheap) to catch events between samples.
4. Segmentation uses **SAM 3.1 video mode on one crop per vessel, per concept** (≤16 objects, ≤15,000 frames per request). Image mode with IoU tracking is the fallback.
5. From step 5 of LIVE on, everything is identical. Progress is shown as "Analyzing 26:00 of 40:00 · 4.2× real time".

### 4.3 Job queue and limits

- Model calls are async with concurrency limits (SAM 2, Muse 2), so capture never waits on the network.
- Retries use backoff. If SAM fails, frames are still recorded and queued for later.
- A per-run spend cap (`RUN_SPEND_CAP_USD`) stops model calls; local measuring continues and the UI says why.

## 5. Data model and evidence layers

The four layers never overwrite each other (D-20). The SQLite tables:

| Table | Holds | Layer |
| --- | --- | --- |
| `experiments` | id, title, recipe_id + version, status (draft, locked, running, finished) | — |
| `plans` | experiment_id, version, hypothesis, prediction, threshold, rivals[], locked_at, sha256; edits add versions, the verdict uses v1 | Observation |
| `runs` | id, experiment_id, mode (live, imported, replay), source info, time_scale, start_time + its source, round (Ax), status | — |
| `vessels` | id, run_id, label (A–F), blind_label, role (control, treatment), condition (factor → value + unit), roi polygon | — |
| `calibrations` | run_id, card spec, homography, mm_per_px ± , print_scale, colour references, camera property states | Observation |
| `frames` | id, run_id, t, file path, quality flags, analyzed | Observation |
| `detections` | frame_id, vessel_id, track_key, concept, outline (simplified polygon), area_px, confidence, backend | Measurement |
| `measurements` | id, vessel_id, frame_id, t, metric, value, uncertainty, unit, method_version | Measurement |
| `derived` | id, run_id, kind (fit, T50, difference, rate, dose-response…), inputs[], value, ci_low, ci_high, unit, method_version | Measurement |
| `events` | id, run_id, vessel_id, t_start, t_end, kind, source (watcher, rule, model, researcher), evidence frame ids | Measurement |
| `notes` | id, run_id, t, author (ai, researcher), level, body (rendered), refs[], model_call_id, check_status, review_status | Explanation / Review |
| `note_attempts` | every AI draft with its claim-check result, including rejected ones | Explanation |
| `verdicts` | id, run_id, provisional, ceiling, verdict, draft, critique, model calls | Explanation |
| `reviews` | target, action (confirm, dismiss, correct), comment, t | Review |
| `view_choices` | experiment_id, picks[] (view id, slot, params, reason, source: muse, rule or researcher) | — |
| `ax_trials` | experiment_id, round, trial index, params, vessel_id, outcome | — |
| `model_calls` | t, function, model, tier, input/cached/output/reasoning tokens, images, frames, cost, latency, cache key, status | — |
| `audit_chain` | batch id, sha256(previous hash + batch) over measurement batches | — |

Files go under `data/<experiment>/<run>/`: `frames/`, `crops/`, `proxy.mp4` plus `proxy-index.json`, `thumbs/`, `exports/`.

## 6. Measurement, calibration and analysis

- **Card detection:**
  1. ArUco `DICT_4X4_50`. IDs 0–3 mean the standard card, IDs 4–7 the compact card.
  2. A homography from the marker corners gives the viewing-angle correction and mm/px. The ± comes from the reprojection error plus the print-scale check: the researcher's measured 100 mm line.
  3. With no card, a two-click ruler calibration is the fallback.
- **Colour:** Lab means of the neutral and colour patches give the first frame's reference; later frames are corrected relative to it. Drift beyond correction raises a warning.
- **Noise floor:** the spread of each metric over a still period (the first minutes, or pre-sprout frames on imports) plus calibration error. Uncertainty is propagated with `uncertainties`. Effects under 3× the noise floor are labeled "not real yet". Rounding: uncertainty first, then the value to the same decimal.
- **Metrics:**
  - area
  - height along the vessel axis
  - skeleton length (roots, cracks)
  - count with a size filter
  - Lab mean and ΔE from baseline
  - cloudiness (later)

  Each metric has a `method_version`.
- **Germination specifics:**
  - Concepts are "mung bean" and "root".
  - A bean is sprouted when an attached root's skeleton exceeds 2 mm.
  - If SAM under-segments thin roots: threshold white-on-brown inside each bean's neighbourhood within the jar ROI, then skeletonize.
- **Fits** (scipy `curve_fit`, covariance kept for CIs): logistic, Gompertz, exponential, first-order decay, linear. Time to target comes from the fitted curve with a delta-method CI. A value not reached in the run is reported as "> end time" (censored), never as a number.
- **Statistics:**
  - group comparisons on vessel-level results (never frames or beans as replicates)
  - dose response on jar results
  - multiple-comparison correction when several are made
- **Derived numbers with IDs:** every number the AI may cite (difference vs control, % change, T50 ± CI, rates, counts, times of events) is computed here and given an ID (D-40). Plan values (threshold, doses, checkpoint time) get IDs too, so a note can cite them.

## 7. AI: `segment()`, `reason()`, claims, verdicts

### 7.1 Contracts (D-05, D-36)

```python
def segment(media: Frame | VideoClip, concept: str, *, roi: Polygon | None = None, mode: Literal["image", "video"]) -> list[Track]
async def reason(task: ReasonTask, *, tier: Literal["routine", "deep"], schema: str, images: list[Snapshot] = []) -> ReasonResult
```

- Both read model IDs, base URL and key from `config`. Nothing else imports a model client.
- `reason()` uses the Responses API with strict `text.format` JSON. Routine calls use effort `minimal` and `max_output_tokens` 4000; deep calls use effort `medium`. Every call sends a `prompt_cache_key` of `argus:{experiment}:{tier}:{prompt_version}`. Snapshots are 768 px on the long side (D-39, D-46).
- **Prompt order** (cache-friendly):
  1. rules
  2. method card
  3. locked plan
  4. running summary
  5. the MEASUREMENTS block (IDs, values, ±, units)
  6. recent events and notes
  7. 1–2 snapshots
- **Deep-tier fallback:** if `muse-wonder-1.0` fails, the call goes to `muse-spark-1.3` at effort `high` and the note says so.
- **Logging:** every call is logged (§5) and counted against the per-run cap.

### 7.2 Notes and the claim checker (D-40, D-41)

**Note schema v2** (replaces `prompts/schemas/note.json`): the same fields, except that text fields cite numbers only as `{ref:<id>}` tokens and `numbers_used` becomes `refs_used: [id]`.

**Checker, in order:**
1. The output matches the schema.
2. Every token and every `refs_used` entry exists in this call's MEASUREMENTS block.
3. No digit appears in a text field outside a token (model names are stripped before this check).
4. `hypothesis_status` is within the verdict ceiling.
5. Every `evidence_id` exists.

**Pass:** render the tokens ("4.6 ± 1.2 mm", "41 h") and save.

**Fail:**
1. Save the attempt with its reasons and retry once with them.
2. If the retry fails too, save a plain note written by code from the same data, labeled as such.

Rejections feed the validation table.

**Levels:** `event` notes on events, `checkpoint` notes on schedule, `insight` notes from the deep tier. Repeated "no change" notes collapse into one line.

### 7.3 Verdicts

1. **Code computes the ceiling** from:
   - direction versus the prediction
   - effect ÷ noise floor
   - the number of replicates showing the effect
   - each planned rival (resolved, with evidence, or open)
   - run state (before or after the plan's checkpoint, still running or ended)

   The ceiling is a set of allowed verdicts. Before the plan's checkpoint: {TOO_EARLY}. With an open rival or too few replicates: {INCONCLUSIVE}. With a clear effect in the predicted direction: {SUPPORTED, INCONCLUSIVE}. With enough data and no effect or the opposite effect: {NOT_SUPPORTED, INCONCLUSIVE}.
2. **Muse Wonder drafts** the verdict, explanation, rivals and "what would change it" in a new strict `verdict.json` schema with refs.
3. **A second Wonder pass critiques the draft** (`verdict-critique.md` and `verdict_critique.json`). The final verdict is the critique's revised verdict if that is in the allowed set; otherwise the draft's verdict if that is allowed; otherwise the most cautious allowed verdict (INCONCLUSIVE, or TOO_EARLY before the checkpoint).
4. **Provisional after the checkpoint while the run continues.** The verdict becomes final only when the run ends and the researcher confirms it.

### 7.4 Other model uses

| Use | Model | Output |
| --- | --- | --- |
| Draft the setup from plain words | Muse Spark | `recipe_draft.json`: concepts, metrics, events, rivals, chosen from the recipe catalog's vocabulary |
| Pick views | Muse Spark | `view_picks.json` (§8) |
| Explain the Ax batch | Muse Spark | A note with refs to the Ax predictions and to past trials |
| Voice notes | Muse Voice Transcribe | Transcript → researcher note (researcher layer; its numbers are the researcher's) |

## 8. View catalog and AI-picked views (D-49)

- **The fixed frame** appears on every experiment: camera with outlines, readouts, timeline (filmstrip, one lane per vessel for the main measurement, Argus and You lanes), notes and events, verdict, drift and noise. Readouts and lanes follow the recipe's **main measurement**, and readouts change shape with it: tiles for counts and lengths, level gauges for heights.
- **The views** are typed components from a catalog. Each entry has:
  - `id`
  - title
  - the question it answers
  - `needs`, a predicate over the experiment design and recipe (for example `factor.numeric && factor.levels >= 3`)
  - params: metric, group_by, threshold, factor
  - slot: run or results
  - the web component that renders it
- **Built for the hackathon (12):** curves over time · share done so far · event grid · colour strip · level gauges · group comparison · dose response · time to target · prediction and next batch · best so far by round · side by side · drift and noise.
- **Next (5):** rate over time · onset raster · two factors · key frames · size distribution.
- **Selection:**
  1. In setup, Muse Spark returns `view_picks.json`: picks with `view_id` (an enum of catalog IDs), slot, params and a one-line reason.
  2. Code checks each pick's `needs` against the design. Failed picks are dropped and recorded; empty slots are filled from recipe defaults.
  3. The researcher keeps, swaps or removes picks, or asks in words ("show root length per bean"), which is one more Muse call.
  4. Rejected views are listed with the reason ("needs 2 or more Ax rounds").
- **Rules:** a view only reads stored measurements and derived numbers. It never computes statistics in the browser beyond drawing.

## 9. Web app

### 9.1 Design system (v2 "soft instrument", D-50)

- **Tokens:** copied from the canvas's `argus.css` into `web/styles/tokens.css`. Light (default) and dark themes are switched by a `data-theme` attribute, following the system setting until the user chooses.
- **Shape:** panel 20 px, video 16 px, tile 14 px, lane 10 px, pill controls.
- **Colour:**
  - White tiles on the `#eceff2` ground, separated by tone steps rather than lines.
  - Teal is the one accent: live, selection, main data. Ink `#0B1220`, teal `#0FA3A3` / `#2DD4BF`.
  - Status colours stay separate.
- **Type:** one typeface for words and figures, with tabular digits. **Inter by default; Manrope or Plus Jakarta Sans if Aymen picks one (open).** Monospace only for IDs.
- **Motion tokens:** 150 / 220 / 320 / 600 ms; ease-out `cubic-bezier(.2,.8,.2,1)`. Transform and opacity only. `prefers-reduced-motion` keeps content and drops travel. The moments are the table on the canvas's Foundations board.
- **Accessibility:** real buttons and links, visible focus rings, 4.5:1 text contrast, no information carried by motion alone.

### 9.2 Screens

| Screen | Route | Key behaviour |
| --- | --- | --- |
| Experiments | `/` | Table of experiments with state, verdict, spend; start from a recipe or plain words |
| Setup wizard | `/experiments/[id]/setup` | Describe (Muse draft) → source → vessels (SAM boxes draw in; keep, merge, remove) → labels and blinding → calibration → lighting check → measurement preview on the frame → **views (Muse picks)** → hypothesis, prediction, threshold → plan lock |
| Run | `/experiments/[id]/run` | Frame with outlines and on-frame pills; readouts; editor-style timeline with playhead handle; notes feed with thumbnails and evidence chips; views row; voice note; log intervention. Clicking a vessel selects it everywhere |
| Results | `/experiments/[id]/results` | Verdict with ceiling checks, critique findings, rivals; results-slot views; per-vessel table; validation strip; confirm or dismiss |
| Next run | `/experiments/[id]/next` | Ax prediction with band and the batch marked; batch table with randomized positions; Muse's explanation; what-if plans; create the next run |
| Report and export | `/experiments/[id]/report` | Draft report from logged settings; approve; PDF, CSV, run record JSON, timelapse, highlights reel, publish replay |
| Settings and usage | `/settings` | Credit used, cache hit rate, per-run call log summed from rows, models by tier, spend cap |
| View catalog | `/views` | Every view with its question, needs and state |
| Phone | responsive | Under 720 px: top bar, latest frame, needs-your-answer card, readouts list, bottom bar |
| Public replay | `/replay/[runId]` | Player with overlay, verdict, views, moments list, how-it-works, validation; no worker needed |

### 9.3 Data layer

- **`RunSource` interface**, with two implementations:
  - `LiveSource`: REST plus SSE, with `Last-Event-ID` resume.
  - `BundleSource`: static JSON files.

  The run bundle uses the same JSON shapes as the live API: run summary, vessels, measurements, derived, events, notes, verdict, views, proxy index, thumbnails.
- **One playhead store** holds `t`, mode (follow live, or play at a speed) and the selected vessel. Components subscribe with selectors.
- **Types** come from the worker's OpenAPI schema (`openapi-typescript`), so the UI and the API can't drift.
- **Charts** are our own SVG on `d3-scale` and `d3-shape`, with a shared chart frame (axes, gridlines, annotations, hover). Shapes: line, step, band, dots, intervals, mosaic, colour strip, gauge.

## 10. Worker API (summary)

REST under `/api`:

- **Experiments:** `GET /experiments`, `POST /experiments`, `GET /experiments/{id}`
- **Setup:**
  - `POST /experiments/{id}/describe`
  - `POST /experiments/{id}/source` (webcam index, video upload or path, folder)
  - `POST /experiments/{id}/vessels/detect`, `PUT /experiments/{id}/vessels`
  - `POST /experiments/{id}/calibrate`, `POST /experiments/{id}/lighting-check`
  - `POST /experiments/{id}/preview`
  - `POST /experiments/{id}/views/pick`, `PUT /experiments/{id}/views`
  - `POST /experiments/{id}/plan/lock`
- **Runs:**
  - `POST /experiments/{id}/runs` (start live or import), `POST /runs/{id}/stop`
  - `GET /runs/{id}`, `GET /runs/{id}/timeline?from&to`
  - `GET /runs/{id}/frames/{frame}.jpg`, `GET /runs/{id}/proxy.mp4`
  - `POST /runs/{id}/notes`, `POST /runs/{id}/voice`
- **Results:** `GET /runs/{id}/results`, `POST /runs/{id}/verdict`, `POST /verdicts/{id}/review`
- **Next run:** `POST /experiments/{id}/next-run`, `POST /experiments/{id}/next-run/accept`
- **Report and export:** `GET /runs/{id}/report`, `POST /runs/{id}/report/approve`, `GET /runs/{id}/export/{csv|json|pdf}`, `POST /runs/{id}/media/{timelapse|reel}`, `POST /runs/{id}/bundle`
- **Usage and cameras:** `GET /usage`, `GET /cameras`, `GET /cameras/{i}/stream.mjpg`

SSE at `GET /api/events` sends: `measurement`, `event`, `note`, `note_rejected`, `verdict`, `run_progress`, `frame_analyzed`, `spend`, `alert`. Each carries the run ID and `t`.

## 11. Media and demo assets

- **Proxy video per run:** analyzed frames → H.264 1280×720, a keyframe every 12 frames (smooth scrubbing), plus `proxy-index.json` mapping frames to `t`. Thumbnails are generated for the feed and the filmstrip.
- **Timelapse with overlay (M9):** in the app, the REPLAY view is the synced timelapse. The shareable MP4 is rendered by compositing overlay frames (chart, timestamp, notes) onto the proxy and encoding with ffmpeg. The overlays are drawn with Pillow, 2× supersampled, in the chosen typeface (Pillow needs approval, §13).
- **Highlights reel:** 30–60 s, chaptered by events, a few seconds of pre-roll and post-roll around each.
- **Demo-video motion graphics:** logo sting, title cards, callouts. These are made with **HyperFrames** (pending approval, §13) from the brand SVG and tokens, as a dev tool, not a product dependency. Transparent exports for the editor. The originals in `brand/` stay until Aymen approves a refined mark.
- **In-app logo states:** resting, watching (the point orbits the ring), locked (the ring closes). These are CSS and SVG, as on the canvas.

## 12. Testing and verification

- **Worker unit tests (pytest)** on fixtures with known answers:
  - card detection and the print-scale check
  - every metric on synthetic masks of known size and length
  - fits recovering known parameters, and censoring
  - derived numbers
  - the claim checker (valid, wrong ref, free digit, verdict above the ceiling)
  - the verdict ceiling table
  - the watcher: catches slow drift, ignores a lamp switch (on recorded fixture frames)
  - view `needs` predicates
  - storage and bundle round-trip
- **Model-dependent tests** use recorded responses (the SAM stream text, Muse JSON). Live API probes stay in `worker/probes/` and are run by hand.
- **Lint:** ruff (check and format), mypy on `argus/` (dev).
- **Web:** `tsc --noEmit` strict, ESLint, Prettier. Vitest (pending approval) for the formatters, `RunSource` and the playhead store. Every screen is checked in the browser at 1440, 768 and 390 px in both themes, with screenshots, before calling it done.
- **End-to-end:** an imported 15-minute real recording, then the germination import, then the live experiment. Each phase ends with evidence (test output, screenshots, real numbers).
- **Validation runs for the table:**
  - 10 objects of known length
  - staged events (dye drop, coin, light switch) with true times
  - claim-checker counts from real runs

## 13. Dependencies

| Status | Packages |
| --- | --- |
| **Approved and installed** (worker) | openai, meta-sam-parser, opencv-python, numpy, scipy, scikit-image, requests, pytest, ruff |
| **Approved in `11`, to install** | statsmodels, uncertainties, ax-platform, ruptures, fastapi, uvicorn; Node: next, react, typescript |
| **Recommended, waiting on Aymen (Q-16, Q-17)** | Tailwind CSS v4, Radix UI primitives, lucide-react, d3-scale + d3-shape, openapi-typescript (dev), Motion (`motion`), HyperFrames (dev tool for video only) |
| **New in this spec, waiting on Aymen** | Pillow for overlay rendering (already present as a scikit-image sub-dependency, HPND licence); Vitest (dev, MIT); mypy (dev, MIT) |

Nothing outside the first two rows is installed before approval.

## 14. Risks

| Risk | Mitigation |
| --- | --- |
| The germination run hasn't started (critical path) | Start by Oct 29. Build import on a 15-minute real recording first, so the pipeline is proven before the footage arrives. If the footage fails, the live experiment and a shorter run carry the demo |
| SAM on thin roots | Test on a phone photo about 24 h into the run; classical threshold-and-skeleton fallback inside SAM's bean regions |
| UI scope (8 screens, 12 views, motion) | Shared chart frame; views share primitives; Should features cut before any Must; Nov 3–4 reserved for the demo |
| `muse-wonder-1.0` is a Preview model | Configured fallback to Spark at high effort, labeled |
| Windows camera quirks (Nuroum not yet tested) | Probe in the first build session; record lock states honestly |
| Large proxy video on Vercel | Compress; fall back to Vercel Blob or a GitHub release |
| Spend | Per-run cap, 768 px snapshots, cache keys, sampling step for imports; expected total $30–45 of $150 |

## 15. Open items

1. **Typeface:** Inter (default), Manrope or Plus Jakarta Sans.
2. **Approve dependencies** in §13, rows 3 and 4 (animation and video tools, UI libraries, Pillow, Vitest, mypy).
3. **Fast live experiment** (Q-12): iodine clock recommended.
4. **Germination start** (Q-14): by Oct 29, with the suggested tweaks in `20`.
5. **Nuroum webcam test:** when it's plugged in.

## 16. Build order (the plan will detail it)

The implementation plan is written phase by phase: phase 1 in full task-level detail first, and each later phase planned at its start with what the earlier phases taught. Each phase ends with a review and evidence before the next begins.

| Phase | Dates | Work |
| --- | --- | --- |
| 1 | Oct 28–29 | Worker foundation (config, domain types, storage, API skeleton with SSE, recipes); calibration detection; measurement core with tests. Web scaffold with tokens and shell |
| 2 | Oct 29–30 | `segment()` with tracking and outlines; import pipeline with sampling and per-vessel SAM video; live capture, quality gate and watcher. Run view frame, readouts and timeline on real data |
| 3 | Oct 30–31 | `reason()`, prompts, claims, notes, events, verdict ceiling and critique. Feed, evidence chips, verdict UI; setup wizard |
| 4 | Oct 31 – Nov 1 | Analysis (fits, stats, derived, dose response); view catalog and selection; Ax loop. The 12 views; Results and Next run screens |
| 5 | Nov 1–2 | Germination import end to end; live experiment rounds; report and exports; settings and usage; phone |
| 6 | Nov 2–3 | Proxy, timelapse and reel; run bundle and Vercel replay; motion polish; validation runs; README; demo footage; logo sting |
| 7 | Nov 4 | Edit the video, final checks, submit early; X post |
