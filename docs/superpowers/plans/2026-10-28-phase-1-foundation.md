# Argus Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A worker that stores experiments, plans, runs, vessels, frames and measurements as tamper-evident evidence; finds the Argus Card and turns masks into calibrated measurements with ±; serves a REST API with live events. Plus a Next.js app in the v2 design that lists and creates experiments end to end.

**Architecture:** Python 3.12 worker (`worker/argus/`): pydantic domain types, SQLite in WAL mode with one writer and numbered migrations, TOML recipes, FastAPI with an SSE broker, calibration and measurement as pure functions on numpy arrays. Next.js App Router app (`web/`) with the canvas's tokens as plain CSS (CSS Modules, no Tailwind) talking to the worker over REST and `EventSource`. Phase 1 calls no models.

**Tech Stack:** uv, Python 3.12, pydantic, FastAPI (+ uvicorn, httpx via `fastapi[standard]`), sqlite3, OpenCV 5, scikit-image, numpy, `uncertainties`, pytest, ruff; Node 24, Next.js (latest stable), React, TypeScript strict, ESLint, Prettier.

**Spec:** `docs/superpowers/specs/2026-10-28-argus-design.md` (phase 1 of §16). Facts and verified library verdicts are in `docs/knowledge-base/`.

## Global Constraints

- Python `>=3.12,<3.13` via uv. Run from `worker/`: `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .` (line length 120). All must pass before every commit.
- Web from `web/`: `npm run lint`, `npm run typecheck`, `npm run build` must pass before every web commit. TypeScript `strict: true`.
- **New dependencies allowed in phase 1 only:** `fastapi[standard]`, `uncertainties` (worker); `next`, `react`, `react-dom`, `typescript`, `eslint`, `eslint-config-next`, `prettier` (web). Tailwind, Radix, lucide, d3, Motion, openapi-typescript, Vitest, mypy and Pillow wait for Aymen's approval (spec §13). Pin exact versions (uv.lock; `save-exact` in `web/.npmrc`).
- No module in `argus/` imports a model client (`openai`); only the future `segment()` and `reason()` will (spec §7.1).
- Evidence is never overwritten: measurement rows can't be updated or deleted, and a locked plan row can't change (enforced by SQLite triggers, spec §5).
- Secrets only in the repo-root `.env`. Every new variable is mirrored in `.env.example`.
- Glossary words in names and UI copy: experiment, plan, run, vessel, frame, measurement, recipe, noise floor, verdict (`docs/knowledge-base/18-glossary.md`).
- Time `t` is real seconds since run start (float, ≥ 0). Lengths in `mm`, areas in `mm²` (unit string `"mm2"`), colour difference unit `"dE00"`.
- `method_version` strings are `"<method>/<n>"`, starting at `/1`.
- Windows: paths via `pathlib`. No shell-specific scripts. Executables are resolved with `shutil.which` (so `npm` resolves to `npm.cmd`).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Work on branch `phase-1`; merge to `main` after the end-of-phase review.
- The spec's `uv run argus dev` is implemented as `uv run python -m argus dev` (the worker project has no build backend).

## Review Focus

1. **Both cards in one frame, or stray markers.** Detection must use one card (the one with the most markers found) and never mix corners from the standard and compact cards. Test in Task 7.
2. **Empty masks** (nothing segmented in a vessel yet). Area, length and count are `0.0` with their units, height is `0.0`, and colour metrics are absent rather than NaN or an exception. Tests in Tasks 9 and 10.
3. **Editing a plan after it is locked.** The save makes a new version; version 1 stays byte-identical and keeps its hash. Test in Task 3.
4. **Worker not running when the web app opens.** The Experiments page shows an error with the worker URL and a Retry button, not a crash or an endless spinner. Verified in Task 13.
5. **Data folder path with spaces and non-ASCII characters** (the Windows profile here is `aymen.LIGER`, and short names like `AYMEN~1.LIG` appear). The database opens, creates parent folders and round-trips. Test in Task 3.

---

## File structure

```
worker/
  pyproject.toml                       modify: deps
  argus/
    __main__.py                        python -m argus → cli.main()
    cli.py                             argparse: dev | card
    config.py                          Settings + load_settings()
    domain.py                          ids, enums, pydantic records, plan hashing
    storage/
      __init__.py
      db.py                            Database (WAL, one writer, readers), migrate()
      migrations/001_core.sql          tables + immutability triggers
      repos.py                         experiments, plans, runs, vessels, frames, measurements
      audit.py                         hash chain over measurement batches
    recipes/
      __init__.py
      model.py                         Recipe pydantic models + validation
      loader.py                        load_recipe(), load_all()
    api/
      __init__.py
      events.py                        EventBroker, format_sse(), event_stream()
      app.py                           create_app(), app_from_env()
    calibration/
      detect.py                        detect_card(), with_print_check(), ruler_scale(), rectify()
      colour.py                        read_patches(), neutral_drift(), correct_lab()
    measure/
      __init__.py
      geometry.py                      area, height, skeleton length, component count
      colour.py                        lab_mean(), delta_e(), colour_metrics()
      uncertainty.py                   noise_floor(), combined_uncertainty(), is_real_effect(), format_pm()
  tests/
    test_config.py  test_domain.py  test_storage.py  test_audit.py  test_recipes.py
    test_events.py  test_api.py  test_detect.py  test_colour_reference.py
    test_geometry.py  test_colour_metrics.py  test_uncertainty.py  test_cli.py
recipes/
  seed-germination.toml  colour-reaction.toml  foam-height.toml  general.toml
web/                                   created by create-next-app in Task 11
  .npmrc  .prettierrc  package.json  tsconfig.json
  app/layout.tsx  app/page.tsx  app/kit/page.tsx  app/globals.css
  styles/tokens.css
  components/brand/Mark.tsx + .module.css
  components/shell/Rail.tsx  PageHeader.tsx  Tabs.tsx  ThemeSwitch.tsx (+ .module.css)
  components/ui/Button.tsx  Badge.tsx  VerdictChip.tsx (+ .module.css)
  components/experiments/ExperimentsTable.tsx  NewExperimentDialog.tsx (+ .module.css)
  lib/api.ts  lib/events.ts  lib/types.ts
.env.example                           modify
```

---

### Task 1: Settings from the environment

**Files:**
- Modify: `worker/pyproject.toml` (add `fastapi[standard]`, `uncertainties` with `uv add`)
- Create: `worker/argus/config.py`
- Modify: `.env.example`
- Test: `worker/tests/test_config.py`

