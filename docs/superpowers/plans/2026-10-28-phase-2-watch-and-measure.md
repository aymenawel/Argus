# Argus Phase 2: Watch and Measure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A run that watches a camera or imports a video, segments vessels' contents with SAM 3.1, and stores calibrated measurements with ± as evidence, while the Run view shows the frame with outlines, a readout per vessel and a timeline, live or as the import progresses.

**Architecture:** The worker gains `capture/` (video files and webcam), a frame-quality gate, a `watcher/` that decides when to segment, `segment/` (the only module that calls SAM), a measurement engine that turns masks into recipe measurements, and `pipeline/` (one frame analyzer shared by the LIVE and IMPORTED pipelines, run as asyncio jobs). CPU work (decoding, watcher, measuring) runs in threads so the API stays responsive. The web app gets a Run view fed by REST plus SSE through a `RunSource` interface and a playhead store.

**Tech Stack:** what phase 1 installed (FastAPI, OpenCV 5, scikit-image, numpy, `uncertainties`, `openai` 3.40 Responses API, `meta-sam-parser` 0.1.0; Next.js 16, React 19, TypeScript strict) plus the ffmpeg 9 CLI from PATH. No new packages.

**Spec:** `docs/superpowers/specs/2026-10-28-argus-design.md`: phase 2 of §16, implementing §4.1, §4.2, §4.3, §5 (detections, events, model calls), §6, §7.1 (`segment()`), §9.2 (Run screen: frame, readouts, timeline), §10 (runs, frames, cameras). Facts: `docs/knowledge-base/03` (watcher), `04` (SAM API), `05` (SAM prices), `09` (camera locking, quality checks). UI reference: the canvas's Run board (`Main.dc.html`, https://claude.ai/artifact/2JeEMitFwx3e3egzNbptwg).

## Inputs needed from Aymen

1. **A real recording for Task 15**, about 15 real minutes or longer, with the Argus Card flat in view next to 1–6 vessels where something changes (ice melting, dye spreading, a sprouting seed, foam settling). A phone video is fine; a fast-motion clip needs its time-scale factor. The germination footage replaces it once it exists.
2. **The printed card's 100 mm line**, measured with a ruler, in mm.
3. **A camera plugged in for the live check** (the Nuroum if possible; the laptop camera works).
4. **Germination start (Q-14):** it is on the critical path (spec §14). Phase 2's import pipeline is built for that footage.

## Global Constraints

- Everything in phase 1's Global Constraints still holds (uv/Python 3.12, ruff line length 120, web lint/typecheck/build before every web commit, secrets only in `.env`, glossary words, `t` in real seconds, `method_version` `"<method>/<n>"`, `pathlib` paths, `shutil.which` for executables, the commit trailer).
- **No new dependencies** (worker or web). ffmpeg is the CLI from PATH (D-45), resolved with `shutil.which("ffmpeg")`. Pillow, d3, Vitest and the rest still wait for approval.
- **Only `argus/segment/` imports `openai`** (spec §7.1). Model ID, base URL and key come from `Settings`. **Tests never touch the network**: they replay recorded SAM streams or use a fake `Segmenter`. Probes in `worker/probes/` are run by hand.
- **Every SAM call is logged** in `model_calls`, failures included (CLAUDE.md rule 4), and counted against the run's `RUN_SPEND_CAP_USD`.
- **SAM 3.1 limits (KB 04):** one concept per request; up to 16 objects; video up to 15,000 frames per request, H.264 MP4; masks are box-local. **Prices (KB 05):** image $0.0025 per request, video $0.0002 per frame with a 50-frame minimum per request.
- **Evidence never changes (spec §5, D-54):** detections and calibrations can't be updated or deleted; a frame's only writable column is `analyzed`; an event's only change is setting `t_end` once. Enforced by triggers in migration 003.
- **A failed segmentation is a gap, never a zero.** Zero is stored only when SAM succeeded and found nothing.
- **Never block the event loop:** decoding, the watcher, the quality gate, rectification and measuring run in `asyncio.to_thread`.
- Files: `data/<experiment_id>/<run_id>/frames/<frame_id>.jpg` (JPEG quality 90), `masks/<detection_id>.png`, `crops/<vessel_label>-<concept>.mp4`.
- The worker formats every number shown in the UI (`display` strings next to `value`/`uncertainty`), so the web never re-implements the ± rule.
- Branch `phase-2`; merge to `main` after the end-of-phase review.

## Review Focus

1. **A vessel where SAM finds nothing** (before sprouting, an empty jar). Geometry metrics are stored as 0 with their ±, colour metrics are absent, nothing raises. A failed call stores no geometry measurement and logs a `segment_failed` event instead. Tests in Task 9.
2. **SAM failing mid-run** (network drop, 5xx, timeout). Each attempt is retried with backoff (1 s, then 4 s) and logged with its status. Frames are still stored and the run continues. Test in Task 9.
3. **Spend cap reached mid-run.** No further SAM calls. Frames are still stored, colour is still measured on the last masks, and one `spend` event says why. Test in Task 9.
4. **Imported video with odd timing:** split files with different frame rates, a frame count that is wrong or zero, a path with spaces and accents. `t` stays continuous and increasing, computed from decoded timestamps × time scale. Test in Task 5.
5. **The worker restarting mid-run** (`argus dev` restarts it on every save). At startup, runs left `running` become `stopped` with an `interrupted` event; their frames and measurements stay, and the Run view shows the run as stopped. Tests in Tasks 1 and 12.

---

## File structure

```
worker/argus/
  config.py                         modify: SAM prices and limits, segment cadence
  domain.py                         modify: RunSource, Calibration, Detection, RunEvent, ModelCall, CameraProperty
  storage/
    migrations/003_watch_and_measure.sql   runs columns, detections, events, model_calls, evidence triggers
    repos.py                        modify: run source/status, calibrations, detections, events, model calls, timeline
    files.py                        RunFiles: paths under data/<experiment>/<run>/
  calibration/
    detect.py                       modify: rectify a region with a size cap
    run.py                          RunCalibration, calibrate(), card_moved()
  segment/
    __init__.py                     segment(), Clip, SegmentResult, SegmentError
    types.py                        MaskPatch, TrackFrame, Track
    sam.py                          request building, stream parsing, cost, model-call record
    outline.py                      mask → simplified polygons
    tracking.py                     assign_to_vessels(), TrackMatcher
  capture/
    __init__.py
    video.py                        VideoFileSource, VideoFrame
    webcam.py                       open_webcam(), list_cameras(), CameraSettings
    quality.py                      assess(), QualityReport, QualityThresholds
  watcher/
    __init__.py
    watcher.py                      Watcher, WatcherSettings, Trigger
  measure/
    engine.py                       measure_vessel(), VesselMeasurements
    uncertainty.py                  modify: format_measurement()
  pipeline/
    __init__.py
    analyzer.py                     Segmenter protocol, SamSegmenter, RunContext, analyze_frame()
    imported.py                     run_import()
    live.py                         run_live(), FrameSource, CameraHub
    jobs.py                         RunJobs: start, stop, interrupted runs at startup
  api/
    app.py                          modify: mount routers, startup hook
    runs.py                         run, timeline, frame, detection and vessel-detect routes
    cameras.py                      camera list and MJPEG stream
  cli.py                            modify: `run <file.json>`
worker/probes/record_sam.py         records SAM streams into test fixtures (run by hand, ≈ $0.02)
worker/tests/fixtures/sam/          coins-image.jsonl, pan-video.jsonl
worker/tests/
  test_storage_phase2.py test_rectify_region.py test_run_calibration.py test_sam.py test_outline_tracking.py
  test_video_source.py test_webcam.py test_quality.py test_watcher.py test_engine.py test_analyzer.py
  test_import.py test_live.py test_api_runs.py   (+ test_cli.py modified)
web/
  lib/types.ts api.ts events.ts     modify
  lib/run-source.ts                 RunSource, LiveSource
  lib/playhead.ts                   playhead store
  lib/scale.ts                      linear scale, time formatting
  app/experiments/[id]/run/page.tsx (+ page.module.css)
  components/run/RunFrame.tsx Readouts.tsx Timeline.tsx (+ .module.css each)
  components/experiments/ExperimentsTable.tsx   modify: rows link to the Run view
```

---

### Task 1: Storage for detections, events and model calls

