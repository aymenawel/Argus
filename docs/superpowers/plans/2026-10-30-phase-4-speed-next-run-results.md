# Phase 4: speed in the verdict, the next run, and Results — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Judge a plan on fitted half-way times or rates with ±, suggest the next run (numbers in code, Ax for numeric
factors, reasons by Muse Wonder), and show a run's result on one Results page.

**Architecture:** A pure fitting module (scipy, covariance → ± via `uncertainties`) feeds both `build_refs` (derived
rows and refs `t50:`/`rate:`/`dt50:`/`drate:`) and the verdict ceiling, which compares fitted quantities with the same
rules as levels. A next-run module computes replicates and run length (and Ax levels) and the deep tier explains them
through the claim checker; suggestions are stored append-only. A fits route and a Results page draw it all in SVG.

**Tech Stack:** Python 3.12 (scipy, uncertainties, ax-platform 1.3.1), FastAPI, SQLite; Next.js 16 / React 19 /
TypeScript.

**Spec:** `docs/superpowers/specs/2026-10-30-phase-4-speed-next-run-results-design.md`

## Global Constraints

- The LLM never computes numbers: fits, statistics, replicates, run length and Ax levels are Python; models only
  explain, citing `{ref:<id>}` tokens that pass the claim checker.
- Never overwrite evidence: fits are derived rows; next-run suggestions are append-only (triggers refuse UPDATE/DELETE).
- Every number has a unit and a ±; a refused fit says why; "not reached" is never extrapolated.
- Unset `plan.quantity` means `level`: locked plans keep their `sha256`.
- Half-way times are in hours (unit `h`), rates in the metric's unit per hour (`<unit>/h`); the plan's `min_effect` is
  in that unit.
- Dependencies: `scipy` and `ax-platform==1.3.1` only (both approved in KB 11); no web chart library (plain SVG).
- Repo is public: never commit keys; grep the staged diff for MODEL_API_KEY and BASETEN_API_KEY before each commit.
- No automatic hardware actions; suggestions never start a run.
- Web pages work at 1440/768/375 px in light and dark.

## Review Focus

1. A fit that converges to nonsense (plateau far above the data, a negative or out-of-range half-way time) is refused
   with a reason, never shown or judged. Test in Task 2.
2. Dishes whose plateaus differ a lot (half the seeds sprout in one) are compared on times to half of different
   totals: the verdict's check names the plateau spread. Test in Task 3.
3. Two runs of one experiment: fits, refs and suggestions come from the run asked about only. Test in Task 4.
4. Ax levels stay inside the bounds and are labelled as suggestions, never measurements. Test in Task 6.
5. A Results page with no fits, no verdict, no labels and no suggestion still reads sensibly. Browser check in Task 4.

---

### Task 1: The plan's quantity (D-78)

**Files:**
- Create: `worker/argus/storage/migrations/008_plan_quantity.sql`
- Modify: `worker/argus/domain.py` (`PlanDraft.quantity`), `worker/argus/storage/repos.py` (`PLAN_COLUMNS`),
  `worker/argus/api/setup.py` (`put_plan`), `worker/argus/recipes/draft.py` (`_build`), `worker/argus/api/app.py`
  (draft response), `prompts/setup/recipe.md`, `prompts/setup/describe.md`, `prompts/schemas/recipe_spec.json`,
  `prompts/schemas/recipe_draft.json`, `web/lib/types.ts`, `web/components/setup/PlanStep.tsx`,
  `web/app/experiments/[id]/setup/SetupScreen.tsx` (`EMPTY_PLAN`), `web/components/experiments/RecipeDraftView.tsx`
- Test: `worker/tests/test_plan_quantity.py`

**Interfaces:**
- Produces: `PlanDraft.quantity: Literal["level", "half_time", "rate"] | None = None` (None = level), stored in
  `plans.quantity`, validated by `PUT /plan`, chosen by the drafts.

