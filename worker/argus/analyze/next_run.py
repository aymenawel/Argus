"""The next run's numbers (D-80), all in code: how many vessels per condition a two-sample t-test needs to see the
plan's smallest effect against this run's own spread, and how long the slowest vessel takes to level off. The model
only explains them. Argus suggests; it never starts a run or moves hardware.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from scipy import stats

from argus.analyze.fits import Fit, vessel_fits
from argus.analyze.levels import level_bounds, suggest_levels
from argus.domain import Direction, Plan, Run, Vessel
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import measurements_for_run, vessels_for_run

ALPHA = 0.05
POWER = 0.8
CAP = 16  # vessels per condition in one run: more and a plate stops being practical
MARGIN = 0.2  # run past the slowest vessel's levelling off by a fifth, so its plateau is measured, not assumed
LEVEL_OFF = 0.95  # "levelled off": 95 % of the fitted plateau


@dataclass(frozen=True)
class NextRunNumbers:
    replicates: int | None
    replicates_reason: str
    hours: float | None
    hours_reason: str
    levels: list[float] = field(default_factory=list)
    levels_reason: str = ""
    levels_unit: str = ""  # the factor's unit, for a numeric factor


def _power(n: int, d: float, alpha: float) -> float:
    """A two-sided two-sample t-test's power with n per group at effect size d, from the noncentral t."""
    df = 2 * n - 2
    crit = float(stats.t.ppf(1 - alpha / 2, df))
    ncp = d * math.sqrt(n / 2)
    return float(stats.nct.sf(crit, df, ncp) + stats.nct.cdf(-crit, df, ncp))


def replicates_needed(
    sd: float | None, min_effect: float | None, *, alpha: float = ALPHA, power: float = POWER, cap: int | None = CAP
) -> int | None:
    """Vessels per condition for a two-sample t-test to detect `min_effect` with this power, given the spread `sd`:
    the smallest n (at least 2) whose power reaches it, at most `cap`. None when the spread is 0 or unknown."""
    if sd is None or min_effect is None or not math.isfinite(sd) or sd <= 0:
        return None
    if not math.isfinite(min_effect) or min_effect <= 0:
        return None
    d = min_effect / sd
    z = float(stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power))
    n = max(2, math.floor(2 * (z / d) ** 2) - 1)  # the normal approximation sits just under the t-test's answer
    while _power(n, d, alpha) < power:
        if cap is not None and n >= cap:
            return cap
        n += 1
    return n if cap is None else min(n, cap)


def replicates_with_reason(sd: float | None, min_effect: float | None, unit: str) -> tuple[int | None, str]:
    """The replicates to suggest and why, in words the Results page shows."""
    if min_effect is None or min_effect <= 0:
        return None, "unknown: the plan sets no smallest effect to detect"
    needed = replicates_needed(sd, min_effect, cap=None)
    if needed is None:
        return (
            None,
            "unknown: the vessels within each condition gave no spread to work from (one vessel each, or all alike)",
        )
    against = f"{min_effect:g} {unit} against a spread of {sd:.2g} {unit} within conditions"
    if needed > CAP:
        return (
            CAP,
            f"{needed} per condition would be needed to see {against}; capped at {CAP} to keep one run practical",
        )
    return needed, f"enough for a two-sample t-test (5 % false alarms, 80 % power) to see {against}"


def time_to_level_off(fit: Fit, share: float = LEVEL_OFF) -> float | None:
    """Hours until a fitted curve reaches `share` of its plateau, from its half-way time, rate and plateau. None for a
    refused or unreached fit, and for a curve that never levels off (exponential, linear)."""
    if not fit.ok or not fit.reached or fit.half_time_h is None:
        return None
    half = fit.half_time_h[0]
    if fit.curve in ("logistic", "gompertz"):
        if fit.rate_per_h is None or fit.plateau is None or fit.plateau[0] <= 0 or fit.rate_per_h[0] <= 0:
            return None
        if fit.curve == "logistic":  # rate = K r / 4
            r = 4 * fit.rate_per_h[0] / fit.plateau[0]
            return half + math.log(share / (1 - share)) / r
        r = math.e * fit.rate_per_h[0] / fit.plateau[0]  # Gompertz: rate = K r / e, half = ti + ln(1 / ln 2) / r
        inflection = half + math.log(math.log(2)) / r
        return inflection - math.log(-math.log(share)) / r
    if fit.curve == "first_order":
        return half * math.log(1 / (1 - share)) / math.log(2)
    return None


def run_length_h(fits: Mapping[str, Fit], *, margin: float = MARGIN) -> float | None:
    """When the slowest vessel's fitted curve levels off, plus `margin`. Refused fits count for nothing; an unreached
    one leaves it unknown (that vessel's curve can't say when it would level off)."""
    fitted = [f for f in fits.values() if f.ok]
    if not fitted or any(not f.reached for f in fitted):
        return None
    times = [time_to_level_off(f) for f in fitted]
    if any(t is None for t in times):
        return None
    return max(t for t in times if t is not None) * (1 + margin)