**Files:**
- Create: `worker/argus/storage/migrations/003_watch_and_measure.sql`, `worker/argus/storage/files.py`
- Modify: `worker/argus/domain.py`, `worker/argus/storage/repos.py`, `worker/argus/config.py`
- Test: `worker/tests/test_storage_phase2.py` (update the schema-version assertion in `test_storage.py` to 3)

**Interfaces:**
- Produces (domain, all `Record`):
  - `SourceKind(StrEnum)`: `webcam`, `video`. `RunSource(kind, camera_index: int | None = None, paths: list[str] = [], start_time: datetime | None = None, start_time_source: Literal["researcher", "file", "run_start"] = "run_start")`
  - `CameraProperty(StrEnum)`: `locked`, `not_locked`, `unknown`
  - `CalibrationDraft(t, card: str, homography: list[list[float]] | None, mm_per_px: float = Field(gt=0), rel_uncertainty: float = Field(ge=0), print_scale: float = 1.0, colour_reference: dict | None, camera_properties: dict[str, CameraProperty])`; `card` is `"standard"`, `"compact"` or `"ruler"`. `Calibration(CalibrationDraft)` adds `id`, `run_id`
  - `DetectionDraft(frame_id, vessel_id, track_key, concept, outline: list[list[tuple[float, float]]], bbox: tuple[float, float, float, float], area_px: int = Field(ge=0), confidence: float | None, backend: str, mask_path: str)`; `Detection(DetectionDraft)` adds `id`
  - `EventKind(StrEnum)`: `first`, `change`, `checkin`, `tick`, `intervention`, `quality`, `camera_moved`, `no_calibration`, `segment_failed`, `spend`, `interrupted`. `RunEvent(id, run_id, vessel_id: str | None, t_start, t_end: float | None, kind, source: Literal["watcher", "quality", "pipeline", "researcher"], detail: dict, frame_ids: list[str])`
  - `ModelCallDraft(function: str, model: str, tier: str, input_tokens: int = 0, cached_tokens: int = 0, output_tokens: int = 0, reasoning_tokens: int = 0, images: int = 0, frames: int = 0, cost_usd: float = Field(ge=0), latency_s: float, cache_key: str | None = None, status: Literal["ok", "error"], error: str | None = None)`; `ModelCall(ModelCallDraft)` adds `id`, `run_id: str | None`, `t: float | None`, `created_at`
- Produces (repos): `create_run(db, experiment_id, mode, source: RunSource, time_scale=1.0) -> Run` (replaces the phase 1 signature; `Run` gains `source`, `ended_at: datetime | None`), `set_run_status(db, run_id, status) -> Run`, `stop_interrupted_runs(db) -> list[str]`, `runs_for_experiment(db, experiment_id) -> list[Run]` (newest first), `get_run(db, run_id) -> Run | None`, `vessels_for_run(db, run_id) -> list[Vessel]`, `add_calibration(db, run_id, draft: CalibrationDraft) -> Calibration`, `latest_calibration(db, run_id, t) -> Calibration | None`, `mark_frame_analyzed(db, frame_id)`, `frames_for_run(db, run_id, t_from=None, t_to=None) -> list[Frame]` (`Frame` gains `analyzed: bool`), `add_detections(db, drafts) -> list[Detection]`, `detections_for_frame(db, frame_id) -> list[Detection]`, `add_event(db, run_id, *, vessel_id: str | None, t_start: float, kind: EventKind, source: str, detail: dict, frame_ids: Sequence[str] = (), t_end: float | None = None) -> RunEvent`, `close_event(db, event_id, t_end) -> RunEvent`, `events_for_run(db, run_id, t_from=None, t_to=None) -> list[RunEvent]`, `add_model_call(db, run_id, t, draft) -> ModelCall`, `run_spend_usd(db, run_id) -> float`
- Produces (files): `RunFiles(data_dir, experiment_id, run_id)` with `frame_path(frame_id) -> Path`, `mask_path(detection_id) -> Path`, `crop_path(label, concept) -> Path` (folders created on first use; concept slugged to `[a-z0-9-]`)
- Produces (config `Settings`, defaults, no env vars): `sam_image_usd = 0.0025`, `sam_video_frame_usd = 0.0002`, `sam_video_min_frames = 50`, `sam_max_objects = 16`, `sam_max_video_frames = 15000`, `sam_concurrency = 2`, `segment_interval_s = 10.0`

Migration 003: `ALTER TABLE runs ADD COLUMN source TEXT NOT NULL DEFAULT '{"kind":"video"}'`, `ADD COLUMN ended_at TEXT`; tables `detections`, `events`, `model_calls` (columns as above, JSON for lists and dicts, index on `(frame_id)`, `(run_id, t_start)`, `(run_id)`); triggers: detections and calibrations no update/no delete/no replace; `frames_evidence BEFORE UPDATE OF id, run_id, t, path, quality_flags ON frames`; events: block delete, and block update unless only `t_end` changes from NULL; model_calls: no update/no delete.

- [ ] **Step 1: Write the failing tests.**

```python
def test_detections_and_calibrations_are_evidence(db, run, vessel, frame): ...
    # add_detections then UPDATE / DELETE / INSERT OR REPLACE each raise sqlite3.IntegrityError
def test_a_frame_only_changes_its_analyzed_flag(db, run):
    f = add_frame(db, run.id, 1.0, "p.jpg", [])
    mark_frame_analyzed(db, f.id)
    assert frames_for_run(db, run.id)[0].analyzed is True
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE frames SET t=2 WHERE id=?", (f.id,))
def test_an_event_closes_once(db, run):
    e = add_event(db, run.id, vessel_id=None, t_start=5.0, kind=EventKind.CHANGE, source="watcher", detail={}, frame_ids=[])
    assert close_event(db, e.id, 9.0).t_end == 9.0
    with pytest.raises(sqlite3.IntegrityError):
        close_event(db, e.id, 12.0)
def test_spend_sums_every_logged_call_including_failures(db, run):
    add_model_call(db, run.id, 1.0, ModelCallDraft(function="segment", model="sam-3.1", tier="segment", images=1,
                   cost_usd=0.0025, latency_s=6.4, status="ok"))
    add_model_call(db, run.id, 2.0, ModelCallDraft(..., cost_usd=0.0025, status="error", error="timeout"))
    assert run_spend_usd(db, run.id) == pytest.approx(0.005)
def test_runs_left_running_are_stopped_with_an_interrupted_event(db, exp):
    r = create_run(db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.VIDEO, paths=["a b é.mp4"]), time_scale=600)
    assert stop_interrupted_runs(db) == [r.id]
    assert get_run(db, r.id).status is RunStatus.STOPPED and events_for_run(db, r.id)[0].kind is EventKind.INTERRUPTED
    assert stop_interrupted_runs(db) == []
def test_run_files_live_under_experiment_and_run(tmp_path):
    files = RunFiles(tmp_path / "data é", "exp_1", "run_1")
    assert files.frame_path("frm_1") == tmp_path / "data é" / "exp_1" / "run_1" / "frames" / "frm_1.jpg"
    assert files.crop_path("A", "mung bean").name == "A-mung-bean.mp4"
```

Add a `frame` fixture to `conftest.py`. Update `conftest.run` to the new `create_run` signature.

- [ ] **Step 2: Run to see them fail.** `uv run pytest tests/test_storage_phase2.py -q`. Expected: FAIL (import errors).
- [ ] **Step 3: Implement** the migration, domain records, repos and `files.py`. Upgrading a copy of `data/argus.sqlite` from version 2 to 3 must work: open a copy, read `user_version` 3, read the old rows.
- [ ] **Step 4: Run everything.** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): storage for detections, events and model calls"`

---

### Task 2: Bounded rectification and run calibration

**Files:**
- Modify: `worker/argus/calibration/detect.py`
- Create: `worker/argus/calibration/run.py`
- Test: `worker/tests/test_rectify_region.py`, `worker/tests/test_run_calibration.py`

