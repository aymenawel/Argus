"""Curve fits (D-79): the recipe's curve fitted to one vessel's readings, in code. The half-way time, the rate and the
plateau carry ± from the fit's covariance (uncertainties.correlated_values). A fit that fails a check is refused
with its reason, never forced; a half-way point after the last reading, or a curve still far from its plateau
at the end, is "not reached", never extrapolated.
Times go in and out in seconds for samples, and in hours for the half-way time and the rate.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit
from uncertainties import correlated_values, umath

from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import measurements_for_run

MIN_POINTS = 6
MIN_DISTINCT = 4
PLATEAU_LIMIT = 1.5  # a fitted plateau above 1.5 × the highest reading: the curve was still rising at the end
BASELINE_LIMIT = 0.25  # a curve from zero fitted to readings starting this far up (share of their range) misplaces
# its half-way point: a baseline (dough's own height) is not part of the rise
RMSE_LIMIT = 0.25  # residuals above a quarter of the data's range: the curve doesn't describe the series
SAMPLES = 100
GROWTH = ("logistic", "gompertz", "first_order", "exponential")

Pair = tuple[float, float]  # (value, ±)


@dataclass(frozen=True)
class Fit:
    curve: str
    ok: bool
    reason: str = ""
    reached: bool = False
    half_time_h: Pair | None = None
    rate_per_h: Pair | None = None
    plateau: Pair | None = None
    rmse: float = 0.0
    samples: list[tuple[float, float]] = field(default_factory=list)  # (t in s, fitted value) over the data's span


def _refused(curve: str, reason: str) -> Fit:
    return Fit(curve, ok=False, reason=reason)


def _pair(value) -> Pair:
    return float(value.nominal_value), float(value.std_dev)


def _logistic(t, K, r, t50):
    return K / (1 + np.exp(-r * (t - t50)))


def _gompertz(t, K, r, ti):
    return K * np.exp(-np.exp(-r * (t - ti)))


def _rising(t, K, k):
    return K * (1 - np.exp(-k * t))


def _falling(t, y0, k):
    return y0 * np.exp(-k * t)


def _exponential(t, y0, r):
    return y0 * np.exp(r * t)


def _linear(t, a, b):
    return a + b * t


def _model(curve: str, t: np.ndarray, y: np.ndarray) -> tuple[str, Callable, list[float], tuple]:
    """The function to fit, its name for messages, starting values from the data and bounds."""
    span = max(float(t[-1] - t[0]), 1e-6)
    top = max(float(y.max()), 1e-6)
    half_at = float(t[int(np.argmax(y >= top / 2))])
    if curve == "logistic":
        return "logistic", _logistic, [top, 4.0 / span, half_at], ([0, 1e-6, -np.inf], [np.inf, np.inf, np.inf])
    if curve == "gompertz":
        return "Gompertz", _gompertz, [top, 2.0 / span, half_at], ([0, 1e-6, -np.inf], [np.inf, np.inf, np.inf])
    if curve == "first_order":
        third = max(len(y) // 3, 1)
        if float(np.mean(y[-third:])) >= float(np.mean(y[:third])):
            return "first-order", _rising, [top, 3.0 / span], ([0, 1e-6], [np.inf, np.inf])
        return "first-order", _falling, [max(float(y[0]), 1e-6), 3.0 / span], ([0, 1e-6], [np.inf, np.inf])
    if curve == "exponential":
        return "exponential", _exponential, [max(float(y[0]), 1e-6), 1.0 / span], ([1e-9, 1e-9], [np.inf, np.inf])
    if curve == "linear":
        return "linear", _linear, [float(y[0]), (float(y[-1]) - float(y[0])) / span], (-np.inf, np.inf)
    raise ValueError(f"unknown curve: {curve}")


def fit_series(times_s: Sequence[float], values: Sequence[float], curve: str) -> Fit:
    """One vessel's readings of one metric, fitted to the recipe's curve."""
    if len(times_s) < MIN_POINTS:
        return _refused(curve, f"needs at least {MIN_POINTS} readings, has {len(times_s)}")
    order = np.argsort(np.asarray(times_s, float))
    t_s = np.asarray(times_s, float)[order]
    y = np.asarray(values, float)[order]
    t = t_s / 3600.0
    if curve in GROWTH and float(y.max()) <= float(y.min()):
        return _refused(curve, "the readings never rose")
    if len(np.unique(np.round(y, 9))) < MIN_DISTINCT:
        return _refused(curve, f"fewer than {MIN_DISTINCT} distinct readings")
    name, function, p0, bounds = _model(curve, t, y)
    if function in (_logistic, _gompertz, _rising):
        start, rise = float(np.median(y[:3])), float(y.max() - y.min())
        if abs(start) > BASELINE_LIMIT * rise:
            return _refused(
                curve,
                f"the readings start well above zero ({start:.3g}, against a rise of {rise:.3g}): a {name} curve "
                "from zero would misplace the half-way point",
            )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            popt, pcov = curve_fit(function, t, y, p0=p0, bounds=bounds, maxfev=20000)
    except (RuntimeError, ValueError) as error:
        return _refused(curve, f"the {name} fit did not converge ({error})")
    if not np.all(np.isfinite(pcov)):
        return _refused(curve, "the fit's uncertainty can't be computed")
    residuals = y - function(t, *popt)
    rmse = float(math.sqrt(float(np.mean(residuals**2))))
    data_range = float(y.max() - y.min())
    if data_range > 0 and rmse > RMSE_LIMIT * data_range:
        return _refused(curve, f"the series does not follow a {name} curve (residuals too large)")
    p = correlated_values(popt, pcov)

    half = rate = plateau = None
    if function is _logistic:
        K, r, t50 = p
        half, rate, plateau = t50, K * r / 4, K
    elif function is _gompertz:
        K, r, ti = p
        half, rate, plateau = ti + math.log(1 / math.log(2)) / r, K * r / math.e, K
    elif function is _rising:
        K, k = p
        half, rate, plateau = umath.log(2) / k, K * k, K
    elif function is _falling:
        y0, k = p
        half, rate = umath.log(2) / k, y0 * k
    elif function is _exponential:
        y0, r = p
        half, rate = umath.log(2) / r, r * y0
    else:
        rate = p[1]

    t_first, t_last = float(t[0]), float(t[-1])
    reached = True
    if half is not None:
        if half.nominal_value < 0:
            return _refused(curve, f"the {name} fit puts the half-way point before the start")
        if half.nominal_value > t_last:
            reached = False  # the half-way point is after the last reading: not reached, never extrapolated
        elif half.std_dev > t_last - t_first:
            return _refused(curve, "the half-way time's ± is larger than the run")
    if reached and plateau is not None and plateau.nominal_value > PLATEAU_LIMIT * float(y.max()):
        reached = False  # past half-way of a plateau far above the data: still rising, its half-way point unknown

    grid = np.linspace(t_first, t_last, SAMPLES)
    samples = [(float(g * 3600.0), float(v)) for g, v in zip(grid, function(grid, *popt), strict=True)]
    return Fit(
        curve,
        ok=True,
        reached=reached,
        half_time_h=_pair(half) if half is not None and reached else None,
        # a growth curve's rate is K × r: with the plateau unknown, so is the rate
        rate_per_h=_pair(rate) if rate is not None and (reached or plateau is None) else None,
        plateau=_pair(plateau) if plateau is not None and reached else None,
        rmse=rmse,
        samples=samples,
    )


def vessel_fits(db: Database, run_id: str, recipe: Recipe, metric: str, t: float | None = None) -> dict[str, Fit]:
    """Each vessel's fit of this run's readings of `metric` up to t (all of them when t is None)."""
    rows = measurements_for_run(db, run_id, metric=metric, t_to=t)
    by_vessel: dict[str, list] = {}
    for row in rows:
        by_vessel.setdefault(row.vessel_id, []).append(row)
    return {
        vessel_id: fit_series([r.t for r in readings], [r.value for r in readings], recipe.curve)
        for vessel_id, readings in by_vessel.items()
    }
