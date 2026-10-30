# Recipes from your words, and re-analysing published data — design

Date: Oct 29, 2026 · Status: approved by Aymen (decisions delegated) · Builds on phase 3 (branch `phase-3`)
Research: `docs/research/Demo experiments and footage options.md` · Decisions: D-70, D-71, D-72, D-73

## Why

Argus is a general research app: the researcher says what they will do, and Argus sets itself up for that
experiment. Today the researcher picks one of four fixed recipes when creating an experiment, and the AI only drafts
the plan inside it. This design lets Argus write the recipe itself from the researcher's words (what to look for,
what to measure, how often, which rival explanations matter), checked by code against Argus's measuring toolbox.

The demo then shows that generality on data nobody filmed for Argus: the researcher describes a germination
comparison in one sentence, Argus configures itself, and re-analyses a published dataset (D-70). The first dataset is
Genze & Grimm's germination set (CC BY 4.0): 3 species × 7 runs × 10–12 petri dishes of 85 mm, one 624×624 px crop
per dish every 30 min for 48 h (97 frames), and a box per seed per frame labelled `<sp>_im` (imbibed, not germinated)
or `<sp>_el` (radicle out, germinated). It is downloaded to `data/datasets/genze/GermPredDataset.zip` (git-ignored).

Nothing here is specific to germination except the dataset adapter, which only prepares demo data.

**Success:**
- Any experiment: one sentence in the new-experiment dialog gives a valid, editable recipe and plan in under a minute,
  or a clear reason why not.
- The demo: by Nov 2 a Genze re-analysis set up that way plays in the Run view with measurements in mm, checked notes,
  a verdict marked "Retrospective re-analysis", and an agreement figure against the dataset's own labels; every frame
  credits its source; nothing third-party is committed.

## Decisions

- **D-73 Argus writes the recipe from the researcher's words.** A drafted recipe is validated by code against the
  recipe schema and the measuring toolbox; it belongs to the experiment, stays editable until the plan is locked, and
  is frozen with it. The four file recipes remain as templates the AI may start from or the researcher may pick.
- **D-71 Retrospective verdicts.** A run whose source is published data is judged as usual, but a plan locked after
  the data was recorded no longer caps it at Too early. Instead the verdict carries a `retrospective` check and the
  label "Retrospective". Live runs and own imports keep D-67 unchanged.
- **D-72 A virtual plate.** Published dishes are tiled frame by frame into one grid image per time step and imported
  as one run, one vessel per tile; the montage is labelled as assembled.
- **Scope cuts:** no relative pixel mode and no wizard option for published data (a CLI starts the run). Phase 4
  (fits, Ax next run, Results screens) gets its own spec.

## Components

### 1. Recipe from your words (general)

- **Toolbox, described for the model.** `argus/recipes/toolbox.py` lists every measuring method in plain words with
  its family and unit: `area` (mm2), `height` (mm), `skeleton_length` (mm), `component_count` (count),
  `touching_count` (count, component 4), `lab_mean` (Lab), `delta_e` (dE00); curves; watcher signals. The prompt
  and the strict schema are built from it, so the model can only choose what Argus can measure.
- **Prompt and schema.** `prompts/setup/recipe.md` and `prompts/schemas/recipe_spec.json`: concepts (1–4 short noun
  phrases SAM can find, one thing each), measurements (id, family, method, from concept, unit, and for
  `touching_count` the touched concept and minimum length), `analysis_step_s`, `curve`, `main_measurement`, rivals,
  plus the plan draft fields already in `recipe_draft.json` (hypothesis, prediction, threshold, metric, direction,
  min_effect, checkpoint_s, treatment, factor, factor_unit, conditions) and `safety_notes`. The template recipes go
  in as examples.
- **Validation and retry.** `draft_recipe(words, *, reasoner) -> RecipeDraft`: Muse Spark (routine tier) answers; code
  checks the answer's schema, then builds a `Recipe` (pydantic: methods fit families, concepts are single and unique,
  measurements read known concepts, main measurement exists, units match the toolbox, the plan's metric is one of
  the recipe's stored metrics). Any failure goes back once as reasons, as for notes; a second failure answers 422
  with the reasons. Every call is logged (`function = "recipe"`, no run).