**Interfaces:**
- Consumes: `detect_card`, `with_print_check`, `ruler_scale`, `read_patches`, `ColourReference` (phase 1); `Calibration`, `CameraProperty` (Task 1).
- Produces:
  - `rectify(image_or_mask, detection, *, region_px: tuple[float, float, float, float] | None = None, px_per_mm: float = 10.0, max_side_px: int = 4096) -> Rectified`. `region_px` is an image-space box `(x0, y0, x1, y1)`; only its card-plane footprint is warped. If the output would exceed `max_side_px`, `px_per_mm` is lowered to fit, and `Rectified.px_per_mm` reports the value used. `region_px=None` keeps the phase 1 whole-frame behaviour with the same cap.
  - `RunCalibration(detection: CardDetection | None, ruler: RulerScale | None, reference: ColourReference | None, marker_corners_px: np.ndarray | None)` (frozen) with `mm_per_px`, `rel_uncertainty`, `card_name: str` (`"standard"`, `"compact"` or `"ruler"`) and `to_draft(t, camera_properties) -> CalibrationDraft` for `add_calibration`.
  - `RulerInput(p1: tuple[float, float], p2: tuple[float, float], distance_mm: float)` (pydantic).
  - `calibrate(image_bgr, *, print_check_mm: float | None = None, ruler: RulerInput | None = None) -> RunCalibration | None`. Uses the card if found (with the print check if given); otherwise the ruler; otherwise None.
  - `card_moved(cal: RunCalibration, image_bgr, *, tolerance_px: float = 3.0) -> bool | None`: whether the marker corners shifted by more than the tolerance. None when no card is visible, or when the calibration came from a ruler.

- [ ] **Step 1: Write the failing tests.**

```python
def test_a_region_on_a_tilted_frame_stays_small_and_square():
    img = scene_with_square_on_card_plane(STANDARD, side_mm=30.0, tilt=TILT)
    d = detect_card(img)
    box = bbox_of_dark_square_in_image(img)            # image px of the 30 mm square, + 20 px margin
    rect = rectify(img, d, region_px=box, px_per_mm=10.0)
    assert max(rect.image.shape[:2]) < 800
    w, h = bounding_box_of_dark_square(rect.image)
    assert w == pytest.approx(300, abs=4) and h == pytest.approx(300, abs=4)

def test_output_is_capped_by_lowering_the_scale():
    img = scene(STANDARD, 5.0, tilt=TILT)
    rect = rectify(img, detect_card(img), px_per_mm=40.0, max_side_px=2000)
    assert max(rect.image.shape[:2]) <= 2000 and rect.px_per_mm < 40.0

def test_calibrate_prefers_the_card_and_applies_the_print_check():
    cal = calibrate(scene(STANDARD, 5.0 * 0.98), print_check_mm=98.0)
    assert cal.card_name == "standard" and cal.mm_per_px == pytest.approx(0.2, rel=0.01)

def test_no_card_and_no_ruler_means_no_millimetres():
    assert calibrate(np.full((600, 800, 3), 255, np.uint8)) is None

def test_ruler_fallback():
    cal = calibrate(np.full((600, 800, 3), 255, np.uint8), ruler=RulerInput(p1=(0, 0), p2=(400, 0), distance_mm=100))
    assert cal.card_name == "ruler" and cal.mm_per_px == 0.25

def test_card_moved():
    cal = calibrate(scene(STANDARD, 5.0))
    shifted = np.roll(scene(STANDARD, 5.0), 8, axis=1)
    assert card_moved(cal, scene(STANDARD, 5.0)) is False and card_moved(cal, shifted) is True
    assert card_moved(cal, np.full((1200, 1600, 3), 255, np.uint8)) is None
```

Add `bbox_of_dark_square_in_image(img, margin=20)` to `tests/helpers.py`: the bounding box of the largest dark component, expanded by the margin.

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** In `rectify`, map the region's corners (not the frame's) to the card plane, then cap the size. `calibrate` reads the colour reference with `read_patches` when a card is found.
- [ ] **Step 4: Run.** `uv run pytest tests/test_rectify_region.py tests/test_run_calibration.py tests/test_detect.py -q`. Expected: all pass (the phase 1 rectify test still passes).
- [ ] **Step 5: Commit.** `git commit -m "feat(calibration): rectify a region with a size cap; calibrate a run"`

---

### Task 3: `segment()` on SAM 3.1

**Files:**
- Create: `worker/argus/segment/__init__.py`, `segment/types.py`, `segment/sam.py`, `worker/probes/record_sam.py`, `worker/tests/fixtures/sam/coins-image.jsonl`, `worker/tests/fixtures/sam/pan-video.jsonl`
- Test: `worker/tests/test_sam.py`

**Interfaces:**
- Consumes: `Settings` (`segment_model`, `meta_base_url`, `model_api_key`, the SAM prices and limits from Task 1); `ModelCallDraft` (Task 1).
- Produces:
  - `MaskPatch(left: int, top: int, mask: np.ndarray)` (frozen; `mask` is a box-local bool array) with `to_canvas(height, width) -> np.ndarray`, `area_px`, and `shifted(dx, dy) -> MaskPatch`.
  - `TrackFrame(index: int, patch: MaskPatch, confidence: float | None)`; `Track(key: str, concept: str, frames: tuple[TrackFrame, ...])`.
  - `Clip(path: Path, frame_count: int, width: int, height: int)`.
  - `SegmentResult(tracks: list[Track], call: ModelCallDraft)`; `SegmentError(RuntimeError)` with `.call: ModelCallDraft`.
  - `async def segment(media: np.ndarray | Clip, concept: str, *, mode: Literal["image", "video"], settings: Settings, roi: tuple[float, float, float, float] | None = None, client: AsyncOpenAI | None = None) -> SegmentResult`. Image mode sends a JPEG (quality 90) of the frame, or of the `roi` box with patches shifted back to frame pixels. Video mode sends the clip as `input_video` with `propagation_direction: "forward"`. The metadata is always `{"mask_encoding": "one_bit", "include_confidence": "true"}`, and `stream=True`.
  - Track keys: video mode uses `obj<id>` from SAM's object id; image mode uses `obj<n>` in record order (stable keys come from Task 4's matcher).
  - Cost: image `settings.sam_image_usd`; video `max(frame_count, sam_video_min_frames) × sam_video_frame_usd`. `tier="segment"`, `function="segment"`, `images=1` or `frames=billed frames`. A transport or parse failure raises `SegmentError` whose call has `status="error"`, the error text, and the cost that would have been billed (0 for errors before any response arrived).
  - Video clips over `sam_max_video_frames` raise `ValueError` before any request (the caller splits them).
  - Departure from spec §7.1, by design: `segment()` is async (each call takes about 6 s) and returns the tracks *with* their call record, so the caller logs it against the run; the spec's `list[Track]` is `result.tracks`.

- [ ] **Step 1: Record the fixtures (live API, by hand, ≈ $0.02).** Copy the coins and clip setup from `probes/sam.py` into `probes/record_sam.py`. Save every stream event as one JSON line (`event.model_dump(mode="json")`) to `tests/fixtures/sam/coins-image.jsonl` (concept `coin`) and `pan-video.jsonl` (the 60-frame pan clip). Run: `uv run --env-file ../.env python -m probes.record_sam`. Expected: two files; the image stream yields 24 coins.
- [ ] **Step 2: Write the failing tests** with a fake client whose `responses.create(**kwargs)` records the kwargs and returns an async iterator. The iterator rebuilds the recorded events with `TypeAdapter(ResponseStreamEvent).validate_python(...)`.

```python
async def test_image_mode_returns_every_coin_as_a_frame_sized_patch(): ...
    # 24 tracks; each single frame; patch inside 384x303; confidence 0.9..1.0; call.images == 1, call.cost_usd == 0.0025
async def test_roi_crops_the_request_and_shifts_patches_back(): ...
    # request image is the roi size; every patch's left/top >= roi x0/y0
async def test_video_mode_keeps_object_ids_across_frames(): ...
    # tracks keyed obj<id>; at most 16; frames indices within 0..59; call.frames == 60, cost == 0.012
async def test_a_short_clip_is_billed_at_least_fifty_frames(): ...   # 20-frame Clip -> call.frames == 50, cost 0.01
async def test_one_concept_per_request():
    with pytest.raises(ValueError): await segment(img, "seed, root", mode="image", settings=s, client=fake)
async def test_a_failed_stream_raises_with_a_logged_call(): ...
    # client raises httpx.ReadTimeout -> SegmentError; err.call.status == "error"; "ReadTimeout" in err.call.error
```

