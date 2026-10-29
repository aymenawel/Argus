# Argus Phase 3: Reason, Notes and Verdicts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A run gets checked AI notes on its timeline and a four-level verdict computed against a locked, structured plan, and a researcher can set up an experiment end to end in a wizard (describe → source → vessels → roles → check → plan → lock and start) instead of writing `run.json`.

**Architecture:** The worker gains `reason/` (the only module besides `segment/sam.py` that talks to a model: Responses API, strict JSON, tiers, cache keys, cost), `claims/` (the numbers a call may cite, called refs, the claim checker and the renderer), `analyze/` (noise floor, recipe rule events, the verdict ceiling), and two pipelines that use them: a `NoteWriter` attached to every run and a verdict job. New evidence tables (derived numbers, notes, note attempts, verdicts, reviews) are append-only like phase 2's. The web app adds a notes feed with evidence chips, a verdict panel and the setup wizard, fed through the same `SnapshotStore`.

**Tech Stack:** what phases 1–2 installed (FastAPI, OpenCV 5, scikit-image, numpy, scipy, `uncertainties`, `openai` 3.40 Responses API, `meta-sam-parser`; Next.js 16, React 19, TypeScript strict, Node's built-in test runner). No new packages.

**Spec:** `docs/superpowers/specs/2026-10-28-argus-design.md`: phase 3 of §16, implementing §4.1 step 6, §5 (plans, derived, notes, note_attempts, verdicts, reviews), §6 (noise floor, derived numbers with IDs), §7.1–§7.4 (`reason()`, notes and the claim checker, verdicts, the setup draft), §9.2 (setup wizard, feed and verdict on the Run screen), §10 (setup, plan, notes, verdict routes; SSE `note`, `note_rejected`, `verdict`). Facts: `docs/knowledge-base/04` (Responses API shapes, effort, `max_output_tokens`, cache keys), `05` (Muse prices), `08` (verdict table, rivals, critique). Prompts: `prompts/README.md`. UI reference: the canvas's Run and Setup boards (https://claude.ai/artifact/2JeEMitFwx3e3egzNbptwg).

## Inputs needed from Aymen

1. **A fast live experiment for Task 15**, set up through the new wizard, with **at least 2 treatment and 2 control vessels** (the verdict needs replicates): for example 2 glasses of warm and 2 of room-temperature water with food colouring, or the iodine clock (Q-12). About 15–20 minutes on the Nuroum, card in view.
2. **The germination run (Q-14)** is still the critical path. Phase 3 doesn't need its footage; phase 5 does.

## Global Constraints

- Everything in phases 1–2's Global Constraints still holds (uv and Python 3.12, ruff line length 120, web lint, typecheck and build before every web commit, secrets only in `.env`, glossary words, `t` in real seconds, `method_version` `"<method>/<n>"`, `pathlib`, the commit trailer, evidence never overwritten, never block the event loop, the worker formats every number the UI shows).
- **No new dependencies** (worker or web).
- **Only `argus/segment/sam.py` and `argus/reason/client.py` import `openai`** (spec §7.1). Model IDs, base URL and key come from `Settings`. **Tests never touch the network:** they replay recorded responses or use fakes. Probes in `worker/probes/` are run by hand.
- **The model never writes a number.** Text fields cite numbers only as `{ref:<id>}` tokens whose ids are in that call's MEASUREMENTS block; the claim checker runs before anything is saved (spec §7.2). Code renders the tokens.
- **Every model call is logged** in `model_calls` (function `note`, `verdict_draft`, `verdict_critique`, `describe` or `preview`), failures and fallbacks included, and counted against the run's `RUN_SPEND_CAP_USD` when it belongs to a run.
- **Reasoning settings (KB 04, spec §7.1):** routine = `muse-spark-1.3`, effort `minimal`, `max_output_tokens` 4000; deep = `muse-wonder-1.0`, effort `medium`, `max_output_tokens` 8000; deep fallback = `muse-spark-1.3` at effort `high`, labelled in what it produces. Every call sends `prompt_cache_key` = `argus:{experiment_id}:{tier}:{prompt_version}`. Snapshots are JPEG, 768 px on the long side. Strict JSON through `text={"format": {"type": "json_schema", "name": ..., "schema": ..., "strict": True}}`; check `status == "completed"` before parsing.
- **Prices (KB 05, per 1M tokens):** Spark $1.25 input, $0.15 cached input, $4.25 output; Wonder $4.00, $0.20, $20.00. Reasoning tokens are billed as output.
- **Prompts live in `prompts/`**, schemas in `prompts/schemas/` (strict: every object has `additionalProperties: false` and lists every key in `required`). Code never holds prompt text beyond the block headers it assembles.
- **Safety (CLAUDE.md rule 8):** no prompt or draft proposes hardware actions; the rules file keeps its safety rule; no medical advice.
- **Evidence layers (spec §5):** derived numbers, note attempts, verdicts and reviews are append-only; a note's only later change is `t_end`, set once, when "no change" notes collapse.
- Branch `phase-3`; merge to `main` after the end-of-phase review.

## Review Focus

1. **A note that states a quantity in words** ("twice as fast", "about forty minutes", "50 percent"). The checker rejects spelled quantities (two and up, twice, double, half, percent, `%`) outside tokens, as it rejects digits; "one" stays allowed. Test in Task 5.
2. **A truncated or incomplete model answer** (`status` `incomplete`, `max_output_tokens` reached, empty text). It is logged as a failed call and never parsed; the note writer retries once and then saves the code-written note. Tests in Tasks 2 and 8.
3. **A design the verdict can't judge:** a single vessel, no control vessel, one treatment vessel, or a plan whose metric the run never measured. Notes still save; the ceiling is {INCONCLUSIVE} with a check that says why in words; nothing raises. Tests in Tasks 4, 7 and 8.
4. **The spend cap reached mid-run.** No further reasoning calls; one code-written note says notes are paused for the spend cap; asking for a verdict answers 409 with the reason. Tests in Tasks 8 and 9.
5. **The plan edited after it was locked.** Edits make version 2; notes and the verdict keep using version 1, the locked one, and say so; locking twice returns the same lock. Tests in Tasks 1 and 7.

## Not in this phase

- **The views step** of the wizard and Muse-picked views (phase 4, with the view catalog). The wizard goes from Check to Plan.
- **Blinding** (blind labels until the run ends) and randomized positions: phase 4 with the DOE pieces. Vessels show their real labels.
- **Insight notes** from the deep tier, the Results and Next run screens, Ax: phase 4. The verdict panel sits on the Run screen until Results exists.
- **Voice notes** and Ask Argus (Should items, spec §2).
- **Choosing the recipe from plain words:** the experiment's recipe is chosen when it is created; `describe` drafts the plan, factor, conditions and rivals within that recipe's vocabulary.
- **Separate source, calibrate and lighting-check routes** (spec §10): the wizard saves the source in the setup and gets calibration and lighting from `preview`, one call instead of three.

---

## File structure

```
worker/argus/
  config.py                          modify: Muse prices, efforts, output limits, note cadence; read SAM_TIMEOUT_S
  domain.py                          modify: structured plan fields, Setup, Derived, Note, NoteAttempt, Verdict, Review
  storage/
    migrations/004_reason_and_verdicts.sql   plan columns, setups, derived, notes, note_attempts, verdicts, reviews
    repos.py                         modify: setups, derived, notes, attempts, verdicts, reviews, first locked plan
  reason/
    __init__.py                      reason(), ReasonTask, ReasonResult, ReasonError
    client.py                        the Responses call, usage → cost, the model-call record (only openai import here)
    prompts.py                       prompt files, prompt_version, block assembly, snapshots
  claims/
    refs.py                          Ref, RefTable, build_refs() (writes the derived rows it shows)
    checker.py                       check_text_fields(), check_note(), render()
    fallback.py                      code-written notes
  analyze/
    noise.py                         noise_floor()
    rules.py                         parse_rule(), RuleEvaluator
    ceiling.py                       VerdictInputs, Check, ceiling(), choose_verdict()
  pipeline/
    notes.py                         NoteWriter: when to write, reason → check → retry → fallback, collapse
    verdict.py                       verdict_inputs(), run_verdict()
    analyzer.py                      modify: rule events after measurements; RunContext.notes
    live.py, imported.py, jobs.py    modify: drive the NoteWriter; run the verdict when a run ends
  api/
    setup.py                         setup, describe, preview, plan, lock
    notes.py                         notes, researcher notes, interventions, verdict, reviews
    app.py, runs.py                  modify: register routes; runs from the saved setup
prompts/
  system/scientific-rules.md         modify: rule 1 says numbers only as {ref:<id>} tokens
  routine/note.md                    the note task
  deep/verdict.md                    the verdict draft task
  deep/verdict-critique.md           modify: refs instead of numbers
  setup/describe.md                  the plan draft task
  recipes/<id>/method.md             one method card per recipe (4)
  schemas/note.json                  v2: refs_used and {ref} tokens
  schemas/verdict.json, verdict_critique.json (modify), recipe_draft.json
worker/probes/record_reason.py       records one real note response as a fixture
web/
  lib/types.ts, api.ts               modify: notes, verdict, plan, setup, preview
  lib/run-snapshot.ts                modify: notes and verdict in the snapshot; note, note_rejected, verdict events
  lib/setup.ts                       wizard state and step checks (pure, tested)
  components/feed/                   Feed, NoteCard, EvidenceChip, NoteComposer
  components/verdict/VerdictPanel.tsx
  components/setup/                  one component per step, SetupFrame (frame with regions to keep or draw)
  app/experiments/[id]/setup/        page + SetupScreen
  app/experiments/[id]/run/RunScreen.tsx   modify: feed and verdict panel
  tests/run-snapshot.test.ts, tests/setup.test.ts
```

---

### Task 1: Settings, storage and domain for phase 3

**Files:**
- Create: `worker/argus/storage/migrations/004_reason_and_verdicts.sql`
- Modify: `worker/argus/config.py`, `worker/argus/domain.py`, `worker/argus/storage/repos.py`
- Test: `worker/tests/test_storage_phase3.py`, `worker/tests/test_config.py`

**Interfaces:**
- Consumes: phase 2 storage (`Database`, `new_id`, `add_event`, the trigger pattern of migration 003).
- Produces:
  - `Settings`: `spark_input_usd=1.25`, `spark_cached_usd=0.15`, `spark_output_usd=4.25`, `wonder_input_usd=4.00`, `wonder_cached_usd=0.20`, `wonder_output_usd=20.00` (per 1M tokens); `routine_effort="minimal"`, `routine_max_output=4000`, `deep_effort="medium"`, `deep_max_output=8000`, `fallback_effort="high"`; `reason_concurrency=2`, `reason_timeout_s=120.0`, `snapshot_px=768`; `ENV_FIELDS` gains `"SAM_TIMEOUT_S": "sam_timeout_s"` (it was documented in `.env.example` but never read).
  - `domain.Direction(StrEnum)`: `HIGHER = "higher"`, `LOWER = "lower"` (the treatment vessels' value relative to the controls').
  - `PlanDraft` gains optional `metric: str | None`, `direction: Direction | None`, `min_effect: float | None` (≥ 0, in the metric's unit), `checkpoint_s: float | None` (≥ 0, run time), `treatment: str | None` (a condition value; `None` means every treatment vessel). `plan_sha256` hashes with `exclude_none=True`, so phase 1 plans keep their hashes.
  - `Setup(Record)`: `source: RunSource | None = None`, `time_scale: float = 1.0`, `vessels: list[VesselDraft] = []`, `print_check_mm: float | None = None`, `ruler: RulerInput | None = None`, `factor: str | None = None`, `factor_unit: str | None = None`.
  - `DerivedDraft(Record)`: `t: float ≥ 0`, `kind: str`, `label: str`, `value: float`, `uncertainty: float ≥ 0`, `unit: str`, `inputs: list[str]`, `method_version`; `Derived(DerivedDraft)`: `id`, `run_id`.
  - `NoteDraft(Record)`: `t: float ≥ 0`, `t_end: float | None`, `author: Literal["ai", "researcher"]`, `level: Literal["event", "checkpoint", "insight"] | None`, `tag: Literal["observation", "intervention", "question"] | None`, `body: dict[str, Any]` (rendered sections), `refs: list[str]`, `evidence: list[str]`, `check_status: Literal["passed", "fallback", "researcher"]`, `model_call_id: str | None`; `Note(NoteDraft)`: `id`, `run_id`.
  - `NoteAttemptDraft(Record)`: `t`, `attempt: int ≥ 1`, `raw: dict`, `reasons: list[str]`, `passed: bool`, `model_call_id: str | None`; `NoteAttempt`: `id`, `run_id`.
  - `VerdictDraft(Record)`: `t`, `provisional: bool`, `allowed: list[VerdictLevel]`, `checks: list[dict]`, `verdict: VerdictLevel`, `body: dict` (rendered explanation, rivals, what would change it, confidence), `draft: dict`, `critique: dict | None`, `refs: list[str]`, `model_call_ids: list[str]`, `fell_back: bool`; `Verdict`: `id`, `run_id`.
  - `ReviewDraft(Record)`: `t: float ≥ 0`, `target_kind: Literal["note", "verdict", "rival", "event"]`, `target_id: str`, `action: Literal["confirm", "dismiss", "correct", "resolve"]`, `comment: str`; `Review`: `id`, `run_id`.
  - `EventKind.RULE = "rule"`; `RunEvent.source` accepts `"rule"`.
  - repos: `first_locked_plan(db, experiment_id) -> Plan | None`; `save_setup(db, experiment_id, setup: Setup) -> Setup`; `get_setup(db, experiment_id) -> Setup` (an empty `Setup()` when none); `add_derived(db, run_id, drafts) -> list[Derived]`; `derived_for_run(db, run_id) -> list[Derived]`; `add_note(db, run_id, draft) -> Note`; `extend_note(db, note_id, t_end) -> Note`; `notes_for_run(db, run_id, t_from=None, t_to=None) -> list[Note]`; `add_note_attempt(db, run_id, draft) -> NoteAttempt`; `note_attempts_for_run(db, run_id) -> list[NoteAttempt]`; `add_verdict(db, run_id, draft) -> Verdict`; `latest_verdict(db, run_id) -> Verdict | None`; `add_review(db, run_id, draft) -> Review`; `reviews_for_run(db, run_id) -> list[Review]`.

- [ ] **Step 1: Write the failing tests**

```python
def test_structured_plan_fields_keep_old_hashes(db, exp):
    old = PlanDraft(hypothesis="h", prediction="p", threshold="t", rivals=["lighting change"])
    assert plan_sha256(old) == plan_sha256(old.model_copy(update={"metric": None}))  # phase 1 hashes unchanged
    full = old.model_copy(update={"metric": "delta_e", "direction": Direction.HIGHER, "min_effect": 5.0,
                                  "checkpoint_s": 600.0, "treatment": "warm"})
    assert plan_sha256(full) != plan_sha256(old)
    save_plan_draft(db, exp.id, full)
    locked = lock_plan(db, exp.id)
    assert locked.direction is Direction.HIGHER and lock_plan(db, exp.id).sha256 == locked.sha256  # idempotent

def test_edits_after_the_lock_leave_the_first_locked_plan(db, exp):
    save_plan_draft(db, exp.id, PlanDraft(hypothesis="h1", prediction="p", threshold="t", rivals=[]))
    lock_plan(db, exp.id)
    save_plan_draft(db, exp.id, PlanDraft(hypothesis="h2", prediction="p", threshold="t", rivals=[]))
    assert first_locked_plan(db, exp.id).hypothesis == "h1"

def test_setup_round_trips_and_defaults_empty(db, exp):
    assert get_setup(db, exp.id) == Setup()
    setup = Setup(source=RunSource(kind=SourceKind.WEBCAM, camera_index=1), print_check_mm=100.0,
                  vessels=[VesselDraft(label="A", role=Role.CONTROL, roi=[(0, 0), (10, 0), (10, 10)])])
    assert get_setup(db, exp.id) == save_setup(db, exp.id, setup) == setup

@pytest.mark.parametrize("table", ["derived", "note_attempts", "verdicts", "reviews"])
def test_reasoning_evidence_is_append_only(db, run, table):
    ...  # add one row of each kind through its repo function, then:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute_write(f"UPDATE {table} SET t = t + 1")  # same helper the phase 2 trigger tests use
    with pytest.raises(sqlite3.IntegrityError):
        db.execute_write(f"DELETE FROM {table}")

def test_a_note_may_only_gain_its_end_time_once(db, run):
    note = add_note(db, run.id, NoteDraft(t=10.0, t_end=None, author="ai", level="checkpoint", tag=None,
                                          body={"observation": "No change."}, refs=[], evidence=[],
                                          check_status="passed", model_call_id=None))
    assert extend_note(db, note.id, 50.0).t_end == 50.0
    with pytest.raises(sqlite3.IntegrityError):
        extend_note(db, note.id, 90.0)

def test_sam_timeout_is_read_from_the_environment():
    assert load_settings({"SAM_TIMEOUT_S": "45"}).sam_timeout_s == 45.0
```

Also extend the phase 2 upgrade path: a database at `user_version` 3 with a plan, a run and a measurement opens at version 4 and reads back.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd worker && uv run pytest tests/test_storage_phase3.py tests/test_config.py -q`
Expected: FAIL (`Direction`, `Setup` and the new repo functions don't exist).

- [ ] **Step 3: Write migration 004, the domain types, the settings and the repo functions**

Migration 004: `ALTER TABLE plans ADD COLUMN` metric, direction, min_effect, checkpoint_s, treatment; tables `setups(experiment_id PRIMARY KEY, body, updated_at)`, `derived`, `notes`, `note_attempts`, `verdicts`, `reviews` (JSON columns as TEXT, an index on `(run_id, t)` for each run table). Triggers in the style of 003: no UPDATE, DELETE or REPLACE on `derived`, `note_attempts`, `verdicts`, `reviews`; on `notes` the only allowed UPDATE sets `t_end` from NULL, every other column unchanged. `setups` is a draft, freely updated. Bump `user_version` to 4.

- [ ] **Step 4: Run them to verify they pass, then the whole suite**

Run: `cd worker && uv run pytest -q`
Expected: all pass (phase 2's 221 plus the new ones).

- [ ] **Step 5: Commit**

```bash
git add worker/argus/storage worker/argus/domain.py worker/argus/config.py worker/tests
git commit -m "feat(storage): plans with a structured prediction, setups, derived numbers, notes, verdicts, reviews"
```

---

### Task 2: `reason()`

**Files:**
- Create: `worker/argus/reason/__init__.py`, `worker/argus/reason/client.py`, `worker/probes/record_reason.py`, `worker/tests/fixtures/reason/note-response.json`
- Test: `worker/tests/test_reason.py`

**Interfaces:**
- Consumes: `Settings` (Task 1), `ModelCallDraft`.
- Produces:
  - `ReasonTask(frozen dataclass)`: `function: str` (`"note"`, `"verdict_draft"`, `"verdict_critique"`, `"describe"`), `experiment_id: str`, `prompt_version: str`, `stable: tuple[str, ...]` (rules, method card, locked plan), `variable: tuple[str, ...]` (summary, MEASUREMENTS block, events, notes, the task's own instructions).
  - `ReasonResult(frozen dataclass)`: `data: dict[str, Any]`, `call: ModelCallDraft`, `model: str`, `fell_back: bool`, `failed_calls: tuple[ModelCallDraft, ...] = ()` (a deep call that fell back reports its failed first attempt here, so it is logged too).
  - `class ReasonError(RuntimeError)`: `.call: ModelCallDraft` (status `"error"`).
  - `async def reason(task: ReasonTask, *, tier: Literal["routine", "deep"], schema: dict, schema_name: str, images: Sequence[bytes] = (), settings: Settings, client: Any = None) -> ReasonResult` — one request: a single user message whose content is every `stable` part, then every `variable` part, as `input_text`, then each image as `input_image` (`data:image/jpeg;base64,…`); `reasoning={"effort": ...}`, `max_output_tokens`, `prompt_cache_key=f"argus:{task.experiment_id}:{tier}:{task.prompt_version}"`, strict `text.format`. On the deep tier, a failure retries once on `deep_fallback_model` at `fallback_effort` and returns `fell_back=True` with the failed attempt in `failed_calls`.
  - `class Reasoner(Protocol)`: `async def __call__(self, task: ReasonTask, *, tier, schema: dict, schema_name: str, images: Sequence[bytes] = ()) -> ReasonResult`; `SettingsReasoner(settings)` implements it with `reason()` and one shared client (closed by `aclose()`, as `SamSegmenter` does). Pipelines take a `Reasoner`, so tests pass a `FakeReasoner`.
  - `reason_client(settings, *, http_client=None)`: `AsyncOpenAI` with `max_retries=0` and `Timeout(settings.reason_timeout_s, connect=5.0)`, as `sam_client` does.
  - Cost from `usage`: `(input − cached) × input price + cached × cached price + output × output price`, per tier's model (`ModelCallDraft.input_tokens`, `cached_tokens`, `output_tokens`, `reasoning_tokens` filled from `usage.input_tokens_details.cached_tokens` and `usage.output_tokens_details.reasoning_tokens`).

- [ ] **Step 1: Record a real response (by hand, about $0.006)**

`worker/probes/record_reason.py` sends one routine note request built from a tiny hand-written block and saves the SDK response as JSON (`response.model_dump()`) to `tests/fixtures/reason/note-response.json`. Check by eye that it holds no key or personal data.

- [ ] **Step 2: Write the failing tests** (a `FakeResponses` returns objects built from the fixture, as `test_sam.py` does)

```python
async def test_a_routine_call_sends_cache_key_effort_and_strict_schema():
    fake = FakeClient(fixture("note-response"))
    result = await reason(TASK, tier="routine", schema=NOTE_SCHEMA, schema_name="ArgusNote",
                          images=[JPEG], settings=SETTINGS, client=fake)
    sent = fake.requests[0]
    assert sent["prompt_cache_key"] == "argus:exp_1:routine:v1" and sent["reasoning"] == {"effort": "minimal"}
    assert sent["max_output_tokens"] == 4000 and sent["text"]["format"]["strict"] is True
    content = sent["input"][0]["content"]
    assert [c["type"] for c in content][-1] == "input_image" and content[0]["text"] == TASK.stable[0]
    assert result.data["level"] in {"event", "checkpoint", "insight"} and result.call.status == "ok"
    assert result.call.cost_usd == pytest.approx(expected_cost(fixture("note-response"), spark_prices))

async def test_an_incomplete_answer_is_an_error_and_never_parsed():
    fake = FakeClient(fixture("note-response") | {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}})
    with pytest.raises(ReasonError) as failure:
        await reason(TASK, tier="routine", schema=NOTE_SCHEMA, schema_name="ArgusNote", settings=SETTINGS, client=fake)
    assert failure.value.call.status == "error" and "max_output_tokens" in failure.value.call.error

async def test_the_deep_tier_falls_back_to_spark_at_high_effort():
    fake = FakeClient(error=APIStatusError(...), then=fixture("note-response"))
    result = await reason(TASK, tier="deep", schema=NOTE_SCHEMA, schema_name="ArgusNote", settings=SETTINGS, client=fake)
    assert [r["model"] for r in fake.requests] == ["muse-wonder-1.0", "muse-spark-1.3"]
    assert fake.requests[1]["reasoning"] == {"effort": "high"} and result.fell_back and result.failed_calls

def test_only_the_two_model_modules_import_openai():
    importers = {p.relative_to(ARGUS).as_posix() for p in ARGUS.rglob("*.py") if "openai" in imports_of(p)}
    assert importers == {"segment/sam.py", "reason/client.py"}
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd worker && uv run pytest tests/test_reason.py -q`
Expected: FAIL (`argus.reason` doesn't exist).

- [ ] **Step 4: Implement `reason()` and `reason_client()`**

Parse `output_text` with `json.loads` only after `status == "completed"`; a JSON error is a `ReasonError` with the call's cost (the tokens were billed).

- [ ] **Step 5: Run them to verify they pass, then commit**

```bash
git add worker/argus/reason worker/probes/record_reason.py worker/tests/test_reason.py worker/tests/fixtures/reason
git commit -m "feat(reason): reason() over the Responses API with strict JSON, cache keys, cost and deep fallback"
```

---

### Task 3: Prompts, schemas and assembly

**Files:**
- Create: `prompts/routine/note.md`, `prompts/deep/verdict.md`, `prompts/setup/describe.md`, `prompts/recipes/{seed-germination,colour-reaction,foam-height,general}/method.md`, `prompts/schemas/verdict.json`, `prompts/schemas/recipe_draft.json`, `worker/argus/reason/prompts.py`
- Modify: `prompts/system/scientific-rules.md` (rule 1), `prompts/deep/verdict-critique.md`, `prompts/schemas/note.json`, `prompts/schemas/verdict_critique.json`, `prompts/README.md`
- Test: `worker/tests/test_prompts.py`

**Interfaces:**
- Consumes: `Recipe`, `Plan`, `ReasonTask` (Task 2).
- Produces:
  - `PROMPTS_DIR = REPO_ROOT / "prompts"`; `load_prompt(relative: str) -> str` (HTML comments stripped); `load_schema(name: str) -> dict` (`$comment` keys stripped at every level).
  - `prompt_version(recipe: Recipe) -> str`: `"p" + sha256(rules + method card + every schema file)[:10]`, so a prompt edit gives a new cache key.
  - `plan_block(plan: Plan | None) -> str`: `"LOCKED PLAN (version N, locked <iso>)"` plus hypothesis, prediction, threshold, the structured fields as refs (`{ref:plan:min_effect}`, `{ref:plan:checkpoint}`) and rivals; `"NO LOCKED PLAN"` when there is none.
  - `measurements_block(refs: RefTable) -> str`: header `MEASUREMENTS (cite only as {ref:<id>})`, then one line per ref, `<id> | <label> | <display>`, sorted by id.
  - `events_block(events, refs) -> str`, `notes_block(notes) -> str` (the last 3 rendered observations; this stands in for the running summary of spec §7.1 until long runs need hourly roll-ups).
  - `note_task(level, recipe, plan, refs, events, notes, *, rejected: Sequence[str] = ()) -> ReasonTask` with `function="note"`; when `rejected` is given, the variable part ends with `"Your previous answer was rejected: <reasons>. Fix exactly these."`.
  - `verdict_task(recipe, plan, refs, *, checks: Sequence[str], allowed: Sequence[str], events, notes) -> ReasonTask` (`function="verdict_draft"`; `checks` are the ceiling's rendered lines, `allowed` the allowed verdict names) and `critique_task(recipe, plan, refs, *, checks, allowed, draft: dict) -> ReasonTask` (`function="verdict_critique"`), both called by Task 7; `describe_task(experiment, recipe, words: str) -> ReasonTask` (`function="describe"`, the recipe's measurement ids filled into the schema's `metric` enum).
  - `snapshot_jpeg(image_bgr, px=768) -> bytes`.
  - `note.json` v2: same fields as v1 except `numbers_used` becomes `refs_used: [string]`; descriptions say "cite numbers only as {ref:<id>}". `verdict.json`: `verdict` (the 4 levels), `explanation`, `rivals: [{name, status: "ruled_out"|"open"|"unclear", reason}]`, `what_would_change_it`, `confidence`, `confidence_reason`, `refs_used`, `evidence_ids`. `verdict_critique.json` adds `refs_used`. `recipe_draft.json`: `hypothesis`, `prediction`, `threshold`, `metric` (enum filled at call time with the recipe's measurement ids), `direction`, `min_effect`, `checkpoint_s`, `treatment`, `factor`, `factor_unit`, `conditions: [{value, role}]`, `rivals`, `question_for_researcher`.
  - Method cards: under 250 words each: what the recipe measures and its unit, the typical curve, what a meaningful change looks like, recipe-specific rivals and their checks. No numbers a note could copy as a measurement.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("name", ["note", "verdict", "verdict_critique", "recipe_draft"])
def test_schemas_are_strict(name):
    for node in objects_in(load_schema(name)):
        assert node["additionalProperties"] is False and set(node["required"]) == set(node["properties"])

def test_the_stable_prefix_comes_first_and_is_identical_across_calls():
    a = note_task("checkpoint", RECIPE, PLAN, refs_at(10.0), [], [])
    b = note_task("event", RECIPE, PLAN, refs_at(20.0), [], [])
    assert a.stable == b.stable and a.stable[0].startswith("# Argus scientific rules")
    assert "MEASUREMENTS" not in "".join(a.stable)  # data never sits in the cached prefix

def test_prompt_version_changes_when_a_prompt_changes(tmp_path, monkeypatch):
    ...  # copy prompts/ to tmp_path, edit the method card, version differs

def test_a_rejected_note_is_retried_with_its_reasons():
    task = note_task("event", RECIPE, PLAN, refs_at(10.0), [], [], rejected=["unknown ref: x1"])
    assert "unknown ref: x1" in task.variable[-1]

def test_the_rules_say_numbers_come_only_as_refs():
    assert "{ref:" in load_prompt("system/scientific-rules.md")
```

- [ ] **Step 2: Run them to verify they fail**, **Step 3: write the prompt files and `prompts.py`**, **Step 4: run them to verify they pass**

Run: `cd worker && uv run pytest tests/test_prompts.py -q`

- [ ] **Step 5: Commit**

```bash
git add prompts worker/argus/reason/prompts.py worker/tests/test_prompts.py
git commit -m "feat(prompts): note, verdict and setup prompts with ref tokens; method cards; strict schemas"
```

---

### Task 4: Refs and the noise floor

**Files:**
- Create: `worker/argus/analyze/__init__.py`, `worker/argus/analyze/noise.py`, `worker/argus/claims/__init__.py`, `worker/argus/claims/refs.py`
- Test: `worker/tests/test_refs.py`

**Interfaces:**
- Consumes: repos (measurements, events, vessels, plan), `format_measurement`, `DerivedDraft` (Task 1).
- Produces:
  - `noise_floor(rows: Sequence[Measurement], *, still_until: float) -> float | None`: the standard deviation (ddof 1) of a vessel's readings of one metric with `t ≤ still_until`; `None` with fewer than 3 readings. `still_until` is the first `intervention`, `rule` or watcher `change` event's `t` for that vessel, else 10 % of the run so far (at least the first 3 readings).
  - `Ref(frozen dataclass)`: `id`, `label`, `value: float`, `uncertainty: float`, `unit: str`, `display: str`, `kind: str`, `t: float | None`, `vessel_id: str | None`, `evidence: tuple[str, ...]`.
  - `RefTable`: `refs: dict[str, Ref]`; `get(id)`; `ids()`.
  - `build_refs(db, run_id, t: float, *, recipe, plan) -> RefTable`, ids short and stable within a call:
    - `m:<label>:<metric>`: the vessel's latest reading of each recipe metric at or before `t` (its measurement id is the evidence);
    - `chg:<label>:<metric>`: change since the vessel's first reading (± in quadrature);
    - `diff:<label>:<metric>`: treatment vessel minus the mean of the control vessels' latest readings (± in quadrature, the control mean's ± as the standard error of the readings when there are 2 or more controls);
    - `noise:<metric>`: the median over vessels of the noise floor;
    - `ev:<n>`: the n-th event's time (`display` `formatRunTime`-style, e.g. "41 h" or "3:05", evidence = the event id);
    - `plan:min_effect`, `plan:checkpoint`; `run:t` (time now).
  - Every `chg`, `diff` and `noise` ref is written as a `derived` row (kind `change`, `difference`, `noise_floor`; `inputs` = the measurement ids used; `method_version` `change/1`, `difference/1`, `noise_floor/1`), and its `evidence` holds that row's id.