- **Safety.** The model lists concerns in `safety_notes`; code also screens the words and concepts for flame, strong
  heat, pressure, hazardous chemicals and pathogens and adds a fixed warning ("Argus won't automate any hardware for
  this; …"). No medical advice, as everywhere.
- **Storage.** Migration 005 adds `experiment_recipes(experiment_id, version, body, origin, created_at)`; origin is
  `drafted` or `edited`. A drafted experiment gets `recipe_id = "own"` and the version in use; `recipe_for(db,
  recipes, experiment) -> Recipe` returns the experiment's own recipe or the file template, and replaces the three
  `recipes[experiment.recipe_id]` look-ups. Edits make a new version until the plan is locked; after that, 409.
- **API.** `POST /experiments/draft {words}` → `{recipe, plan, setup_hints, safety_notes, question}` (nothing saved);
  `POST /experiments {title, recipe}` accepts a full recipe as well as a template id; `GET/PUT
  /experiments/{id}/recipe`.
- **Web.** The new-experiment dialog starts with "What will you do?" and offers "Pick a template instead". The
  draft appears in plain words — "Argus will look for: seed, root · measure: root length, germinated seeds · every
  30 min" — with each line editable, the suggested numbers (step, smallest effect, checkpoint) marked "suggested",
  and any safety warning shown. Creating the experiment saves the recipe and plan draft and opens the wizard as today.

### 2. Published-image source — `worker/argus/capture/images.py`

- `SourceKind.IMAGES`; `RunSource` gains `manifest: str | None` and `provenance: Provenance | None`
  (`dataset, doi, url, licence, credit, assembled, retrospective`), stored in the existing `runs.source` JSON.
- A manifest (`argus/datasets/manifest.py`, pydantic): `dataset, doi, url, licence, credit, interval_s, frames`
  (file names in time order), `tiles: [{label, condition, run, dish, box, seeds, labels: {metric: [value per
  frame]}}]`, `assembled, retrospective, dish_diameter_mm`. Any published image set can be described this way.
- `ImageSequenceSource(manifest_path).frames()` yields `(t = index × interval_s, image)`; the import pipeline accepts
  it wherever it takes `VideoFileSource`.
- `POST /experiments/{id}/runs` accepts `{mode: "imported", manifest: "<path>", roles: {"<condition>": "control" |
  "treatment"}}`; vessels come from the tiles (label, ROI = box, condition, role from `roles`). Every condition needs
  a role, and at least one is the control.
- Run view: a "Published data · retrospective" badge and the credit line under the frame.

### 3. The dish as the ruler (general) — `worker/argus/calibration/dish.py`

- `dish_scale(image_bgr, rois, diameter_mm) -> DishScale | None`: in each vessel's ROI, fits the rim (Hough circle on
  the grey image, refined by an ellipse fit to the edge points); `mm_per_px = diameter_mm / major_axis_px`; the run's
  scale is the median over dishes. `rel_uncertainty` combines the spread across dishes (relative standard deviation)
  with a 3 % allowance for nominal sizes and the seed-to-rim height (research: ±3–5 %). None when fewer than half the
  ROIs give a rim within 15 % of the median, or a minor/major ratio is under 0.9 (tilt).
- `calibrate()` falls back to it when there is no card or ruler and the setup or manifest gives a dish diameter;
  stored with `card = "dish"` (the column is free text). The Run view reads "Dish rim · 85 mm · 7.06 px/mm ± 3.4 %".

### 4. Counting objects that touch another (general) — toolbox method `touching_count`

- `MeasurementSpec` gains `touching: str | None` and `min_length_mm: float | None`. `touching_count` counts the
  objects of concept `from` whose 3-px-dilated mask touches a component of concept `touching` at least
  `min_length_mm` long (skeleton length). Each object counts once, however many components touch it.