- [ ] **Step 3: Run to see them fail.** `uv run pytest tests/test_sam.py -q`. Expected: FAIL.
- [ ] **Step 4: Implement** `types.py`, `sam.py` and `__init__.py`, following `probes/sam.py` (`parse_responses_stream` with `image_segmentation_format()` / `video_segmentation_format()`, `decode_mask_to_raster` placed at `record.bounds`).
- [ ] **Step 5: Run.** Expected: 6 passed; `grep -rl "import openai\|from openai" argus` lists only `argus/segment/sam.py`.
- [ ] **Step 6: Commit.** `git commit -m "feat(segment): SAM 3.1 image and video segmentation with cost records"`

---

### Task 4: Outlines and tracking

**Files:**
- Create: `worker/argus/segment/outline.py`, `segment/tracking.py`
- Test: `worker/tests/test_outline_tracking.py`

**Interfaces:**
- Consumes: `MaskPatch` (Task 3), `Vessel` (phase 1).
- Produces:
  - `outline_polygons(patch: MaskPatch, *, epsilon_px: float = 1.0, min_area_px: float = 4.0) -> list[list[tuple[float, float]]]`: external contours in frame pixels, simplified with `cv2.approxPolyDP`, each with ≥ 3 points.
  - `assign_to_vessels(patches: Sequence[MaskPatch], vessels: Sequence[Vessel], frame_shape: tuple[int, int]) -> dict[str, list[int]]`: each patch goes to the vessel whose ROI polygon covers the largest share of it, if that share is ≥ 0.5; otherwise to no vessel.
  - `TrackMatcher()` with `match(vessel: Vessel, concept: str, patches: Sequence[MaskPatch]) -> list[str]`. Keys are `"{label}:{concept}:{n}"`. A patch takes the previous frame's key for the same vessel and concept when the IoU is ≥ 0.3 (greedy, highest IoU first); otherwise it gets the next `n`. With `restore(vessel_id, concept, keyed: dict[str, MaskPatch])`, a video chunk can continue the keys of the previous chunk.

- [ ] **Step 1: Write the failing tests.**

```python
def test_outline_of_a_disc_is_a_closed_polygon_in_frame_pixels():
    patch = disc_patch(cx=150, cy=90, r=30)                  # helper: MaskPatch of a filled disc
    [poly] = outline_polygons(patch)
    xs, ys = zip(*poly)
    assert 8 <= len(poly) <= 60 and min(xs) == pytest.approx(120, abs=2) and max(ys) == pytest.approx(120, abs=2)

def test_two_blobs_give_two_polygons_and_specks_are_dropped(): ...

def test_patches_go_to_the_vessel_that_holds_most_of_them():
    a = vessel("A", roi=[(0, 0), (100, 0), (100, 200), (0, 200)])
    b = vessel("B", roi=[(100, 0), (200, 0), (200, 200), (100, 200)])
    out = assign_to_vessels([disc_patch(50, 100, 20), disc_patch(160, 100, 20), disc_patch(100, 300, 10)], [a, b], (400, 200))
    assert out == {a.id: [0], b.id: [1]}

def test_keys_follow_overlap_from_frame_to_frame():
    m = TrackMatcher(); v = vessel("A", roi=SQUARE)
    first = m.match(v, "root", [disc_patch(50, 50, 10), disc_patch(120, 50, 10)])
    second = m.match(v, "root", [disc_patch(122, 52, 10), disc_patch(52, 50, 10), disc_patch(50, 150, 10)])
    assert first == ["A:root:1", "A:root:2"] and second == ["A:root:2", "A:root:1", "A:root:3"]
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** ROI coverage uses `cv2.fillPoly` on a frame-sized canvas, intersected with the patch's box.
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(segment): simplified outlines, vessel assignment and IoU tracking"`

---

### Task 5: Video files and the webcam

**Files:**
- Create: `worker/argus/capture/__init__.py`, `capture/video.py`, `capture/webcam.py`
- Test: `worker/tests/test_video_source.py`, `worker/tests/test_webcam.py`

**Interfaces:**
- Produces:
  - `VideoFrame(t: float, video_s: float, file_index: int, image: np.ndarray)` (frozen).
  - `VideoFileSource(paths: Sequence[Path], *, time_scale: float)`: `frames() -> Iterator[VideoFrame]` decodes every frame of every file in order. `video_s` comes from `CAP_PROP_POS_MSEC` after each `read()` (falling back to `index / fps` when the backend reports 0 for a frame after the first). Each later file is offset by the previous file's last timestamp plus one frame interval. `t = video_s × time_scale`. `CAP_PROP_FRAME_COUNT` is never trusted. A path that doesn't open raises `FileNotFoundError` naming it.
  - `CameraSettings(width: int = 1280, height: int = 720, fps: int = 30, exposure: float | None = None, white_balance: int | None = None, focus: int | None = None)`.
  - `open_webcam(index: int, settings: CameraSettings, *, capture_factory=cv2.VideoCapture) -> tuple[cv2.VideoCapture, dict[str, CameraProperty]]`. It opens with `cv2.CAP_DSHOW`, sets FOURCC `MJPG` before the size, sets the requested locks (`AUTO_EXPOSURE` 0.25 then `EXPOSURE`; `AUTO_WB` 0 then `WB_TEMPERATURE`; `AUTOFOCUS` 0 then `FOCUS`) and reads each back. `locked` means the read-back matches within 1%. `unknown` means the read-back is -1 or `set` returned False. Otherwise the property is `not_locked`. It always reports `exposure`, `white_balance` and `focus`; properties that weren't requested are `not_locked`. A camera that doesn't open raises `RuntimeError("camera <i> did not open")`.
  - `list_cameras(max_index: int = 4, *, capture_factory=cv2.VideoCapture) -> list[int]`.

- [ ] **Step 1: Write the failing tests.** Synthetic files are made in the test with `cv2.VideoWriter` (`mp4v`), drawing the frame number as a bar.

```python
def test_split_files_with_different_frame_rates_give_continuous_time(tmp_path):
    a = write_clip(tmp_path / "part 1 é.mp4", frames=20, fps=10)      # 0.0 .. 1.9 s
    b = write_clip(tmp_path / "part 2.mp4", frames=10, fps=5)          # continues at 2.0 s, step 0.2 s
    ts = [f.t for f in VideoFileSource([a, b], time_scale=600).frames()]
    assert len(ts) == 30 and all(t2 > t1 for t1, t2 in zip(ts, ts[1:]))
    assert ts[19] == pytest.approx(1.9 * 600, rel=0.02) and ts[20] == pytest.approx(2.0 * 600, rel=0.02)
    assert ts[-1] == pytest.approx(3.8 * 600, rel=0.02)

def test_a_missing_file_is_named(tmp_path):
    with pytest.raises(FileNotFoundError, match="nope.mp4"):
        list(VideoFileSource([tmp_path / "nope.mp4"], time_scale=1).frames())

def test_read_back_decides_locked_not_locked_unknown():
    cap, props = open_webcam(0, CameraSettings(exposure=-6, white_balance=4500), capture_factory=FakeCapture(
        readback={cv2.CAP_PROP_EXPOSURE: -1, cv2.CAP_PROP_WB_TEMPERATURE: 4500}))
    assert props == {"exposure": CameraProperty.UNKNOWN, "white_balance": CameraProperty.LOCKED,
                     "focus": CameraProperty.NOT_LOCKED}

def test_mjpeg_is_requested_before_the_size(): ...   # FakeCapture logs set() order: FOURCC before WIDTH/HEIGHT
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: 4 passed. Then by hand, with a camera plugged in: `uv run python -c "from argus.capture.webcam import *; print(open_webcam(0, CameraSettings(white_balance=4500))[1])"`. Expected: the property states print; record them in the ledger.
- [ ] **Step 5: Commit.** `git commit -m "feat(capture): video files with continuous time; webcam with read-back locks"`

---

### Task 6: Frame-quality gate

**Files:**
- Create: `worker/argus/capture/quality.py`
- Test: `worker/tests/test_quality.py`

**Interfaces:**
- Produces:
  - `QualityThresholds(blur_min: float = 60.0, saturated_max: float = 0.05, occlusion_change_min: float = 0.25)` (frozen).
  - `QualityReport(blur: float, saturated: dict[str, float], outside_change: float | None, flags: tuple[str, ...])`, with `ok` (no `blurred` and no `occluded` flag). `flags` is drawn from `"blurred"`, `"saturated:<vessel_id>"` and `"occluded"`.
  - `assess(image_bgr, vessels: Sequence[Vessel], *, previous_good: np.ndarray | None, thresholds: QualityThresholds = QualityThresholds()) -> QualityReport`. `blur` is the variance of the Laplacian on the grey frame. `saturated[v]` is the share of pixels in a vessel ROI with any channel ≥ 250. `outside_change` is the share of pixels outside all ROIs whose grey value moved by more than 40 since `previous_good`, computed at half size.

- [ ] **Step 1: Write the failing tests** on a textured synthetic frame (checkerboard plus the card scene).

```python
def test_a_sharp_frame_passes(): assert assess(frame, vessels, previous_good=frame).ok
def test_blur_is_flagged(): assert "blurred" in assess(cv2.GaussianBlur(frame, (31, 31), 10), vessels, previous_good=None).flags
def test_glare_in_one_vessel_is_flagged_for_that_vessel(): ...   # white-out vessel B -> ("saturated:" + b.id) in flags, ok still True
def test_a_hand_outside_the_vessels_is_an_occlusion():           # dark blob over 40% of the outside area
    assert "occluded" in assess(with_hand(frame), vessels, previous_good=frame).flags
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(capture): frame-quality gate for blur, glare and occlusion"`

