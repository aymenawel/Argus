# Speed in the verdict, the next run, and Results — design (phase 4)

Date: Oct 30, 2026 · Status: approved by Aymen in chat ("write the spec and you can start building after without
asking") · Builds on branch `open-weights` (phase 3, re-analysis, D-77) · Decisions: D-78, D-79, D-80

## Why

Argus's loop is plan → watch → measure → judge → **next run**. Phases 1–3 and the re-analysis built the first four
steps, and judge them on a level: each treatment vessel's latest reading against the controls'. The Genze re-run
(D-76) showed the gap: the plan said "pearl millet germinates **faster** than rye", the labels show millet germinating
hours earlier, yet both species end near 9 of 10 seeds, so a judgement on end counts can't see the difference the
hypothesis is about. A scientist would compare **speed**: the time to half the final count, or the growth rate, read
off a fitted curve with its uncertainty. Argus also stops at the verdict: it never proposes the next run, the step that
makes it a lab partner rather than a recorder. And nothing shows a run's result on one page for the video.

**Success (by Nov 2, demo-ready):**
- On the Genze plate, a plan predicting a shorter half-way time is judged on fitted half-way times with ±; the page
  shows millet's and rye's curves and times, and the verdict says what they allow.
- Every finished run can get a next-run suggestion: replicates and run length computed in code, the next factor
  levels from Ax when the factor is numeric, the reasons written by the model with every number cited.
- One Results page per experiment shows the curves, the per-vessel times or rates with ±, the verdict, the agreement
  with labels (published data) and the next run.

## Decisions

- **D-78 The plan says what is predicted: a level, a half-way time or a rate.** `PlanDraft.quantity` is `level`
  (today's comparison of latest readings, the default when unset), `half_time` (time to half the fitted plateau) or
  `rate` (the fitted maximum rate). The smallest effect that matters is in that quantity's unit (h for a half-way
  time). Drafting from words chooses it: "faster/sooner/slower" → `half_time`, "grows faster" → `rate`, "more/less
  by the end" → `level`. Unset on old plans means `level`, so locked plans keep their hash.
- **D-79 Speed comes from the recipe's curve, fitted in code.** scipy `curve_fit` fits the recipe's `curve` to each
  vessel's readings, keeping the covariance; the half-way time, rate and plateau carry ± from it
  (`uncertainties.correlated_values`). A fit that fails its checks is reported with its reason, never forced; a
  half-way point past the last reading is "not reached", never extrapolated.
- **D-80 The next run is computed in code and explained by the model.** Code computes replicates per condition and run
  length from the run's own spread and curves; for a numeric factor, Ax (`ax-platform`, approved in KB 11) proposes
  the next levels. Muse Wonder writes why, citing refs, through the claim checker. Argus suggests; it never starts a
  run or touches hardware.
- **Scope cuts:** no curve comparison beyond half-way time and rate (no lag-phase or AUC verdicts), no multi-run
  pooling, no "start this run" button. If time runs short, Ax is cut first: the replicate and run-length suggestion
  stays.

## Components

### 1. The plan's quantity (D-78)

- `PlanDraft.quantity: Literal["level", "half_time", "rate"] | None = None` (None = level). Migration 008 adds the
  `plans.quantity` column. `plan_sha256` leaves out None fields, so plans locked before keep their hash.
- `PUT /plan` refuses `half_time` or `rate` when the recipe's curve has no such quantity (`linear` has no half-way
  time; every curve has a rate).
- Drafting: `prompts/setup/recipe.md` and `prompts/setup/describe.md` explain the choice; the plan blocks of
  `recipe_spec.json` and `recipe_draft.json` gain `quantity` (enum). The wizard's plan step shows it as a choice; the
  draft view says "judged on the half-way time".

### 2. Curve fits — `worker/argus/analyze/fits.py`

- `fit_series(times, values, curve) -> Fit`: the recipe's curve, fitted to one vessel's readings of one metric.
  - logistic `K / (1 + exp(-r (t - t50)))`: plateau K, half-way time t50, max rate `K r / 4`;
  - gompertz `K exp(-exp(-r (t - ti)))`: half-way time `ti + ln(1/ln 2)/r`, max rate `K r / e`;
  - first_order `K (1 - exp(-k t))` (rising) or decay: half-time `ln 2 / k`, rate `K k` at the start;
  - exponential `y0 exp(r t)`: doubling time `ln 2 / r` as its half-way time, rate r;
  - linear `a + b t`: rate b, no half-way time.
- `Fit`: parameters with covariance, `half_time`, `rate`, `plateau` as (value, ±) or None, `reached: bool`, `ok`,
  `reason`, `rmse`, and the curve sampled at 100 points for drawing.
- Checks (refused with a reason): fewer than 6 readings or fewer than 4 distinct values; no convergence; a non-finite
  covariance; a half-way time ± larger than the time span; for growth curves, a series that never rose. Half-way
  point after the last reading: `reached=False`, no value.
- Starting values from the data (plateau = max, midpoint = time of half the max), bounds keep K > 0 and rates > 0.

### 3. Refs and the verdict on speed

