# Re-analysing published data — design

Date: Oct 29, 2026 · Status: approved by Aymen (decisions delegated) · Builds on phase 3 (branch `phase-3`)
Research: `docs/research/Demo experiments and footage options.md` · Decisions: D-70, D-71, D-72

## Why

The demo's long-experiment segment re-analyses published data instead of footage Aymen films (D-70). The first
dataset is Genze & Grimm's germination set (CC BY 4.0): 3 species × 7 runs × 10–12 petri dishes of 85 mm, one
624×624 px crop per dish every 30 min for 48 h (97 frames), and a box per seed per frame labelled `<sp>_im`
(imbibed, not germinated) or `<sp>_el` (radicle out, germinated). It is already downloaded to
`data/datasets/genze/GermPredDataset.zip` (git-ignored).

**Success:** by Nov 1 a Genze re-analysis plays in the Run view with real measurements in mm, checked notes, a
verdict marked "Retrospective re-analysis", and an agreement figure against the dataset's own labels; every frame
credits its source; nothing third-party is committed.

## Decisions

- **D-71 Retrospective verdicts.** A run whose source is published data is judged as usual, but a plan locked after
  the data was recorded no longer caps it at Too early. Instead the verdict carries a `retrospective` check
  ("Re-analysis of published data: the plan was written after the data was recorded, so this verdict tests
  consistency with the plan, not a prediction") and the label "Retrospective" in the UI. Live runs and own
  imports keep D-67 unchanged.
- **D-72 A virtual plate.** Published dishes are tiled frame by frame into one grid image per time step and imported
  as one run, one vessel per tile, so the existing pipeline, verdict and Run view work unchanged. The montage is
  labelled as assembled. Rejected: one run per dish (needs a cross-run comparison layer; shows one dish at a time),
  and rendering an MP4 for the video importer (lossy, timing becomes a fudge factor, no place for provenance or
  labels).
- **Scope cuts:** no relative pixel mode and no wizard option for published data (a CLI starts the run); both can
  come later. Phase 4 (fits, Ax next run, Results screens) gets its own spec.

## Components

### 1. Dataset adapter — `worker/argus/datasets/genze.py`, CLI `python -m argus dataset genze`

- `build_plate(zip_path, out_dir, *, dishes: list[DishRef], columns: int) -> Manifest`, where
  `DishRef(species, run, dish)`. Reads the zip in place (no full extraction), checks every chosen dish has the same
  frame indices, writes `frames/frame_###.jpg` (tiles in the order given, row-major, no resizing; a 2-px dark
  gutter) and `manifest.json`.
- `Manifest` (pydantic, also the import's contract): `dataset`, `doi`, `url`, `licence`, `credit` (the CC BY credit
  line, ending "cropped and tiled by Argus"), `interval_s` (1800), `frames` (file names in time order),
  `tiles: [{label, species, run, dish, box: [x0, y0, x1, y1], germinated: [int per frame], seeds: int}]`,
  `assembled: true`, `retrospective: true`, `dish_diameter_mm` (85).
- Default plate: 3 rye and 3 pearl-millet dishes, each species from two runs; overridable by flags.

### 2. Published-image source — `worker/argus/capture/images.py`

- `SourceKind.IMAGES`; `RunSource` gains `manifest: str | None` and `provenance: Provenance | None`
  (`dataset, doi, url, licence, credit, assembled, retrospective`). Stored in the existing `runs.source` JSON: no
  migration for this part.
- `ImageSequenceSource(manifest_path).frames()` yields `(t = index × interval_s, image)`; the import pipeline accepts
  it wherever it takes `VideoFileSource` (scan → segment → measure), with sampling by the recipe's analysis step.
- `POST /experiments/{id}/runs` accepts `{mode: "imported", manifest: "<path>", roles: {"<species>": "control" |
  "treatment"}}`; vessels come from the manifest's tiles (label = tile label, ROI = tile box, condition = species,
  role from `roles`). Every species needs a role, and at least one is the control.
- Run view: a "Published data · retrospective" badge and the credit line under the frame.

### 3. The dish as the ruler — `worker/argus/calibration/dish.py`

- `dish_scale(image_bgr, rois, diameter_mm) -> DishScale | None`: in each vessel's ROI, fits the rim (Hough circle
  on the grey image, refined by an ellipse fit to the edge points); `mm_per_px = diameter_mm / major_axis_px`; the
  run's scale is the median over dishes. `rel_uncertainty` = the spread across dishes (relative standard deviation)
  combined with a 3 % allowance for nominal sizes and the seed-to-rim height (research: ±3–5 %). Fails (None) when
  fewer than half the ROIs give a rim within 15 % of the median, or the minor/major ratio is under 0.9 (tilt).
