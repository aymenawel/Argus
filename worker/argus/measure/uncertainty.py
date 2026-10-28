"""Noise floor, ± propagation and reporting (JCGM 100:2008 7.2.6, via the uncertainty-and-units skill)."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from uncertainties import ufloat

NOISE_FACTOR = 3.0  # an effect under 3x the noise floor is "not real yet" (spec §6)


def noise_floor(values: Sequence[float]) -> float:
    """Spread (sample SD) of readings of something that should not change."""
    if len(values) < 3:
        raise ValueError("a noise floor needs at least 3 readings")
    return statistics.stdev(values)


def combined_uncertainty(value: float, noise: float, scale_rel: float, *, power: int = 1) -> float:
    """Standard uncertainty of a reading with its noise floor and the calibration scale's relative error.

    `power` is how many lengths the metric multiplies: 1 for lengths, 2 for areas.
    A zero noise floor or scale error stays a plain number (the library warns on zero-spread terms).
    """
    reading = ufloat(value, noise) if noise > 0 else value
    scale = ufloat(1.0, scale_rel) if scale_rel > 0 else 1.0
    return float(getattr(reading * scale**power, "std_dev", 0.0))


def is_real_effect(effect: float, noise: float) -> bool:
    return abs(effect) > NOISE_FACTOR * noise


def format_pm(value: float, uncertainty: float, unit: str) -> str:
    """'19.2 ± 2.6 mm': round the uncertainty first (2 digits if it leads with 1 or 2, else 1), then the value."""
    if not (uncertainty > 0 and math.isfinite(uncertainty)):
        raise ValueError(f"an uncertainty must be a positive number, got {uncertainty}")
    exponent = math.floor(math.log10(uncertainty))
    digits = 2 if int(uncertainty / 10**exponent) in (1, 2) else 1
    decimals = digits - 1 - exponent

    def text(x: float) -> str:
        rounded = round(x, decimals)
        return f"{rounded:.{decimals}f}" if decimals > 0 else str(int(rounded))

    return f"{text(value)} ± {text(uncertainty)} {unit}"