- `build_refs` adds, for the plan's metric when the quantity is `half_time` or `rate`: per vessel `t50:<label>:<m>`
  or `rate:<label>:<m>` (a derived row `fit_<curve>/1`, inputs = the readings used), and per treatment vessel its
  difference from the controls' mean, `dt50:` / `drate:` (± in quadrature with the controls' mean ±, as for levels).
- `VerdictInputs.quantity`; the ceiling compares those differences with the same rules (clear: > 2× its ± and at least
  the smallest effect, in the predicted direction; small: its ± rules out the smallest effect). There is no noise
  floor for a fitted quantity: its fit ± takes that place, and the check says so.
- Guards: fewer than 2 treatment vessels or no control with a reached, accepted fit → Inconclusive, the check naming
  each refused fit and why; the never-changed guard (C1) still applies to the readings themselves. A treatment that
  never reached half while the controls did is listed as "not reached", counted for nothing, and named in the check.
- The verdict prompt receives the quantity's refs; the critique sees the fits' checks.

### 4. Next run — `worker/argus/analyze/next_run.py`, `worker/argus/pipeline/next_run.py`

- **Computed in code** (`NextRunNumbers`):
  - replicates per condition: the vessels needed so a two-sample t-test (α 0.05, power 0.8) detects the smallest
    effect, from the observed between-vessel spread of the judged quantity within conditions (pooled SD); capped at
    16 per run (SAM's object limit is per vessel, the cap keeps a plate practical); "unknown" with a reason when
    there is no spread to use;
  - run length: when the slowest vessel's fitted curve reaches 95 % of its plateau, plus 20 %; for `level`, the plan's
    checkpoint unless the readings still rose at the end;
  - next levels (numeric factor only): Ax `Client` with the factor as a range parameter (bounds: the tested range
    widened by half its width, never below 0) and the judged quantity as the objective (minimise for a lower
    prediction), each finished vessel attached as a completed trial; 3 suggested levels. A categorical factor (a
    species) gets none, and says so.
- **Explained by the model:** Muse Wonder (deep tier) gets the numbers as refs (`next:replicates`, `next:hours`,
  `next:level:1..3`) and the verdict's checks, and writes `why`, `change` (what to do differently: e.g. "put both
  species in the same run" when the run-to-run rival is open) and `watch_for` (one if-this-then-that). Claim-checked;
  two failures → a code-written suggestion.
- Stored append-only in `next_runs` (migration 008): numbers, the body, refs, model call ids. `POST
  /runs/{id}/next-run` (finished runs only, 409 otherwise), `GET /runs/{id}/next-run` (latest or null).
- Safety: suggestions never include automatic hardware actions; a factor named after a hazard gets the fixed warning.

### 5. Results page — `web/app/experiments/[id]/results`

- `GET /runs/{id}/fits?metric=` → per vessel: label, role, condition, readings, the fit (ok/reason, half-time ±, rate
  ±, plateau ±, reached) and the sampled curve.
- The page (latest run, a run picker when several): a chart per metric, points per vessel and its fitted curve,
  coloured by condition, the plan's checkpoint as a line, half-way times as ticks; a table of each vessel's half-way
  time, rate and plateau with ±; the verdict card; the agreement table when labels exist; the next-run card with a
  "Suggest the next run" button. Plain SVG (no chart library), light and dark, 1440/768/375 px.
- The Run view links to it ("Results").

## Data flow

Readings (stored) → fits per vessel at verdict or Results time (derived rows) → refs → ceiling → verdict (Wonder
explains). Finished run → next-run numbers (code, Ax) → Wonder explains → stored suggestion → Results page.

## Errors

- A fit refused: the vessel shows "no fit: <reason>" on the page and the verdict check names it; nothing is guessed.
- Ax unavailable or failing: the suggestion keeps replicates and run length, and says the level search failed.
- Not enough data for replicates or run length: "unknown" with the reason.
- A next run asked for a running run: 409 "the run is still going".

## Testing

- Fits on synthetic logistic/gompertz/first-order series with known parameters: half-way time within its ±, the ±
  shrinks with more points; refusals for too few points, flat series, a half-way point beyond the data.
- The ceiling on half-way times: clear faster treatments → Supported allowed; small with tight ± → Not supported
  allowed; an unreached or refused fit → named and Inconclusive.
- Next run: replicates from a known SD and effect match the t-test formula; run length from known curves; Ax suggests
  levels inside the bounds (slow test); a categorical factor gets none.
- API and web: fits route, next-run routes (409, storage), Results page in the browser on the Genze run.
- End to end on the Genze plate: a plan on half-way time (millet lower by at least 2 h, locked before a new import)
  gives fitted times for every dish and a verdict on them; a next run is suggested.

## Review focus

1. A fit that converges to nonsense (plateau far above the data, negative half-way time) must be refused, not shown.
2. Half-way times from vessels with very different plateaus (a dish where only half the seeds sprout) compare times to
   half of different totals; the check should say the plateaus differ.
3. A run imported again into the same experiment: fits and suggestions belong to the run, never mixed across runs.
4. Ax's suggestions must stay inside the bounds and never be presented as measured.
5. The Results page with no fits, no verdict or no labels must still read sensibly.

## Order and effort (about 3 days)

1. Plan quantity + fits + refs + ceiling (1 day). 2. Results page with fits route (0.75 day). 3. Next run without
Ax, then Ax (0.75 day). 4. Genze end to end, docs, final review (0.5 day).
