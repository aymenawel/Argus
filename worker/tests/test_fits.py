"""Curve fits (D-79): the recipe's curve fitted to one vessel's readings, with the half-way time, rate and plateau
carrying ± from the fit's covariance. A fit that fails its checks says why; a half-way point after the last reading
is "not reached", never extrapolated."""

import math

import numpy as np
import pytest

from argus.analyze.fits import fit_series

HALF_HOUR = 1800.0


def series(curve, *, hours=48.0, step_h=0.5, noise=0.2, seed=1):
    """Times in seconds and values from `curve(t_h)` with seeded noise."""
    t_h = np.arange(0.0, hours + 1e-9, step_h)
    rng = np.random.default_rng(seed)
    values = curve(t_h) + rng.normal(0.0, noise, t_h.size)
    return list(t_h * 3600.0), list(values)


def logistic(K=10.0, r=0.5, t50=20.0):
    return lambda t: K / (1 + np.exp(-r * (t - t50)))


def within(estimate, truth, k=2.0):
    value, u = estimate
    return abs(value - truth) <= k * u


def test_a_logistic_series_gives_its_half_way_time_within_its_uncertainty():
    fit = fit_series(*series(logistic()), "logistic")
    assert fit.ok and fit.reached and within(fit.half_time_h, 20.0) and fit.half_time_h[1] < 1.0
    assert within(fit.plateau, 10.0) and within(fit.rate_per_h, 10.0 * 0.5 / 4)
    assert len(fit.samples) == 100 and fit.samples[0][0] == 0.0 and fit.samples[-1][0] == pytest.approx(48 * 3600)


def test_more_points_tighten_the_half_way_time():
    sparse = fit_series(*series(logistic(), step_h=2.0), "logistic")
    dense = fit_series(*series(logistic(), step_h=0.5), "logistic")
    assert sparse.ok and dense.ok and dense.half_time_h[1] < sparse.half_time_h[1]


def test_gompertz_first_order_and_exponential_recover_their_times():
    gompertz = fit_series(*series(lambda t: 10 * np.exp(-np.exp(-0.3 * (t - 15)))), "gompertz")
    assert gompertz.ok and within(gompertz.half_time_h, 15 + math.log(1 / math.log(2)) / 0.3)
    rising = fit_series(*series(lambda t: 8 * (1 - np.exp(-0.2 * t))), "first_order")
    assert rising.ok and within(rising.half_time_h, math.log(2) / 0.2)
    falling = fit_series(*series(lambda t: 8 * np.exp(-0.2 * t), noise=0.05), "first_order")
    assert falling.ok and within(falling.half_time_h, math.log(2) / 0.2)
    growing = fit_series(*series(lambda t: np.exp(0.1 * t), hours=24, noise=0.05), "exponential")
    assert growing.ok and within(growing.half_time_h, math.log(2) / 0.1)


def test_a_linear_series_has_a_rate_and_no_half_way_time():
    fit = fit_series(*series(lambda t: 2 + 0.5 * t), "linear")
    assert fit.ok and fit.half_time_h is None and within(fit.rate_per_h, 0.5)


def test_too_few_points_are_refused():
    times, values = series(logistic())
    fit = fit_series(times[:5], values[:5], "logistic")
    assert not fit.ok and "6 readings" in fit.reason and fit.samples == []


def test_a_flat_series_is_refused():
    fit = fit_series([i * HALF_HOUR for i in range(20)], [0.0] * 20, "logistic")
    assert not fit.ok and "never rose" in fit.reason


def test_a_half_way_point_after_the_last_reading_is_not_reached():
    fit = fit_series(*series(logistic(r=0.15, t50=30.0), hours=24, noise=0.05), "logistic")
    assert fit.ok and not fit.reached and fit.half_time_h is None


def test_a_fit_that_lands_far_from_the_data_is_refused():
    times, values = series(logistic(), noise=0.05)
    crashed = [v if t < 30 * 3600 else 0.0 for t, v in zip(times, values, strict=True)]
    fit = fit_series(times, crashed, "logistic")
    assert not fit.ok and "does not follow a logistic curve" in fit.reason