---

### Task 7: The watcher

**Files:**
- Create: `worker/argus/watcher/__init__.py`, `watcher/watcher.py`
- Test: `worker/tests/test_watcher.py`

**Interfaces:**
- Consumes: `WatcherSpec` (recipe), `Vessel`.
- Produces:
  - `WatcherSettings(mode: Literal["continuous", "smart_trigger", "hybrid"], interval_s: float, ssim_min: float = 0.90, colour_shift_max: float = 4.0, debounce: int = 3, cooldown_s: float = 60.0, checkin_s: float = 3600.0, hybrid_active_s: float = 120.0, roi_max_px: int = 256)` (frozen). `from_recipe(recipe) -> WatcherSettings` takes the mode from `default_mode` and `interval_s` from `analysis_step_s`.
  - `Trigger(vessel_id: str | None, reason: Literal["first", "change", "checkin", "tick"], ssim: float | None, colour_shift: float | None)` (frozen).
  - `Watcher(vessels, spec: WatcherSpec, settings: WatcherSettings)` with:
    - `observe(t, image_bgr) -> list[Trigger]`.
    - `mark_analyzed(t, image_bgr) -> None`, which makes this frame every vessel's keyframe.

    `observe` behaviour:
    - It compares each vessel's ROI crop (resized so the long side is `roi_max_px`) with that vessel's keyframe. Before comparing, the L channel of both is z-scored (with `light_normalization = "strong"`, each tile of a 4×4 grid is z-scored separately).
    - Signals:
      - `ssim` (`structural_similarity` on the normalized L channel) below `ssim_min`;
      - `colour_shift`, the distance between the mean (a*, b*) values, above `colour_shift_max`;
      - only the signals listed in `spec.signals` count.
    - A change must persist for `debounce` consecutive observations before it triggers. After a vessel's change trigger, that vessel doesn't trigger again for `cooldown_s`.
    - Check-ins: `checkin` fires when nothing was analyzed for `checkin_s`.
    - Modes:
      - `continuous` emits one `tick` every `interval_s`;
      - `hybrid` behaves like `continuous` within `hybrid_active_s` of the last change trigger, and like `smart_trigger` otherwise;
      - the very first observation returns `first`.

- [ ] **Step 1: Write the failing tests** on synthetic sequences: a textured background, two vessel ROIs, and a disc growing in vessel A.

```python
def test_slow_growth_triggers_once_it_adds_up():
    w = smart_watcher()                                   # smart_trigger, debounce 3, cooldown 0
    frames = [scene_with_disc(r=20 + i * 0.4) for i in range(60)]
    assert all(ssim_between(f1, f2) > 0.97 for f1, f2 in zip(frames, frames[1:]))   # frame to frame looks still
    triggers = run(w, frames, analyze_on_trigger=True)
    assert any(t.reason == "change" and t.vessel_id == A for t in triggers)

def test_a_lamp_switch_does_not_trigger():
    frames = [scene_with_disc(r=20)] * 10 + [brighten(scene_with_disc(r=20), 1.6)] * 20
    assert [t.reason for t in run(smart_watcher(), frames)] == ["first"]

def test_a_one_frame_flash_is_debounced(): ...
def test_cooldown_and_checkin(): ...      # second change inside cooldown_s ignored; checkin after checkin_s of quiet
def test_continuous_ticks_at_the_interval(): ...   # interval 2 s, frames every 0.5 s for 10 s -> 5 ticks after "first"
def test_hybrid_ticks_while_active_then_settles(): ...
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** `day_night` is accepted and ignored in phase 2, which the ledger records: normalization covers indoor lighting until real day/night footage shows a need.
- [ ] **Step 4: Run.** Expected: 6 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(watcher): keyframe SSIM and colour shift with debounce, cooldown and check-ins"`

---

### Task 8: Measurement engine and display strings

**Files:**
- Create: `worker/argus/measure/engine.py`
- Modify: `worker/argus/measure/uncertainty.py`, `recipes/general.toml` (lab_mean unit becomes `"Lab"`), `worker/argus/recipes/model.py` (lab_mean measurements must use unit `"Lab"`)
- Test: `worker/tests/test_engine.py`, `worker/tests/test_uncertainty.py`

**Interfaces:**
- Consumes: `RunCalibration` and `rectify(..., region_px=...)` (Task 2), the phase 1 geometry and colour functions, `combined_uncertainty`, `format_pm`, `correct_lab`, `Recipe`, `MeasurementDraft`.
- Produces:
  - `format_measurement(value: float, uncertainty: float, unit: str) -> str`. With `uncertainty > 0` this is `format_pm`. With 0, it shows the value alone: an integral value as an integer, otherwise 3 significant figures. The unit `count` is omitted, so `"3"` and `"12.5 mm"`.
  - `VesselMeasurements(drafts: list[MeasurementDraft], lab: dict[str, tuple[float, float, float]])`, where `lab` maps a measurement id to the Lab mean it used (it becomes the ΔE baseline).
  - `measure_vessel(recipe, vessel, masks: dict[str, np.ndarray], image_bgr, cal: RunCalibration, *, t, frame_id, baselines: dict[str, tuple[float, float, float]], current_reference: ColourReference | None, families: frozenset[str] = frozenset({"size", "count", "colour"})) -> VesselMeasurements`. `masks` maps a concept to its frame-sized boolean union inside this vessel; a missing concept means an empty mask. Card calibrations rectify the vessel's ROI box; ruler calibrations measure unrectified.

    | Recipe method | Stored metric id (unit) | ± (`combined_uncertainty(value, noise, cal.rel_uncertainty, power)`) |
    | --- | --- | --- |
    | `area` | `<id>` (mm2) | noise = ½ px × contour perimeter px × mm_per_px²; power 2 |
    | `height` (base = bottom of the rectified ROI) | `<id>` (mm) | noise = 1 px × mm_per_px; power 1 |
    | `skeleton_length` | `<id>` (mm) | noise = 2 px × mm_per_px; power 1 |
    | `component_count` (min area 1 mm²) | `<id>` (count) | 0 |
    | `lab_mean` | `<id>_l`, `<id>_a`, `<id>_b` (L*, a*, b*), after `correct_lab` when a reference exists | pixel std ÷ √n, no scale term |
    | `delta_e` | `<id>` (dE00), only once a baseline exists | √(SE_now² + SE_baseline²), summed over L*, a*, b* |
    | `event_count`, `threshold` | not measured in phase 2 (rule evaluation is phase 4) | — |

    Empty masks give 0 for size and count metrics (with their ±) and nothing for colour metrics. The ± here is what a single measurement knows (calibration and boundary). The noise floor over a still period is a derived number, computed in phase 4 for the "real effect" test (spec §6).

- [ ] **Step 1: Write the failing tests.**

