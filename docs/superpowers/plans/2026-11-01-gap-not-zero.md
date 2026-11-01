# A miss is a gap, not a zero — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Once SAM has found an object in a vessel, a later empty answer becomes a recorded miss (no reading, a `missed` event), readings older than a miss stop counting as current, and Results shows how often SAM found each vessel's object.

**Architecture:** Every SAM answer is stored as evidence (`sam_answers`). The analyzer drops an empty answer after a first sighting before measuring and opens or closes one `missed` event per stretch. `build_refs` marks a reading followed by a miss as `last_reading`, which the controls' mean, the differences and the verdict leave out. `fits_view` adds per-vessel coverage, which the fit table shows.

**Tech Stack:** Python 3.12 (pydantic, SQLite, pytest with anyio), Next.js + TypeScript (node --test).

**Spec:** `docs/superpowers/specs/2026-11-01-gap-not-zero-design.md` (D-90, D-91)

## Global Constraints

- Branch `phase-4`; nothing pushed, nothing merged into main.
- No new dependency.
- Evidence is never overwritten: `sam_answers` gets no-update, no-delete and no-replace triggers, like every evidence table. Events change only by `close_event`.
- The LLM never computes numbers: coverage, staleness and counts are code.
- Prompts live in `prompts/`; each method card stays within 40–250 words (`test_every_recipe_has_a_short_method_card`).
- Before every commit, run the key scan: `for name in MODEL_API_KEY BASETEN_API_KEY; do KEY=$(grep -E "^$name=" ../.env | cut -d= -f2-); if [ -n "$KEY" ] && git diff --cached | grep -qF "$KEY"; then echo "$name FOUND"; exit 1; fi; done` (from `worker/`; use `.env` from the repo root).
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Gate each commit on a passing run with `set -o pipefail` (a `| tail` must not hide a failure).
- Worker tests: `cd worker && uv run pytest -q`; lint: `uv run ruff check . && uv run ruff format --check .`. Web: `cd web && npm test && npm run typecheck && npm run lint`.

## Review Focus