**Interfaces:**
- Produces:
  - `Settings` (pydantic `BaseModel`, frozen) with fields:
    - `model_api_key: SecretStr | None`
    - `meta_base_url: str = "https://api.meta.ai/v1"`
    - `routine_model: str = "muse-spark-1.3"`
    - `deep_model: str = "muse-wonder-1.0"`
    - `deep_fallback_model: str = "muse-spark-1.3"`
    - `segment_model: str = "sam-3.1"`
    - `voice_model: str = "muse-voice-transcribe-1.0"`
    - `run_spend_cap_usd: float = 10.0` (must be > 0)
    - `data_dir: Path`
    - `recipes_dir: Path`
    - `web_origin: str = "http://localhost:3000"`
  - `REPO_ROOT: Path`
  - `load_settings(env: Mapping[str, str] | None = None) -> Settings`. It reads `os.environ` when `env` is None.
  - Env names: `MODEL_API_KEY`, `META_BASE_URL`, `REASONING_ROUTINE_MODEL`, `REASONING_DEEP_MODEL`, `REASONING_DEEP_FALLBACK_MODEL`, `SEGMENT_MODEL`, `VOICE_MODEL`, `RUN_SPEND_CAP_USD`, `ARGUS_DATA_DIR` (default `REPO_ROOT / "data"`), `ARGUS_RECIPES_DIR` (default `REPO_ROOT / "recipes"`), `ARGUS_WEB_ORIGIN`.

- [ ] **Step 1: Add dependencies.** Run `uv add "fastapi[standard]" uncertainties` in `worker/`.
  Expected: `uv.lock` updated, `uv run python -c "import fastapi, httpx, uncertainties"` succeeds.

- [ ] **Step 2: Write the failing tests.**

```python
def test_defaults_when_env_is_empty():
    s = load_settings({})
    assert s.routine_model == "muse-spark-1.3" and s.deep_model == "muse-wonder-1.0"
    assert s.deep_fallback_model == "muse-spark-1.3" and s.run_spend_cap_usd == 10.0
    assert s.data_dir == REPO_ROOT / "data" and s.recipes_dir == REPO_ROOT / "recipes"
    assert s.model_api_key is None

def test_env_overrides_and_key_is_hidden():
    s = load_settings({"MODEL_API_KEY": "k" * 48, "RUN_SPEND_CAP_USD": "2.5", "ARGUS_DATA_DIR": "C:/tmp/argus data"})
    assert s.run_spend_cap_usd == 2.5 and s.data_dir == Path("C:/tmp/argus data")
    assert "k" * 48 not in repr(s) and s.model_api_key.get_secret_value() == "k" * 48

@pytest.mark.parametrize("bad", ["abc", "0", "-1"])
def test_invalid_spend_cap_is_rejected(bad):
    with pytest.raises(ValidationError):
        load_settings({"RUN_SPEND_CAP_USD": bad})
```

- [ ] **Step 3: Run to see them fail.** `uv run pytest tests/test_config.py -v`. Expected: FAIL, `ModuleNotFoundError: argus.config`.
- [ ] **Step 4: Implement `config.py`** with the fields above (`PositiveFloat` for the cap; an empty string counts as unset). Add `REASONING_DEEP_FALLBACK_MODEL=muse-spark-1.3`, `ARGUS_DATA_DIR=`, `ARGUS_RECIPES_DIR=` and `ARGUS_WEB_ORIGIN=http://localhost:3000` to `.env.example`, each with a one-line comment.
- [ ] **Step 5: Run to see them pass.** `uv run pytest tests/test_config.py -v`. Expected: 5 passed.
- [ ] **Step 6: Commit.** `git commit -m "feat(worker): settings from the environment"`

---

### Task 2: Domain records

**Files:**
- Create: `worker/argus/domain.py`
- Test: `worker/tests/test_domain.py`

**Interfaces:**
- Produces:
  - `new_id(prefix: str) -> str`: `f"{prefix}_{uuid4().hex[:12]}"`. Prefixes: `exp`, `run`, `ves`, `frm`, `mea`.
  - Enums (`StrEnum`):
    - `ExperimentStatus{DRAFT="draft", LOCKED="locked", RUNNING="running", FINISHED="finished"}`
    - `RunMode{LIVE="live", IMPORTED="imported", REPLAY="replay"}`
    - `RunStatus{RUNNING="running", FINISHED="finished", STOPPED="stopped"}`
    - `Role{CONTROL="control", TREATMENT="treatment"}`
    - `VerdictLevel{SUPPORTED="SUPPORTED", NOT_SUPPORTED="NOT_SUPPORTED", INCONCLUSIVE="INCONCLUSIVE", TOO_EARLY="TOO_EARLY"}`
  - Pydantic models (frozen):
    - `Experiment(id, title, recipe_id, recipe_version: int, status, created_at: datetime)`
    - `PlanDraft(hypothesis, prediction, threshold, rivals: list[str])`
    - `Plan(PlanDraft + experiment_id, version: int, locked_at: datetime | None, sha256: str | None)`
    - `Run(id, experiment_id, mode, status, time_scale: float = 1.0 (> 0), round: int = 1, started_at: datetime)`
    - `Condition(factor, value: float | str, unit: str | None)`
    - `VesselDraft(label, role, blind_label: str | None, condition: Condition | None, roi: list[tuple[float, float]])`
    - `Vessel(VesselDraft + id, run_id)`
    - `Frame(id, run_id, t: float ≥ 0, path, quality_flags: list[str])`
    - `MeasurementDraft(vessel_id, frame_id: str | None, t: float ≥ 0, metric, value: float, uncertainty: float ≥ 0, unit: non-empty str, method_version: matches "^[a-z_]+/[0-9]+$")`
    - `Measurement(MeasurementDraft + id)`
  - `plan_sha256(draft: PlanDraft) -> str`: sha256 of JSON with sorted keys, no whitespace, UTF-8.

- [ ] **Step 1: Write the failing tests.**

```python
def test_new_id_has_prefix_and_is_unique():
    ids = {new_id("mea") for _ in range(1000)}
    assert len(ids) == 1000 and all(re.fullmatch(r"mea_[0-9a-f]{12}", i) for i in ids)

def test_verdict_levels_are_the_four_spec_words():
    assert [v.value for v in VerdictLevel] == ["SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "TOO_EARLY"]

@pytest.mark.parametrize("field,value", [("uncertainty", -0.1), ("unit", ""), ("method_version", "area"), ("t", -1.0)])
def test_measurement_draft_rejects_bad_values(field, value):
    good = dict(vessel_id="ves_1", frame_id=None, t=0.0, metric="area", value=1.0, uncertainty=0.1, unit="mm2", method_version="area/1")
    with pytest.raises(ValidationError):
        MeasurementDraft(**{**good, field: value})

def test_plan_hash_is_stable_and_order_independent():
    a = PlanDraft(hypothesis="h", prediction="p", threshold="12 h", rivals=["light", "position"])
    assert plan_sha256(a) == plan_sha256(PlanDraft(**a.model_dump()))
    assert plan_sha256(a) != plan_sha256(a.model_copy(update={"threshold": "13 h"}))
```