```python
def test_display_strings():
    assert format_measurement(4.6312, 0.3, "mm") == "4.6 ± 0.3 mm"
    assert format_measurement(3.0, 0.0, "count") == "3" and format_measurement(12.5, 0.0, "mm") == "12.5 mm"

def test_root_length_and_area_of_a_known_shape_on_a_tilted_card():
    img, mask = card_scene_with_bar(length_mm=40, width_mm=3, tilt=TILT)     # bar on the card plane
    out = measure_vessel(RECIPE_SIZE, vessel_around(mask), {"root": mask}, img, calibrate(img), t=0, frame_id="f",
                         baselines={}, current_reference=None)
    m = {d.metric: d for d in out.drafts}
    assert m["length"].value == pytest.approx(40, rel=0.03) and m["length"].unit == "mm"
    assert m["area"].value == pytest.approx(120, rel=0.06) and m["area"].uncertainty > 0

def test_empty_masks_store_zeros_for_size_and_nothing_for_colour(): ...
def test_delta_e_waits_for_a_baseline_then_measures_change(): ...   # first call: no delta_e, lab returned; second call with baseline: dE ~ expected
def test_rule_based_methods_are_not_measured_yet(): ...              # seed-germination: only root_length drafts
def test_lab_mean_requires_the_lab_unit(): ...                       # recipe with lab_mean unit "L*" -> RecipeError
```

`RECIPE_SIZE` is a test recipe with `length` (skeleton_length, from root) and `area` (area, from root).

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run everything.** `uv run pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(measure): recipe measurements from masks with ± and display strings"`

---

### Task 9: The frame analyzer

**Files:**
- Create: `worker/argus/pipeline/__init__.py`, `pipeline/analyzer.py`
- Test: `worker/tests/test_analyzer.py`

**Interfaces:**
- Consumes: Tasks 1–8, `EventBroker`.
- Produces:
  - `class Segmenter(Protocol)`: `async def image(self, image_bgr, concept) -> SegmentResult`; `async def video(self, clip: Clip, concept) -> SegmentResult`. `SamSegmenter(settings)` calls `segment()`.
  - `RunContext` (dataclass): `db, broker, settings, files: RunFiles, recipe, run, vessels, segmenter`. It also holds:
    - `calibration: RunCalibration | None`;
    - `matcher: TrackMatcher`;
    - `last_masks: dict[str, dict[str, np.ndarray]]`;
    - `baselines: dict[str, dict[str, tuple]]` (vessel id → measurement id → Lab);
    - `semaphore: asyncio.Semaphore(settings.sam_concurrency)`;
    - `cap_reported: bool`;
    - `retry_delays_s: tuple[float, ...] = (1.0, 4.0)`.
  - `async def segment_with_retries(ctx, image_or_clip, concept, *, t) -> SegmentResult | None`.
    - It logs every attempt with `add_model_call`.
    - Before each attempt it checks `run_spend_usd + expected cost > settings.run_spend_cap_usd`. If so, it returns None and, the first time only, adds a `spend` event and publishes `spend` `{run_id, spent_usd, cap_usd}`.
    - After the last failed attempt it adds a `segment_failed` event and returns None.
  - `async def analyze_frame(ctx, t, image_bgr, *, frame_id: str | None = None, segment: bool, masks: dict[str, dict[str, list[tuple[str, MaskPatch]]]] | None = None, quality_flags: Sequence[str] = ()) -> AnalysisOutcome`. `masks` (vessel id → concept → keyed patches) lets the import pipeline hand over masks from video mode: the frame counts as segmented and SAM isn't called. Steps:
    1. Stores the frame, unless `frame_id` is given.
    2. If `segment` is True, segments each recipe concept, assigns patches to vessels, keys them, stores one detection per patch (mask PNG + outline) and updates `last_masks`. Injected `masks` are stored as detections the same way, with `backend="sam-3.1/video"`.
    3. When the card is visible, reads its patches. A neutral drift (`neutral_drift`) above 6 dE00 stores a `quality` event with `detail={"colour_drift": <dE>}`; otherwise the reading is the `current_reference` for colour correction.
    4. Measures each vessel: all families on segmented frames; colour only, on `last_masks`, otherwise.
    5. Stores the measurements as one audited batch, marks the frame analyzed, and publishes SSE `frame_analyzed` `{run_id, frame_id, t, quality_flags}` and one `measurement` per row `{run_id, vessel_id, frame_id, t, metric, value, uncertainty, unit, display}`.
    6. Without a calibration, nothing is measured; one `no_calibration` event is stored and published.
  - Spec §4.3 says frames whose segmentation failed are "queued for later". Here the next trigger or check-in segments again (live), and import falls back to image mode. A later "re-segment the gaps" job is left for phase 5 if real runs show gaps.
  - `AnalysisOutcome(frame_id: str, segmented: bool, measurements: int, failed_concepts: list[str])`.

- [ ] **Step 1: Write the failing tests** with a `FakeSegmenter` that thresholds dark blobs into `SegmentResult`s and can be scripted to fail N times or to find nothing.

```python
async def test_a_frame_becomes_detections_measurements_and_events(ctx): ...
    # 1 frame with a dark bar in vessel A: 1 detection (outline, mask file exists), measurements with display, SSE frame_analyzed + measurement
async def test_nothing_found_is_a_zero_but_a_failure_is_a_gap(ctx):
    ctx.segmenter.script(["empty"]);      await analyze_frame(ctx, 0.0, img, segment=True)
    ctx.segmenter.script(["fail"] * 3);   out = await analyze_frame(ctx, 60.0, img, segment=True)
    rows = measurements_for_run(ctx.db, ctx.run.id, metric="length")
    assert [r.t for r in rows] == [0.0] and rows[0].value == 0.0
    assert out.failed_concepts == ["root"] and events_kinds(ctx) == ["segment_failed"]
async def test_failed_attempts_are_retried_and_each_is_logged(ctx):
    ctx.segmenter.script(["fail", "fail", "ok"]); ctx.retry_delays_s = (0, 0)
    out = await analyze_frame(ctx, 0.0, img, segment=True)
    assert out.segmented and [c.status for c in calls(ctx)] == ["error", "error", "ok"]
async def test_spend_cap_stops_segmenting_but_not_recording(ctx):
    ctx.settings = ctx.settings.model_copy(update={"run_spend_cap_usd": 0.004})
    for t in (0.0, 60.0, 120.0):
        await analyze_frame(ctx, t, img, segment=True)
    assert len(calls(ctx)) == 1 and len(frames_for_run(ctx.db, ctx.run.id)) == 3
    assert events_kinds(ctx).count("spend") == 1
    assert measurements_for_run(ctx.db, ctx.run.id, t_from=120.0, metric="colour_l")      # colour still measured on last masks
async def test_without_calibration_nothing_is_measured(ctx): ...
async def test_colour_drift_beyond_correction_is_flagged(ctx): ...   # card neutrals shifted by ~10 dE -> one quality event with colour_drift
```

`ctx` is a fixture: a recipe with concept `root`, measurements `length` (skeleton_length) and `colour` (lab_mean, unit Lab), two vessels, a calibration from the card scene, and a `RunFiles` in `tmp_path`.

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** CPU steps go through `asyncio.to_thread`.
- [ ] **Step 4: Run.** Expected: 6 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(pipeline): frame analyzer with retries, spend cap and gaps for failures"`

---

### Task 10: The import pipeline

**Files:**
- Create: `worker/argus/pipeline/imported.py`
- Test: `worker/tests/test_import.py`

**Interfaces:**
- Consumes: `VideoFileSource` (Task 5), `assess` (Task 6), `Watcher` (Task 7), `calibrate`/`card_moved` (Task 2), `analyze_frame`/`segment_with_retries` (Task 9).
- Produces: `ImportRequest(paths: list[Path], time_scale: float, print_check_mm: float | None, ruler: RulerInput | None)`, and `async def run_import(ctx, request, *, cancel: asyncio.Event) -> RunStatus`, which runs three stages.
  1. **Scan** (thread). For every decoded frame:
     - The watcher observes it; a `change` trigger adds that frame to the samples and stores a `change` event.
     - Every `recipe.analysis_step_s` of `t` gives a sample.
     - Each sample goes through the quality gate. Good samples are stored as frames; bad ones are logged as `quality` events.
     - The first good sample calibrates the run (`add_calibration`). Later samples check `card_moved`, which stores a new calibration and a `camera_moved` event.
     - Publishes `run_progress` `{run_id, stage: "scan", t, t_end: null, speed}`.
  2. **Segment.** For each vessel × concept, it writes the vessel's ROI box (+ 8 px) from every stored sample into `crops/<label>-<concept>.mp4`. The encode is `ffmpeg -y -framerate 10 -i <dir>/%06d.jpg -c:v libx264 -pix_fmt yuv420p -g 12 <out>`, in chunks of at most `sam_max_video_frames`. It segments in video mode, shifting patches by the crop offset; chunks continue keys via `TrackMatcher.restore`. If video mode fails after the retries, it falls back to image mode on full frames for that concept. Publishes `run_progress` with `stage: "segment"`.
  3. **Measure.** For each sample in order it calls `analyze_frame(ctx, t, image, frame_id=..., segment=False, masks=<that frame's patches from stage 2>)`. Publishes `run_progress` `{stage: "measure", t, t_end, speed}`, where `speed` = run-time seconds analyzed ÷ wall seconds.

  It sets the run `finished` (or `stopped` when `cancel` is set) and publishes `run_status` `{run_id, status}`.