- [ ] **Step 1: Write the failing tests** (on stored measurements built with phase 2's repos)

```python
def test_change_and_difference_carry_their_uncertainty(db, two_by_two_run):
    refs = build_refs(db, RUN, 600.0, recipe=COLOUR, plan=PLAN)
    c = refs.get("chg:C:delta_e")
    assert c.value == pytest.approx(25.0 - 0.5) and c.uncertainty == pytest.approx(hypot(0.06, 0.05))
    d = refs.get("diff:C:delta_e")
    assert d.value == pytest.approx(25.0 - mean([4.0, 5.0])) and d.display.endswith("dE00")
    assert all(db_row_exists(db, "derived", e) for e in d.evidence)

def test_the_noise_floor_comes_from_the_still_period(db, run):
    ...  # 6 readings 0.5 ± small before a change event at t=60, then big jumps
    assert noise_floor(rows, still_until=60.0) == pytest.approx(statistics.stdev(first_six))

def test_a_run_without_controls_has_no_differences(db, single_vessel_run):
    refs = build_refs(db, RUN, 600.0, recipe=COLOUR, plan=PLAN)
    assert not [r for r in refs.ids() if r.startswith("diff:")] and "m:A:delta_e" in refs.ids()

def test_refs_render_like_the_ui(db, two_by_two_run):
    assert build_refs(db, RUN, 600.0, recipe=COLOUR, plan=PLAN).get("m:C:delta_e").display == "25.6 ± 0.1 dE00"
```

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest tests/test_refs.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(claims): refs a model may cite, stored as derived numbers; noise floor from the still period"`

---

### Task 5: The claim checker, the renderer and code-written notes

**Files:**
- Create: `worker/argus/claims/checker.py`, `worker/argus/claims/fallback.py`
- Test: `worker/tests/test_claims.py`

**Interfaces:**
- Consumes: `RefTable` (Task 4), `VerdictLevel`.
- Produces:
  - `TOKEN = re.compile(r"\{ref:([A-Za-z0-9_:.\-]+)\}")`.
  - `MODEL_NAMES = ("SAM 3.1", "Muse Spark 1.3", "Muse Wonder 1.0", "muse-spark-1.3", "muse-wonder-1.0", "sam-3.1")` — stripped before the digit check.
  - `NUMBER_WORDS`: two … twenty, thirty, forty, fifty, sixty, seventy, eighty, ninety, hundred, thousand, million, twice, double, triple, half, percent (whole words, any case), plus the `%` sign.
  - `check_text_fields(data: dict, fields: Sequence[str], refs: RefTable) -> list[str]`: reasons, empty when clean: `"unknown ref: <id>"`, `"number outside a ref in <field>: '<text>'"`, `"quantity in words in <field>: '<word>'"`.
  - `check_note(data: dict, refs: RefTable, *, allowed: set[VerdictLevel], evidence: set[str]) -> list[str]`: the spec §7.2 order: schema keys present; every token and `refs_used` id in `refs`; no digit or number word outside tokens in `observation`, `interpretation`, `confidence_reason`, `rival_explanations[*]`, `next_step`, `question_for_researcher`; `hypothesis_status` in `allowed` (else `"status above the ceiling: <status>"`); every `evidence_ids` entry in `evidence` (else `"unknown evidence: <id>"`).
  - `render(text: str, refs: RefTable) -> str`: tokens → `display`.
  - `render_note(data, refs) -> dict`: the note's text fields rendered, ready for `Note.body`.
  - `fallback_note(level, refs, *, reason: str) -> dict`: a body written by code from the refs only (one sentence per vessel from `m:` and `chg:` refs, sorted by label), with `"written_by": "code"` and the reason ("the model's answers failed the claim check twice", "notes paused: spend cap").

- [ ] **Step 1: Write the failing tests**

```python
REFS = refs_table({"m:A:delta_e": "3.7 ± 0.1 dE00", "chg:C:delta_e": "25.1 ± 0.1 dE00", "ev:1": "2:05"})

def test_a_clean_note_passes_and_renders():
    note = clean_note(observation="Glass C changed by {ref:chg:C:delta_e} after {ref:ev:1}.", refs_used=["chg:C:delta_e", "ev:1"])
    assert check_note(note, REFS, allowed=ALL, evidence=set()) == []
    assert render_note(note, REFS)["observation"] == "Glass C changed by 25.1 ± 0.1 dE00 after 2:05."

@pytest.mark.parametrize("text, reason", [
    ("Changed by 25 dE.", "number outside a ref in observation: '25'"),
    ("Changed by {ref:chg:Z:delta_e}.", "unknown ref: chg:Z:delta_e"),
    ("Warm water was twice as fast.", "quantity in words in observation: 'twice'"),
    ("About forty minutes later.", "quantity in words in observation: 'forty'"),
    ("A 50% rise.", "number outside a ref in observation: '50'"),
])
def test_numbers_outside_refs_are_rejected(text, reason):
    assert reason in check_note(clean_note(observation=text), REFS, allowed=ALL, evidence=set())

def test_model_names_and_the_word_one_are_allowed():
    assert check_note(clean_note(observation="SAM 3.1 found one glass."), REFS, allowed=ALL, evidence=set()) == []

def test_a_status_above_the_ceiling_is_rejected():
    note = clean_note(hypothesis_status="SUPPORTED")
    assert "status above the ceiling: SUPPORTED" in check_note(note, REFS, allowed={VerdictLevel.TOO_EARLY}, evidence=set())

def test_unknown_evidence_is_rejected():
    assert "unknown evidence: frm_x" in check_note(clean_note(evidence_ids=["frm_x"]), REFS, allowed=ALL, evidence={"frm_a"})

def test_a_code_note_uses_only_refs_and_says_so():
    body = fallback_note("checkpoint", REFS, reason="notes paused: spend cap")
    assert body["written_by"] == "code" and "3.7 ± 0.1 dE00" in body["observation"] and "spend cap" in body["reason"]
```

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest tests/test_claims.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(claims): the claim checker, ref rendering and code-written notes"`

---

### Task 6: Recipe rule events

**Files:**
- Create: `worker/argus/analyze/rules.py`
- Modify: `worker/argus/recipes/model.py` (validate `when` at load), `worker/argus/pipeline/analyzer.py` (evaluate after measurements are stored)
- Test: `worker/tests/test_rules.py`

**Interfaces:**
- Consumes: `Recipe.events`, stored `Measurement` rows, `add_event`.
- Produces:
  - `Rule(frozen dataclass)`: `id`, `metric`, `op` (`">"`, `">="`, `"<"`, `"<="`), `value: float`; `parse_rule(event_id: str, when: str) -> Rule` for exactly `<metric> <op> <number>` (no `eval`); a `ValueError` otherwise.
  - `Recipe` validation: every event's metric is a measurement id of the recipe; a rule whose metric is a not-yet-measured method (`event_count`) is accepted but never fires.
  - `RuleEvaluator(recipe)`: `fired(measurements: Sequence[Measurement]) -> list[tuple[Rule, Measurement]]` returns each rule's first crossing per vessel, once per run (it remembers what fired).
  - `RunContext.rules: RuleEvaluator` (built in `__post_init__`); `analyze_frame` adds one `EventKind.RULE` event per firing (`source="rule"`, `vessel_id`, `t_start` = the measurement's `t`, `detail={"rule": id, "metric": ..., "measurement_id": ...}`, `frame_ids=[frame_id]`) and publishes it.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_rule_fires_once_per_vessel_at_its_first_crossing():
    evaluator = RuleEvaluator(COLOUR)  # switch: delta_e > 20
    assert evaluator.fired([reading("A", 10.0, 3.0)]) == []
    [(rule, m)] = evaluator.fired([reading("A", 11.0, 21.0), reading("B", 11.0, 2.0)])
    assert rule.id == "switch" and m.vessel_id == "A"
    assert evaluator.fired([reading("A", 12.0, 25.0)]) == []

@pytest.mark.parametrize("when", ["delta_e >", "__import__('os')", "delta_e > 20 or 1", "unknown > 3"])
def test_bad_rules_are_refused_at_load(when):
    with pytest.raises(ValidationError):
        Recipe.model_validate(colour_with_event(when))

async def test_the_analyzer_stores_rule_events(ctx_colour, scene_turning_red):
    ...  # analyze frames until delta_e passes 20
    [event] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "rule"]
    assert event.detail["rule"] == "switch" and event.source == "rule"
```

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest tests/test_rules.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(analyze): recipe rule events, parsed without eval, fired once per vessel"`

---

### Task 7: The verdict

**Files:**
- Create: `worker/argus/analyze/ceiling.py`, `worker/argus/pipeline/verdict.py`
- Modify: `worker/argus/pipeline/jobs.py` (a verdict when a run ends after its checkpoint)
- Test: `worker/tests/test_ceiling.py`, `worker/tests/test_verdict.py`

**Interfaces:**
- Consumes: `first_locked_plan`, `build_refs`, `noise_floor`, `check_text_fields`, `verdict_task`/`critique_task` (Task 3), the `Reasoner` (Task 2), `reviews_for_run`.
- Produces:
  - `Check(frozen dataclass)`: `id: str`, `ok: bool | None` (None = open), `text: str` (rendered, for the UI), `refs: tuple[str, ...]`.
  - `VerdictInputs(frozen dataclass)`: `t`, `running: bool`, `checkpoint_s: float | None`, `controls: int`, `treatments: int`, `effects: dict[str, Ref]` (vessel label → its `diff:` ref), `noise: Ref | None`, `min_effect: float`, `direction: Direction`, `rivals: dict[str, Literal["resolved", "open"]]`, `measured: bool` (the run has readings of the plan's metric).
  - `ceiling(inputs) -> tuple[set[VerdictLevel], list[Check]]`, first rule that applies:
    1. no locked plan, or before `checkpoint_s` → {TOO_EARLY};
    2. not `measured`, no control, or fewer than 2 treatment vessels → {INCONCLUSIVE};
    3. any open rival → {INCONCLUSIVE};
    4. a vessel shows a **clear** effect when its `diff` is in the predicted direction, `|diff| > 3 × noise` and `|diff| ≥ min_effect`; a clear effect against the prediction counts as opposed. 2 or more clear and none opposed → {SUPPORTED, INCONCLUSIVE}; none clear → {NOT_SUPPORTED, INCONCLUSIVE}; otherwise {INCONCLUSIVE}.
  - `choose_verdict(allowed, draft: VerdictLevel, critique: VerdictLevel | None) -> VerdictLevel`: the critique's if allowed, else the draft's if allowed, else TOO_EARLY when it is allowed, else INCONCLUSIVE.
  - `verdict_inputs(db, run: Run, *, recipe: Recipe, plan: Plan | None, t: float) -> VerdictInputs` (refs from `build_refs`; `running` from the run's status; rival states from the checks below).
  - `allowed_now(db, run: Run, *, recipe: Recipe, t: float) -> set[VerdictLevel]`: `ceiling(verdict_inputs(...))[0]` with the first locked plan (used by the note writer, Task 8).
  - `rival_states(db, run: Run, rivals: Sequence[str]) -> dict[str, Literal["resolved", "open"]]`, by keyword, case-insensitive: `lighting`/`exposure` → resolved when the run had no "colour not corrected" episode and no `rebaselined` quality event; `camera` → resolved with no `camera_moved` event; `handling`/`intervention` → resolved with no `intervention` event; any rival → resolved by a `reviews` row (`target_kind="rival"`, `target_id=<rival name>`, `action="resolve"`, `comment` = the reason). Everything else stays open.
  - `async def run_verdict(db: Database, broker: EventBroker, settings: Settings, run: Run, *, recipe: Recipe, reasoner: Reasoner) -> Verdict`: inputs → `ceiling` → draft (`verdict_draft`, deep) → `check_text_fields` on `explanation`, `rivals[*].reason`, `what_would_change_it`, `confidence_reason` (one retry with reasons, then a code-written explanation from the checks) → critique (`verdict_critique`, deep; on a check failure the critique is dropped and recorded) → `choose_verdict` → `add_verdict` (provisional while the run is running or no `confirm` review exists) → SSE `verdict`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("inputs, allowed", [
    (inputs(t=300, checkpoint_s=600), {TOO_EARLY}),
    (inputs(controls=0), {INCONCLUSIVE}),
    (inputs(treatments=1), {INCONCLUSIVE}),
    (inputs(measured=False), {INCONCLUSIVE}),
    (inputs(rivals={"temperature": "open"}), {INCONCLUSIVE}),
    (inputs(effects={"C": diff(20.0), "D": diff(18.0)}, noise=1.0, min_effect=5.0), {SUPPORTED, INCONCLUSIVE}),
    (inputs(effects={"C": diff(0.2), "D": diff(-0.3)}, noise=1.0, min_effect=5.0), {NOT_SUPPORTED, INCONCLUSIVE}),
    (inputs(effects={"C": diff(20.0), "D": diff(0.1)}, noise=1.0, min_effect=5.0), {INCONCLUSIVE}),
    (inputs(effects={"C": diff(20.0), "D": diff(-20.0)}, noise=1.0, min_effect=5.0), {INCONCLUSIVE}),
])
def test_the_ceiling_table(inputs, allowed):
    assert ceiling(inputs)[0] == allowed

def test_every_ceiling_says_why_in_words():
    _, checks = ceiling(inputs(controls=0))
    assert any(c.id == "control" and c.ok is False and "no control vessel" in c.text for c in checks)

@pytest.mark.parametrize("allowed, draft, critique, final", [
    ({SUPPORTED, INCONCLUSIVE}, SUPPORTED, INCONCLUSIVE, INCONCLUSIVE),
    ({SUPPORTED, INCONCLUSIVE}, SUPPORTED, NOT_SUPPORTED, SUPPORTED),
    ({INCONCLUSIVE}, SUPPORTED, SUPPORTED, INCONCLUSIVE),
    ({TOO_EARLY}, SUPPORTED, None, TOO_EARLY),
])
def test_choosing_the_final_verdict(allowed, draft, critique, final):
    assert choose_verdict(allowed, draft, critique) is final

async def test_a_verdict_is_drafted_critiqued_checked_and_stored(verdict_ctx):
    reasoner = FakeReasoner([verdict_draft("SUPPORTED", "C rose by {ref:diff:C:delta_e}."), critique("INCONCLUSIVE")])
    verdict = await run_verdict(verdict_ctx, reasoner=reasoner)
    assert verdict.verdict is INCONCLUSIVE and verdict.provisional is True and "dE00" in verdict.body["explanation"]
    assert [c.function for c in model_calls(verdict_ctx)] == ["verdict_draft", "verdict_critique"]

async def test_the_verdict_uses_the_first_locked_plan(verdict_ctx_with_v2_plan):
    verdict = await run_verdict(verdict_ctx_with_v2_plan, reasoner=FakeReasoner([...]))
    assert "version 1" in reasoner.tasks[0].stable[2]

def test_rivals_are_resolved_by_their_checks_or_by_the_researcher(db, run):
    assert rival_states(db, run, ["lighting change"]) == {"lighting change": "resolved"}
    add_event(db, run.id, vessel_id=None, t_start=50.0, kind=EventKind.QUALITY, source="quality",
              detail={"message": "colour not corrected: the card is not in view"})
    assert rival_states(db, run, ["lighting change", "temperature"]) == {"lighting change": "open", "temperature": "open"}
    add_review(db, run.id, ReviewDraft(t=60.0, target_kind="rival", target_id="temperature", action="resolve",
                                       comment="All four glasses sat side by side in one room."))
    assert rival_states(db, run, ["temperature"]) == {"temperature": "resolved"}
```

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest tests/test_ceiling.py tests/test_verdict.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(verdict): the ceiling in code, a Wonder draft and critique, the most cautious allowed choice"`

---

### Task 8: The note writer

**Files:**
- Create: `worker/argus/pipeline/notes.py`
- Modify: `worker/argus/pipeline/analyzer.py` (`RunContext.notes`, `RunContext.reasoner`), `live.py`, `imported.py`, `jobs.py`
- Test: `worker/tests/test_notes.py`

**Interfaces:**
- Consumes: the `Reasoner` (Task 2), `note_task` (Task 3), `build_refs` (Task 4), `check_note`/`render_note`/`fallback_note` (Task 5), `allowed_now` (Task 7), `first_locked_plan` (Task 1: notes, like the verdict, read the plan's locked version 1).
- Produces:
  - `RunContext.reasoner: Reasoner | None` (the jobs' `SettingsReasoner`; `None` turns notes off, as in phase 2's tests) and `RunContext.notes: NoteWriter`.
  - `note_interval_s(recipe) -> float` = `max(120.0, 24 × recipe.analysis_step_s)` (colour reaction 120 s; germination 7,200 s).
  - `NoteWriter(ctx)`:
    - `due(t, new_events) -> Literal["event", "checkpoint"] | None`: a checkpoint note when `t − last_note_t ≥ note_interval_s`; an event note for an `intervention` (any source), a `rule` event, `camera_moved` or `segment_failed` when `t − last_note_t ≥ note_interval_s / 4`; watcher `change` events never trigger a note by themselves.
    - `async def write(t, level, *, image_bgr) -> Note | None`: refs → task → `reason(routine)` → `check_note` → on failure, one retry with the reasons → on a second failure, `fallback_note`. Every answer is saved as a `NoteAttempt` (with its reasons) and every call in `model_calls`. A note whose refs show no `chg:` beyond 3 × its metric's noise floor since the last note, while the last note was also "no change", extends that note's `t_end` instead (`extend_note`) with no model call; the "no change" test is code's, never the model's.
    - Spend cap: when `run_spend_usd + expected` passes the cap, no call; one `fallback_note(reason="notes paused: spend cap")` per run, then silence.
    - Publishes `note` (the saved note) and `note_rejected` (attempt id, reasons) over SSE.
  - Live: `run_live` asks `ctx.notes.due(...)` after each analysis and starts `write` as a background task (at most one in flight; a due note while one is in flight is dropped, not queued). Import: the measure stage calls `due`/`write` inline after each sample.

- [ ] **Step 1: Write the failing tests** (a `FakeReasoner` returns scripted dicts or raises `ReasonError`)

```python
async def test_a_checkpoint_note_is_checked_rendered_and_saved(ctx):
    ctx.reasoner = FakeReasoner([clean_note(observation="C changed by {ref:chg:C:delta_e}.")])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed" and "dE00" in note.body["observation"]
    assert [a.passed for a in note_attempts_for_run(ctx.db, ctx.run.id)] == [True]

async def test_a_rejected_note_is_retried_once_with_its_reasons(ctx):
    ctx.reasoner = FakeReasoner([clean_note(observation="Changed by 25."), clean_note(observation="Changed by {ref:chg:C:delta_e}.")])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed" and "number outside a ref" in ctx.reasoner.tasks[1].variable[-1]
    assert [a.passed for a in note_attempts_for_run(ctx.db, ctx.run.id)] == [False, True]

async def test_two_failures_save_a_code_note(ctx):
    ctx.reasoner = FakeReasoner([ReasonError("incomplete", ERROR_CALL), clean_note(observation="Changed by 25.")])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "fallback" and note.body["written_by"] == "code"
    assert model_call_statuses(ctx) == ["error", "ok"]

async def test_quiet_stretches_collapse_into_one_note(ctx_still):
    first = await ctx_still.notes.write(120.0, "checkpoint", image_bgr=FRAME)
    again = await ctx_still.notes.write(240.0, "checkpoint", image_bgr=FRAME)
    assert again.id == first.id and again.t_end == 240.0 and ctx_still.reasoner.calls == 1

async def test_a_single_vessel_run_still_gets_notes(ctx_one_vessel):
    ctx_one_vessel.reasoner = FakeReasoner([clean_note(observation="A reads {ref:m:A:delta_e}.")])
    note = await ctx_one_vessel.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed"  # no control: no diff refs, and nothing raises

def test_watcher_changes_alone_never_trigger_a_note(ctx):
    assert ctx.notes.due(30.0, [change_event(30.0)]) is None
    assert ctx.notes.due(40.0, [intervention_event(40.0)]) == "event"

async def test_the_spend_cap_pauses_notes_once(ctx_at_cap):
    first = await ctx_at_cap.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert first.check_status == "fallback" and "spend cap" in first.body["reason"]
    assert await ctx_at_cap.notes.write(720.0, "checkpoint", image_bgr=FRAME) is None
    assert ctx_at_cap.reasoner.calls == 0
```

Plus one live-loop test (notes appear while frames keep flowing; a slow reasoner never delays capture, as Task 3 of phase 2's fix pass tested for SAM) and one import test (a 12-sample import with a rule crossing gets one event note and its checkpoint notes, in time order).

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest tests/test_notes.py tests/test_live.py tests/test_import.py -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(pipeline): checked AI notes on events and checkpoints, retried once, collapsed when nothing changes"`

---

### Task 9: Setup, plan, notes and verdict routes

**Files:**
- Create: `worker/argus/api/setup.py`, `worker/argus/api/notes.py`
- Modify: `worker/argus/api/app.py` (register; SSE kinds), `worker/argus/api/runs.py` (`RunCreate.vessels` optional: taken from the saved setup when omitted; `experiment` GET includes the plan versions)
- Test: `worker/tests/test_api_setup.py`, `worker/tests/test_api_notes.py`

**Interfaces:**
- Consumes: Tasks 1–8, `CameraHub`, the jobs' segmenter and reasoner, `calibrate`, `assess`, `measure_vessel`.
- Produces (all under `/api`):
  - `GET /experiments/{id}/setup` → `Setup`; `PUT /experiments/{id}/setup` (body `Setup`) → `Setup`; 409 once the experiment's plan is locked and a run exists.
  - `POST /experiments/{id}/describe` `{words}` → `RecipeDraft` (the `recipe_draft.json` fields; nothing is saved; `model_calls` row with `function="describe"`, no run).
  - `POST /experiments/{id}/preview` `{camera_index | path, video_s}` → `{frame_jpeg_b64, calibration: {card, px_per_mm, rel_uncertainty} | null, quality: {blur, flags}, vessels: [{label, outlines, readings: [{metric, display}]}]}` using the saved setup's vessels and print check; one SAM image call per concept (`function="preview"`). With no vessels saved yet it returns the frame, calibration and quality only, with no SAM call.
  - `GET /experiments/{id}/plan` → `[Plan]`; `PUT /experiments/{id}/plan` (`PlanDraft`) → `Plan`; `POST /experiments/{id}/plan/lock` → `Plan` (422 when `metric`, `direction` or `checkpoint_s` is missing, naming the missing fields).
  - `GET /runs/{id}/notes` → `{notes: [Note], rejected: int}`; `POST /runs/{id}/notes` `{t, tag, text}` → `Note` (`author="researcher"`, `check_status="researcher"`; a tag of `intervention` also adds an `intervention` event with `source="researcher"`).
  - `GET /runs/{id}/verdict` → `Verdict | null`; `POST /runs/{id}/verdict` → `Verdict` (409 with the reason when the run has no locked plan or the spend cap is reached); `POST /runs/{id}/reviews` (`ReviewDraft`) → `Review`.
  - SSE kinds: `note`, `note_rejected`, `verdict` (each with `run_id` and `t`).

- [ ] **Step 1: Write the failing tests** (TestClient with the fake segmenter and `FakeReasoner`)

```python
def test_a_run_started_without_vessels_takes_them_from_the_setup(client, experiment):
    client.put(f"/api/experiments/{EXP}/setup", json=setup_with_video(CLIP, vessels=TWO))
    created = client.post(f"/api/experiments/{EXP}/runs", json={"mode": "imported", "paths": [str(CLIP)]})
    assert [v["label"] for v in created.json()["vessels"]] == ["A", "B"]

def test_the_plan_locks_only_with_its_structured_fields(client, experiment):
    client.put(f"/api/experiments/{EXP}/plan", json=plan(metric=None))
    lock = client.post(f"/api/experiments/{EXP}/plan/lock")
    assert lock.status_code == 422 and "metric" in lock.json()["detail"]

def test_a_researcher_intervention_note_is_also_an_event(client, finished_run):
    client.post(f"/api/runs/{RUN}/notes", json={"t": 30.0, "tag": "intervention", "text": "Added dye"})
    assert any(e["kind"] == "intervention" and e["source"] == "researcher" for e in timeline(client)["events"])

def test_asking_for_a_verdict_at_the_spend_cap_says_why(client, capped_run):
    answer = client.post(f"/api/runs/{RUN}/verdict")
    assert answer.status_code == 409 and "spend cap" in answer.json()["detail"]

def test_describe_returns_a_draft_and_logs_the_call(client, experiment):
    draft = client.post(f"/api/experiments/{EXP}/describe", json={"words": "Does warm water spread dye faster?"}).json()
    assert draft["metric"] in {"delta_e"} and logged_functions(client) == ["describe"]
```

- [ ] **Step 2–4: fail, implement, pass** — `cd worker && uv run pytest -q`
- [ ] **Step 5: Commit** — `git commit -m "feat(api): setup, describe, preview, plan lock, notes, verdict and reviews"`

---

### Task 10: Web data for notes, verdicts, plans and setups

**Files:**
- Modify: `web/lib/types.ts`, `web/lib/api.ts`, `web/lib/run-snapshot.ts`, `web/lib/run-source.ts`
- Create: `web/lib/setup.ts`
- Test: `web/tests/run-snapshot.test.ts` (extend), `web/tests/setup.test.ts`

**Interfaces:**
- Consumes: Task 9's shapes.
- Produces:
  - types `Note`, `Verdict`, `Check`, `Review`, `Plan`, `PlanDraft`, `Setup`, `RecipeDraft`, `Preview`; `RunSnapshot` gains `notes: Note[]` (sorted by t), `rejected: number`, `verdict: Verdict | null`.
  - api: `getNotes`, `postNote`, `getVerdict`, `askVerdict`, `postReview`, `getSetup`, `putSetup`, `describe`, `preview`, `getPlans`, `putPlan`, `lockPlan`, `startRun`, plus phase 2's routes the wizard needs: `getCameras` (`GET /cameras`), `cameraStreamUrl(index)` and `detectVessels(experimentId, {concept, camera_index | path, video_s})`.
  - `SnapshotStore` applies `note` (insert or replace by id, so a collapsed note's new `t_end` updates it), `note_rejected` (count + 1) and `verdict` (replace) in the same batched way as measurements.
  - `lib/setup.ts`: `type StepId = "describe" | "source" | "vessels" | "roles" | "check" | "plan" | "start"`; `stepProblems(step, state): string[]` (empty when the step can be left: source chosen; ≥ 1 vessel; every vessel has a role, at least one control; a card or ruler found in the check; plan has metric, direction and checkpoint); `nextLabel(vessels): string` (A–Z, skipping labels in use).

- [ ] **Step 1: Write the failing tests** (Node's runner)

```ts
test("a collapsed note updates in place", () => { /* note n1, then note n1 with t_end 240 → one note, t_end 240 */ });
test("a rejected note bumps the count without adding a note", () => { /* note_rejected → rejected 1, notes [] */ });
test("a verdict event replaces the verdict", () => { /* two verdict events → the second */ });
test("the roles step needs a role on every vessel and one control", () => {
  assert.deepEqual(stepProblems("roles", stateWith([{ label: "A", role: "treatment" }])), ["Mark at least one vessel as control."]);
});
test("new vessel labels skip the ones in use", () => assert.equal(nextLabel([{ label: "A" }, { label: "C" }]), "B"));
```

- [ ] **Step 2–4: fail, implement, pass** — `cd web && npm test && npm run lint && npm run typecheck`
- [ ] **Step 5: Commit** — `git commit -m "feat(web): notes, verdicts, plans and setups in the data layer"`

---

### Task 11: The notes feed and the researcher's notes

**Files:**
- Create: `web/components/feed/Feed.tsx`, `NoteCard.tsx`, `EvidenceChip.tsx`, `NoteComposer.tsx` (+ CSS modules)
- Modify: `web/app/experiments/[id]/run/RunScreen.tsx` (feed beside the readouts on wide screens, below them under 1100 px)
- Test: browser check

**Interfaces:**
- Consumes: `RunSnapshot.notes`, `playhead`, `postNote`.
- Produces: `Feed({ snapshot, source })`: notes newest first; each card shows author (Argus or You), level or tag, `formatRunTime(t)` (a range when `t_end` is set: "No change 2:00–5:30"), the rendered sections (observation; interpretation; confidence with its reason; rivals; next step labelled "Suggestion"; question), a "Checked" mark for `passed`, "Written by code" with its reason for `fallback`, and evidence chips. A chip shows the ref's display or the frame thumbnail; clicking it moves the playhead to that `t` and selects its vessel. A "Show rejected (n)" line opens nothing yet (the count only; the attempts view is phase 4's validation strip). `NoteComposer`: tag pills (Observation, Intervention, Question), a text field, "at 3:05" bound to the playhead (or "now" when following live), Enter to save; quick buttons "Added something", "Moved a vessel", "Opened the lid" post an intervention.

- [ ] **Step 1: Build the components**, **Step 2: check in the browser** on the live dye run (`run_d29b95d54ef9` has no notes; use Task 15's run or a run made with the fake reasoner in dev): the feed scrolls on its own, chips move the playhead, a typed intervention appears on the timeline's lane at the right time, 1440 / 768 / 390 px, light and dark, no horizontal scroll, keyboard reachable.
- [ ] **Step 3: `cd web && npm run lint && npm run typecheck && npm run build && npm test`**, **Step 4: Commit** — `git commit -m "feat(web): notes feed with evidence chips, researcher notes and quick interventions"`

---

### Task 12: The verdict panel

**Files:**
- Create: `web/components/verdict/VerdictPanel.tsx` (+ CSS)
- Modify: `RunScreen.tsx`
- Test: browser check

**Interfaces:**
- Consumes: `RunSnapshot.verdict`, `askVerdict`, `postReview`, `VerdictChip`.
- Produces: `VerdictPanel({ snapshot })`: "Get a verdict" (disabled with the reason while the run has no locked plan); then the `VerdictChip` (provisional while provisional), the allowed set in words ("Allowed now: Supported or Inconclusive"), each check with ok / open / failed and its text, the explanation, rivals with status and a "Mark resolved" action that asks for one line of reason (a `resolve` review), what would change it, the critique's findings (item, problem, fix), "Fell back to Muse Spark" when it did, and Confirm / Dismiss (reviews; Confirm only after the run ended).

- [ ] **Step 1–2: build, check in the browser** (fake-reasoner verdict in dev, then Task 15's real one), **Step 3: checks**, **Step 4: Commit** — `git commit -m "feat(web): the verdict panel with its checks, rivals, critique and review"`

---

### Task 13: Setup wizard, part 1: describe, source, vessels, roles

**Files:**
- Create: `web/app/experiments/[id]/setup/page.tsx`, `SetupScreen.tsx`, `web/components/setup/{Stepper,DescribeStep,SourceStep,VesselsStep,RolesStep,SetupFrame}.tsx` (+ CSS)
- Modify: `web/components/experiments/ExperimentsTable.tsx` (a draft experiment links to its setup)
- Test: browser check; `web/tests/setup.test.ts` covers the step rules

**Interfaces:**
- Consumes: `getSetup`/`putSetup`, `describe`, `getCameras` (phase 2), `detectVessels` (phase 2's `POST /experiments/{id}/vessels/detect`), `stepProblems`, `nextLabel`.
- Produces:
  - Stepper across the top (7 steps; done, current, locked), Back / Next, Next disabled with the step's problems listed under it. Every change is saved with `putSetup` (debounced 500 ms), so a reload resumes where it was.
  - **Describe:** "What are you testing?" text → `describe` → the draft fills the plan step's fields and the factor and conditions; "Skip" goes on with an empty draft.
  - **Source:** live camera (the camera list with an MJPEG preview of the selected one) or video file paths (one per line) with the time-scale factor and an optional start time.
  - **Vessels:** a frame from the source (`preview` without vessels for the image, or the camera's latest JPEG); "Find vessels" with a concept field (default: the recipe's first concept) draws SAM's proposals with confidence; click a region to keep or drop it; drag on the frame to draw a box; regions get labels A, B, C in reading order.
  - **Roles:** a row per vessel: label, role (control / treatment), condition value (the factor's name and unit shown once above).

- [ ] **Step 1–2: build, check in the browser** at 1440 / 768 / 390 px, light and dark, keyboard only once through, **Step 3: checks**, **Step 4: Commit** — `git commit -m "feat(web): setup wizard: describe, source, vessels and roles"`

---

### Task 14: Setup wizard, part 2: check, plan, lock and start

**Files:**
- Create: `web/components/setup/{CheckStep,PlanStep,StartStep}.tsx` (+ CSS)
- Modify: `SetupScreen.tsx`
- Test: browser check

**Interfaces:**
- Consumes: `preview`, `putPlan`, `lockPlan`, `startRun`, `putSetup`.
- Produces:
  - **Check:** the print-check field (the 100 mm line), "Check the setup" → `preview`: the frame with the regions and SAM's outlines, the card ("Compact card · 3.05 px/mm ± 0.6 %" or "No card: draw a ruler" with a two-click ruler and its length), sharpness and glare per vessel in words, and "What Argus will measure" per vessel (its readings' `display`). Re-check after changes.
  - **Plan:** hypothesis, prediction, threshold (text), then the structured prediction: metric (the recipe's measurements), direction ("Treatment higher than control" / "lower"), treatment (all treatment vessels, or one condition), smallest effect that matters (number + the metric's unit), checkpoint (h:mm of run time), rivals (the recipe's as chips, add or remove).
  - **Lock and start:** a summary; "Lock the plan" (`lockPlan`; shows the lock time and the first 12 characters of its sha256, and that later edits make a new version the verdict ignores); then "Start the run" (`startRun` with the setup's source; a live run opens the Run view, an import shows its progress there).

- [ ] **Step 1–2: build, check in the browser** end to end on the camera with the fake reasoner in dev (lock, start, Run view opens), **Step 3: checks**, **Step 4: Commit** — `git commit -m "feat(web): setup wizard: check with a measurement preview, plan, lock and start"`

---

### Task 15: End to end on a real experiment

**Files:**
- Modify: `docs/knowledge-base/15-decisions-log.md` (D-65 onward: refs and the claim checker as built, note cadence, the ceiling table and rival checks, anything the run teaches), `docs/knowledge-base/17-build-plan.md` (phase 3 evidence), `docs/knowledge-base/16-open-questions.md` (Q-12 if the iodine clock is used)

- [ ] **Step 1: Set up Aymen's fast experiment through the wizard** (2 treatment + 2 control vessels, the card in view, a plan with metric, direction, smallest effect and a checkpoint about 5 minutes in). Expected: describe returns a usable draft; the preview shows the card, the regions and readings; the lock shows its hash; the run starts from the wizard.
- [ ] **Step 2: Watch the run.** Expected: checkpoint notes about every 2 minutes and an event note for the dye going in (intervention) and for each `switch` rule event; every AI note is "Checked" or "Written by code" with a reason; chips land on the right frames; record the counts of notes, attempts, rejections (and their reasons), the reasoning spend and the cache hit rate (`cached_tokens / input_tokens`).
- [ ] **Step 3: Ask for a verdict after the checkpoint (provisional), and again after Stop.** Expected: a ceiling with its checks in words, a Wonder draft and critique, the final within the allowed set; resolve one open rival with a reason and ask again; confirm the final verdict. Record the cost and latency of the draft and critique.
- [ ] **Step 4: Run every check**

```
cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .
cd ../web && npm run lint && npm run typecheck && npm test && npm run build
```

Expected: all pass.

- [ ] **Step 5: Update the decisions log, the build plan and open questions, then commit** — `git commit -m "docs: phase 3 evidence and decisions"`

---

## End of phase

Final whole-branch review (a fresh reviewer on the most capable model, with this plan's Review Focus and the ledger's rulings). Fix Critical and Important findings test-first; ledger the minors. Merge `phase-3` into `main` after Aymen's go-ahead, delete the workspace, and plan phase 4 (fits and statistics as derived numbers, the view catalog and Muse-picked views, the Ax loop, the Results and Next run screens).