- [ ] **Step 2: Run to see them fail.** `uv run pytest tests/test_domain.py -v`. Expected: FAIL, import error.
- [ ] **Step 3: Implement `domain.py`** with the records above.
- [ ] **Step 4: Run to see them pass.** Expected: 7 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): domain records and ids"`

---

### Task 3: Database, migrations, repositories

**Files:**
- Create: `worker/argus/storage/__init__.py`, `storage/db.py`, `storage/migrations/001_core.sql`, `storage/repos.py`
- Test: `worker/tests/test_storage.py`

**Interfaces:**
- Consumes: Task 2 records.
- Produces:
  - `Database(path: Path)`:
    - Creates parent folders, opens the writer connection with `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, and runs `migrate()`.
    - `write() -> ContextManager[sqlite3.Connection]` (one writer, guarded by a `threading.Lock`; commits on exit, rolls back on exception).
    - `read() -> ContextManager[sqlite3.Connection]` (a new read-only connection each call, `row_factory = sqlite3.Row`).
    - `close()`.
  - `migrate(conn) -> int`: applies `migrations/NNN_*.sql` in order, tracked by `PRAGMA user_version`; returns the version.
  - `001_core.sql` tables (columns as in spec §5):
    - `experiments`
    - `plans` (primary key `(experiment_id, version)`)
    - `runs`
    - `vessels` (`roi` and `condition` as JSON text)
    - `calibrations`
    - `frames`
    - `measurements`
    - `audit_chain(run_id, batch_index, sha256, measurement_ids JSON, created_at, PRIMARY KEY(run_id, batch_index))`
  - Triggers: `BEFORE UPDATE OR DELETE ON measurements → RAISE(ABORT, 'measurements are evidence')`; `BEFORE UPDATE ON plans WHEN OLD.locked_at IS NOT NULL → RAISE(ABORT, 'locked plan')`.
  - `repos.py` functions, each taking `db: Database` first:
    - `create_experiment(db, title, recipe_id, recipe_version) -> Experiment`
    - `list_experiments(db) -> list[Experiment]` (newest first)
    - `get_experiment(db, experiment_id) -> Experiment | None`
    - `save_plan_draft(db, experiment_id, draft) -> Plan`: updates the latest version while unlocked; creates version n+1 when the latest is locked.
    - `lock_plan(db, experiment_id) -> Plan`: sets `locked_at` and `sha256`; sets experiment status `locked`.
    - `get_plans(db, experiment_id) -> list[Plan]` (by version)
    - `create_run(db, experiment_id, mode, time_scale=1.0) -> Run`
    - `add_vessels(db, run_id, drafts) -> list[Vessel]`
    - `add_frame(db, run_id, t, path, quality_flags) -> Frame`
    - `add_measurements(db, run_id, drafts) -> list[Measurement]` (one transaction; also calls `audit.append_batch`, Task 4)
    - `measurements_for_run(db, run_id, *, t_from=None, t_to=None, metric=None) -> list[Measurement]` (ordered by `t`)

- [ ] **Step 1: Write the failing tests.** Fixtures:
  - `db` on `tmp_path / "data dir é" / "argus.sqlite"`
  - `exp`, `run`, `vessel`: one of each, created through the repos
  - `DRAFT`: a `PlanDraft`
  - `draft(vessel_id, t, value=1.0)`: a `MeasurementDraft` with metric `area`, unit `mm2`, uncertainty `0.1`, method `area/1`

```python
def test_wal_mode_and_schema_version(db):
    with db.read() as c:
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1

def test_path_with_space_and_accent_round_trips(db):
    exp = create_experiment(db, "Salt-stress germination", "seed-germination", 1)
    assert get_experiment(db, exp.id) == exp and list_experiments(db)[0].id == exp.id

def test_editing_a_locked_plan_creates_a_new_version(db, exp):
    save_plan_draft(db, exp.id, DRAFT)
    v1 = lock_plan(db, exp.id)
    v2 = save_plan_draft(db, exp.id, DRAFT.model_copy(update={"threshold": "13 h"}))
    plans = get_plans(db, exp.id)
    assert (v1.version, v2.version) == (1, 2) and plans[0] == v1 and plans[0].sha256 == plan_sha256(DRAFT)
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE plans SET threshold='x' WHERE experiment_id=? AND version=1", (exp.id,))

def test_measurements_are_queryable_and_immutable(db, run, vessel):
    rows = add_measurements(db, run.id, [draft(vessel.id, t=t, value=t / 10) for t in (0.0, 300.0, 600.0)])
    assert [m.t for m in measurements_for_run(db, run.id, t_from=300.0)] == [300.0, 600.0]
    for sql in ("UPDATE measurements SET value=0 WHERE id=?", "DELETE FROM measurements WHERE id=?"):
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql, (rows[0].id,))

def test_reads_are_not_blocked_by_an_open_write(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0, value=1.0)])
    with db.write() as w:
        w.execute("INSERT INTO frames(id, run_id, t, path, quality_flags) VALUES ('frm_x', ?, 1.0, 'p', '[]')", (run.id,))
        assert len(measurements_for_run(db, run.id)) == 1
```

- [ ] **Step 2: Run to see them fail.** `uv run pytest tests/test_storage.py -v`. Expected: FAIL, import error.
- [ ] **Step 3: Implement `db.py`, `001_core.sql` and `repos.py`.** Migrations are read with `importlib.resources`. JSON columns use `json.dumps(..., separators=(",", ":"))`. Datetimes are stored as ISO-8601 UTC strings.
- [ ] **Step 4: Run to see them pass.** Expected: 5 passed. Then the full suite: `uv run pytest -q`, all green.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): SQLite storage with versioned plans and immutable measurements"`

---

### Task 4: Tamper-evident audit chain

**Files:**
- Create: `worker/argus/storage/audit.py`
- Test: `worker/tests/test_audit.py`

**Interfaces:**
- Consumes: `Database`, `Measurement`.
- Produces:
  - `GENESIS = "0" * 64`
  - `batch_hash(previous: str, rows: Sequence[Measurement]) -> str`: sha256 over `previous + canonical JSON of [row.model_dump(mode="json") for row in rows]` (sorted keys, no whitespace).
  - `append_batch(conn, run_id: str, rows: Sequence[Measurement]) -> str`: called inside `add_measurements`' transaction.
  - `verify_chain(db, run_id) -> bool`: recomputes every batch from the stored measurement rows.

- [ ] **Step 1: Write the failing tests.**