- [ ] **Step 1: Write the failing tests.** A synthetic MP4 at 10 fps with `time_scale` 60 shows the card plus a bar that grows in vessel A. `FakeSegmenter.video` thresholds each frame of the clip.

```python
async def test_import_measures_growth_at_the_analysis_step(ctx, clip):          # recipe analysis_step_s = 60
    status = await run_import(ctx, ImportRequest(paths=[clip], time_scale=60, print_check_mm=None, ruler=None), cancel=asyncio.Event())
    lengths = [m.value for m in measurements_for_run(ctx.db, ctx.run.id, metric="length")]
    assert status is RunStatus.FINISHED and len(lengths) >= 10 and lengths[-1] > lengths[0] + 10
    # every stored frame sits on the 60 s grid (within one video frame = 6 s of run time) or at a change event
    assert all(on_grid(f.t, 60, tol=6) or f.t in change_event_times(ctx) for f in frames_for_run(ctx.db, ctx.run.id))
async def test_video_mode_failure_falls_back_to_image_mode(ctx, clip): ...      # FakeSegmenter.video always fails -> measurements still exist, calls show both modes
async def test_cancel_stops_the_run(ctx, clip): ...                             # cancel set after scan -> RunStatus.STOPPED, run row stopped
async def test_crop_clip_is_h264(ctx, clip): ...                                # ffprobe-free check: cv2 opens it and its FOURCC is avc1/h264
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run everything.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(pipeline): import video with sampling, per-vessel SAM video and progress"`

---

### Task 11: The live pipeline and the camera hub

**Files:**
- Create: `worker/argus/pipeline/live.py`, `worker/argus/pipeline/jobs.py`
- Test: `worker/tests/test_live.py`

**Interfaces:**
- Produces:
  - `class FrameSource(Protocol)`: `read() -> np.ndarray | None`, `close()`.
  - `CameraHub(settings)`: owns open webcams by index (the worker is the only camera owner). It offers:
    - `acquire(index, camera_settings) -> (FrameSource, dict[str, CameraProperty])`, shared and ref-counted;
    - `latest_jpeg(index) -> bytes | None`, the most recent frame from a capture thread that keeps reading.
  - `async def run_live(ctx, source: FrameSource, watcher: Watcher, *, cancel: asyncio.Event, clock: Callable[[], float] = time.monotonic, print_check_mm=None, ruler=None) -> RunStatus`. Cadence (decision D-56):
    - Every frame goes through the quality gate and the watcher, at most 5 frames per second.
    - Every `analysis_step_s`, a frame is stored and its colour measured on the latest masks.
    - SAM runs on `first`, `change`, `checkin` and `tick` triggers, but never sooner than `settings.segment_interval_s` after the previous segmentation.
    - An `occluded` frame stores an `intervention` event; measuring waits until a frame passes the gate again.
    - Calibration happens on the first good frame; with no card and no ruler, one `no_calibration` event, and frames are still recorded.
  - `RunJobs(db, broker, settings, recipes, hub)`: `start_import(run, vessels, request)`, `start_live(run, vessels, camera_index, camera_settings, ...)`, `stop(run_id) -> bool` and `running(run_id) -> bool`, using one asyncio task per run. `shutdown()` cancels every job and marks its run `stopped`.

- [ ] **Step 1: Write the failing tests** with a `ListSource` that returns prepared frames and a fake clock that moves 0.2 s per read.

```python
async def test_live_segments_on_change_and_measures_colour_every_step(ctx): ...
    # 300 frames (60 s), change at 20 s; analysis_step 5 s; segment_interval 10 s ->
    # frames stored every 5 s; segment calls only at first + change (+ ticks/checkins none in smart mode); colour rows every 5 s
async def test_segmentation_never_runs_closer_than_the_interval(ctx): ...   # continuous mode, interval 1 s, segment_interval 10 s -> calls ~6 over 60 s
async def test_a_hand_pauses_measuring_and_logs_an_intervention(ctx): ...
async def test_stop_ends_the_run(ctx): ...                                   # cancel after 2 s -> RunStatus.STOPPED
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** The capture read loop runs in a thread and pushes into a size-1 queue (only the newest frame is kept).
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(pipeline): live runs with trigger cadence and a shared camera hub"`

---

### Task 12: Runs API, cameras and `argus run`

**Files:**
- Create: `worker/argus/api/runs.py`, `worker/argus/api/cameras.py`
- Modify: `worker/argus/api/app.py`, `worker/argus/cli.py`
- Test: `worker/tests/test_api_runs.py`, `worker/tests/test_cli.py`

**Interfaces:**
- Consumes: `RunJobs`, `CameraHub` (Task 11) and every repo from Task 1.
- Produces (all under `/api`):
  - `POST /experiments/{id}/runs` with `RunCreate` `{mode: "live"|"imported", camera_index?, paths: [], time_scale: >0 = 1, start_time?, vessels: [{label, role, condition?, roi: [[x, y]…] ≥ 3 points}] (1–16, unique labels), print_check_mm?: 90–110, ruler?}` → 201 `RunView`.
    - 404 for an unknown experiment.
    - 422 `"file not found: <path>"`, and 422 if `mode` doesn't match the source fields.
    - 409 `"a run is already running for this experiment"`.
    - Starting a run sets the experiment `running`.
  - `GET /experiments/{id}/runs` → `[RunView]` newest first. `GET /runs/{id}` → `RunView` `{run, vessels, calibration?, spend_usd, running: bool}`.
  - `POST /runs/{id}/stop` → 200 `RunView` (409 if not running).
  - `GET /runs/{id}/timeline?t_from&t_to` → `{frames: [{id, t, analyzed, quality_flags}], measurements: [{…, display}], events: [RunEvent]}`.
  - `GET /runs/{id}/frames/{frame_id}.jpg?w=` → JPEG, resized to width `w` when given (16–1920).
  - `GET /runs/{id}/frames/{frame_id}/detections` → `[{vessel_id, track_key, concept, outline, confidence}]`.
  - `POST /experiments/{id}/vessels/detect` `{camera_index? | path + video_s, concept}` → `[{roi: [[x, y]…], confidence}]`. This is SAM image mode on one frame; its model call is logged with `run_id` null and `function="vessel_detect"`.
  - `GET /cameras` → `[{index}]`; `GET /cameras/{i}/stream.mjpg` → `multipart/x-mixed-replace` from `CameraHub` at ≤ 10 fps.
  - Startup: `app_from_env` calls `stop_interrupted_runs` and publishes nothing; shutdown calls `RunJobs.shutdown()`.
  - `argus run <file.json> [--api URL]` posts the file's `RunCreate` JSON to the worker and prints the run id plus `http://localhost:3000/experiments/<id>/run`.

- [ ] **Step 1: Write the failing tests** with a `RunJobs` built on a `FakeSegmenter` and a tiny synthetic clip.

```python
def test_import_run_end_to_end_over_the_api(client, exp, clip): ...
    # POST runs (imported) -> 201 running; poll GET /runs/{id} until running False (<= 10 s);
    # timeline has measurements with display strings; frames/{id}.jpg?w=160 is a 160-px-wide JPEG; detections have outlines
def test_bad_requests(client, exp): ...         # missing file 422 names it; live without camera_index 422; second run 409; unknown experiment 404
def test_runs_left_running_are_stopped_at_startup(tmp_path): ...   # create a running run in a db, then app_from_env-style startup -> stopped + interrupted event
def test_cli_run_posts_the_file(monkeypatch, tmp_path): ...       # fake requests.post captures URL and JSON
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run everything.** `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(api): runs, timeline, frames, cameras and argus run"`

---

### Task 13: Run view: data layer and the frame