def pooled_sd(groups: Mapping[str, Sequence[float]]) -> float | None:
    """The spread within groups, pooled over every group with two or more values; None with none."""
    parts = [(len(values) - 1, statistics.variance(values)) for values in groups.values() if len(values) >= 2]
    dof = sum(n for n, _ in parts)
    if dof == 0:
        return None
    return math.sqrt(sum(n * var for n, var in parts) / dof)


def _condition(vessel: Vessel) -> str:
    return f"{vessel.role}:{vessel.condition.value if vessel.condition else ''}"


def _hours(h: float) -> str:
    return f"{h:.0f} h" if h >= 10 else f"{h:.1f} h"


JUDGED = {"level": "level at the checkpoint", "half_time": "half-way time", "rate": "rate"}


def _next_levels(
    vessels: Sequence[Vessel], judged: Mapping[str, float], plan: Plan | None, quantity: str
) -> tuple[list[float], str, str]:
    """Ax's levels for a numeric factor, from each measured vessel's (level, judged value); the factor's unit; why."""
    conditions = [v.condition for v in vessels if v.condition is not None]
    if not conditions:
        return [], "", "the vessels have no condition to vary"
    if not all(isinstance(c.value, float | int) for c in conditions):
        return [], "", f"{conditions[0].factor} isn't numeric, so there are no levels to search"
    unit = next((c.unit for c in conditions if c.unit), None) or ""
    tested = [(float(v.condition.value), judged[v.id]) for v in vessels if v.condition is not None and v.id in judged]
    if len({level for level, _ in tested}) < 2:
        return [], unit, "at least two tested levels are needed to search for the next ones"
    bounds = level_bounds([level for level, _ in tested])
    minimize = plan is not None and plan.direction is Direction.LOWER
    try:
        levels = suggest_levels(tested, minimize=minimize, bounds=bounds)
    except Exception as error:  # noqa: BLE001 - whatever breaks inside Ax, the rest of the suggestion stands
        return [], unit, f"the level search failed: {error}"
    goal = "lowest" if minimize else "highest"
    span = f"{bounds[0]:g} to {bounds[1]:g} {unit}".strip()
    return (
        levels,
        unit,
        f"Ax's picks for the {goal} {JUDGED[quantity]}, searched over {span} from {len(tested)} vessels",
    )


def next_run_numbers(db: Database, run: Run, recipe: Recipe, plan: Plan | None) -> NextRunNumbers:
    """Replicates from the spread of the judged quantity within conditions (each vessel's level at the checkpoint, or
    its fitted half-way time or rate), run length from the fitted curves, from this run only."""
    metric = plan.metric if plan is not None and plan.metric else recipe.main_measurement
    quantity = plan.quantity if plan is not None and plan.quantity in ("half_time", "rate") else "level"
    checkpoint = plan.checkpoint_s if plan is not None else None
    vessels = vessels_for_run(db, run.id)
    fits = vessel_fits(db, run.id, recipe, metric)
    rows = measurements_for_run(db, run.id, metric=metric)
    unit = rows[0].unit if rows else next((m.unit for m in recipe.measurements if m.id == metric), "")
    last_h = max((r.t for r in rows), default=0.0) / 3600

    if quantity == "half_time":
        judged = {vid: f.half_time_h[0] for vid, f in fits.items() if f.ok and f.half_time_h is not None}
        judged_unit = "h"
    elif quantity == "rate":
        judged = {vid: f.rate_per_h[0] for vid, f in fits.items() if f.ok and f.rate_per_h is not None}
        judged_unit = f"{unit}/h"
    else:
        judged = {r.vessel_id: r.value for r in rows if checkpoint is None or r.t <= checkpoint}  # the latest wins
        judged_unit = unit
    groups: dict[str, list[float]] = {}
    for vessel in vessels:
        if vessel.id in judged:
            groups.setdefault(_condition(vessel), []).append(judged[vessel.id])
    replicates, replicates_reason = replicates_with_reason(
        pooled_sd(groups), plan.min_effect if plan is not None else None, judged_unit
    )

    hours = run_length_h(fits)
    levelled = [time_to_level_off(f) for f in fits.values() if f.ok]
    still_rising = any(f.ok and not f.reached for f in fits.values()) or any(
        t is not None and t > last_h for t in levelled
    )
    if quantity == "level" and checkpoint is not None and not still_rising:
        hours = checkpoint / 3600
        hours_reason = (
            "the plan's checkpoint, where the level is judged; this run's readings had levelled off by its end"
        )
    elif hours is not None:
        hours_reason = (
            f"when the slowest vessel's fitted {recipe.curve} curve reaches {LEVEL_OFF * 100:.0f} % of its plateau, "
            f"plus {MARGIN * 100:.0f} %"
        )
    elif not any(f.ok for f in fits.values()):
        hours_reason = f"unknown: no vessel's readings follow a {recipe.curve} curve"
    elif any(f.ok and not f.reached for f in fits.values()):
        hours_reason = (
            f"unknown: a vessel had not reached half its final value by the end; run longer than {_hours(last_h)}"
        )
    else:
        hours_reason = f"unknown: a {recipe.curve} curve never levels off"

    levels, levels_unit, levels_reason = _next_levels(vessels, judged, plan, quantity)
    return NextRunNumbers(replicates, replicates_reason, hours, hours_reason, levels, levels_reason, levels_unit)