- Every vessel lost at once: `build_refs` must still build (the noise floor's unit must not come from current readings only). Test in Task 3.
- Two frames analysed at the same time right after a sighting (live overlap): exactly one `missed` event opens. Test in Task 2.
- A recipe with two concepts where only one is lost: the other concept's readings carry on. Test in Task 2.
- A run recorded before this change, or a published replay bundle: no answers and no `coverage` field. Results shows "—", not a crash. Tests in Tasks 4 and 5.
- A colour metric that keeps being read from the last outline after a miss stays current. Test in Task 3.

---

### Task 1: Records and settings a miss needs

**Files:**
- Create: `worker/argus/storage/migrations/010_sam_answers.sql`
- Modify: `worker/argus/domain.py` (`EventKind`, new `SamAnswer` after `Detection`), `worker/argus/storage/repos.py` (new functions after `detections_for_frame`), `worker/argus/recipes/model.py` (`Concept`, `Recipe`), `recipes/foam-height.toml`
- Test: `worker/tests/test_storage_phase2.py`, `worker/tests/test_storage.py:24`, `worker/tests/test_storage_phase3.py:226` (user_version 9 → 10), `worker/tests/test_recipes.py`

**Interfaces:**
- Produces:
  - `EventKind.MISSED = "missed"`.
  - `class SamAnswer(Record)` with fields `frame_id: str`, `vessel_id: str`, `concept: str`, `found: int = Field(ge=0)` and `t: float` (the frame's time).
  - `add_sam_answers(db: Database, run_id: str, frame_id: str, answers: Mapping[tuple[str, str], int]) -> None`, keyed by (vessel_id, concept).
  - `sam_answers_for_run(db: Database, run_id: str) -> list[SamAnswer]`, ordered by the frame's t, then rowid.
  - `Concept.can_vanish: bool = False`.
  - `Recipe.measurement_for(metric: str) -> MeasurementSpec`, which maps a stored metric name to its spec (a lab_mean's `<id>_l/_a/_b` too) and raises `KeyError` on an unknown one.

- [ ] **Step 1: Write the failing tests**

```python
# test_storage_phase2.py
def test_sam_answers_are_evidence(db, run, vessel, frame):
    add_sam_answers(db, run.id, frame.id, {(vessel.id, "root"): 2, (vessel.id, "bean"): 0})
    answers = sam_answers_for_run(db, run.id)
    assert [(a.concept, a.found, a.t) for a in answers] == [("root", 2, frame.t), ("bean", 0, frame.t)]
    for sql in (
        "UPDATE sam_answers SET found=5",
        "DELETE FROM sam_answers",
        f"INSERT OR REPLACE INTO sam_answers(run_id, frame_id, vessel_id, concept, found) "
        f"VALUES ('{run.id}', '{frame.id}', '{vessel.id}', 'root', 9)",
    ):
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql)

# test_recipes.py
def test_only_foam_can_vanish_and_metrics_map_back_to_their_concepts():
    recipes = load_all(REPO_ROOT / "recipes")
    assert [c.can_vanish for c in recipes["foam-height"].concepts] == [True]
    assert not any(c.can_vanish for r in recipes.values() if r.id != "foam-height" for c in r.concepts)
    colour = recipes["colour-reaction"]
    lab = next(m for m in colour.measurements if m.method == "lab_mean")
    assert colour.measurement_for(f"{lab.id}_a") is lab
    assert recipes["seed-germination"].measurement_for("root_length").source == "root"
    with pytest.raises(KeyError):
        colour.measurement_for("nope")
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd worker && uv run pytest -q tests/test_storage_phase2.py tests/test_recipes.py`
Expected: FAIL with ImportError (`add_sam_answers`), then AttributeError (`can_vanish`).

- [ ] **Step 3: Implement**

The migration has columns `run_id` (refs runs), `frame_id` (refs frames), `vessel_id` (refs vessels), `concept`, and `found INTEGER NOT NULL CHECK (found >= 0)`, with `PRIMARY KEY (frame_id, vessel_id, concept)` and an index on `run_id`. Its three triggers follow `009_next_runs.sql` and raise `'SAM answers are evidence'`; the replace trigger fires when a row with the same key exists. `sam_answers_for_run` joins frames for t. In `foam-height.toml`, set `can_vanish = true` on the foam concept and `version = 2`. Update the two `user_version` asserts to 10.

- [ ] **Step 4: Run the whole worker suite**

Run: `cd worker && set -o pipefail && uv run pytest -q 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 5: Commit** `feat(storage): every SAM answer is evidence; foam can vanish (D-90)`

---

### Task 2: The analyzer turns a miss into a gap (D-90)

**Files:**
- Modify: `worker/argus/pipeline/analyzer.py` (the `RunContext` fields; `analyze_frame` between the occlusion filter and `_store_detections`)
- Test: `worker/tests/test_analyzer.py`

**Interfaces:**
- Consumes: Task 1's `add_sam_answers`, `EventKind.MISSED`, `Concept.can_vanish`, and `format_run_time` from `argus.claims.refs`.
- Produces:
  - New `RunContext` fields:
    - `sighted: dict[str, set[str]]` (vessel → concepts seen);
    - `missing: dict[tuple[str, str], str]` ((vessel, concept) → open event id);
    - `last_found_t: dict[tuple[str, str], float]`;
    - `miss_lock: asyncio.Lock`.
  - The `missed` event: `source="pipeline"`, `vessel_id`, `frame_ids=[frame_id]`, and detail `{"concept": c, "last_seen_t": t0, "message": f"SAM found no {c} in {label} after finding it at {format_run_time(t0)}: no reading until it is found again"}`.

- [ ] **Step 1: Write the failing tests** (use injected masks, `masks={vessel_id: {"root": [...]}}`, to script each vessel; `patch` as in `test_injected_masks_count_as_segmented_without_a_call`)

```python
async def test_after_a_first_sighting_nothing_found_is_a_miss_not_a_zero(ctx, scene):
    # A: found at 0, empty at 60 and 120, found at 180. B: empty throughout (never seen: zeros).
    # Assert:
    # - A's length readings are at [0.0, 180.0] only;
    # - B reads 0.0 at every frame;
    # - exactly one missed event, for A, with t_start 60.0, t_end 180.0, detail["concept"] == "root" and
    #   detail["last_seen_t"] == 0.0;
    # - sam_answers_for_run gives A found [1, 0, 0, 1] and B found [0, 0, 0, 0];
    # - published "event" messages include the opening and the close (t_end 180.0).

async def test_a_miss_still_open_at_the_end_stays_open(ctx, scene):  # found, then empty: t_end is None

async def test_a_concept_that_can_vanish_reads_zero_after_a_sighting(ctx, scene):
    # ctx.recipe = a copy of RECIPE with concepts [{"name": "root", "can_vanish": True}];
    # found, then empty → A reads [length, 0.0] and there is no missed event

async def test_a_hand_in_front_neither_ends_nor_repeats_a_miss(ctx, scene):
    # found at 0, empty at 60 (miss opens), occluded:A at 120, found at 180
    # → one missed event, closed at 180; no answer row for A at 120

async def test_two_frames_at_once_open_one_miss(ctx, scene):
    # found at 0; then asyncio.gather of two empty frames at 60 and 120 → exactly one missed event

async def test_losing_one_concept_keeps_the_other(ctx, scene):
    # recipe with concepts root and bean, each with a size measurement; A: both found, then root empty and bean found
    # → bean's reading at 60 exists, root's doesn't, and the one missed event has detail["concept"] == "root"
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd worker && uv run pytest -q tests/test_analyzer.py -k "miss or vanish or hand_in_front or one_concept"`
Expected: FAIL (A reads 0.0 at 60 and 120; no missed event).

- [ ] **Step 3: Implement**

Right after `keyed` drops blocked vessels, and under `ctx.miss_lock`:
- record `{(vessel, concept): len(patches)}` with `add_sam_answers` (on a thread, as for other writes), when there are any;
- for each answer with objects: add the concept to `sighted`, set `last_found_t`, and if a miss is open, close it with `close_event` at t and publish it the way `_colour_reference` publishes its closed event;
- for an empty answer whose concept was sighted and can't vanish: delete it from `keyed[vessel]`, and open a `missed` event through `ctx.event` unless one is already open.

The rest of `analyze_frame` is unchanged: a vessel left with an empty dict gets no geometry, `last_masks` keeps its newest outline, and `segmented` stays `bool(keyed)`.

- [ ] **Step 4: Run the whole worker suite**

Run: `cd worker && set -o pipefail && uv run pytest -q 2>&1 | tail -3`
Expected: all pass (the existing "nothing found is a zero" tests still pass: their empties come before any sighting).

- [ ] **Step 5: Commit** `feat(pipeline): an empty SAM answer after a first sighting is a miss, not a zero (D-90)`

---

### Task 3: A reading followed by a miss is not current (D-91)

**Files:**
- Modify: `worker/argus/claims/refs.py` (`NOTABLE`, `_measurement_ref`, `build_refs`, event refs), `worker/argus/pipeline/verdict.py` (`verdict_inputs`)
- Test: `worker/tests/test_refs.py`, `worker/tests/test_verdict_speed.py` (next to its direct `verdict_inputs` test)

**Interfaces:**
- Consumes: `Recipe.measurement_for` and `EventKind.MISSED` from Task 1; the missed event's `detail["concept"]` from Task 2.
- Produces:
  - A ref with `kind="last_reading"` keeps its `m:<label>:<metric>` id.
  - Labels:
    - stale `m:`: `f"{name}: {metric} at its last reading, before SAM stopped finding the {concept}"`;
    - stale `chg:`: `f"{name}: {metric} change from its first reading to its last"`;
    - missed event ref: `f"Time SAM stopped finding the {concept} in {name}"`.
    - Here `name` is `_vessel_label(vessel)` and `concept` is the missed event's.

- [ ] **Step 1: Write the failing tests** (in `test_refs.py`, on `two_by_two`, with a helper `missed(db, run, vessel, *, t)` that calls `add_event(db, run.id, vessel_id=vessel.id, t_start=t, kind=EventKind.MISSED, source="pipeline", detail={"concept": "liquid", "last_seen_t": 600.0, "message": "m"})`; `delta_e` reads `liquid` in the colour-reaction recipe)

```python
def test_a_control_lost_after_its_last_reading_is_left_out_of_the_mean(db, two_by_two):
    run, vessels = two_by_two
    a = vessels[0]  # control A, last reading 4.0 at 600 s
    missed(db, run, a, t=650.0)
    refs = build_refs(db, run.id, 700.0, recipe=COLOUR, plan=PLAN)
    assert refs.get("m:A:delta_e").kind == "last_reading" and "before SAM stopped finding" in refs.get("m:A:delta_e").label
    assert refs.get("diff:C:delta_e").value == pytest.approx(25.6 - 5.0)  # B alone
    assert refs.get("m:B:delta_e").kind == "measurement"

def test_a_lost_treatment_has_no_difference(db, two_by_two): ...  # miss on C at 650 → "diff:C:delta_e" not in refs

def test_a_miss_before_the_last_reading_changes_nothing(db, two_by_two): ...  # miss on A at 500 (readings go on to 600) → kind "measurement"

def test_every_vessel_lost_still_builds(db, two_by_two): ...  # misses on all four → refs build, noise:delta_e present, no diff refs

def test_the_missed_event_ref_names_the_concept_and_vessel(db, two_by_two): ...  # an ev: ref's label == f"Time SAM stopped finding the liquid in {_vessel_label(A)}"
```

```python
# test_verdict_speed.py, next to the existing direct call
def test_a_lost_control_is_not_counted_as_measured(db, exp): ...
# two controls and one treatment on a level plan, one control lost after its last reading
# → verdict_inputs(...).controls == 1
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd worker && uv run pytest -q tests/test_refs.py tests/test_verdict_speed.py`
Expected: FAIL (kind "measurement"; A still in the mean).

- [ ] **Step 3: Implement**

In `build_refs`, a vessel's latest reading of a metric is lost when a missed event for that vessel has a `detail["concept"]` in `{spec.source, spec.touching}` (where `spec = recipe.measurement_for(metric)`) and a `t_start` after that reading. The events are already cut at t.
- Keep `latest` for every vessel (the noise unit reads from it).
- Build the controls' mean and the treatments' differences only from vessels that are not lost.
- `_measurement_ref` takes `lost: str | None` (the concept) for the label and kind.
- Add `"missed"` to `NOTABLE`, not to the note `TRIGGERS`.

In `verdict_inputs`, `controls` and `measured` count only refs whose kind is not `"last_reading"`.

- [ ] **Step 4: Run the whole worker suite**

Run: `cd worker && set -o pipefail && uv run pytest -q 2>&1 | tail -3`
Expected: all pass.

- [ ] **Step 5: Commit** `feat(claims): a reading SAM lost the object after is not a reading of now (D-91)`

---

### Task 4: Coverage per vessel on the fits route

**Files:**
- Create: `worker/argus/analyze/coverage.py`
- Modify: `worker/argus/analyze/fits.py` (`fits_view`)
- Test: `worker/tests/test_fits.py` (unit), `worker/tests/test_api_results.py` (route)

**Interfaces:**
- Consumes: `SamAnswer`, `sam_answers_for_run` and `Recipe.measurement_for` from Task 1.
- Produces:
  - `@dataclass(frozen=True) class Coverage` with fields `concept: str`, `asked: int`, `found: int`, `first_found_t: float | None` and `missed_after: int`.
  - `detection_coverage(answers: Sequence[SamAnswer], vessel_id: str, concept: str) -> Coverage | None`, which returns `None` when that vessel has no answers for the concept.
  - Each `fits_view` vessel gains `"coverage": asdict(c) | None`, for `recipe.measurement_for(metric).source`.

- [ ] **Step 1: Write the failing tests**

```python
def test_coverage_counts_what_sam_found_and_missed_after_the_first_find():
    answers = [SamAnswer(frame_id=f"f{i}", vessel_id="v", concept="c", found=n, t=60.0 * i) for i, n in enumerate([0, 0, 2, 0, 1, 0])]
    assert detection_coverage(answers, "v", "c") == Coverage("c", asked=6, found=2, first_found_t=120.0, missed_after=2)
    assert detection_coverage(answers, "other", "c") is None
    never = [a.model_copy(update={"found": 0}) for a in answers]
    assert detection_coverage(never, "v", "c") == Coverage("c", 6, 0, None, 0)

def test_fits_carry_coverage_and_none_for_a_run_without_answers(client, db, experiment):
    # run_of(...) stores readings only → every vessel's "coverage" is None;
    # add frames and add_sam_answers for one vessel → its coverage has asked/found from them
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd worker && uv run pytest -q tests/test_fits.py tests/test_api_results.py`
Expected: FAIL with ImportError, then KeyError `coverage`.

- [ ] **Step 3: Implement** (`missed_after` counts answers with `found == 0` and `t > first_found_t`)

- [ ] **Step 4: Run the whole worker suite**, as in Task 1 Step 4. Expected: all pass (`test_bundle.py` included).

- [ ] **Step 5: Commit** `feat(results): how often SAM found each vessel's object (D-90)`

---

### Task 5: Results and timeline show misses

**Files:**
- Create: `web/lib/misses.ts`, `web/tests/misses.test.ts`
- Modify:
  - `web/lib/types.ts`: `RunEventKind` gets `"missed"`; new `Coverage`; `FitsView` vessel gets `coverage?: Coverage | null`.
  - `web/components/results/FitTable.tsx`.
  - `web/components/run/Timeline.tsx` and `Timeline.module.css`.
  - `web/components/feed/NoteCard.tsx`.

**Interfaces:**
- Consumes: Task 4's `coverage` shape (snake_case, times in s).
- Produces:
  - `coverageLines(c: Coverage | null | undefined, span: number): [string, string | null]`;
  - `markEnd(e: RunEvent, tEnd: number): number`.

- [ ] **Step 1: Write the failing test** (`web/tests/misses.test.ts`, node:test like `chart.test.ts`, importing `../lib/misses.ts`)

```ts
test("coverage reads as pictures found and misses since the first find", () => {
  const c = { concept: "microbial colony", asked: 145, found: 14, first_found_t: 40320, missed_after: 131 };
  assert.deepEqual(coverageLines(c, 86400), ["14 of 145 pictures", "not found in 131 since 11:12"]);
  assert.deepEqual(coverageLines({ ...c, found: 145, missed_after: 0 }, 86400), ["145 of 145 pictures", null]);
  assert.deepEqual(coverageLines({ ...c, found: 0, first_found_t: null, missed_after: 0 }, 86400), ["0 of 145 pictures", "never found"]);
  assert.deepEqual(coverageLines(undefined, 86400), ["—", null]); // a bundle published before coverage existed
});

test("an open miss runs to the end of the run; other open events are a mark", () => {
  const e: RunEvent = { id: "e", vessel_id: "v", t_start: 100, t_end: null, kind: "missed", source: "pipeline", detail: {} };
  assert.equal(markEnd(e, 900), 900);
  assert.equal(markEnd({ ...e, t_end: 300 }, 900), 300);
  assert.equal(markEnd({ ...e, kind: "quality" }, 900), 100);
});
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd web && npm test`
Expected: FAIL, cannot find `../lib/misses.ts`.

- [ ] **Step 3: Implement**

- `coverageLines` uses `formatRunTime` from `./scale.ts`.
- FitTable gets a "Found by SAM" column after "Condition". It shows line one, and line two in the role's small style. The span is the largest reading t across vessels.
- Timeline adds `"missed"` to `MARKED` and draws each mark's width to `markEnd(e, tEnd)`.
- `.missed { fill: var(--neg-bg); opacity: 0.55; }`.
- NoteCard `EVENT.missed = "Lost by SAM"`.

- [ ] **Step 4: Run the web checks**

Run: `cd web && npm test && npm run typecheck && npm run lint`
Expected: all pass, no lint warnings.

- [ ] **Step 5: Commit** `feat(web): Results says how often SAM found each dish; the timeline shows misses`

---

### Task 6: Prompts and docs say what a miss means

**Files:**
- Modify: `prompts/recipes/colony-spread/method.md`, `prompts/recipes/seed-germination/method.md`, `prompts/recipes/general/method.md`, `prompts/system/scientific-rules.md`, `docs/knowledge-base/15-decisions-log.md`, `docs/knowledge-base/18-glossary.md`
- Test: `worker/tests/test_prompts.py`

**Interfaces:** none (copy only).

- [ ] **Step 1: Write the failing test**

```python
def test_the_cards_say_a_miss_after_a_sighting_is_a_gap():
    for recipe in ("colony-spread", "seed-germination", "general"):
        assert "miss" in load_prompt(f"recipes/{recipe}/method.md")
    assert "last reading" in load_prompt("system/scientific-rules.md")
```

- [ ] **Step 2: Run it to see it fail.** Run: `cd worker && uv run pytest -q tests/test_prompts.py`. Expected: FAIL.

- [ ] **Step 3: Write the copy**

Colony-spread: the sentences from "A dish where SAM found nothing reads zero" through "before and after." become:

> Before SAM first finds the colony in a dish, the dish reads zero. After that, a scan where SAM finds nothing is a miss: no reading, and a "missed" event until it is found again. A failed segmentation is a gap too. SAM misses a colony while it is small and faint, so an early zero is not proof that nothing grew: compare it with the image.

Seed-germination: "A jar where SAM found no root reads zero; a failed segmentation is a gap, not a zero." becomes:

> A jar reads zero until SAM first finds a root; after that, a picture where SAM finds no root is a miss (a gap, with a "missed" event), not a zero. A failed segmentation is a gap too.

General: "A region where nothing was found reads zero area; a failed segmentation is a gap." becomes:

> A region reads zero area until the object is first found; after that, a picture where SAM finds nothing is a miss (a gap, with a "missed" event). A failed segmentation is a gap too.

Scientific rules: append to rule 3:

> A reading labelled as the last before SAM stopped finding the object is not a reading of now: say when it was taken and that the object has not been found since.

KB 15 gets rows D-90 and D-91, worded from the spec's Decisions section and dated Nov 1. KB 18 gets "**Miss**: a picture where SAM finds nothing in a vessel after it has found the object there once. Recorded as a gap with a `missed` event, never as a zero (except for things that can vanish, such as foam)."

- [ ] **Step 4: Run the whole worker suite** (method cards within 250 words). Expected: all pass.

- [ ] **Step 5: Commit** `docs(prompts): a miss after a sighting is a gap, in the cards, the rules and the KB (D-90, D-91)`

---

### Task 7: Check it on the swarming scans

Approved in the design (Nov 1): about $2.20 of SAM calls plus one verdict. The run stays local (D-89): no bundle, no publish.

- [ ] **Step 1:** Restart the worker preview so it runs this branch's code, and confirm `/api/health` (or the root route) answers.
- [ ] **Step 2:** Start the import from the request saved for the first run: `cd worker && uv run python -m argus run "<scratchpad>/swarm_run.json"`. The experiment is `exp_fbf009d4df33` and the manifest is `data/datasets/swarming/frames/manifest.json`. Wait for status `finished` (run in the background; you are notified when it ends).
- [ ] **Step 3:** Request the verdict with `POST /api/runs/<new run>/verdict`.
- [ ] **Step 4:** Read from the database and the API, and record in the ledger:
  - fliA 0.1's readings: zeros after its first non-zero reading (expected none);
  - its missed events;
  - its coverage line;
  - the verdict, and whether its replicates check counts fliA 0.1 as not measured at 24 h;
  - the run's spend.
- [ ] **Step 5:** Open Results for the new run in the browser pane and check the "Found by SAM" column and the timeline's missed stretches.

Expected: no zero reading for any dish after its first sighting; at least one missed stretch on fliA 0.1; the verdict INCONCLUSIVE or TOO_EARLY with a reason that rests on gaps, not on zeros.