**Files:**
- Create: `web/lib/run-source.ts`, `web/lib/playhead.ts`, `web/lib/scale.ts`, `web/app/experiments/[id]/run/page.tsx` (+ `page.module.css`), `web/components/run/RunFrame.tsx` (+ css)
- Modify: `web/lib/types.ts`, `web/lib/api.ts`, `web/lib/events.ts`, `web/components/experiments/ExperimentsTable.tsx`

**Interfaces:**
- Consumes: the Task 12 endpoints and the SSE types `measurement`, `frame_analyzed`, `event`, `run_progress`, `run_status`, `spend`, `resync`.
- Produces:
  - Types: `Run`, `Vessel`, `Calibration`, `RunView`, `FrameRow`, `MeasurementRow` (with `display`), `RunEvent`, `DetectionOutline`, `RunProgress`.
  - `interface RunSource { load(): Promise<RunSnapshot>; subscribe(onChange: (snapshot: RunSnapshot) => void): () => void; frameUrl(frameId: string, width?: number): string; detections(frameId: string): Promise<DetectionOutline[]> }`. `LiveSource(runId)` implements it over REST + SSE: it merges rows by id, re-loads on `resync`, and drops events for other runs. `RunSnapshot = { view: RunView; frames: FrameRow[]; measurements: MeasurementRow[]; events: RunEvent[]; progress: RunProgress | null }`.
  - `playhead.ts`: a store `{ t: number; follow: boolean; selectedVesselId: string | null }` with `usePlayhead(selector)`, `setT(t)` (which turns `follow` off), `followLive()` and `selectVessel(id | null)`. In `follow` mode `t` tracks the newest analyzed frame.
  - `scale.ts`: `linearScale(domain: [number, number], range: [number, number])` returning `{ (x): number; invert(y): number }`; `formatRunTime(t: number): string` → `"41:20"` (hours:minutes) for runs ≥ 1 h, `"3:05"` (minutes:seconds) below.
  - The page `/experiments/[id]/run` loads the newest run.
    - Header: `PageHeader` with crumb `Experiments / <title>`, the title, and a `Badge` with LIVE or IMPORTED. The finding line is the run state, e.g. "Analyzing 26:00 of 40:00 · 4.2× real time", "Stopped at 12:40", or "Finished, 864 frames analyzed".
    - Empty state: "No run yet. Start one with `uv run python -m argus run run.json`." Error state as on the Experiments page.
  - `<RunFrame source={RunSource} />` shows:
    - the analyzed frame nearest at or before the playhead (`<img>` with width/height attributes so nothing jumps);
    - an SVG overlay in frame pixels (`viewBox` = frame size) with each detection's outline in its vessel's colour, the selected vessel drawn with the accent;
    - a pill per vessel at the top of its ROI (label, plus the main measurement's `display` at `t`);
    - clicking a vessel (pill or ROI) calls `selectVessel`;
    - "IMPORTED" or "LIVE" plus `formatRunTime(t)` on the frame (HUD pills, as on the canvas's Main board).
  - Experiments table rows link to `/experiments/<id>/run` (supersedes the phase 1 ruling that rows aren't links).

- [ ] **Step 1: Build** the data layer, page and frame to the canvas's Main board (camera panel, on-frame pills, HUD).
- [ ] **Step 2: Verify.** `npm run lint && npm run typecheck && npm run build`. Expected: all succeed.
- [ ] **Step 3: Check in the browser** with the worker running and a finished synthetic import run (from Task 12's test clip via `argus run`).
  1. Open `/experiments/<id>/run`. Expected: the frame with outlines and vessel pills, and no console errors.
  2. Click vessel B. Expected: its outline turns teal and its pill turns ink.
  3. Start a second, long import. Expected: new frames and pills update without a reload; the finding line shows progress.
  4. Take screenshots at 1440 and 390 px, light and dark.
- [ ] **Step 4: Commit.** `git commit -m "feat(web): run view data layer and the frame with outlines"`

---

### Task 14: Readouts and the timeline

**Files:**
- Create: `web/components/run/Readouts.tsx`, `web/components/run/Timeline.tsx` (+ css each)
- Modify: `web/app/experiments/[id]/run/page.tsx`

**Interfaces:**
- Consumes: `RunSource`, `usePlayhead`, `linearScale`, `formatRunTime` (Task 13).
- Produces:
  - `<Readouts snapshot={RunSnapshot} />` is a strip with one tile per vessel: the label, its condition (e.g. "0.5 % NaCl"), the main measurement's `display` at or before `t` (or "—" before the first value), and a small line for the change since the first value. The selected vessel's tile has the accent ring; clicking a tile selects the vessel. Six tiles per row on desktop, two on phones (canvas `.strip`).
  - `<Timeline snapshot={RunSnapshot} />`, with:
    - a ruler from 0 to the newest `t` (or the import's `t_end`), ticks via `formatRunTime`;
    - a filmstrip of thumbnails (`frameUrl(id, 160)`), at most one per 48 px;
    - one lane per vessel with a sparkline of the main measurement, drawn as an SVG polyline through `linearScale`, plus event blocks for `change`, `intervention`, `camera_moved` and `segment_failed`;
    - a playhead with a time handle you can drag (pointer events) or click to set `t`, and a "Follow live" button while a run is running;
    - keyboard: Left/Right step to the previous/next analyzed frame; Home/End go to the ends.
  - Lanes and the frame share `selectedVesselId`, so selecting anywhere highlights everywhere.

- [ ] **Step 1: Build** both components to the canvas's Main board (readout strip, editor-style timeline).
- [ ] **Step 2: Verify.** `npm run lint && npm run typecheck && npm run build`. Expected: all succeed.
- [ ] **Step 3: Check in the browser** on the synthetic import run.
  1. Expected: the vessel A lane's line rises with the bar's growth; the readout shows `display` with ±.
  2. Drag the playhead back. Expected: the frame, its outlines and the readouts change to that `t`; "Follow live" appears while running.
  3. Use the keyboard (Tab to the timeline, then Left/Right). Expected: it steps frame by frame, with a visible focus ring.
  4. Take screenshots at 1440, 768 and 390 px, light and dark. Expected: no horizontal page scroll at 390 px (the timeline scrolls inside its panel).
- [ ] **Step 4: Commit.** `git commit -m "feat(web): readouts and an editor-style timeline with a draggable playhead"`

---

### Task 15: End to end on real data

**Files:**
- Modify: `docs/knowledge-base/15-decisions-log.md` (D-56: live cadence; D-57: vessel-level measurements on mask unions, per-object measurements in phase 4; anything else the run teaches), `docs/knowledge-base/17-build-plan.md` (phase 2 evidence), `docs/knowledge-base/09-measurement-and-calibration.md` (the Nuroum read-back results, if tested)

- [ ] **Step 1: Import Aymen's recording.**
  1. Write `run.json` (mode `imported`, the file paths, `time_scale`, vessels with ROIs drawn on the first frame; `POST /experiments/{id}/vessels/detect` proposes them).
  2. Run `uv run python -m argus run run.json`.

  Expected:
  - the run finishes;
  - the Run view shows outlines on the real frames;
  - every vessel has measurements with ±;
  - the spend shown matches the sum of `model_calls` rows.

  Record the frame count, the number of SAM calls, the total cost, the wall time and the speed factor.
- [ ] **Step 2: Sanity-check the scale.** Measure one object of known length that is in view (or the card's own 20 mm marker side) from a stored frame with `calibrate` and a hand-drawn mask. Expected: within 2 % of its true length; record the number.
- [ ] **Step 3: Run live** on the camera, with the card and one changing vessel in view, for 10 minutes. Expected:
  - the MJPEG preview plays;
  - a change triggers segmentation;
  - colour readings arrive every analysis step;
  - covering the card with a hand logs an `intervention` event;
  - Stop ends the run.
- [ ] **Step 4: Run every check.**

  ```
  cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .
  cd ../web && npm run lint && npm run typecheck && npm run build
  ```

  Expected: all pass.
- [ ] **Step 5: Update the decisions log and the build plan, then commit.** `git commit -m "docs: phase 2 evidence and decisions"`

---

## End of phase

Final whole-branch review (a fresh reviewer on the most capable model, with this plan's Review Focus and the ledger's rulings). Fix Critical and Important findings test-first; ledger the minors. Merge `phase-2` into `main` after Aymen's go-ahead, delete the workspace, and plan phase 3 (`reason()`, claims, notes, verdicts, the feed and the setup wizard).
