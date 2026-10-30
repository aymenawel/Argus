"""Agreement with a published dataset's labels (D-71): each of Argus's readings set against the dataset's value for
the same vessel at the same time. A frame Argus didn't measure is skipped, never counted as zero. Computed in code
from stored rows; nothing here is written back.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from argus.storage.db import Database
from argus.storage.repos import measurements_for_run, reference_values_for_run, vessels_for_run

PAIR_WINDOW_S = 1.0  # a reading pairs with the label taken within a second of it
EXACT = 0.5  # counts that round to the same whole number match exactly


@dataclass(frozen=True)
class VesselAgreement:
    label: str
    mean_abs_diff: float | None  # None when no frame paired
    exact_share: float | None
    t50_argus: float | None  # when Argus's reading first reached half the final label value
    t50_labels: float | None  # when the labels did
    frames: int  # frames with both a reading and a label


@dataclass(frozen=True)
class Agreement:
    metric: str
    source: str
    vessels: list[VesselAgreement]
    mean_abs_diff: float | None  # over every paired frame of every vessel
    exact_share: float | None


def _first_reaching(series: Sequence[tuple[float, float]], level: float) -> float | None:
    return next((t for t, value in series if value >= level), None)


def agreement(db: Database, run_id: str, metric: str) -> Agreement | None:
    """None when the run has no labels for this metric."""
    labels = reference_values_for_run(db, run_id, metric)
    if not labels:
        return None
    readings: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for m in measurements_for_run(db, run_id, metric=metric):
        readings[m.vessel_id].append((m.t, m.value))
    by_vessel: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in labels:
        by_vessel[r.vessel_id].append((r.t, r.value))
    names = {v.id: v.label for v in vessels_for_run(db, run_id)}

    vessels: list[VesselAgreement] = []
    all_diffs: list[float] = []
    for vessel_id, series in by_vessel.items():
        series.sort()
        mine = sorted(readings.get(vessel_id, []))
        pairs = []
        for t, expected in series:
            near = [(abs(t - tm), value) for tm, value in mine if abs(t - tm) <= PAIR_WINDOW_S]
            if near:
                pairs.append((t, min(near)[1], expected))
        diffs = [abs(got - expected) for _, got, expected in pairs]
        all_diffs += diffs
        half = series[-1][1] / 2
        vessels.append(
            VesselAgreement(
                label=names.get(vessel_id, vessel_id),
                mean_abs_diff=sum(diffs) / len(diffs) if diffs else None,
                exact_share=sum(d < EXACT for d in diffs) / len(diffs) if diffs else None,
                t50_argus=_first_reaching([(t, got) for t, got, _ in pairs], half) if half > 0 else None,
                t50_labels=_first_reaching(series, half) if half > 0 else None,
                frames=len(pairs),
            )
        )
    vessels.sort(key=lambda v: v.label)
    return Agreement(
        metric=metric,
        source=labels[0].source,
        vessels=vessels,
        mean_abs_diff=sum(all_diffs) / len(all_diffs) if all_diffs else None,
        exact_share=sum(d < EXACT for d in all_diffs) / len(all_diffs) if all_diffs else None,
    )