- `calibrate()` falls back to it when there is no card or ruler and the setup or manifest gives a dish diameter;
  stored as a calibration with `card = "dish"` (the column is free text). The calibration line in the Run view reads
  "Dish rim · 85 mm · 7.06 px/mm ± 3.4 %".

### 4. Germination on dishes — recipe `recipes/germination-dish.toml` and a count method

- Concepts `seed` and `root`; measurements `root_length` (skeleton, mm, total per dish) and `germinated`
  (count): the number of seed objects whose 3-px-dilated mask touches a root component at least 2 mm long, the
  same meaning as the labels' `_el`. Method `seeds_with_roots` in the measure engine; it is pure geometry on the
  two concepts' masks, so it is tested on synthetic masks.

### 5. Agreement with the dataset's labels

- Migration 005: append-only table `reference_values(id, run_id, vessel_id, t, metric, value, source)`; the import
  writes the manifest's per-tile germinated counts as rows with `source = "<dataset> labels"`. They never touch
  `measurements`.
- `agreement(db, run_id, metric="germinated") -> Agreement`: per vessel, the mean absolute difference between
  Argus's count and the label count at the same t, the share of frames where they match exactly, and the time to
  50 % germinated by each; plus totals. `GET /runs/{id}/agreement`.
- Verdict panel: a small "Checked against the dataset's labels" table (per dish and overall). Notes don't cite the
  agreement (it would need a new ref kind); the panel shows it.

### 6. Retrospective verdicts and the montage rival

- `verdict_inputs`: when `run.source.provenance.retrospective`, `locked` means "a plan is locked" (the D-71 rule),
  and the ceiling adds the `retrospective` check (ok = None, wording above) in place of D-69's "preregistered" check;
  the stored verdict gets `body.retrospective = true`.
- When tiles come from different runs, code adds the rival "run-to-run differences" to the verdict's rival states (the
  locked plan is unchanged); it stays open until the researcher resolves it with a reason, e.g. "same rig and
  protocol per the paper", through the existing `resolve` review.
- `VerdictChip` shows "Retrospective" beside the level.

## Data flow

zip → `build_plate` → `frames/` + `manifest.json` (data/, git-ignored) → `POST /runs` with the manifest → scan
(quality gate, watcher) → dish scale → SAM video per tile and concept → measurements → reference values from the
manifest → notes → final verdict (retrospective) → `GET /agreement` → Run view.

## Errors

- A missing or tampered zip (SHA-256 recorded on first build) or uneven frame indices: `build_plate` refuses with the
  dish named.
- No dish rim found: the run measures nothing in mm and says so (the existing no-calibration event), never a
  default scale.
- Seeds above SAM's 16-object limit in a tile: the existing limit event; the default plate stays under it (≤ 12).
- Lid condensation (maize, day 2): the quality gate's blur flag leaves gaps, which the notes report.
- SAM missing thin roots: root length and the germinated count come out low; the agreement check shows it rather
  than hiding it.

## Testing

- `build_plate` on a tiny synthetic zip (two dishes, three frames, XML labels): tile layout, manifest contents,
  germinated counts per frame, refusal on uneven frames.
- `ImageSequenceSource`: frame times, order, manifest validation.
- `dish_scale` on drawn circles of known size (with noise and a tilted ellipse): scale within 1 %, refusal on tilt
  and on too few rims.
- `seeds_with_roots` on synthetic masks: touching vs not, short vs long roots, rye-like multiple roots per seed
  counted once.
- `agreement` on stored measurements and reference values: mean absolute difference, exact-match share, time to 50 %.
- Verdict: retrospective run with a plan locked after recording gets a real ceiling plus the check; a live run keeps
  D-67; the run-to-run rival appears only for mixed runs.
- One end-to-end import of a real 6-dish Genze plate (marked slow), checking scale ≈ 7 px/mm (±5 %), non-zero
  germinated counts by the last frame and an agreement figure.

## Order and effort (about 2.5 days)

1. Adapter and manifest (0.5 d) · 2. image source and provenance (0.5 d) · 3. dish ruler (0.5 d) · 4. germination
count (0.5 d) · 5. reference values and agreement (0.5 d) · 6. retrospective verdict and montage rival (0.25 d) · real
plate run and screen check. Phase 4 starts after; if time runs short, cut 5's panel to the API and a note.