```python
def test_chain_links_batches_and_verifies(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0)])
    add_measurements(db, run.id, [draft(vessel.id, t=300.0), draft(vessel.id, t=600.0)])
    with db.read() as c:
        hashes = [r[0] for r in c.execute("SELECT sha256 FROM audit_chain WHERE run_id=? ORDER BY batch_index", (run.id,))]
    assert len(hashes) == 2 and hashes[0] != hashes[1] and verify_chain(db, run.id)

def test_a_changed_hash_breaks_verification(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0)])
    with db.write() as c:
        c.execute("UPDATE audit_chain SET sha256=? WHERE run_id=?", ("f" * 64, run.id))
    assert not verify_chain(db, run.id)
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `audit.py`** and call `append_batch` from `repos.add_measurements` inside the same `db.write()` block.
- [ ] **Step 4: Run to see them pass.** `uv run pytest tests/test_audit.py tests/test_storage.py -v`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): hash chain over measurement batches"`

---

### Task 5: Recipes in TOML

**Files:**
- Create: `worker/argus/recipes/__init__.py`, `recipes/model.py`, `recipes/loader.py`
- Create: `recipes/seed-germination.toml`, `recipes/colour-reaction.toml`, `recipes/foam-height.toml`, `recipes/general.toml`
- Test: `worker/tests/test_recipes.py`

**Interfaces:**
- Produces:
  - `Recipe` (pydantic, frozen) with fields:
    - `id`, `version: int`, `title`
    - `default_mode: Literal["continuous", "smart_trigger", "hybrid"]`
    - `analysis_step_s: float > 0`
    - `main_measurement: str`
    - `curve: Literal["logistic", "gompertz", "exponential", "first_order", "linear"]`
    - `rivals: list[str]`, `default_views: list[str]`
    - `concepts: list[Concept(name)]`, `measurements: list[MeasurementSpec(id, family, method, source, unit, rule: str | None)]`, `events: list[EventSpec(id, when)]`
    - `watcher: WatcherSpec(signals: list[Literal["ssim", "colour"]], light_normalization: Literal["normal", "strong"], day_night: bool)`
  - Allowed methods per family: `size` → `area`, `height`, `skeleton_length`; `colour` → `lab_mean`, `delta_e`; `count` → `component_count`, `event_count`; `state` → `threshold`.
  - Validation: a concept name contains no `,` or `+` (SAM takes one concept per request, spec §7); `measurement.source` is a concept name; `main_measurement` is a measurement id; ids are unique.
  - `RecipeError(ValueError)`: message `"<file>: <field>: <problem>"`.
  - `load_recipe(path: Path) -> Recipe` (stdlib `tomllib`) and `load_all(recipes_dir: Path) -> dict[str, Recipe]`.
  - TOML key `from` maps to the field `source`.
- View ids for `default_views` (the catalog validates them in phase 4): `curves`, `cumulative`, `grid`, `colourstrip`, `gauge`, `groups`, `dose`, `target`, `optimize`, `best`, `crops`, `drift`, `rate`, `onsets`, `interaction`, `keyframes`, `sizes`.
- Recipe content:

  | Recipe | Concepts | Main measurement | Curve | Mode and step | Watcher | Default views |
  | --- | --- | --- | --- | --- | --- | --- |
  | `seed-germination` | "mung bean", "root" | `root_length` (size, skeleton_length, mm), plus `sprouted` (count, event_count, rule `"root_length > 2"`) | logistic | smart_trigger, step 300 s | ssim + colour, strong normalization, day_night true | cumulative, grid, curves, dose, target |
  | `colour-reaction` | "liquid" | `delta_e` (colour, delta_e, dE00), event `switch` when `"delta_e > 20"` | logistic | continuous, step 0.5 s | — | colourstrip, curves, target, best |
  | `foam-height` | "foam" | `height` (size, height, mm) | logistic | continuous, step 5 s | — | gauge, curves, target, groups |
  | `general` | "object" | `area` (size, area, mm2), plus `colour` (colour, lab_mean) | linear | hybrid, step 60 s | — | curves, groups, crops |

  `seed-germination` rivals: temperature, uneven watering, position in the row, seed batch.

- [ ] **Step 1: Write the failing tests** (`VALID` is a dict of a minimal valid recipe; `write_recipe(dir, data)` writes it as TOML and returns the path):

```python
def test_bundled_recipes_load_and_point_to_real_measurements():
    recipes = load_all(REPO_ROOT / "recipes")
    assert set(recipes) == {"seed-germination", "colour-reaction", "foam-height", "general"}
    for r in recipes.values():
        assert r.main_measurement in {m.id for m in r.measurements}

@pytest.mark.parametrize("patch,field", [
    ({"concepts": [{"name": "seed, root"}]}, "concepts"),
    ({"measurements": [{"id": "x", "family": "size", "method": "delta_e", "from": "root", "unit": "mm"}]}, "method"),
    ({"main_measurement": "nope"}, "main_measurement"),
])
def test_invalid_recipes_are_rejected_with_file_and_field(tmp_path, patch, field):
    path = write_recipe(tmp_path, {**VALID, **patch})
    with pytest.raises(RecipeError, match=rf"{path.name}: {field}"):
        load_recipe(path)
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement the models and loader, and write the 4 TOML files** with the content in the table. Top-level keys go before any `[[table]]`.
- [ ] **Step 4: Run to see them pass.** Expected: 4 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): TOML recipes with validation and four starter recipes"`

---

### Task 6: Live events and the API skeleton

**Files:**
- Create: `worker/argus/api/__init__.py`, `api/events.py`, `api/app.py`
- Test: `worker/tests/test_events.py`, `worker/tests/test_api.py`

**Interfaces:**
- Consumes: `Settings`, `Database`, repos, `load_all`.
- Produces:
  - `ServerEvent(id: int, type: str, data: dict)` (frozen dataclass)
  - `EventBroker(history: int = 500)`:
    - `publish(type: str, data: Mapping) -> ServerEvent`: thread-safe; ids start at 1 and increase; history is a ring buffer.
    - `since(last_id: int) -> list[ServerEvent]`
    - `async subscribe() -> AsyncIterator[ServerEvent]`: wakes from other threads via `loop.call_soon_threadsafe`.
  - `format_sse(e) -> str`: exactly `f"id: {e.id}\nevent: {e.type}\ndata: {json}\n\n"` (compact JSON).
  - `async event_stream(broker, last_event_id: int | None, *, heartbeat_s: float = 15.0) -> AsyncIterator[str]`: replays `since(last_event_id)`, then live events, with `": keep-alive\n\n"` while idle.
  - `create_app(settings, db, broker, recipes: dict[str, Recipe]) -> FastAPI`. CORS allows `settings.web_origin`. Routes:
    - `GET /api/health` → `{"status": "ok", "version": "0.1.0"}`
    - `GET /api/recipes` → `[{id, version, title, main_measurement}]`
    - `GET /api/experiments` → `list[Experiment]`
    - `POST /api/experiments {title, recipe_id}` → 201 `Experiment`, and publishes event `experiment` with the experiment JSON. An unknown recipe → 422 `{"detail": "unknown recipe: <id>"}`.
    - `GET /api/experiments/{id}` → `Experiment`, or 404 `{"detail": "experiment not found"}`.
    - `GET /api/events` → `StreamingResponse(event_stream(...), media_type="text/event-stream")`, reading the `Last-Event-ID` header.
  - `app_from_env() -> FastAPI`: `load_settings()`, `Database(settings.data_dir / "argus.sqlite")`, a new broker, `load_all(settings.recipes_dir)`. This is the uvicorn factory.

