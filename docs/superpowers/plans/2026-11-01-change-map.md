# Point SAM at what changed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When SAM finds nothing for an object that grows into view, Argus compares the vessel with how it looked at the start, asks SAM again with boxes on what changed, and outlines the change itself as a last resort, with every outline saying who drew it.

**Architecture:** A code-only change map (`argus/segment/change.py`) turns a vessel crop and its start reference into regions. A pipeline step (`argus/pipeline/pointing.py`) keeps the start reference per vessel and concept, sends the regions to SAM as box prompts through `segment()`, and falls back to the regions as a code outline. The live analyzer and the still-picture import both call it after an empty by-name answer. Each mask patch carries its source into detections (`backend`), SAM answers (`via`), coverage, refs and the web.

**Tech Stack:** Python 3.12 (numpy, OpenCV, scikit-image, pydantic, SQLite, pytest with anyio), Next.js + TypeScript (node --test).

**Spec:** `docs/superpowers/specs/2026-11-01-change-map-design.md` (D-92, D-93)

## Global Constraints

- Branch `phase-4`. Push and merge into main only on Aymen's go-ahead.
- No new dependency (numpy, OpenCV and scikit-image are already in the stack).
- The LLM never computes numbers: the change map, thresholds, areas and counts are code.
- Only `segment()` calls SAM; every pointed call goes through `segment_with_retries` and is logged.
- Evidence is never overwritten: migration 011 adds a column, nothing is updated; the swarming re-import is a new run.
- Prompts live in `prompts/`; claim-checked text may not hold digits.
- Only recipes with a concept marked `appears = true` ever compute a change map or point SAM.
- Values pinned by the spec (D-92): 3 reference crops; rim erosion 6% of the equivalent radius; light correction from at least 500 outside pixels; noise = 1.4826 × the median ΔE of the reference crops from their median; core above max(8 × noise, 6 ΔE); fringe above max(4 × noise, 3 ΔE); regions smaller than max(0.2% of the vessel area, 25 px) dropped; at most 16 regions, largest first; boxes padded by 15% of their size on each side, clipped, `x2`/`y2` inclusive; a SAM mask covering ≥ 85% of the vessel dropped when the regions cover < 50% of it.
- Labels pinned by the spec (D-93): backends `sam-3.1/image`, `sam-3.1/video`, `sam-3.1/pointed`, `change-map`; via `name`, `pointed`, `code`; ref label suffix ", outlined by code from the change since the start, not by SAM"; Run page title "Outlined by code (change since the start), not SAM"; Results header "Found".
- Before every commit, run the key scan from `worker/`: `for name in MODEL_API_KEY BASETEN_API_KEY; do KEY=$(grep -E "^$name=" ../.env | cut -d= -f2-); if [ -n "$KEY" ] && git diff --cached | grep -qF "$KEY"; then echo "$name FOUND"; exit 1; fi; done`
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Gate each commit on a passing run with `set -o pipefail`. Worker: `cd worker && uv run pytest -q` and `uv run ruff check . && uv run ruff format --check .`. Web: `cd web && npm test && npm run typecheck && npm run lint && npm run format:check`.
- Third-party data stays in git-ignored `data/` and `worker/probes/out/`; no swarming pixels or masks in the repo.

## Review Focus

