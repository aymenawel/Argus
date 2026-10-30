# 08 · Scientific rigor, verdicts, reproducibility and validation

> Rigor is where Argus beats "AI camera" products. Ideas come from the installed skills (experimental-design, hypothesis-generation, statistical-power, scientific-critical-thinking, uncertainty-and-units). Runtime rules: `prompts/system/scientific-rules.md`.

## Before the run: plan it properly

- **Hypothesis builder:** splits the idea into hypothesis, measurable prediction ("treated seeds reach 50% germination ≥12 h sooner") and success threshold. Observation, hypothesis and evidence are separate fields.
- **Rival explanations up front:** lighting change, evaporation, temperature, position in frame, contamination. Each gets a check (control, sensor, background region).
- **Design-of-experiments planner:** for 2–6 variables, full or fractional factorial, screening, or response-surface designs; shows how many runs each costs. Full factorial = `itertools.product`; Latin hypercube = `scipy.stats.qmc.LatinHypercube`; pull in `pydoe` only for fractional factorial / Plackett-Burman / central composite / Box-Behnken.
- **Replicate calculator:** asks for the smallest effect worth detecting; uses statsmodels power functions; shows a range when there is no prior data. Never "post-hoc power."
- **Randomized layout:** treatments assigned to frame positions at random; block by day/batch for multi-day runs.
- **Blinding:** vessels shown as A, B, C until the run ends.
- **Pre-registration lock:** hypothesis, prediction, threshold frozen with a timestamp at start; later edits allowed but logged; the verdict uses the locked version.

## During the run: keep it honest

- **Measurement self-test (noise floor):** during the first minutes, measure things that should not change (background, card). The spread is the noise floor; an effect smaller than ~3× the noise floor is "not real yet."
- **Control-aware notes:** every note compares treatment with control at the same moment.
- **Drift watch:** background brightness, card color, camera position.

## After the run: judge it like a reviewer

- **Statistics in code:** effect size with confidence interval; t-test / ANOVA or curve-parameter comparison as the design requires; correction for many comparisons. The model explains, never computes.
- **Curve models to fit** (scipy `curve_fit`, keep the covariance for CIs): logistic and Gompertz (growth, germination, wound closure: lag, max rate, plateau), exponential, first-order decay (color fading: rate constant k, half-life), linear (steady rates).
- **Verdict logic** (code computes the inputs; the model writes the explanation):

| Verdict | When |
| --- | --- |
| SUPPORTED | In ≥2 measured treatment vessels, a difference from the controls in the predicted direction that is > 3× the noise floor, > 2× its own ± and ≥ the plan's smallest effect; none against the prediction; no unresolved rival |
| NOT_SUPPORTED | Enough data and replicates, and every treatment's effect either clear against the prediction or ruled below the smallest effect with its ± (difference + 2u < smallest effect). Without a smallest effect, no clear effect is not evidence of none |
| INCONCLUSIVE | Too noisy, too few replicates, or a rival explanation is unresolved |
| TOO_EARLY | Before the planned checkpoint, or no plan locked before the data began (an import's recording start, when given). Written by code: no model is asked |

  Early verdicts during a run are labeled **provisional**.
- **Judging speed (D-78, D-79):** a plan can predict a level, a half-way time or a rate. For the last two, each vessel's readings are fitted to the recipe's curve and the same rules apply to the fitted value (the smallest effect in h or per h), with each effect judged by its own ± (never the readings' noise floor, which is in another unit). A fit's ± covers the fit only, since cumulative readings are autocorrelated, so each treatment's difference also carries the spread between dishes of one condition, and a fitted plan needs 2 controls. Any compared vessel without a fitted value (a refused fit, nothing grown, or still rising at the end) caps the verdict at Inconclusive and is named (D-81); plateaus more than 25 % apart are named too, since half-way times or rates are then measured against different totals. A rising series that starts well above zero is refused: these curves start at zero.
- **Self-critique pass:** deep tier reviews the draft verdict for pseudo-replication, confounding, multiplicity, early stopping, plan drift, over-claiming, unsupported numbers (`prompts/deep/verdict-critique.md`, output `prompts/schemas/verdict_critique.json`).
- **The next run (D-80):** replicates per condition from a two-sample t-test (α 0.05, power 0.8) on this run's spread of the judged quantity within conditions (for a level, the latest readings, the ones the verdict compared), capped at 16 per run; run length from the slowest fitted curve reaching 95 % of its plateau, plus 20 %; for a numeric factor, three levels from Ax. Unknown numbers say why; a run with no locked plan or no readings is refused before any model call (D-82). The model explains them through the claim checker; the page labels them "Suggested, not measured".
- **What-if planning:** likely / better / worse scenario for the next run with a trigger and response each ("if the control also rises, check temperature first"). Written in our own words; the what-if-oracle skill is CC BY-NC-SA and is not copied.

## Uncertainty and units

Every number has a unit and a ±. Noise floor + calibration error feed each measurement; curve parameters keep their CIs. Libraries: `uncertainties` for ± propagation (recommended), `pint` for units (optional; column names like `height_mm` are enough for the hackathon). Rule: round the uncertainty first, then round the value to the same decimal place.

## Evidence and interpretation stay separate

| Layer | Holds | Written by |
| --- | --- | --- |
| Observation | Raw frame, sensor reading, log line, with time and source | Camera, sensors, instruments |
| Measurement and detection | Numbers from observations; events found by rules/models | Argus code |
| Explanation | AI interpretation with links to the rows below | Muse models |
| Researcher review | Confirmed, dismissed or corrected findings; researcher's conclusions | The researcher |

No layer overwrites an earlier one. Dismissed alerts are kept and used to tune triggers. Reports stay **draft until approved**; any claim about cause is the researcher's call.

## Reproducibility and provenance

- **Run record:** brief and locked plan (+ timestamped edits), recipe and version, camera model and settings, calibration results, model names, prompt versions, cost per call, sensor logs, interventions, notes, software version, random seeds.
- **Raw data first:** keyframes and the full measurement table always kept; re-analyze old runs with a newer recipe.
- **Tamper-evident log:** each measurement batch hashed with the previous hash.
- **Exports:** report (methods written from logged settings), CSV, Jupyter notebook that rebuilds figures, RO-Crate package (schema.org JSON-LD), eLabFTW entry (later), highlights video.

## Prove Argus works (validation table for README + one demo slide)

| Check | How | Report |
| --- | --- | --- |
| Measurement accuracy | Measure objects/heights with a ruler, compare with Argus | Mean error in mm |
| Event detection | Stage known events (drop of dye, coin dropped in, light switched) and note true times | Events caught / staged, false alarms per hour |
| Detection delay | Same staged events | Seconds from true time to alert |
| Claim checker | Count notes rejected for numbers that didn't match | Rejected notes and reasons |
| Time saved | Time to check/log a run by hand vs reviewing Argus's timeline | Minutes per run (only once actually measured) |

Test on runs not used to tune thresholds; count whole runs, not frames.
