"""The noise floor: how much a reading wobbles while nothing should be changing (spec §6, KB 08).

From the still period before anything happened to the vessel; when that is too short (a hand at the bench in the
first seconds), from the wobble of all its readings: second differences cancel a steady trend, and their median
ignores the few sudden jumps an experiment makes (the dye going in).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from argus.domain import Measurement

MIN_READINGS = 3


def noise_floor(rows: Sequence[Measurement], *, still_until: float) -> float | None:
    """The standard deviation of one vessel's readings of one metric up to `still_until` (a still period);
    None with fewer than three readings to judge from."""
    still = [r.value for r in rows if r.t <= still_until]
    return statistics.stdev(still) if len(still) >= MIN_READINGS else None


MIN_WOBBLE_READINGS = 5
MAD_TO_SD = 1.4826  # a normal distribution's standard deviation per median absolute deviation


def wobble_floor(rows: Sequence[Measurement]) -> float | None:
    """The standard deviation of one vessel's readings estimated from their second differences: a second difference
    of independent readings has 6 times their variance. None with fewer than five readings."""
    values = [r.value for r in rows]
    if len(values) < MIN_WOBBLE_READINGS:
        return None
    second = [abs(values[i + 2] - 2 * values[i + 1] + values[i]) for i in range(len(values) - 2)]
    return MAD_TO_SD * statistics.median(second) / math.sqrt(6)