- A vessel whose crop has fewer than 500 pixels outside its region (a dish filling the frame): no light correction and no crash. Test in Task 1.
- The spend cap refusing the pointed call, or every attempt failing: the change is still outlined by code, and nothing crashes. Test in Task 5.
- A camera move mid-run (the vessel's region changes): the reference starts again and nothing is pointed for the next 3 kept frames. Test in Task 5.
- A run or published bundle from before this change (no `via`, no `backend`): Results shows the two coverage lines as before and outlines are solid. Tests in Tasks 6 and 7.
- A recipe with two concepts where only one appears: the other concept is never pointed. Test in Task 5.

---

### Task 1: The change map

**Files:**
- Create: `worker/argus/segment/change.py`
- Test: `worker/tests/test_change.py`

**Interfaces:**
- Produces (all in `argus.segment.change`):
  - Constants `REFERENCE_FRAMES = 3`, `RIM_ERODE = 0.06`, `MIN_OUTSIDE_PX = 500`, `CORE_NOISE = 8.0`, `CORE_MIN = 6.0`, `FRINGE_NOISE = 4.0`, `FRINGE_MIN = 3.0`, `MIN_AREA_FRACTION = 0.002`, `MIN_AREA_PX = 25`, `MAX_REGIONS = 16`.
  - `@dataclass(frozen=True) class ChangeRegion: box: tuple[int, int, int, int]` (x0, y0, x1, y1 in crop pixels, x1/y1 exclusive), `peak: tuple[int, int]` (x, y of the strongest change), `mask: np.ndarray` (bool, crop-sized).
  - `@dataclass(frozen=True) class ChangeReference: lab: np.ndarray` (float32 H×W×3), `noise: float`, `inside: np.ndarray` (bool: the vessel without its rim), `outside: np.ndarray` (bool: crop pixels outside the vessel's region), `roi: tuple[tuple[float, float], ...]`.
  - `change_reference(crops: Sequence[np.ndarray], vessel_mask: np.ndarray, roi: Sequence[tuple[float, float]]) -> ChangeReference` (BGR uint8 crops of one shape; `vessel_mask` is the vessel's region in crop pixels).
  - `change_regions(reference: ChangeReference, crop: np.ndarray) -> list[ChangeRegion]`, largest first.

- [ ] **Step 1: Write the failing tests.** A shared helper builds a 120×120 grey agar crop (BGR 90, noise σ = 1.5 from `np.random.default_rng(seed)`), a vessel mask that is a disc of radius 50 at the centre, and a reference from 3 such crops (seeds 1–3). Tests:
  - `test_a_faint_growing_patch_is_found`: a disc of radius 15 at (70, 60) raised by 40 grey levels → exactly one region whose box contains (55, 45, 85, 75) and whose peak lies in the disc.
  - `test_noise_alone_changes_nothing`: a fresh noisy crop (seed 4) → `[]`.
  - `test_light_changing_everywhere_is_not_growth`: the crop raised by 20 grey levels inside and outside the vessel → `[]`.
  - `test_a_speck_below_the_size_floor_is_dropped`: a 3×3 speck raised by 80 → `[]`.
  - `test_the_rim_is_left_out`: a ring between radius 48 and 50 raised by 80 → `[]`.
  - `test_a_vessel_filling_its_crop_skips_the_light_correction`: vessel mask all True, the patch from the first test → one region, no error.
  - `test_at_most_sixteen_regions_largest_first`: 20 separate square patches of growing size raised by 60 → 16 regions, areas non-increasing.
- [ ] **Step 2: Run them.** `cd worker && uv run pytest tests/test_change.py -q` → FAIL (module missing).
- [ ] **Step 3: Implement `change_reference` and `change_regions`.** Lab from `cv2.cvtColor(crop.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)`; the reference is the per-pixel median; `inside` is `vessel_mask` eroded by `round(RIM_ERODE * sqrt(area / π))` px with an elliptical kernel; `outside` is `~vessel_mask`. Light correction: when `outside.sum() >= MIN_OUTSIDE_PX`, subtract the median of (Lab now − Lab ref) over `outside` from Lab now. ΔE is CIE76. Thresholds and the size floor as in Global Constraints, hysteresis with `skimage.filters.apply_hysteresis_threshold` on ΔE set to 0 outside `inside`, regions with `skimage.measure.label` (8-connected).
- [ ] **Step 4: Run them.** Same command → PASS. If a test's margin is wrong (not the code), rule on the test value and ledger it.
- [ ] **Step 5: Commit.** `git add worker/argus/segment/change.py worker/tests/test_change.py && git commit -m "feat(segment): a code-only change map against the vessel's start (D-92)"`

### Task 2: Probe box prompts on a real crop

**Files:**
- Create: `worker/probes/sam_pointed.py`, `worker/tests/fixtures/sam/image_pointed.jsonl`
- Modify: `docs/knowledge-base/04-models-and-api.md` (SAM 3.1 section)

**Interfaces:**
- Consumes: `change_reference`, `change_regions` (Task 1); `roi_box`, `roi_mask` from `argus.rois`; the probe helpers in `worker/probes/_common.py`.
- Produces: a ledger ruling `BOX_AND_POINT: yes|no` (whether `1<|box;…|><|point;…|>` for one object is accepted and returns that object), and a ruling on whether the spec's thresholds find the swarm on the real crop.

- [ ] **Step 1: Write the probe.** It reads run `run_abe054d55ff3` from `data/argus.sqlite` (read-only), picks a frame between 14 and 20 h where fliA 0.1's `sam_answers.found` is 0, crops the vessel (`roi_box`, margin 8), builds the reference from the run's first 3 frames, and prints the noise, each region's area and the median ΔE inside the largest region. It saves the crop with the regions drawn to `worker/probes/out/pointed_regions.png`. Then three calls, each printing the objects returned, their area against the region's, and the latency:
  - (a) the crop with one box per region;
  - (b) the crop with the largest region's box and its peak as `1<|box;…|><|point;…|>`;
  - (c) scikit-image's `coins` with one box around one coin, its events saved as JSON lines to `worker/tests/fixtures/sam/image_pointed.jsonl` (like `probes/record_sam.py`).
- [ ] **Step 2: Run it.** `cd worker && uv run python -m probes.sam_pointed`. Expected: three `response.completed` streams, at most $0.0075. Look at `pointed_regions.png`.
- [ ] **Step 3: Record the outcome** in KB 04 under SAM 3.1 (accepted forms, objects returned, whether SAM outlined the dish, latency, measured Nov 2). Ledger the two rulings. If boxes are refused outright, ledger "pointing off": Task 3 still lands, and Task 5 goes straight to the code outline.
- [ ] **Step 4: Commit.** `git add worker/probes/sam_pointed.py worker/tests/fixtures/sam/image_pointed.jsonl docs/knowledge-base/04-models-and-api.md && git commit -m "probe(sam): box prompts on a swarm crop and a recorded pointed stream"`

### Task 3: segment() takes box prompts

**Files:**
- Modify: `worker/argus/segment/types.py` (`MaskPatch`, new `ObjectPrompt`), `worker/argus/segment/__init__.py` (export `ObjectPrompt`), `worker/argus/segment/sam.py`, `worker/argus/pipeline/analyzer.py` (`Segmenter`, `SamSegmenter`, `segment_with_retries`)
- Test: `worker/tests/test_sam.py`, `worker/tests/test_analyzer.py`

**Interfaces:**
- Consumes: `tests/fixtures/sam/image_pointed.jsonl` (Task 2); the `BOX_AND_POINT` ruling.
- Produces:
  - `MaskPatch.source: str | None = None`, kept by `shifted`.
  - `@dataclass(frozen=True) class ObjectPrompt: box: tuple[int, int, int, int]` (x0, y0, x1, y1 in the image's pixels, inclusive), `point: tuple[int, int] | None = None`.
  - `prompt_tokens(prompts: Sequence[ObjectPrompt], width: int, height: int) -> str` in `argus.segment.sam`; `ValueError` for no prompt or more than 16.
  - `segment(..., prompts: Sequence[ObjectPrompt] = ())`: with prompts, the `input_text` is `prompt_tokens(...)` for the image's size, image mode only (`ValueError` for video or with `roi`); tracks still carry `concept`.
  - `Segmenter.pointed(self, image_bgr: np.ndarray, concept: str, prompts: Sequence[ObjectPrompt]) -> SegmentResult`, implemented by `SamSegmenter`.
  - `segment_with_retries(ctx, media, concept, *, t, frame_ids=(), prompts: Sequence[ObjectPrompt] = ())`: with prompts it calls `ctx.segmenter.pointed`; cost and cap as for an image.

- [ ] **Step 1: Write the failing tests.**

```python
def test_prompt_tokens_put_one_box_on_each_object():
    prompts = [ObjectPrompt((10, 20, 49, 79)), ObjectPrompt((0, 0, 9, 9))]
    assert prompt_tokens(prompts, 384, 303) == (
        "<0f>1<|box;x1=10;y1=20;x2=49;y2=79;w=384;h=303|>,2<|box;x1=0;y1=0;x2=9;y2=9;w=384;h=303|>"
    )
```

  Also `test_prompt_tokens_refuse_none_or_more_than_sixteen`; if `BOX_AND_POINT` is yes, `test_a_point_follows_its_box` (`1<|box;…|><|point;x=30;y=50;w=384;h=303|>`), else `point` is ignored and a test says so; `test_a_pointed_request_sends_tokens_not_the_concept` (FakeClient with `recorded("image_pointed")`: the content's text equals the tokens, at least one track, its concept "coin"); `test_prompts_are_image_mode_only`; `test_a_shifted_patch_keeps_its_source`; in `test_analyzer.py`, `test_prompts_go_to_the_pointed_segmenter_and_are_logged` (one `pointed` call, no `image` call, one logged model call of $0.0025).
- [ ] **Step 2: Run them.** `uv run pytest tests/test_sam.py tests/test_analyzer.py -q` → the new tests FAIL.
- [ ] **Step 3: Implement** the interfaces above.
- [ ] **Step 4: Run them.** Same command → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(segment): SAM asked with box prompts through segment() (D-92)"`

### Task 4: Records say how an object was found

**Files:**
- Create: `worker/argus/storage/migrations/011_sam_answer_via.sql`
- Modify: `worker/argus/domain.py` (`SamAnswer`), `worker/argus/storage/repos.py` (`add_sam_answers`, `sam_answers_for_run`), `worker/argus/recipes/model.py` (`Concept`), `recipes/colony-spread.toml`
- Test: `worker/tests/test_storage_phase2.py`, `worker/tests/test_storage.py` and `worker/tests/test_storage_phase3.py` (user_version 10 → 11), `worker/tests/test_recipes.py`

**Interfaces:**
- Produces:
  - Migration: `ALTER TABLE sam_answers ADD COLUMN via TEXT NOT NULL DEFAULT 'name' CHECK (via IN ('name', 'pointed', 'code'));`
  - `SamAnswer.via: Literal["name", "pointed", "code"] = "name"`.
  - `add_sam_answers(db, run_id, frame_id, answers, via: Mapping[tuple[str, str], str] | None = None) -> None` (a key missing from `via` is `name`); `sam_answers_for_run` returns `via`.
  - `Concept.appears: bool = False`, with the comment: an object that is not there at the start and grows into view; an empty answer for it is checked against the change since the start (D-92).
  - `recipes/colony-spread.toml`: `version = 2`, `appears = true` on "microbial colony", the header comment naming D-92.

- [ ] **Step 1: Write the failing tests:** `test_sam_answers_record_how_the_object_was_found` (via `pointed` and `code` read back; a missing key reads `name`; `via='guess'` raises `sqlite3.IntegrityError`; the no-update trigger still holds); the user_version asserts at 11; `test_only_the_colony_appears` (colony-spread v2's concept has `appears`, every other built-in recipe's concepts don't).
- [ ] **Step 2: Run them** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/test_storage.py tests/test_storage_phase2.py tests/test_storage_phase3.py tests/test_recipes.py -q` → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(storage): SAM answers say whether the object was found by name, by pointing or by code (D-93)"`

### Task 5: Point again, live and in still-picture imports

**Files:**
- Create: `worker/argus/pipeline/pointing.py`
- Modify: `worker/argus/pipeline/analyzer.py` (`RunContext`, `analyze_frame`, `_store_detections`, `_track_misses`), `worker/argus/pipeline/imported.py` (`_segment_stills`)
- Test: `worker/tests/test_analyzer.py`, `worker/tests/test_import.py`

**Interfaces:**
- Consumes: Tasks 1, 3 and 4.
- Produces:
  - In `argus.pipeline.pointing`: `POINTED = "sam-3.1/pointed"`, `CODE = "change-map"`; `pointing_concepts(recipe: Recipe) -> set[str]`; `vessel_crop(vessel: Vessel, image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]` (the crop with `roi_box(margin=CROP_MARGIN_PX)`, the vessel's mask in it, the crop's (x0, y0)); `observe(ctx, vessel, concept, image_bgr) -> ChangeReference | None` (adds the crop while the reference is building, starts again when the vessel's `roi` differs from the reference's, and returns the reference only if it was complete before this frame); `async point_again(ctx, vessel, concept, image_bgr, reference, *, t: float, frame_id: str) -> list[MaskPatch]` (frame-coordinate patches with `source` POINTED or CODE; `[]` when there is no region and then no call).
  - `RunContext.change_crops: dict[tuple[str, str], list[np.ndarray]]` and `RunContext.change_refs: dict[tuple[str, str], ChangeReference]`, keyed by (vessel id, concept).
  - `_store_detections` stores `patch.source or backend`; `_track_misses` passes via `code` when any patch's source is CODE, `pointed` when any is POINTED, else `name`.
- Rulings already made: a pointed call the spend cap refuses, or whose every attempt fails, falls back to the code outline (the change is code and costs nothing); `CROP_MARGIN_PX` moves from `imported.py` to `pointing.py` and is imported back; `pointing.py` imports `RunContext` and `segment_with_retries` from `analyzer.py` at module level, so `analyze_frame` imports from `pointing.py` inside the function (no import cycle).

- [ ] **Step 1: Write the failing tests** in `test_analyzer.py`. The ctx's recipe gets `appears = true` on "root"; the reference frames are the scene with the bar painted in the background's colour; `FakeSegmenter.pointed` is scripted like `image`.
  - `test_an_empty_answer_where_the_vessel_changed_points_sam_at_the_change`: 3 plain frames, then the bar with an empty by-name answer → one `pointed` call whose box contains the bar; a detection with backend `sam-3.1/pointed`; via `pointed`; a length reading on that frame.
  - `test_when_pointed_sam_finds_nothing_code_outlines_the_change`: `pointed` empty → backend `change-map`, via `code`, a reading on that frame.
  - `test_a_vessel_sized_answer_is_dropped_for_the_code_outline`: `pointed` returns the whole ROI → backend `change-map`.
  - `test_no_change_means_no_pointed_call`: plain frame, empty answer → no `pointed` call, no reading after a sighting (a gap, D-90).
  - `test_a_concept_that_does_not_appear_is_never_pointed`: a second concept without `appears`, empty answers on a changed frame → `pointed` called for "root" only.
  - `test_a_refused_or_failed_pointed_call_still_outlines_the_change`: spend cap reached, then all attempts failing → backend `change-map` both times, a `segment_failed` event for the failure.
  - `test_the_reference_starts_again_after_the_vessel_moves`: after 3 plain frames, the vessel's `roi` shifts by 5 px → the next 3 frames never call `pointed`; the 4th does.
  - In `test_import.py`: `test_an_import_points_sam_at_what_changed_in_a_still` (stills_view `vessel`, 5 stills: 3 plain, 2 with the bar; `image` empty → `pointed` called on the 2 last stills' crops; their detections carry the pointed backend).
- [ ] **Step 2: Run them.** `uv run pytest tests/test_analyzer.py tests/test_import.py -q` → the new tests FAIL.
- [ ] **Step 3: Implement `pointing.py`** with the interfaces above and D-92's steps 3–4: prompts from each region's box padded by 15% of its size per side, clipped, inclusive (plus its peak if `BOX_AND_POINT`); SAM's patches shifted to frame coordinates; a patch covering ≥ 85% of `reference.inside` dropped when the regions cover < 50% of it; no patch left → each region's mask as a patch.
- [ ] **Step 4: Wire it in.** In `analyze_frame`, in the by-name branch only, after the occlusion filter and before `_track_misses`: for each kept vessel and each concept in `pointing_concepts`, `observe`; if a reference came back and `keyed[vessel][concept]` is empty, replace it with `point_again`'s patches keyed by `ctx.matcher.match`. In `_segment_stills`, after `_keep`, the same for the sample (reading the frame when it wasn't read).
- [ ] **Step 5: Run** the full worker suite and lint → PASS.
- [ ] **Step 6: Commit.** `git commit -m "feat(pipeline): an empty answer where the vessel changed points SAM at the change, then outlines it by code (D-92)"`

### Task 6: Everything downstream says who drew the outline

**Files:**
- Modify: `worker/argus/analyze/coverage.py`, `worker/argus/api/runs.py` (detections route), `worker/argus/claims/refs.py`, `worker/argus/claims/fallback.py`, `prompts/system/scientific-rules.md` (rule 3), `docs/knowledge-base/15-decisions-log.md` (D-92, D-93 from the spec), `docs/knowledge-base/18-glossary.md` ("Change map", "Code outline"), `docs/knowledge-base/06-modes-and-recipes.md` (`appears`)
- Test: `worker/tests/test_fits.py`, `worker/tests/test_api_results.py`, `worker/tests/test_refs.py`, `worker/tests/test_claims.py`, `worker/tests/test_prompts.py`

**Interfaces:**
- Consumes: `SamAnswer.via` (Task 4); detections with backend `change-map` (Task 5).
- Produces:
  - `Coverage` gains `by_name: int = 0`, `pointed: int = 0`, `by_code: int = 0` (found pictures per via).
  - The detections route returns `backend`.
  - `CODE_OUTLINED = ", outlined by code from the change since the start, not by SAM"` in `argus.claims.refs`; `_measurement_ref(vessel, metric, last, lost=None, coded=False)` appends it to the label; `build_refs` sets `coded` when the latest reading's frame has a detection for that vessel and the metric's source concept with backend `change-map`.
  - The fallback note writes "{display} now (outlined by code, not SAM)" for such a reading.
  - Rule 3 gains: 'A reading labelled "outlined by code" was drawn by Argus from the change since the start, not by SAM: say so when you cite it.'

- [ ] **Step 1: Write the failing tests:** `test_coverage_counts_how_each_picture_was_found`; the detections route includes `backend`; `test_a_code_outlined_reading_says_so_in_its_label`; `test_the_fallback_says_a_reading_was_outlined_by_code`; a rule pin that rule 3 holds "outlined by code".
- [ ] **Step 2: Run them** → FAIL.
- [ ] **Step 3: Implement**, and write the docs rows.
- [ ] **Step 4: Run** the full worker suite and lint → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(results): coverage, refs, notes and rules say whether SAM or code drew the outline (D-93)"`

### Task 7: The web shows who drew each outline

**Files:**
- Modify: `web/lib/types.ts` (`Coverage`, `DetectionOutline`), `web/lib/misses.ts`, `web/components/results/FitTable.tsx`, `web/components/run/RunFrame.tsx`, `web/components/run/RunFrame.module.css`
- Test: `web/tests/misses.test.ts`

**Interfaces:**
- Consumes: `coverage.by_name/pointed/by_code` and detections' `backend` (Task 6).
- Produces:
  - `Coverage` gains optional `by_name`, `pointed`, `by_code`; `DetectionOutline` gains optional `backend`.
  - `coverageLines(c, span): [string, string | null, string | null]`: found, how ("55 by name · 30 pointed · 12 by code" when pointed + by code > 0, else null), missed.
  - `CODE_OUTLINE = "change-map"` and `outlinedByCode(d: DetectionOutline): boolean` in `web/lib/misses.ts`.
  - FitTable's header reads "Found" and shows the how line under the count; RunFrame adds `styles.coded` (`stroke-dasharray: 5 4`) and a `<title>` "Outlined by code (change since the start), not SAM" to code outlines.

- [ ] **Step 1: Update and write the failing tests** in `misses.test.ts`: the three-line coverage (with the split; without it; an old bundle without the fields → how is null), `outlinedByCode` true only for `change-map` and false when `backend` is missing.
- [ ] **Step 2: Run** `cd web && npm test` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the web checks → PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(web): Results splits how each dish was found; code outlines are dashed (D-93)"`

### Task 8: Check it on the swarming scans

Approved in the design (Nov 1): about $3.50 of SAM calls, plus one verdict. The run stays local (D-89): no bundle, no publish.

- [ ] **Step 1:** Start the worker preview on this branch's code and confirm it answers.
- [ ] **Step 2:** Re-import from the saved request: `cd worker && uv run python -m argus run "<scratchpad>/swarm_run.json"` (experiment `exp_fbf009d4df33`, manifest `data/datasets/swarming/frames/manifest.json`), in the background, until status `finished`.
- [ ] **Step 3:** Ask for the verdict with `POST /api/runs/<new run>/verdict`.
- [ ] **Step 4:** Read from the database and record in the ledger, for each dish, pictures found in the old run (`run_abe054d55ff3`) and the new one, split by name, pointed and code; the new run's misses; the verdict; the run's spend.
- [ ] **Step 5:** Open the new run in the browser pane and look at about ten outlines, code outlines first, on fliA 0.1 and fliA 1. Note any that outline something other than the swarm.
- [ ] **Step 6:** Write the outcome into KB 17 (Phase 5 section, a "Fix 2" line) and commit: `git commit -m "docs: fix 2 on the swarming scans"`.

Expected: every dish found in more pictures than before; code outlines on fliA 0.1 follow the faint swarm by eye. If code outlines visibly trace condensation or the rim, stop and report to Aymen rather than tuning thresholds past the time box.