- [ ] **Step 1: Write the failing tests.**

```python
# test_events.py
def test_format_sse_is_exact():
    assert format_sse(ServerEvent(7, "note", {"a": 1})) == 'id: 7\nevent: note\ndata: {"a":1}\n\n'

def test_since_returns_later_events_and_history_is_bounded():
    b = EventBroker(history=3)
    for i in range(5):
        b.publish("m", {"i": i})
    assert [e.id for e in b.since(0)] == [3, 4, 5] and [e.id for e in b.since(4)] == [5]

async def test_stream_replays_then_delivers_an_event_published_from_another_thread():
    b = EventBroker()
    b.publish("m", {"i": 1})
    stream = event_stream(b, last_event_id=0, heartbeat_s=60)
    assert (await anext(stream)).startswith("id: 1\n")
    threading.Thread(target=b.publish, args=("m", {"i": 2})).start()
    assert (await asyncio.wait_for(anext(stream), 2)).startswith("id: 2\n")

# test_api.py (client = TestClient(create_app(settings, db, broker, load_all(REPO_ROOT / "recipes"))))
def test_create_list_get_experiment_and_event(client, broker):
    r = client.post("/api/experiments", json={"title": "Iodine clock timing", "recipe_id": "colour-reaction"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    assert client.get("/api/experiments").json()[0]["id"] == r.json()["id"]
    assert client.get(f"/api/experiments/{r.json()['id']}").status_code == 200
    assert broker.since(0)[-1].type == "experiment"

def test_unknown_recipe_and_missing_experiment(client):
    assert client.post("/api/experiments", json={"title": "x", "recipe_id": "nope"}).json() == {"detail": "unknown recipe: nope"}
    assert client.get("/api/experiments/exp_000000000000").status_code == 404

def test_cors_allows_the_web_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run to see them fail.** `uv run pytest tests/test_events.py tests/test_api.py -v`. Expected: FAIL. For the async test, mark it `@pytest.mark.anyio` (anyio comes with FastAPI) and add an `anyio_backend` fixture returning `"asyncio"` in `tests/conftest.py`; no new plugin.
- [ ] **Step 3: Implement `events.py` and `app.py`.**
- [ ] **Step 4: Run to see them pass.** Expected: 6 passed. Then a manual check: `uv run --env-file ../.env uvicorn --factory argus.api.app:app_from_env --port 8000`, then `curl http://localhost:8000/api/health` → `{"status":"ok","version":"0.1.0"}`.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): REST skeleton and server-sent events with replay"`

---

### Task 7: Find the Argus Card, scale and rectify

**Files:**
- Create: `worker/argus/calibration/detect.py`
- Test: `worker/tests/test_detect.py`

**Interfaces:**
- Consumes: `CardSpec`, `CARDS`, `render_raster`, `aruco_dictionary` from `calibration/card.py`.
- Produces:
  - `CardDetection` (frozen dataclass):
    - `spec: CardSpec`, `marker_ids: tuple[int, ...]`
    - `image_to_card: np.ndarray` (3×3, image px → card mm)
    - `mm_per_px: float`: local scale at the card centre, `sqrt(|det J|)` of the mapping.
    - `reprojection_error_mm: float`: RMS of the marker corners.
    - `print_scale: float = 1.0`
    - `rel_uncertainty: float`
    - `px_to_mm(points_px: np.ndarray) -> np.ndarray`: N×2 → card-plane mm, print scale applied.
  - `detect_card(image_bgr, cards=CARDS, *, min_markers: int = 2) -> CardDetection | None`: uses the single card spec with the most markers found; markers of other specs are ignored.
  - `rel_uncertainty = sqrt((reprojection_error_mm / marker_span_mm)**2 + p**2)`, where `marker_span_mm` is the distance between the outer marker corners. `p = 0.01` until the print is checked; after the check, `p = 0.5 / measured_line_mm`.
  - `with_print_check(d, measured_line_mm: float) -> CardDetection`: `print_scale = 100 / measured_line_mm`. Raises `ValueError` outside 90–110 mm.
  - `RulerScale(mm_per_px: float, rel_uncertainty: float)` and `ruler_scale(p1, p2, distance_mm, *, click_error_px: float = 1.0) -> RulerScale`, with `rel = click_error_px * sqrt(2) / pixel_distance`.
  - `Rectified(image: np.ndarray, px_per_mm: float, origin_mm: tuple[float, float])` and `rectify(image_or_mask, d, *, px_per_mm: float = 10.0) -> Rectified`: warps the whole image into card-plane coordinates over the bounding box of the image corners; nearest-neighbour interpolation for boolean masks.

- [ ] **Step 1: Write the failing tests.** Test helpers go in `tests/helpers.py` (Task 8 reuses them):
  - `scene(spec, px_per_mm, tilt=None, cover_ids=())`: renders a card with `render_raster` into a 1600×1200 white frame, optionally warps it with the 3×3 `TILT`, and paints white over covered markers.
  - `scene_with_patch_centres`: the same, also returning each patch centre in image px and card mm.
  - `scene_both_cards`: one full card plus N markers of the other spec.
  - `scene_with_square_on_card_plane`: a black square of known mm size drawn on the card plane before tilting.
  - `bounding_box_of_dark_square`: width and height in px of the dark pixels outside the card.

