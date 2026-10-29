"""Refs: the numbers a reasoning call may cite, each with an id the model writes as {ref:<id>} (spec §6, §7.2).

The model never writes a number; code renders each token as its ref's `display`. build_refs() (the numbers for a
run at a time t) writes the derived rows behind the numbers it shows, so every cited number stays traceable.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from argus.analyze.noise import noise_floor, wobble_floor
from argus.domain import DerivedDraft, Measurement, Plan, Role, RunEvent, Vessel
from argus.measure.uncertainty import format_measurement
from argus.recipes.model import Recipe
from argus.storage.db import Database
from argus.storage.repos import add_derived, events_for_run, measurements_for_run, vessels_for_run

NOTABLE = frozenset({"intervention", "rule", "camera_moved", "segment_failed", "interrupted", "spend", "quality"})
MAX_EVENT_REFS = 20
STILL_SHARE = 0.10  # without an event, the first tenth of the run so far counts as still


@dataclass(frozen=True)
class Ref:
    id: str
    label: str
    value: float
    uncertainty: float
    unit: str
    display: str  # what a {ref:<id>} token renders as, formatted like the UI ("25.6 ± 0.1 dE00")
    kind: str  # measurement, change, difference, noise_floor, event, plan, time
    t: float | None
    vessel_id: str | None
    evidence: tuple[str, ...] = ()  # ids of the rows behind it: a measurement, a derived row, an event


@dataclass(frozen=True)
class RefTable:
    refs: Mapping[str, Ref] = field(default_factory=dict)

    def get(self, ref_id: str) -> Ref | None:
        return self.refs.get(ref_id)

    def ids(self) -> list[str]:
        return sorted(self.refs)

    def __contains__(self, ref_id: object) -> bool:
        return ref_id in self.refs


def format_run_time(t: float, span: float | None = None) -> str:
    """Run time as the UI shows it (web/lib/scale.ts): h:mm when the run spans an hour or more, else m:ss."""
    s = max(0.0, t)
    if max(span if span is not None else s, s) >= 3600:
        return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}"
    return f"{int(s // 60)}:{int(s % 60):02d}"


def _quadrature(*values: float) -> float:
    return math.sqrt(sum(v * v for v in values))


def _vessel_label(vessel: Vessel) -> str:
    condition = f", {vessel.condition.value}" if vessel.condition else ""
    return f"Vessel {vessel.label} ({vessel.role.value}{condition})"


def _still_until(vessel_id: str, rows: Sequence[Measurement], events: Sequence[RunEvent], t: float) -> float:
    """The end of the vessel's still period: its first intervention, rule crossing or watcher change; without
    one, the first tenth of the run so far (and at least its first three readings)."""
    marks = [
        e.t_start for e in events if e.kind in ("intervention", "rule", "change") and e.vessel_id in (None, vessel_id)
    ]
    if marks:
        return min(marks)
    third = rows[2].t if len(rows) >= 3 else t
    return max(STILL_SHARE * t, third)


def _measurement_ref(vessel: Vessel, metric: str, last: Measurement) -> Ref:
    return Ref(
        id=f"m:{vessel.label}:{metric}",
        label=f"{_vessel_label(vessel)}: {metric} now",
        value=last.value,
        uncertainty=last.uncertainty,
        unit=last.unit,
        display=format_measurement(last.value, last.uncertainty, last.unit),
        kind="measurement",
        t=last.t,
        vessel_id=vessel.id,
        evidence=(last.id,),
    )


def build_refs(db: Database, run_id: str, t: float, *, recipe: Recipe, plan: Plan | None) -> RefTable:
    """Every number a call at time t may cite: each vessel's latest reading, its change since its first reading,
    each treatment vessel's difference from the controls' mean, the noise floor per metric, notable events, plan
    values and the time now. Changes, differences and noise floors are written as derived rows (evidence)."""
    vessels = vessels_for_run(db, run_id)
    readings = measurements_for_run(db, run_id, t_to=t)
    events = events_for_run(db, run_id, t_to=t)
    refs: dict[str, Ref] = {}
    pending: list[tuple[str, DerivedDraft, float | None, str | None]] = []  # ref id, row, t, vessel id

    for metric in recipe.stored_metrics():
        latest: dict[str, Measurement] = {}
        floors: list[tuple[float, list[str]]] = []
        wobbled = False  # a vessel's floor came from its wobble, not a still period
        for vessel in vessels:
            rows = [r for r in readings if r.vessel_id == vessel.id and r.metric == metric]
            if not rows:
                continue
            first, last = rows[0], rows[-1]
            latest[vessel.id] = last
            refs[f"m:{vessel.label}:{metric}"] = _measurement_ref(vessel, metric, last)
            if len(rows) >= 2:
                change = DerivedDraft(
                    t=t,
                    kind="change",
                    label=f"{_vessel_label(vessel)}: {metric} change since its first reading",
                    value=last.value - first.value,
                    uncertainty=_quadrature(last.uncertainty, first.uncertainty),
                    unit=last.unit,
                    inputs=[first.id, last.id],
                    method_version="change/1",
                )
                pending.append((f"chg:{vessel.label}:{metric}", change, last.t, vessel.id))
            still = _still_until(vessel.id, rows, events, t)
            floor = noise_floor(rows, still_until=still)
            if floor is not None:
                floors.append((floor, [r.id for r in rows if r.t <= still]))
            elif (wobble := wobble_floor(rows)) is not None:  # too short a still period: an event came early
                floors.append((wobble, [r.id for r in rows]))
                wobbled = True

        controls = [latest[v.id] for v in vessels if v.role is Role.CONTROL and v.id in latest]
        if controls:
            values = [c.value for c in controls]
            spread = statistics.stdev(values) / math.sqrt(len(values)) if len(values) >= 2 else 0.0
            measured = _quadrature(*(c.uncertainty for c in controls)) / len(controls)
            mean, u_mean = statistics.fmean(values), _quadrature(spread, measured)
            for vessel in vessels:
                if vessel.role is not Role.TREATMENT or vessel.id not in latest:
                    continue
                mine = latest[vessel.id]
                difference = DerivedDraft(
                    t=t,
                    kind="difference",
                    label=f"{_vessel_label(vessel)}: {metric} minus the controls' mean",
                    value=mine.value - mean,
                    uncertainty=_quadrature(mine.uncertainty, u_mean),
                    unit=mine.unit,
                    inputs=[mine.id, *(c.id for c in controls)],
                    method_version="difference/1",
                )
                pending.append((f"diff:{vessel.label}:{metric}", difference, mine.t, vessel.id))
        if floors:
            noise = DerivedDraft(
                t=t,
                kind="noise_floor",
                label=f"Noise floor of {metric} (median over vessels"
                + (", some from the wobble of all their readings)" if wobbled else ")"),
                value=statistics.median(f for f, _ in floors),
                uncertainty=0.0,
                unit=next(iter(latest.values())).unit,
                inputs=[i for _, ids in floors for i in ids],
                method_version="noise_floor_wobble/1" if wobbled else "noise_floor/1",
            )
            pending.append((f"noise:{metric}", noise, t, None))

    if pending:
        stored = add_derived(db, run_id, [draft for _, draft, _, _ in pending])
        for (ref_id, draft, ref_t, vessel_id), row in zip(pending, stored, strict=True):
            refs[ref_id] = Ref(
                id=ref_id,
                label=draft.label,
                value=draft.value,
                uncertainty=draft.uncertainty,
                unit=draft.unit,
                display=format_measurement(draft.value, draft.uncertainty, draft.unit),
                kind=draft.kind,
                t=ref_t,
                vessel_id=vessel_id,
                evidence=(row.id,),
            )

    notable = [e for e in events if e.kind in NOTABLE][-MAX_EVENT_REFS:]
    for n, event in enumerate(notable, start=1):
        refs[f"ev:{n}"] = Ref(
            id=f"ev:{n}",
            label=f"Time of the {event.kind} event",
            value=event.t_start,
            uncertainty=0.0,
            unit="s",
            display=format_run_time(event.t_start, t),
            kind="event",
            t=event.t_start,
            vessel_id=event.vessel_id,
            evidence=(event.id,),
        )

    if plan is not None and plan.locked_at is not None:
        unit = next((r.unit for r in readings if r.metric == plan.metric), "")
        if plan.min_effect is not None:
            refs["plan:min_effect"] = Ref(
                id="plan:min_effect",
                label="The plan's smallest effect that matters",
                value=plan.min_effect,
                uncertainty=0.0,
                unit=unit,
                display=format_measurement(plan.min_effect, 0.0, unit) if unit else f"{plan.min_effect:g}",
                kind="plan",
                t=None,
                vessel_id=None,
            )
        if plan.checkpoint_s is not None:
            refs["plan:checkpoint"] = Ref(
                id="plan:checkpoint",
                label="The plan's checkpoint (run time)",
                value=plan.checkpoint_s,
                uncertainty=0.0,
                unit="s",
                display=format_run_time(plan.checkpoint_s, max(t, plan.checkpoint_s)),
                kind="plan",
                t=None,
                vessel_id=None,
            )
    refs["run:t"] = Ref(
        id="run:t",
        label="Run time now",
        value=t,
        uncertainty=0.0,
        unit="s",
        display=format_run_time(t, t),
        kind="time",
        t=t,
        vessel_id=None,
    )
    return RefTable(refs)
