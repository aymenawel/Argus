"""Refs a reasoning call may cite, built from stored measurements and events, and the noise floor."""

import statistics
from datetime import UTC, datetime
from math import hypot

import pytest

from argus.analyze.noise import noise_floor
from argus.claims.refs import build_refs, format_run_time
from argus.config import REPO_ROOT
from argus.domain import (
    Condition,
    Direction,
    EventKind,
    MeasurementDraft,
    Plan,
    Role,
    RunMode,
    RunSource,
    SourceKind,
    VesselDraft,
)
from argus.measure.uncertainty import format_measurement
from argus.recipes.loader import load_recipe
from argus.storage.repos import (
    add_event,
    add_measurements,
    add_vessels,
    create_run,
    derived_for_run,
    measurements_for_run,
)

COLOUR = load_recipe(REPO_ROOT / "recipes" / "colour-reaction.toml")
PLAN = Plan(
    experiment_id="exp_1",
    version=1,
    hypothesis="h",
    prediction="p",
    threshold="t",
    rivals=[],
    metric="delta_e",
    direction=Direction.HIGHER,
    min_effect=5.0,
    checkpoint_s=300.0,
    treatment="warm",
    locked_at=datetime(2026, 10, 29, tzinfo=UTC),
)
# Readings (t, value, ±) of delta_e per vessel: two room-temperature controls, two warm treatments.
READINGS = {
    "A": [(0.0, 0.6, 0.05), (300.0, 2.0, 0.05), (600.0, 4.0, 0.05)],
    "B": [(0.0, 0.5, 0.05), (300.0, 3.0, 0.05), (600.0, 5.0, 0.05)],
    "C": [(0.0, 0.5, 0.05), (300.0, 10.0, 0.06), (600.0, 25.6, 0.06)],
    "D": [(0.0, 0.4, 0.05), (300.0, 9.0, 0.06), (600.0, 24.0, 0.06)],
}


def vessel(label, role, condition):
    return VesselDraft(
        label=label,
        role=role,
        condition=Condition(factor="water temperature", value=condition),
        roi=[(0, 0), (10, 0), (10, 10)],
    )


def store(db, run, vessels, readings):
    drafts = []
    for v in vessels:
        for t, value, u in readings[v.label]:
            drafts.append(
                MeasurementDraft(
                    vessel_id=v.id,
                    frame_id=None,
                    t=t,
                    metric="delta_e",
                    value=value,
                    uncertainty=u,
                    unit="dE00",
                    method_version="delta_e/1",
                )
            )
    add_measurements(db, run.id, drafts)


@pytest.fixture
def two_by_two(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    vessels = add_vessels(
        db,
        run.id,
        [
            vessel("A", Role.CONTROL, "room"),
            vessel("B", Role.CONTROL, "room"),
            vessel("C", Role.TREATMENT, "warm"),
            vessel("D", Role.TREATMENT, "warm"),
        ],
    )
    store(db, run, vessels, READINGS)
    return run, vessels


def test_latest_reading_change_and_difference_carry_their_uncertainty(db, two_by_two):
    run, _ = two_by_two
    refs = build_refs(db, run.id, 600.0, recipe=COLOUR, plan=PLAN)
    latest = refs.get("m:C:delta_e")
    assert (
        latest.value == 25.6
        and latest.display == format_measurement(25.6, 0.06, "dE00")
        and latest.kind == "measurement"
    )
    change = refs.get("chg:C:delta_e")
    assert change.value == pytest.approx(25.6 - 0.5) and change.uncertainty == pytest.approx(hypot(0.06, 0.05))
    diff = refs.get("diff:C:delta_e")
    controls = [4.0, 5.0]
    spread = statistics.stdev(controls) / 2**0.5
    measured = hypot(0.05, 0.05) / 2
    assert diff.value == pytest.approx(25.6 - statistics.mean(controls))
    assert diff.uncertainty == pytest.approx(hypot(0.06, hypot(spread, measured)))
    assert diff.display.endswith("dE00") and "diff:A:delta_e" not in refs  # controls get no difference
    stored = {d.id: d for d in derived_for_run(db, run.id)}
    assert set(diff.evidence) <= set(stored) and stored[diff.evidence[0]].kind == "difference"
    assert stored[change.evidence[0]].inputs == [
        m.id for m in measurements_for_run(db, run.id) if m.vessel_id == change.vessel_id and m.t in (0.0, 600.0)
    ]


def test_refs_only_see_what_was_known_at_t(db, two_by_two):
    run, _ = two_by_two
    refs = build_refs(db, run.id, 300.0, recipe=COLOUR, plan=PLAN)
    assert refs.get("m:C:delta_e").value == 10.0


def test_plan_values_events_and_time_are_refs(db, two_by_two):
    run, vessels = two_by_two
    add_event(
        db,
        run.id,
        vessel_id=vessels[2].id,
        t_start=125.0,
        kind=EventKind.RULE,
        source="rule",
        detail={"rule": "switch"},
    )
    add_event(db, run.id, vessel_id=None, t_start=130.0, kind=EventKind.CHANGE, source="watcher", detail={})
    refs = build_refs(db, run.id, 600.0, recipe=COLOUR, plan=PLAN)
    assert refs.get("plan:min_effect").display == "5 dE00" and refs.get("plan:checkpoint").display == "5:00"
    assert refs.get("run:t").display == "10:00"
    events = [refs.get(i) for i in refs.ids() if i.startswith("ev:")]
    assert [e.display for e in events] == ["2:05"]  # watcher changes are too many to cite one by one
    assert events[0].evidence[0].startswith("evt_")


def test_the_noise_floor_comes_from_the_still_period(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    [a] = add_vessels(db, run.id, [vessel("A", Role.CONTROL, "room")])
    still = [0.50, 0.55, 0.45, 0.52, 0.48, 0.50]
    rows = [(i * 10.0, v, 0.01) for i, v in enumerate(still)] + [(60.0 + i * 10.0, 10.0 + i, 0.01) for i in range(6)]
    store(db, run, [a], {"A": rows})
    add_event(db, run.id, vessel_id=a.id, t_start=55.0, kind=EventKind.INTERVENTION, source="researcher", detail={})
    readings = measurements_for_run(db, run.id)
    assert noise_floor(readings, still_until=55.0) == pytest.approx(statistics.stdev(still))
    assert noise_floor(readings[:2], still_until=55.0) is None  # fewer than three readings
    refs = build_refs(db, run.id, 110.0, recipe=COLOUR, plan=PLAN)
    assert refs.get("noise:delta_e").value == pytest.approx(statistics.stdev(still))


def test_a_run_without_controls_has_no_differences(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    [c] = add_vessels(db, run.id, [vessel("C", Role.TREATMENT, "warm")])
    store(db, run, [c], {"C": READINGS["C"]})
    refs = build_refs(db, run.id, 600.0, recipe=COLOUR, plan=None)
    assert not [i for i in refs.ids() if i.startswith("diff:")] and "m:C:delta_e" in refs
    assert "plan:min_effect" not in refs


def test_a_run_with_no_readings_yet_has_only_its_time(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    add_vessels(db, run.id, [vessel("A", Role.CONTROL, "room")])
    assert build_refs(db, run.id, 5.0, recipe=COLOUR, plan=None).ids() == ["run:t"]


@pytest.mark.parametrize(
    "t, span, text", [(0, 0, "0:00"), (125, 600, "2:05"), (3600, 3600, "1:00"), (149_000, 200_000, "41:23")]
)
def test_run_time_reads_like_the_ui(t, span, text):
    assert format_run_time(t, span) == text
