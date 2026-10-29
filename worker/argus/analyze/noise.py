"""The noise floor: how much a reading wobbles while nothing should be changing (spec §6, KB 08)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from argus.domain import Measurement

MIN_READINGS = 3


def noise_floor(rows: Sequence[Measurement], *, still_until: float) -> float | None:
    """The standard deviation of one vessel's readings of one metric up to `still_until` (a still period);
    None with fewer than three readings to judge from."""
    still = [r.value for r in rows if r.t <= still_until]
    return statistics.stdev(still) if len(still) >= MIN_READINGS else None
