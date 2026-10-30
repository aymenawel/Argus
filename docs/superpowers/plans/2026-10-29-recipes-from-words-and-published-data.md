# Recipes From Your Words and Published Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Argus sets itself up from the researcher's words (a validated recipe and plan), and can re-analyse published image data — measured from the dish rim, judged retrospectively and checked against the dataset's own labels — shown on the Genze germination set.

**Architecture:** A toolbox module describes every measuring method; Muse Spark drafts a recipe within it and code validates it as a `Recipe`, storing it per experiment (`recipe_for` replaces the fixed look-ups). Published images enter as a new source kind driven by a manifest (frames, interval, tiles, provenance, labels); the dish ruler and `touching_count` are general additions to calibration and the measure engine; the verdict learns "retrospective"; labels become append-only reference values with an agreement report.

**Tech Stack:** Python 3.12 worker (FastAPI, pydantic, OpenCV, SQLite migrations), `openai` SDK via `reason()`; Next.js 16 / React 19 / TypeScript; Node's test runner for web units.

**Spec:** `docs/superpowers/specs/2026-10-29-published-data-reanalysis-design.md` (D-70–D-73). Branch: `reanalysis`, cut from `phase-3` (phase 3's live dye run is still pending; this branch builds on it).

## Global Constraints

- The LLM never computes numbers: a drafted recipe's numbers (analysis step, smallest effect, checkpoint) are suggestions the UI marks as such; measurements and agreement are code.
- Only `segment()` and `reason()` call models; prompts live in `prompts/`, JSON schemas in `prompts/schemas/`; every model call is logged (`function = "recipe"`, no run, for drafts).
- Never overwrite evidence: reference values are their own append-only table; a recipe version is immutable once saved, and an experiment's recipe is frozen when its plan is locked.
- Repo is public: third-party data stays in `data/` (git-ignored); only scripts and manifests' code are committed; credits come from the manifest. No secrets; mirror new env variables in `.env.example`.
- No new dependency: OpenCV (`HoughCircles`, `fitEllipse`), `zipfile` and `hashlib` cover everything.
- Safety: no automatic hardware actions for flame, strong heat, pressure, hazardous chemicals or pathogens; no medical advice.
- Vocabulary from `docs/knowledge-base/18-glossary.md`; add "recipe draft", "virtual plate", "reference values", "retrospective verdict".

## Review Focus

1. **A plausible but unmeasurable concept** ("growth", "the change", "seeds and roots"): the draft is rejected with a reason and retried, never saved as a recipe SAM can't act on. Test in Task 1.
2. **Words describing a hazardous experiment** (a candle, bleach, bacteria from a hospital): the draft carries the fixed safety warning, and no field proposes automation. Test in Task 1.
3. **A recipe edited after the plan was locked, or a run started meanwhile**: 409, and the run uses the version the plan locked. Test in Task 2.
4. **A manifest whose frames are missing or out of order on disk**: the import refuses before measuring anything, naming the file. Test in Task 5.
5. **Tiles where the dish rim isn't found, or dishes disagree on scale**: no millimetres at all rather than a wrong scale, and the run says why. Test in Task 6.

---

### Task 1: The toolbox and drafting a recipe from words

**Files:**
- Create: `worker/argus/recipes/toolbox.py`, `worker/argus/recipes/draft.py`, `prompts/setup/recipe.md`, `prompts/schemas/recipe_spec.json` (the static parts; enums filled from the toolbox at call time)
- Modify: `worker/argus/recipes/model.py` (`MeasurementSpec.touching`, `MeasurementSpec.min_length_mm`; `"touching_count"` in the count family; concepts of at most 4 words with no " and ")
- Test: `worker/tests/test_recipe_draft.py`

**Interfaces:**
- Consumes: `Reasoner`, `ReasonError`, `ReasonTask` (phase 3), `schema_errors` (`argus/claims/schema.py`), `load_prompt`, `load_schema`, the four file recipes as templates.
- Produces:
  - `Tool(method: str, family: str, unit: str, words: str)`; `TOOLBOX: tuple[Tool, ...]` with area (mm2), height (mm), skeleton_length (mm), component_count (count), touching_count (count), lab_mean (Lab), delta_e (dE00).
  - `recipe_spec_schema() -> dict` (strict; `method` and `unit` enums from `TOOLBOX`, `curve` from `Recipe`).
  - `RecipeDraft(recipe: Recipe, plan: PlanDraft, setup_hints: dict, safety_notes: list[str], question: str)`.
  - `async draft_recipe(words: str, *, reasoner: Reasoner, templates: Mapping[str, Recipe], experiment_id: str = "draft") -> tuple[RecipeDraft, list[ModelCallDraft]]`; raises `RecipeRefused(reasons: list[str], calls: list[ModelCallDraft])` after two failed answers.
  - `SAFETY_WARNING: str` = "Argus won't automate any hardware for this experiment. Take care: it mentions {what}." and `safety_screen(words: str, concepts: Sequence[str]) -> list[str]` (flame, fire, candle, burn, boil, pressure, bleach, acid, ammonia, bacteria, pathogen, mould spores, blood).

- [ ] **Step 1: Write the failing tests** (a `FakeReasoner` from `tests/reasoning.py` returns scripted answers)

```python
async def test_a_valid_answer_becomes_a_recipe_and_a_plan():
    draft, calls = await draft_recipe(WORDS_GERMINATION, reasoner=FakeReasoner([answer()]), templates=TEMPLATES)
    assert draft.recipe.concepts[0].name == "seed" and draft.recipe.main_measurement == "germinated"
    assert draft.plan.metric in draft.recipe.stored_metrics() and len(calls) == 1 and calls[0].function == "recipe"

async def test_an_unmeasurable_answer_is_retried_with_its_reasons():
    bad = answer(concepts=["growth of seeds and roots"], measurements=[{"id": "g", "family": "size", "method": "volume", "from": "x", "unit": "ml"}])
    reasoner = FakeReasoner([bad, answer()])
    draft, calls = await draft_recipe(WORDS_GERMINATION, reasoner=reasoner, templates=TEMPLATES)
    retry = reasoner.tasks[1].variable[-1]
    assert "method: 'volume' is not one of" in retry and "one thing" in retry and len(calls) == 2

async def test_two_bad_answers_are_refused_with_the_reasons():
    with pytest.raises(RecipeRefused) as refused:
        await draft_recipe(WORDS_GERMINATION, reasoner=FakeReasoner([answer(metric="nonsense")] * 2), templates=TEMPLATES)
    assert any("metric" in r for r in refused.value.reasons) and len(refused.value.calls) == 2

async def test_hazardous_words_carry_the_fixed_warning():
    draft, _ = await draft_recipe("I will heat sugar over a candle flame and film it", reasoner=FakeReasoner([answer()]), templates=TEMPLATES)
    assert any(n.startswith("Argus won't automate any hardware") and "flame" in n for n in draft.safety_notes)

def test_the_schema_offers_only_the_toolbox():
    schema = recipe_spec_schema()
    methods = schema["properties"]["measurements"]["items"]["properties"]["method"]["enum"]
    assert set(methods) == {t.method for t in TOOLBOX}

@pytest.mark.slow  # real Muse Spark calls; skipped without MODEL_API_KEY
@pytest.mark.parametrize("words", [WORDS_GERMINATION, "Dough rising in four jars, two with extra sugar", "Apple slices browning, half dipped in vitamin C"])
async def test_real_drafts_validate_without_edits(words, settings):
    draft, _ = await draft_recipe(words, reasoner=SettingsReasoner(settings), templates=TEMPLATES)
    assert draft.recipe.concepts and draft.plan.metric in draft.recipe.stored_metrics()
```

Helpers in the test file: `WORDS_GERMINATION = "I'll compare how fast rye and pearl millet seeds germinate in petri dishes"`, `TEMPLATES = load_all(REPO_ROOT / "recipes")`, and `answer(**overrides) -> dict`, a valid answer for germination (concepts seed and root; measurements root_length skeleton_length mm from root, germinated touching_count count from seed touching root min_length_mm 2; analysis_step_s 1800; curve logistic; main germinated; plan metric germinated, direction higher, min_effect 2, checkpoint_s 86400) with the given fields replaced.

- [ ] **Step 2: Run** `cd worker && uv run pytest tests/test_recipe_draft.py -q` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** `draft_recipe` builds a `ReasonTask` (`function="recipe"`, stable: rules + toolbox described in words + the templates as TOML examples; variable: the words, then the task), calls `reasoner(tier="routine", schema=recipe_spec_schema(), schema_name="ArgusRecipe")`, then: `schema_errors` → `Recipe.model_validate` (catch `ValidationError`, each error becomes a reason; the concept rule's message reads "'<name>' names more than one thing; give each thing its own concept") → the plan's metric must be in `stored_metrics()` → retry once with the reasons; the recipe `id` is always `"own"`, `version` 1. A `ReasonError` counts as a failed answer. The prompt (`prompts/setup/recipe.md`) asks for 1–4 concepts SAM can find as short noun phrases, measurements only from the toolbox, an analysis step that fits how fast the thing changes, rivals that apply, and says its numbers are suggestions the researcher confirms.
- [ ] **Step 4: Run** the tests again — Expected: PASS; then `uv run pytest -q tests/test_recipes.py tests/test_prompts.py` (the model change must keep the four templates valid).
- [ ] **Step 5: Commit** — `git commit -m "feat(recipes): Argus drafts a recipe from the researcher's words, validated against its toolbox"`

### Task 2: Recipes that belong to an experiment

**Files:**
- Create: `worker/argus/storage/migrations/005_own_recipes.sql`, `worker/argus/recipes/resolve.py`
- Modify: `worker/argus/storage/repos.py`, `worker/argus/api/app.py`, `worker/argus/api/setup.py`, `worker/argus/api/notes.py`, `worker/argus/pipeline/jobs.py`
- Test: `worker/tests/test_api_recipes.py`

**Interfaces:**
- Consumes: Task 1's `draft_recipe`, `RecipeDraft`, `RecipeRefused`.
- Produces:
  - Table `experiment_recipes(experiment_id, version, body, origin CHECK IN ('drafted','edited'), created_at, PRIMARY KEY(experiment_id, version))`, no updates or deletes (triggers).
  - `save_recipe(db, experiment_id, recipe: Recipe, origin) -> int` (the new version; also sets `experiments.recipe_id = 'own'` and `recipe_version`), `own_recipe(db, experiment_id, version: int | None = None) -> Recipe | None`.
  - `recipe_for(db, templates, experiment) -> Recipe` — the experiment's own version in use, else the template; used everywhere `recipes[experiment.recipe_id]` was.
  - API: `POST /api/experiments/draft {words}` → `{recipe, plan, setup_hints, safety_notes, question}` (503 without a reasoner, 422 with reasons on `RecipeRefused`; calls logged with no run); `POST /api/experiments` accepts `{title, recipe_id}` or `{title, recipe, plan?}` (saves the recipe as `drafted` and the plan draft); `GET /api/experiments/{id}/recipe`; `PUT /api/experiments/{id}/recipe` (`edited`; 409 once a plan is locked); `GET /api/recipes/{id}` unchanged for templates.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_drafted_recipe_creates_an_experiment_that_uses_it(client, reasoner):
    reasoner.answers.append(answer())
    draft = client.post("/api/experiments/draft", json={"words": WORDS_GERMINATION}).json()
    exp = client.post("/api/experiments", json={"title": "Seeds", "recipe": draft["recipe"], "plan": draft["plan"]}).json()
    assert exp["recipe_id"] == "own" and client.get(f"/api/experiments/{exp['id']}/recipe").json()["concepts"][0]["name"] == "seed"
    assert client.get(f"/api/experiments/{exp['id']}/plan").json()[0]["metric"] == draft["plan"]["metric"]

def test_the_recipe_freezes_when_the_plan_locks(client, own_experiment):
    client.post(f"/api/experiments/{own_experiment}/plan/lock")
    edited = client.put(f"/api/experiments/{own_experiment}/recipe", json=answer_recipe(analysis_step_s=60))
    assert edited.status_code == 409 and "locked" in edited.json()["detail"]

def test_runs_and_verdicts_read_the_experiments_own_recipe(db, own_experiment_with_run):
    exp, run = own_experiment_with_run
    assert recipe_for(db, TEMPLATES, get_experiment(db, exp)).id == "own"

def test_a_refused_draft_answers_422_with_reasons(client, db, reasoner):
    reasoner.answers += [answer(metric="nonsense")] * 2
    refused = client.post("/api/experiments/draft", json={"words": WORDS_GERMINATION})
    assert refused.status_code == 422 and "metric" in refused.json()["detail"]
    assert logged_functions(db) == ["recipe", "recipe"]
```

- [ ] **Step 2: Run** `uv run pytest tests/test_api_recipes.py -q` — Expected: FAIL.
- [ ] **Step 3: Implement** the migration (with `PRAGMA user_version = 5`), repos, `recipe_for`, and the routes; replace the three look-ups (`api/notes.py`, `api/setup.py`, `pipeline/jobs.py`) and `describe`/`preview` with `recipe_for`.
- [ ] **Step 4: Run** the tests, then the whole worker suite: `uv run pytest -q` — Expected: all pass (existing experiments keep template recipes).
- [ ] **Step 5: Commit** — `git commit -m "feat(recipes): experiments keep their own recipe, editable until the plan locks"`

### Task 3: "What will you do?" in the web app

**Files:**
- Create: `web/components/experiments/RecipeDraftView.tsx` (+ CSS), `web/lib/recipe.ts`
- Modify: `web/components/experiments/NewExperimentDialog.tsx`, `web/lib/api.ts` (`draftRecipe`, `createExperiment` with a recipe, `getExperimentRecipe`, `putExperimentRecipe`), `web/lib/types.ts` (`RecipeSpec`, `MeasurementSpec`, `RecipeDraftResult`)
- Test: `web/tests/recipe.test.ts`; browser check

**Interfaces:**
- Consumes: Task 2's routes.
- Produces: `recipeInWords(recipe: RecipeSpec): { lookFor: string; measure: string; every: string }` (for example "seed, root", "root length (mm), seeds with a root (count)", "every 30 min"); `RecipeDraftView({ draft, onChange })`; the dialog's first field "What will you do?", a "Draft it" button, the draft in words with each line editable (concept names, measurement list from the toolbox, analysis step), suggested numbers marked "suggested", safety notes shown, "Pick a template instead", then Create → the wizard.

- [ ] **Step 1: Write the failing test** — `recipeInWords` on a germination draft gives exactly `{ lookFor: "seed, root", measure: "root length (mm), seeds with a root (count)", every: "every 30 min" }`, and on `analysis_step_s: 0.5` gives "every 0.5 s".
- [ ] **Step 2: Run** `cd web && npm test` — Expected: FAIL.
- [ ] **Step 3: Implement**, then **check in the browser** at 1440, 768 and 390 px in light and dark: a real draft for "I'll compare how fast rye and pearl millet seeds germinate in petri dishes" appears in under a minute; editing a concept saves; a refused draft shows its reasons and offers the templates.
- [ ] **Step 4: Run** `npm test && npm run lint && npm run typecheck && npm run build` — Expected: all clean.
- [ ] **Step 5: Commit** — `git commit -m "feat(web): describe the experiment and Argus drafts its recipe"`

### Task 4: `touching_count` in the measure engine

**Files:**
- Modify: `worker/argus/measure/engine.py`, `worker/argus/pipeline/analyzer.py` (a measurement is due when its `from` and `touching` concepts were both segmented on the frame)
- Test: `worker/tests/test_touching_count.py`

**Interfaces:**
- Consumes: `MeasurementSpec.touching`, `min_length_mm` (Task 1).
- Produces: `touching_count(objects: Sequence[np.ndarray], touched: np.ndarray, mm_per_px: float, *, min_length_mm: float, dilate_px: int = 3) -> int` in `argus/measure/geometry.py`; `measure_vessel` stores it as a count with uncertainty 0.

- [ ] **Step 1: Write the failing tests** — synthetic 200×200 masks: a seed with a 30-px root at 0.1 mm/px (3 mm) counts 1; a 10-px root (1 mm) counts 0 at `min_length_mm=2`; a seed 5 px away from a root counts 0; a seed touched by three roots counts 1; two seeds sharing one root count 2.
- [ ] **Step 2: Run** `uv run pytest tests/test_touching_count.py -q` — Expected: FAIL.
- [ ] **Step 3: Implement** with connected components of the touched mask and `skeleton_length_mm` per component (existing geometry), dilating each object mask by `dilate_px`.
- [ ] **Step 4: Run** the tests and `uv run pytest -q tests/test_engine.py tests/test_analyzer.py` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(measure): count objects that touch another concept (seeds with a root)"`

### Task 5: Published images as a source, with provenance

**Files:**
- Create: `worker/argus/datasets/__init__.py`, `worker/argus/datasets/manifest.py`, `worker/argus/capture/images.py`
- Modify: `worker/argus/domain.py` (`SourceKind.IMAGES`, `RunSource.manifest`, `Provenance`, `RunSource.provenance`), `worker/argus/pipeline/imported.py` (`ImportRequest.manifest`; `_scan` takes frames from `ImageSequenceSource` when set), `worker/argus/api/runs.py` (`RunCreate.manifest`, `RunCreate.roles`), `web/app/experiments/[id]/run/RunScreen.tsx` + `web/components/run/RunFrame.tsx` (badge and credit line), `web/lib/types.ts`
- Test: `worker/tests/test_images_source.py`, additions to `worker/tests/test_api_runs.py`

**Interfaces:**
- Produces:
  - `Tile(label, condition, run: str, dish: int, box: tuple[int, int, int, int], seeds: int, labels: dict[str, list[float]])` (`run` names the source run, e.g. "sc1"); `Manifest(dataset, doi, url, licence, credit, interval_s, frames: list[str], tiles: list[Tile], assembled: bool, retrospective: bool, dish_diameter_mm: float | None, sha256: str | None)`; `load_manifest(path) -> Manifest` (frames resolved next to the manifest; raises `ManifestError` naming the first missing or unreadable file).
  - `Provenance(dataset, doi, url, licence, credit, assembled, retrospective)`.
  - `ImageSequenceSource(manifest_path).frames() -> Iterator[VideoFrame]` with `t = index * interval_s`, `video_s = t`, `file_index = 0`.
  - `POST /experiments/{id}/runs {mode: "imported", manifest, roles}`: vessels from tiles; 422 when a condition has no role or no control.

- [ ] **Step 1: Write the failing tests** — a 3-frame manifest of two 40×40 tiles: times 0, 1800, 3600; a missing `frame_002.jpg` raises `ManifestError("frame_002.jpg …")` before any frame is yielded; `POST /runs` with that manifest makes two vessels labelled from the tiles with ROIs equal to the boxes and roles from `roles`, stores the provenance on the run, and finishes; a `roles` missing a condition answers 422.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; the Run view shows "PUBLISHED · RETROSPECTIVE" in the badge row and the credit line under the frame when `run.source.provenance` is set.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_images_source.py tests/test_api_runs.py tests/test_import.py`, then the web checks — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(import): published image sequences with a manifest and their provenance"`

### Task 6: The dish as the ruler

**Files:**
- Create: `worker/argus/calibration/dish.py`
- Modify: `worker/argus/calibration/run.py` (`RunCalibration.dish: DishScale | None`; `card_name` "dish"; `calibrate(..., dish_diameter_mm: float | None = None, rois: Sequence[Sequence[tuple[float, float]]] = ())`), `worker/argus/pipeline/imported.py` and `worker/argus/api/setup.py` (pass the manifest's or setup's dish diameter and the vessels' ROIs), `worker/argus/domain.py` (`CalibrationDraft.card` adds `"dish"`; `Setup.dish_diameter_mm`)
- Test: `worker/tests/test_dish.py`

**Interfaces:**
- Produces: `DishScale(mm_per_px: float, rel_uncertainty: float, dishes: list[tuple[float, float, float, float]])` (cx, cy, major, minor per dish); `dish_scale(image_bgr, rois, diameter_mm) -> DishScale | None`; `NOMINAL_ALLOWANCE = 0.03`, `MIN_AXIS_RATIO = 0.9`, `AGREEMENT = 0.15`.

- [ ] **Step 1: Write the failing tests** — six drawn rims of 600 px on a dark background inside their ROIs with ±2 px noise: `mm_per_px` within 1 % of 85/600 and `rel_uncertainty` ≥ 0.03; one tile tilted to a 0.8 axis ratio returns None; three of six tiles blank returns None; `calibrate(image, dish_diameter_mm=85, rois=…)` gives a calibration whose draft reads `card == "dish"`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**: per ROI crop, `cv2.HoughCircles` (HOUGH_GRADIENT_ALT) for the rim, then `cv2.fitEllipse` on Canny edge points within ±4 % of that radius; major axis → mm/px per dish; median; `rel_uncertainty = hypot(rsd, NOMINAL_ALLOWANCE)`; refuse per the constants.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_dish.py tests/test_run_calibration.py tests/test_import.py` — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(calibration): the dish rim as the ruler, with its honest uncertainty"`

### Task 7: Retrospective verdicts and the montage rival

**Files:**
- Modify: `worker/argus/pipeline/verdict.py` (`verdict_inputs`, `rival_states`), `worker/argus/analyze/ceiling.py` (`VerdictInputs.retrospective: bool = False`; the `retrospective` check), `web/components/ui/VerdictChip.tsx`, `web/components/verdict/VerdictPanel.tsx`, `web/lib/types.ts`
- Test: additions to `worker/tests/test_verdict.py`

**Interfaces:**
- Produces: for runs with `source.provenance.retrospective`: `locked = plan locked at all`, check `retrospective` (ok None) instead of `preregistered`, `body.retrospective = True`; `rival_states` adds `"run-to-run differences": "open"` when the run's vessels come from more than one `Tile.run` (read from the manifest), resolvable by a `resolve` review of that name; `VerdictChip({ level, provisional, retrospective })` reads "Supported · retrospective".

- [ ] **Step 1: Write the failing tests** — a retrospective run (plan locked after `start_time`) gets a ceiling past Too early and the `retrospective` check; the same run without provenance stays Too early (D-67); tiles from two runs add an open rival that holds the verdict at Inconclusive, and a `resolve` review releases it; tiles from one run add none.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest -q tests/test_verdict.py tests/test_ceiling.py` and the web checks — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(verdict): retrospective verdicts on published data, and the run-to-run rival"`

### Task 8: Agreement with a dataset's labels

**Files:**
- Create: `worker/argus/storage/migrations/006_reference_values.sql`, `worker/argus/analyze/agreement.py`, `web/components/verdict/AgreementTable.tsx` (+ CSS)
- Modify: `worker/argus/storage/repos.py`, `worker/argus/pipeline/imported.py` (write the manifest's labels after the scan), `worker/argus/api/runs.py` (`GET /runs/{id}/agreement`), `web/components/verdict/VerdictPanel.tsx`, `web/lib/api.ts`, `web/lib/types.ts`
- Test: `worker/tests/test_agreement.py`

**Interfaces:**
- Produces: table `reference_values(id, run_id, vessel_id, t, metric, value, source)` append-only; `add_reference_values(db, run_id, rows)`, `reference_values_for_run(db, run_id, metric)`; `VesselAgreement(label, mean_abs_diff, exact_share, t50_argus: float | None, t50_labels: float | None, frames: int)`, `Agreement(metric, source, vessels: list[VesselAgreement], mean_abs_diff, exact_share)`; `agreement(db, run_id, metric) -> Agreement | None` (None without reference values); readings are paired with the label at the same `t` (±1 s); t50 is the first t at which a series reaches half its final label value.

- [ ] **Step 1: Write the failing tests** — two vessels, labels [0, 1, 3, 5] and Argus [0, 1, 2, 5] at the same four times: mean_abs_diff 0.25, exact_share 0.75, t50_labels = t50_argus = third time; a run without labels → None; a frame Argus left as a gap is skipped, not counted as 0.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; the panel shows per dish "Argus vs labels: off by 0.3 seeds on average · same count in 75 % of frames · half germinated at 14:00 vs 13:30".
- [ ] **Step 4: Run** `uv run pytest -q tests/test_agreement.py tests/test_import.py` and the web checks — Expected: PASS.
- [ ] **Step 5: Commit** — `git commit -m "feat(analyze): agreement with a published dataset's labels, kept apart from measurements"`

### Task 9: The Genze plate, end to end

**Files:**
- Create: `worker/argus/datasets/genze.py`, `worker/tests/test_genze.py`
- Modify: `worker/argus/cli.py` (`dataset genze`), `docs/knowledge-base/15-decisions-log.md` (evidence), `docs/knowledge-base/17-build-plan.md` (progress), `docs/knowledge-base/18-glossary.md`, `README.md` (credits and how to fetch the data)

**Interfaces:**
- Consumes: Tasks 1–8.
- Produces: `DishRef(species: Literal["zm", "sc", "pg"], run: int, dish: int)`; `build_plate(zip_path, out_dir, *, dishes: Sequence[DishRef], columns: int = 3) -> Manifest`; `DEFAULT_PLATE` = rye runs 1 and 2 (dishes 1, 2 and 1), pearl millet runs 1 and 2 (dishes 1, 2 and 1); CLI `python -m argus dataset genze --zip data/datasets/genze/GermPredDataset.zip --out data/datasets/genze/plate`.

- [ ] **Step 1: Write the failing tests** on a synthetic zip (two dishes, three frames, VOC XML with `_im`/`_el` boxes): tiles at `(0,0,624,624)` and `(626,0,1250,624)`, `labels.germinated` per frame equals the `_el` counts, `seeds` equals the first frame's boxes, the credit line ends "cropped and tiled by Argus", a dish with a missing frame is refused by name, and a changed zip fails the SHA-256 check.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**, then **run it for real**: build the default plate; with the worker running, describe "I'll compare how fast rye and pearl millet seeds germinate in petri dishes" in the new-experiment dialog, accept the draft, lock the plan (rye as control, millet as treatment, checkpoint 24 h), start the import from the manifest, and check in the Run view: dish-rim scale ≈ 7 px/mm (±5 %), outlines on seeds and roots, germinated counts rising, notes, a retrospective verdict with the run-to-run rival open until resolved, and the agreement table. Record the numbers and the spend.
- [ ] **Step 4: Run every check** — `cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`; `cd web && npm run lint && npm run typecheck && npm test && npm run build` — Expected: all pass.
- [ ] **Step 5: Commit** — `git commit -m "feat(datasets): the Genze germination plate, and evidence of a re-analysis set up from words"`

---

## End of plan

Final whole-branch review (a fresh reviewer on the most capable model, with this Review Focus and the ledger's rulings). Fix Critical and Important findings test-first; ledger the minors. Merge after Aymen's go-ahead, together with phase 3 once its live dye run is done. Then phase 4's own spec (fits, the next-run suggestion, Results), cut to the next-run suggestion if time is short.