- Germination uses it as "seeds with a root ≥ 2 mm" (the labels' `_el`); other uses: bubbles on a leaf, crystals
  touching a seed, colonies touching a disk.

### 5. Agreement with a dataset's labels (general for labelled data)

- Migration 005 also adds append-only `reference_values(id, run_id, vessel_id, t, metric, value, source)`; the
  import writes the manifest's per-tile labels as rows with `source = "<dataset> labels"`. They never touch
  `measurements`.
- `agreement(db, run_id, metric) -> Agreement`: per vessel, the mean absolute difference between Argus's reading and
  the label at the same t, the share of frames that match exactly, and the time to 50 % of the final label value by
  each; plus totals. `GET /runs/{id}/agreement?metric=`.
- Verdict panel: a small "Checked against the dataset's labels" table. Notes don't cite it.

### 6. Retrospective verdicts and the montage rival

- `verdict_inputs`: when `run.source.provenance.retrospective`, `locked` means "a plan is locked" (D-71), and the
  ceiling adds the `retrospective` check (ok = None: "Re-analysis of published data: the plan was written after the
  data was recorded, so this verdict tests consistency with the plan, not a prediction") in place of D-69's
  "preregistered" check; the stored verdict gets `body.retrospective = true`.
- When tiles come from different runs, code adds the rival "run-to-run differences" to the verdict's rival states (the
  locked plan is unchanged); it stays open until the researcher resolves it with a reason through the existing
  `resolve` review.
- `VerdictChip` shows "Retrospective" beside the level.

### 7. The Genze adapter (demo data only) — `worker/argus/datasets/genze.py`, CLI `python -m argus dataset genze`

- `build_plate(zip_path, out_dir, *, dishes: list[DishRef], columns: int) -> Manifest`, `DishRef(species, run,
  dish)`. Reads the zip in place, checks the chosen dishes share frame indices, writes `frames/frame_###.jpg` (tiles
  row-major, no resizing, a 2-px dark gutter) and `manifest.json` with each tile's `labels.germinated` per frame
  (count of `_el` boxes), `seeds` (boxes in the first frame), the credit line ending "cropped and tiled by Argus",
  `interval_s = 1800`, `dish_diameter_mm = 85`, and the zip's SHA-256.
- Default plate: 3 rye and 3 pearl-millet dishes, each species from two runs.

## Data flow

Words → `POST /experiments/draft` → validated recipe + plan → experiment (own recipe) → wizard → plan locked. Zip →
`build_plate` → `frames/` + `manifest.json` (data/, git-ignored) → `POST /runs` with the manifest and roles → scan
(quality gate, watcher) → dish scale → SAM video per tile and concept → measurements → reference values → notes →
final verdict (retrospective) → `GET /agreement` → Run view.

## Errors

- A recipe the model can't get right twice: 422 with the reasons; the dialog offers the templates.
- A concept SAM can't find: the preview shows no outlines for it before anything is locked.
- A missing or changed zip (SHA-256) or uneven frame indices: `build_plate` refuses, naming the dish.
- No dish rim found: nothing is measured in mm and the run says so (the existing no-calibration event).
- More than 16 objects of a concept in a tile: the existing limit event; the default plate stays under it (≤ 12).
- Lid condensation (maize, day 2): the quality gate's blur flag leaves gaps, which the notes report.
- SAM missing thin roots: lengths and counts come out low; the agreement check shows it rather than hiding it.

## Testing

- Recipe drafting with a scripted reasoner: a valid answer becomes a `Recipe`; an unknown method, a two-thing concept
  or a metric outside the recipe is retried with reasons, then 422; safety words add the fixed warning; the call is
  logged; `recipe_for` returns own recipes and templates; edits after lock answer 409.
- One real `draft` call (marked slow) on three different descriptions — germination in dishes, dough rising in jars,
  apple browning — each validating without edits.
- `build_plate` on a tiny synthetic zip; `ImageSequenceSource` frame times and order; `dish_scale` on drawn circles
  (within 1 %, refusing tilt and too few rims); `touching_count` on synthetic masks (touching vs not, short vs long,
  several roots per seed counted once); `agreement` on stored readings and reference values.
- Verdict: a retrospective run with a late plan gets a real ceiling plus the check; a live run keeps D-67; the
  run-to-run rival appears only for mixed runs.
- One end-to-end Genze plate (slow): scale ≈ 7 px/mm (±5 %), germinated counts by the last frame, an agreement figure.

## Order and effort (about 4 days)

1. Recipe from your words (1–1.5 d) · 2. image source and provenance (0.5 d) · 3. dish ruler (0.5 d) · 4.
`touching_count` (0.5 d) · 5. retrospective verdict and montage rival (0.25 d) · 6. reference values and agreement
(0.5 d) · 7. Genze adapter and the real plate (0.5 d). If time runs short, 6 goes to the API only, then the
published-data badge styling; phase 4 then shrinks to the next-run suggestion alone.