```python
def test_standard_card_scale():
    d = detect_card(scene(STANDARD, 5.0))
    assert d.spec is STANDARD and d.marker_ids == (0, 1, 2, 3) and d.mm_per_px == pytest.approx(0.2, rel=0.005)

def test_points_map_to_card_mm_under_perspective():
    img, centres_px, centres_mm = scene_with_patch_centres(STANDARD, 6.0, tilt=TILT)
    assert np.abs(detect_card(img).px_to_mm(centres_px) - centres_mm).max() < 0.2

def test_three_markers_are_enough():
    d = detect_card(scene(COMPACT, 6.0, cover_ids=(5,)))
    assert len(d.marker_ids) == 3 and d.mm_per_px == pytest.approx(1 / 6, rel=0.01)

def test_both_cards_in_frame_never_mix():
    d = detect_card(scene_both_cards(full=STANDARD, stray_compact_markers=1))
    assert d.spec is STANDARD and set(d.marker_ids) <= {0, 1, 2, 3}

def test_no_card_returns_none():
    assert detect_card(np.full((600, 800, 3), 255, np.uint8)) is None

def test_print_check_rescales_and_bounds():
    d = detect_card(scene(STANDARD, 5.0)); c = with_print_check(d, 98.0)
    pts = c.px_to_mm(np.array([[700.0, 600.0], [800.0, 600.0]]))
    assert np.linalg.norm(pts[1] - pts[0]) == pytest.approx(20.0 * 100 / 98, rel=0.01)
    with pytest.raises(ValueError):
        with_print_check(d, 80.0)

def test_ruler_scale():
    r = ruler_scale((0, 0), (400, 0), 100.0)
    assert r.mm_per_px == 0.25 and r.rel_uncertainty == pytest.approx(np.sqrt(2) / 400)

def test_rectify_makes_a_tilted_square_square():
    img = scene_with_square_on_card_plane(STANDARD, side_mm=30.0, tilt=TILT)
    rect = rectify(img, detect_card(img), px_per_mm=10.0)
    w, h = bounding_box_of_dark_square(rect.image)
    assert w == pytest.approx(300, abs=4) and h == pytest.approx(300, abs=4)
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `detect.py`.** Use `cv2.findHomography` on all detected corners (`card mm ↔ image px`), and get the local scale from mapping the centre ±0.5 px.
- [ ] **Step 4: Run to see them pass.** `uv run pytest tests/test_detect.py tests/test_card.py -v`. Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): card detection, print check, ruler fallback and rectification"`

---

### Task 8: Colour reference from the card

**Files:**
- Create: `worker/argus/calibration/colour.py`
- Test: `worker/tests/test_colour_reference.py`

**Interfaces:**
- Consumes: `CardDetection`, `CardSpec.patches()`.
- Produces:
  - `PatchReading(name: str, lab: tuple[float, float, float])`
  - `ColourReference(patches: tuple[PatchReading, ...])`
  - `read_patches(image_bgr, d: CardDetection) -> ColourReference`: the mean Lab (skimage `rgb2lab`) of the inner 60% of each patch, located through the inverse of `d.image_to_card`.
  - `neutral_drift(reference, current) -> float`: the mean CIEDE2000 over `neutral_*` patches.
  - `correct_lab(lab: np.ndarray, reference, current) -> np.ndarray`: subtracts the mean neutral-patch Lab offset, a relative correction (spec §6).

- [ ] **Step 1: Write the failing tests** (reuse `scene` from `test_detect.py` via `tests/helpers.py`; `rgb_to_lab(rgb)` converts one sRGB triple with skimage):

```python
def test_patches_read_close_to_their_printed_colour():
    img = scene(STANDARD, 6.0); ref = read_patches(img, detect_card(img))
    for p, spec_patch in zip(ref.patches, STANDARD.patches(), strict=True):
        assert deltaE_ciede2000(np.array(p.lab), rgb_to_lab(spec_patch.rgb)) < 2.0

def test_dimmer_light_shows_as_drift_and_is_corrected():
    img = scene(STANDARD, 6.0); d = detect_card(img)
    ref = read_patches(img, d); cur = read_patches((img * 0.85).astype(np.uint8), d)
    assert neutral_drift(ref, cur) > 3.0
    mid = np.array(next(p.lab for p in cur.patches if p.name == "neutral_60"))
    assert deltaE_ciede2000(correct_lab(mid, ref, cur), np.array(next(p.lab for p in ref.patches if p.name == "neutral_60"))) < 3.0
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `colour.py`.**
- [ ] **Step 4: Run to see them pass.** Expected: 2 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): colour reference and drift from the card patches"`

---

### Task 9: Geometry measurements

**Files:**
- Create: `worker/argus/measure/__init__.py`, `measure/geometry.py`
- Test: `worker/tests/test_geometry.py`

**Interfaces:**
- Consumes: boolean masks already rectified to the card plane (`Rectified.px_per_mm`, Task 7), so `mm_per_px = 1 / px_per_mm`.
- Produces:
  - `MetricValue(metric: str, value: float, unit: str, method_version: str)` (frozen dataclass)
  - `area_mm2(mask, mm_per_px) -> MetricValue("area", …, "mm2", "area/1")`
  - `height_mm(mask, mm_per_px, *, base_y_px: float) -> MetricValue("height", …, "mm", "height/1")`: `base_y_px` minus the topmost mask row; `0.0` for an empty mask.
  - `skeleton_length_mm(mask, mm_per_px) -> MetricValue("skeleton_length", …, "mm", "skeleton_length/1")`. Method: `skimage.morphology.skeletonize`, then sum 1 for each 4-connected pixel pair and √2 for each diagonal pair whose two pixels share no 4-connected skeleton neighbour.
  - `component_count(mask, mm_per_px, *, min_area_mm2: float) -> MetricValue("component_count", …, "count", "component_count/1")`: 8-connected components at or above the size filter.

- [ ] **Step 1: Write the failing tests.** Helpers: `line_mask(kind, thickness)` draws a 100-px horizontal line, a 100-px 45° diagonal, or an L of 100 + 60 px with `cv2.line` on a 200×200 canvas; `blobs([(x, y, r)])` draws filled circles.

```python
def test_area_of_a_rectangle():
    m = np.zeros((100, 100), bool); m[10:30, 10:50] = True
    assert area_mm2(m, 0.25).value == pytest.approx(50.0)

def test_height_from_the_base():
    m = np.zeros((200, 50), bool); m[120:180, 10:40] = True
    assert height_mm(m, 0.5, base_y_px=180).value == pytest.approx(30.0)

@pytest.mark.parametrize("draw,expected_px", [("horizontal", 99.0), ("diagonal", 99 * np.sqrt(2)), ("l_shape", 99.0 + 59.0)])
def test_skeleton_length(draw, expected_px):
    assert skeleton_length_mm(line_mask(draw, thickness=5), 0.25).value == pytest.approx(expected_px * 0.25, rel=0.03)

def test_count_ignores_specks():
    m = blobs([(20, 20, 6), (60, 60, 6), (100, 30, 6)]); m[5, 5] = True
    assert component_count(m, 0.25, min_area_mm2=1.0).value == 3

def test_empty_mask_gives_zeros_not_errors():
    e = np.zeros((40, 40), bool)
    values = [area_mm2(e, 0.25), height_mm(e, 0.25, base_y_px=39), skeleton_length_mm(e, 0.25),
              component_count(e, 0.25, min_area_mm2=1.0)]
    assert [v.value for v in values] == [0.0, 0.0, 0.0, 0.0]
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement `geometry.py`.**
- [ ] **Step 4: Run to see them pass.** Expected: 7 passed.
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): area, height, skeleton length and count in mm"`

---

### Task 10: Colour metrics, noise floor and ±