- [ ] **Step 1: Write the failing tests** — `test_an_unset_quantity_keeps_a_locked_plans_hash` (`plan_sha256(PlanDraft(..., quantity=None)) == plan_sha256` of the same plan built without the field, a stored constant from today's code); `test_a_quantity_is_saved_and_read_back` (PUT plan with `quantity="half_time"` → GET returns it); `test_a_linear_recipe_has_no_half_way_time` (an experiment on the `general` template, whose curve is linear: PUT plan with `quantity="half_time"` → 422 "has no half-way time"; `rate` → 200); `test_a_draft_carries_the_quantity` (`draft_recipe` on an answer with `plan.quantity = "half_time"` → `draft.plan.quantity == "half_time"`).
- [ ] **Step 2: Run** `uv run pytest -q tests/test_plan_quantity.py` — Expected: FAIL.
- [ ] **Step 3: Implement.** Migration 008: `ALTER TABLE plans ADD COLUMN quantity TEXT`. `put_plan` refuses `half_time` on a `linear` curve. Schemas: `quantity` enum `["level","half_time","rate"]` in both plan blocks (required). Prompts: one rule each — "faster/sooner/slower → half_time (lower = faster), a growth or reaction rate → rate, more or less by a time → level; min_effect in hours for half_time". Web: `quantity` in `PlanDraft`, a "Judged on" select (level / half-way time / rate) in the plan step whose help text gives the unit ("h" for half-way time), `EMPTY_PLAN.quantity = null`, the draft view's "Judged on" line names it.
- [ ] **Step 4: Run** the task's tests and `uv run pytest -q tests/test_setup_api.py tests/test_recipe_draft.py tests/test_storage.py tests/test_storage_phase3.py` (schema version now 8) and `cd web && npm test && npm run typecheck` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(plan): the plan says whether it predicts a level, a half-way time or a rate (D-78)`

### Task 2: Curve fits (D-79)

**Files:**
- Create: `worker/argus/analyze/fits.py`
- Modify: `worker/pyproject.toml` (add `scipy>=1.18.1`)
- Test: `worker/tests/test_fits.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) Fit(curve: str, ok: bool, reason: str, reached: bool, half_time_h: tuple[float, float] | None, rate_per_h: tuple[float, float] | None, plateau: tuple[float, float] | None, rmse: float, samples: list[tuple[float, float]])` (samples: 100 `(t_s, y)` points over the data's span; empty when not ok); `fit_series(times_s: Sequence[float], values: Sequence[float], curve: str) -> Fit`; `MIN_POINTS = 6`.
- Curves (t in hours inside the fit): logistic `K/(1+exp(-r(t-t50)))`, half = t50, rate = K·r/4; gompertz `K·exp(-exp(-r(t-ti)))`, half = ti + ln(1/ln 2)/r, rate = K·r/e; first_order rising `K(1-exp(-k t))` when the last third's mean exceeds the first third's, else falling `y0·exp(-k t)`, half = ln 2/k, rate = K·k (rising) or y0·k; exponential `y0·exp(r t)`, half = ln 2/r (doubling time), rate = r·y0; linear `a + b t`, half None, rate b.

- [ ] **Step 1: Write the failing tests** — synthetic data from each curve with known parameters and small seeded noise: `test_a_logistic_series_gives_its_half_way_time_within_its_uncertainty` (K=10, r=0.5/h, t50=20 h, 48 points every 30 min: `abs(fit.half_time_h[0]-20) <= 2*fit.half_time_h[1]` and the ± < 1 h); `test_more_points_tighten_the_half_way_time` (96 vs 24 points: ± smaller); `test_gompertz_and_first_order_and_exponential_recover_their_times`; `test_a_linear_series_has_a_rate_and_no_half_way_time`; `test_too_few_points_are_refused` (5 points → `ok False`, reason mentions "6 readings"); `test_a_flat_series_is_refused` (all zeros → reason "never rose"); `test_a_half_way_point_after_the_last_reading_is_not_reached` (logistic with t50 = 60 h sampled to 30 h → `reached False`, `half_time_h None`); `test_a_fit_that_lands_far_from_the_data_is_refused` (Review Focus 1: series that rises then crashes back to 0 → refused, reason "does not follow a logistic curve"; refuse when the fitted plateau is more than 1.5× the data's maximum, the half-way time falls outside [0, 2× the data span], or the rmse exceeds a quarter of the data's range).
- [ ] **Step 2: Run** `uv run pytest -q tests/test_fits.py` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement `fit_series`** with `scipy.optimize.curve_fit` (`maxfev=20000`, bounds keeping K, r, k > 0), starting values from the data (K = max, t50 = time of half the max), and the ± of each derived quantity from `uncertainties.correlated_values(popt, pcov)`; a non-finite covariance is refused ("the fit's uncertainty can't be computed").
- [ ] **Step 4: Run** the tests — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(analyze): fit the recipe's curve per vessel with honest uncertainty (D-79)`

### Task 3: Refs and the verdict on half-way times and rates

**Files:**
- Modify: `worker/argus/claims/refs.py` (`build_refs`), `worker/argus/analyze/ceiling.py` (`VerdictInputs`, `ceiling`), `worker/argus/pipeline/verdict.py` (`verdict_inputs`)
- Test: `worker/tests/test_verdict_speed.py`

**Interfaces:**
- Consumes: `fit_series`, `Fit` (Task 2); `Plan.quantity` (Task 1).
- Produces: `vessel_fits(db, run_id, recipe, metric, t) -> dict[str, Fit]` in `argus/analyze/fits.py` (vessel id → fit of that run's readings up to t, using the recipe's `curve`); refs `t50:<label>:<metric>` (h) or `rate:<label>:<metric>` (`<unit>/h`) for each vessel with an ok, reached fit (derived row kind `fit`, method `fit_<curve>/1`, inputs = the readings' ids), and per treatment vessel `dt50:<label>:<metric>` / `drate:<label>:<metric>` (difference from the controls' mean, ± in quadrature, as `diff:`); `VerdictInputs.quantity: str = "level"`, `VerdictInputs.fit_notes: tuple[str, ...] = ()`.

- [ ] **Step 1: Write the failing tests** — a run with 2 controls and 2 treatments whose counts follow logistic curves (written as measurements every 30 min for 48 h) and a locked plan with `quantity="half_time"`, `direction="lower"`, `min_effect=2.0` (h), `checkpoint_s=86400`:
  - `test_clearly_faster_treatments_allow_supported` (treatment t50 = 14 h, controls 22 h → allowed contains SUPPORTED; a check "Judged on fitted half-way times" with ok True; refs `dt50:C:germinated` in the verdict's refs);
  - `test_equal_speeds_with_tight_fits_allow_not_supported` (all t50 = 20 h → NOT_SUPPORTED allowed);
  - `test_a_refused_or_unreached_fit_is_named_and_counts_for_nothing` (one treatment flat → its check says "no fit for D: never rose"; only one treatment fitted → INCONCLUSIVE);
  - `test_very_different_plateaus_are_named` (Review Focus 2: control plateaus 10, treatment plateaus 5 and 10 → a check `plateaus` with ok None saying the plateaus differ by more than 25 %);
  - `test_a_level_plan_is_judged_as_before` (same data, quantity None → no `t50:` refs, the existing `noise` check present).
- [ ] **Step 2: Run** `uv run pytest -q tests/test_verdict_speed.py` — Expected: FAIL.
- [ ] **Step 3: Implement.** `build_refs` adds the fit refs only when the plan's quantity is `half_time` or `rate` (for the plan's metric). In `ceiling`, a fitted quantity replaces the noise requirement with the check `fits` ("Judged on fitted half-way times: each carries its fit's ±", ok True) and judges effects with noise 0; `fit_notes` become checks (ok None or False). `verdict_inputs` reads `vessel_fits` for the problems, the controls with fits, and the plateau spread; `registered` for a fitted quantity means "the readings moved at all" (span > 0) in a compared vessel.
- [ ] **Step 4: Run** the task's tests and `uv run pytest -q tests/test_verdict.py tests/test_ceiling.py tests/test_notes.py tests/test_claims.py` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(verdict): judge half-way times and rates from fitted curves`

### Task 4: The fits route and the Results page

**Files:**
- Create: `worker/argus/api/results.py`, `web/app/experiments/[id]/results/page.tsx` (+ `page.module.css`), `web/app/experiments/[id]/results/ResultsScreen.tsx`, `web/components/results/CurveChart.tsx` (+ CSS), `web/components/results/FitTable.tsx` (+ CSS), `web/lib/chart.ts`
- Modify: `worker/argus/api/app.py` (register), `web/lib/api.ts`, `web/lib/types.ts`, `web/app/experiments/[id]/run/RunScreen.tsx` (a "Results" link)
- Test: `worker/tests/test_api_results.py`, `web/tests/chart.test.ts`

**Interfaces:**
- Consumes: `vessel_fits` (Task 3).
- Produces: `GET /api/runs/{run_id}/fits?metric=` → `{"metric", "unit", "curve", "quantity", "vessels": [{"vessel_id", "label", "role", "condition", "readings": [[t_s, value]], "fit": {"ok", "reason", "reached", "half_time_h", "rate_per_h", "plateau", "samples"}}]}` (metric defaults to the locked plan's metric, else the recipe's main measurement); web `getFits(runId, metric?)`, types `FitsView`; `lib/chart.ts`: `linearScale(domain: [number, number], range: [number, number]) -> (x: number) => number`, `niceTicks(min, max, count) -> number[]`.

- [ ] **Step 1: Write the failing tests** — `test_fits_of_a_run_come_from_that_run_only` (Review Focus 3: two runs of one experiment with different curves → each run's fits match its own readings); `test_fits_default_to_the_plans_metric_and_name_refused_fits`; `test_an_unknown_metric_is_a_422`; web `chart.test.ts`: `linearScale([0, 10], [0, 100])(5) === 50`, `niceTicks(0, 47, 5)` gives round steps covering the range.
- [ ] **Step 2: Run** them — Expected: FAIL.
- [ ] **Step 3: Implement** the route and the page: latest run (picker when several); per metric chart (points per vessel, fitted curve, colour by condition, the checkpoint as a dashed line, half-way ticks); `FitTable` (vessel, condition, half-way time ±, rate ±, plateau ±, "no fit: <reason>" / "not reached"); the verdict summary (chip + allowed + checks) via `getVerdict`; `AgreementTable` when labels exist; a next-run slot (Task 5 fills it). Empty states for no run, no fits, no verdict (Review Focus 5). Run view header gets a "Results" link.
- [ ] **Step 4: Run** `uv run pytest -q tests/test_api_results.py` and `cd web && npm test && npm run lint && npm run typecheck`, then **check in the browser** on the Genze run at 1440/768/375 in light and dark, including a run with no fits — Expected: PASS and readable.
- [ ] **Step 5: Commit** — `feat(results): fitted curves, half-way times and the verdict on one page`

### Task 5: The next run, computed and explained (D-80, without Ax)

**Files:**
- Create: `worker/argus/analyze/next_run.py`, `worker/argus/pipeline/next_run.py`, `worker/argus/api/next_run.py`, `worker/argus/storage/migrations/009_next_runs.sql`, `prompts/deep/next-run.md`, `prompts/schemas/next_run.json`, `web/components/results/NextRunCard.tsx` (+ CSS)
- Modify: `worker/argus/domain.py` (`NextRunDraft`, `NextRun`), `worker/argus/storage/repos.py` (`add_next_run`, `latest_next_run`), `worker/argus/api/app.py`, `web/lib/api.ts`, `web/lib/types.ts`, `ResultsScreen.tsx`
- Test: `worker/tests/test_next_run.py`

**Interfaces:**
- Consumes: `vessel_fits`, `build_refs`, the claim checker, `reasoner(tier="deep")`.
- Produces: `replicates_needed(sd: float, min_effect: float, *, alpha=0.05, power=0.8, cap=16) -> int | None` (two-sample t-test, iterated with t quantiles, at least 2; None when sd is 0 or unknown); `run_length_h(fits: Mapping[str, Fit], *, margin=0.2) -> float | None` (slowest vessel's time to 95 % of its plateau, + margin); `NextRunNumbers(replicates: int | None, replicates_reason: str, hours: float | None, hours_reason: str, levels: list[float], levels_reason: str)`; `suggest_next_run(db, run, recipe, reasoner, settings) -> NextRun` (raises `NextRunRefused` while the run is running); routes `POST/GET /api/runs/{run_id}/next-run`; refs `next:replicates` (count), `next:hours` (h), `next:level:<i>` (factor unit) added to the run's refs for the model.

- [ ] **Step 1: Write the failing tests** — `test_replicates_match_the_t_test` (sd 2 h, effect 2 h → 17, so capped at 16 with the reason saying so; sd 1, effect 2 → 6); `test_no_spread_means_unknown_replicates`; `test_run_length_is_when_the_slowest_curve_plateaus` (logistic K, r, t50 → t50 + ln(19)/r, × 1.2); `test_a_finished_run_gets_a_checked_suggestion` (FakeReasoner answer citing `{ref:next:replicates}` → stored, rendered, 201; GET returns it); `test_an_answer_with_free_numbers_is_retried_then_written_by_code`; `test_a_running_run_gets_409`; `test_next_runs_are_evidence` (UPDATE raises).
- [ ] **Step 2: Run** `uv run pytest -q tests/test_next_run.py` — Expected: FAIL.
- [ ] **Step 3: Implement.** Pooled SD of the judged quantity within conditions (latest level, or fitted half-way time / rate); prompt and schema (`why`, `change`, `watch_for`, `refs_used`), text fields claim-checked like notes; two failures → a code-written body listing the numbers; migration 009 with no-update/no-delete triggers; `NextRunCard` (numbers with units, the reasons, "Suggest the next run" button, "Suggested, not measured" label).
- [ ] **Step 4: Run** the tests, `uv run pytest -q tests/test_api_results.py`, and the web checks — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(next-run): replicates and run length in code, reasons by Muse Wonder (D-80)`

### Task 6: Ax for a numeric factor

**Files:**
- Create: `worker/argus/analyze/levels.py`
- Modify: `worker/pyproject.toml` (`ax-platform==1.3.1`), `worker/argus/analyze/next_run.py` (levels), `worker/argus/pipeline/next_run.py`
- Test: `worker/tests/test_levels.py`

**Interfaces:**
- Produces: `suggest_levels(tested: Sequence[tuple[float, float]], *, minimize: bool, bounds: tuple[float, float], count: int = 3, seed: int = 0) -> list[float]` ((level, outcome) per finished vessel; Ax `ax.api.client.Client`, one range parameter, each pair attached and completed as a trial); `level_bounds(levels: Sequence[float]) -> tuple[float, float]` (tested range widened by half its width, never below 0).

- [ ] **Step 1: Write the failing tests** — `test_bounds_widen_the_tested_range_and_stay_non_negative` (levels 20, 40 → (10, 50); 0, 10 → (0, 15)); `test_ax_suggests_levels_inside_the_bounds` (Review Focus 4: 6 attached trials of a quadratic outcome → 3 levels, all inside the bounds); `test_a_categorical_factor_gets_no_levels` (conditions "rye"/"pearl millet" → `levels == []`, reason "the factor isn't numeric").
- [ ] **Step 2: Run** `uv run pytest -q tests/test_levels.py` — Expected: FAIL.
- [ ] **Step 3: Implement** with Ax 1.x (KB 11 example); a failure inside Ax leaves `levels` empty with the reason "the level search failed: <error>".
- [ ] **Step 4: Run** the tests and `uv run pytest -q tests/test_next_run.py` — Expected: PASS.
- [ ] **Step 5: Commit** — `feat(next-run): Ax suggests the next levels of a numeric factor`

### Task 7: The Genze plate on speed, end to end; docs

**Files:**
- Modify: `docs/knowledge-base/15-decisions-log.md` (D-78, D-79, D-80), `docs/knowledge-base/08-science-rigor.md` (verdict on fitted quantities), `docs/knowledge-base/17-build-plan.md` (progress and evidence), `docs/knowledge-base/18-glossary.md` (half-way time, fit, next run)

- [ ] **Step 1: Run it for real.** With the worker restarted: a new experiment from "I'll test whether pearl millet germinates faster than rye" in the dialog; check the drafted plan picks `half_time` (lower = faster) or set it; checkpoint 24 h; lock; import the Genze manifest (labels → the recipe's count). Check: every dish has a fit (or a named refusal), the verdict is judged on half-way times, a next run is suggested, and the Results page shows it at 1440/768/375. Record numbers and spend.
- [ ] **Step 2: Run every check** — `cd worker && uv run pytest -q && uv run ruff check . && uv run ruff format --check .`; `cd web && npm run lint && npm run typecheck && npm test && npm run build` — Expected: all pass.
- [ ] **Step 3: Commit** — `docs: phase 4 decisions and evidence on the Genze plate`