**Files:**
- Create: `worker/argus/measure/colour.py`, `measure/uncertainty.py`
- Test: `worker/tests/test_colour_metrics.py`, `worker/tests/test_uncertainty.py`

**Interfaces:**
- Consumes: `MetricValue` (Task 9).
- Produces:
  - `lab_mean(image_bgr, mask) -> tuple[float, float, float] | None` (None for an empty mask)
  - `delta_e(lab1, lab2) -> float` (CIEDE2000)
  - `colour_metrics(image_bgr, mask, baseline_lab) -> list[MetricValue]`: returns `lab_l`, `lab_a`, `lab_b` (units `L*`, `a*`, `b*`, method `lab_mean/1`) and `delta_e` (unit `dE00`, method `delta_e/1`); `[]` for an empty mask.
  - `NOISE_FACTOR = 3.0`
  - `noise_floor(values: Sequence[float]) -> float`: sample SD with ddof 1; `ValueError` for fewer than 3 values.
  - `combined_uncertainty(value: float, noise: float, scale_rel: float, *, power: int = 1) -> float`, computed with `uncertainties`: the std dev of `ufloat(value, noise) * ufloat(1, scale_rel) ** power`.
  - `is_real_effect(effect: float, noise: float) -> bool`: `abs(effect) > NOISE_FACTOR * noise`.
  - `format_pm(value: float, uncertainty: float, unit: str) -> str`. Rounding rule:
    1. Round the uncertainty to 2 significant digits when its leading digit is 1 or 2, otherwise to 1.
    2. Round the value to the same decimal place.
    3. Keep trailing zeros.
    4. Raise `ValueError` if the uncertainty is ≤ 0.

- [ ] **Step 1: Write the failing tests.**

```python
@pytest.mark.parametrize("v,u,unit,text", [
    (12.34567, 0.02345, "mm", "12.346 ± 0.023 mm"),
    (12.34567, 0.1, "mm", "12.35 ± 0.10 mm"),
    (1234, 250, "s", "1230 ± 250 s"),
    (19.23, 2.61, "mm", "19.2 ± 2.6 mm"),
    (4.63, 0.41, "mm", "4.6 ± 0.4 mm"),
])
def test_format_pm_follows_the_reporting_rule(v, u, unit, text):
    assert format_pm(v, u, unit) == text

def test_noise_floor_and_the_3x_rule():
    nf = noise_floor([10.0, 10.4, 9.6, 10.2, 9.8])
    assert nf == pytest.approx(0.3162, rel=1e-3) and is_real_effect(1.0, nf) and not is_real_effect(0.9, nf)

def test_area_uncertainty_counts_the_scale_twice():
    assert combined_uncertainty(100.0, 0.0, 0.01, power=2) == pytest.approx(2.0, rel=1e-3)

def test_colour_metrics_and_empty_mask():
    img = np.zeros((20, 20, 3), np.uint8); img[:, :10] = (40, 160, 220); m = np.zeros((20, 20), bool); m[:, :10] = True
    base = lab_mean(img, m); out = {x.metric: x for x in colour_metrics(img, m, base)}
    assert out["delta_e"].value == pytest.approx(0.0, abs=1e-6) and out["lab_l"].unit == "L*"
    assert colour_metrics(img, np.zeros_like(m), base) == [] and lab_mean(img, np.zeros_like(m)) is None
```

- [ ] **Step 2: Run to see them fail.** Expected: FAIL.
- [ ] **Step 3: Implement both modules.**
- [ ] **Step 4: Run to see them pass.** Expected: 8 passed. Then the full suite and lint: `uv run pytest -q && uv run ruff check . && uv run ruff format --check .`
- [ ] **Step 5: Commit.** `git commit -m "feat(worker): colour metrics, noise floor and uncertainty formatting"`

---

### Task 11: Web scaffold with the v2 tokens

**Files:**
- Create: `web/` via create-next-app; `web/.npmrc` (`save-exact=true`); `web/.prettierrc` (`{"printWidth": 120, "singleQuote": false}`); `web/styles/tokens.css`; `web/app/globals.css`; `web/app/layout.tsx`
- Modify: `web/package.json` (scripts `typecheck: tsc --noEmit`, `format: prettier --write .`; exact versions)

**Interfaces:**
- Produces:
  - **Tokens.** The CSS custom properties from the canvas's `argus.css` v2 (`--ground`, `--surface`, `--raised`, `--active`, `--sunk`, `--border`, `--rule`, `--control`, `--text`, `--muted`, `--faint`, `--accent`, `--accent-ink`, `--accent-tint`, `--accent-soft`, `--primary-bg`, `--primary-ink`, status, `--grid`, `--frame`, shadows, radii `--r-card: 20px; --r-tile: 14px; --r-media: 16px; --r-small: 10px; --r-pill: 999px`, motion durations and easings), defined in three places:
    - `:root, :root[data-theme="light"]` (the light values)
    - `:root[data-theme="dark"]` (the dark values)
    - `@media (prefers-color-scheme: dark) { :root:not([data-theme]) { …dark… } }`
  - **Font.** `--font` comes from `next/font/google` Inter (variable `--font-inter`). Inter is the default until Aymen picks a typeface.

- [ ] **Step 1: Read current flags.** Run `npx create-next-app@latest --help` and note the flags for TypeScript, ESLint, App Router, no Tailwind, no `src/`, import alias `@/*`, npm.
- [ ] **Step 2: Scaffold.** From the repo root, run create-next-app into `web` with those flags. Expected: `web/package.json` exists and `npm run dev` serves the starter page.
- [ ] **Step 3: Pin and tidy.**
  1. Add `.npmrc`, then `npm i -D prettier`.
  2. Replace every `^`/`~` range in `package.json` with the installed version from `package-lock.json`.
  3. Delete the starter's page content, images and CSS.
  4. Add `tokens.css` and `globals.css` (body `background: var(--ground)`, `color: var(--text)`, `font-family: var(--font)`, `font-variant-numeric: tabular-nums` on `.num`).
- [ ] **Step 4: Verify.** In `web/`: `npm run lint && npm run typecheck && npm run build`. Expected: all succeed with no warnings.
- [ ] **Step 5: Commit.** `git commit -m "feat(web): Next.js scaffold with the v2 design tokens"`

---

### Task 12: Shell and kit components

**Files:**
- Create:
  - `web/components/brand/Mark.tsx`
  - `web/components/shell/Rail.tsx`, `PageHeader.tsx`, `Tabs.tsx`, `ThemeSwitch.tsx`
  - `web/components/ui/Button.tsx`, `Badge.tsx`, `VerdictChip.tsx`
  - a `.module.css` for each
  - `web/app/kit/page.tsx`
- Modify: `web/app/layout.tsx` (Rail plus content area)

**Interfaces:**
- Produces:
  - `<Mark state="resting" | "watching" | "locked" size={number} />`: the brand mark SVG from `brand/argus-mark.svg`. In `watching` the point orbits the ring (2.4 s linear); in `locked` the ring closes over 900 ms. Both respect `prefers-reduced-motion`.
  - `<Rail />`: client component. Mark at top; nav items Experiments `/`, Views `/views`, Kit `/kit`; Settings `/settings` pinned at the bottom. The active item (from `usePathname`) is a white 44 px tile with `--shadow-tile`. Every icon has an `aria-label` and a tooltip `title`.
  - `<PageHeader crumb={ReactNode} title={string} finding={ReactNode} actions={ReactNode} />` renders one `h1`.
  - `<Tabs items={{href, label}[]} active={href} />`: pill track; the active tab is an ink pill.
  - `<Button variant="primary" | "secondary" | "text" icon?>`: pill, 36 px, press scale .97.
  - `<Badge source="live" | "replay" | "imported" />`: LIVE pulses; the others are still.
  - `<VerdictChip level={VerdictLevel} provisional?={boolean} />` uses the words Supported, Not supported, Inconclusive, Too early.
  - `<ThemeSwitch />`: System / Light / Dark. It sets `data-theme` on `<html>`, or removes it for System, and remembers the choice in `localStorage` inside try/catch.
  - `/kit` page shows every component in every state.

- [ ] **Step 1: Build the components and the `/kit` page** to the canvas's Foundations board (shape, colour, pill tabs, badges, verdict chips, buttons, mark states).
- [ ] **Step 2: Verify.** `npm run lint && npm run typecheck && npm run build` all succeed.
- [ ] **Step 3: Check in the browser.**
  1. Run `npm run dev`.
  2. Open `http://localhost:3000/kit` in the browser pane.
  3. Take screenshots at 1440 and 390 px in light and dark.

  Expected: matches the Foundations board; no horizontal scroll at 390 px; focus rings visible when tabbing; the LIVE dot pulses and the others don't.
- [ ] **Step 4: Commit.** `git commit -m "feat(web): shell, theme switch and design-system components"`

---

### Task 13: Experiments end to end, plus `python -m argus dev`

**Files:**
- Create:
  - `web/lib/types.ts` (hand-written `Experiment`, `RecipeSummary`, `ExperimentStatus`, until generated types are approved)
  - `web/lib/api.ts`, `web/lib/events.ts`
  - `web/components/experiments/ExperimentsTable.tsx`, `NewExperimentDialog.tsx` (+ CSS)
  - `worker/argus/cli.py`, `worker/argus/__main__.py`
  - `worker/tests/test_cli.py`
- Modify: `web/app/page.tsx`

**Interfaces:**
- Consumes: the Task 6 endpoints and the `experiment` SSE event; Task 12 components.
- Produces:
  - `apiBase() -> string`: `process.env.NEXT_PUBLIC_ARGUS_API ?? "http://localhost:8000"`. Add `NEXT_PUBLIC_ARGUS_API` to `.env.example`.
  - `getExperiments(): Promise<Experiment[]>`, `getRecipes(): Promise<RecipeSummary[]>`, `createExperiment(title, recipeId): Promise<Experiment>`. They throw `ApiError(status, detail)`.
  - `subscribe(onEvent: (type: string, data: unknown) => void): () => void`: an `EventSource` on `/api/events`. The browser resends `Last-Event-ID` on reconnect.
  - **Experiments page** (`/`), client-side:
    - `PageHeader` with the title "Experiments" and a finding line built from the data.
    - A table of experiments with name, recipe, state, created.
    - A "New experiment" primary button opens a native `<dialog>` with a title field and a recipe select; it calls POST, and the new row arrives through SSE.
    - Loading: skeleton rows at the real row height.
    - Error: "Couldn't reach the Argus worker at {apiBase()}. Start it with `uv run python -m argus dev`." plus a Retry button.
    - Empty: "No experiments yet" plus the same button.
  - `worker/argus/cli.py`:
    - `Command(args: list[str], cwd: Path)`
    - `dev_commands(repo: Path) -> list[Command]`:
      - `[uv, "run", "--env-file", "../.env", "uvicorn", "--factory", "argus.api.app:app_from_env", "--reload", "--port", "8000"]` with cwd `repo / "worker"`
      - `[npm, "run", "dev"]` with cwd `repo / "web"`
      - executables resolved by `shutil.which`; `FileNotFoundError` naming the missing tool
    - `main(argv: list[str] | None = None) -> int`, with subcommands:
      - `dev`: starts both and stops both on Ctrl+C
      - `card --out PATH`: calls `card_export.export`

- [ ] **Step 1: Write the failing CLI test.**

```python
def test_dev_commands_start_worker_and_web(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: f"C:/bin/{name}.cmd")
    worker, web = dev_commands(tmp_path)
    assert worker.cwd == tmp_path / "worker" and "argus.api.app:app_from_env" in worker.args and worker.args[0].endswith("uv.cmd")
    assert web.cwd == tmp_path / "web" and web.args[-2:] == ["run", "dev"]

def test_missing_tool_is_named(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None if name == "npm" else name)
    with pytest.raises(FileNotFoundError, match="npm"):
        dev_commands(tmp_path)
```

- [ ] **Step 2: Run to see it fail, implement `cli.py` and `__main__.py`, and run to see it pass.** `uv run pytest tests/test_cli.py -v`. Expected: 2 passed.
- [ ] **Step 3: Build the API client, the event subscription and the Experiments page.** Then `npm run lint && npm run typecheck && npm run build`, all succeeding.
- [ ] **Step 4: Verify end to end in the browser pane.**
  1. Run `uv run python -m argus dev` from `worker/`.
  2. Open `http://localhost:3000`. It shows the empty state.
  3. Create "Iodine clock timing" with recipe `colour-reaction`. The row appears without a reload, and the worker log shows the POST and the SSE event.
  4. Stop the worker and reload. The error state shows the URL and Retry; starting the worker and pressing Retry restores the list.
  5. Take screenshots at 1440 and 390 px, light and dark.
- [ ] **Step 5: Run the whole suite and commit.**
  ```
  cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .
  cd ../web && npm run lint && npm run typecheck && npm run build
  ```
  Then `git commit -m "feat: experiments end to end and the dev command"`

---

## End of phase

- [ ] **Review.** One fresh review of the whole `phase-1` branch against the spec's phase 1 scope and the Global Constraints. Fix the findings.
- [ ] **Merge.** Merge `phase-1` into `main` and push. In `docs/knowledge-base/17-build-plan.md`, mark phase 1 done with the evidence (test counts, screenshots).
- [ ] **Next.** Write the phase 2 plan (`segment()`, tracking, the import pipeline, live capture and the watcher, the Run view on real data).
