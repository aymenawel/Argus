"""Agreement with a dataset's labels: Argus's readings set against the published values at the same times, kept in
their own table, apart from measurements (evidence is never overwritten)."""

import sqlite3

import pytest

from argus.analyze.agreement import agreement
from argus.domain import MeasurementDraft, ReferenceValueDraft, Role, RunMode, RunSource, SourceKind, VesselDraft
from argus.storage.repos import (
    add_measurements,
    add_reference_values,
    add_vessels,
    create_run,
    reference_values_for_run,
)

TIMES = [0.0, 1800.0, 3600.0, 5400.0]
LABELS = [0, 1, 3, 5]
ARGUS = [0, 1, 2, 5]


@pytest.fixture
def plate(db, exp):
    run = create_run(db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.IMAGES, manifest="m.json"))
    drafts = [
        VesselDraft(label=label, role=role, roi=[(0, 0), (9, 0), (9, 9)])
        for label, role in (("A1", Role.CONTROL), ("B1", Role.TREATMENT))
    ]
    vessels = {v.label: v for v in add_vessels(db, run.id, drafts)}
    return db, run, vessels


def measure(db, run, vessel, values, times=TIMES):
    rows = [
        MeasurementDraft(
            vessel_id=vessel.id,
            frame_id=None,
            t=t,
            metric="germinated",
            value=v,
            uncertainty=0.0,
            unit="count",
            method_version="touching_count/1",
        )
        for t, v in zip(times, values, strict=True)
    ]
    add_measurements(db, run.id, rows)


def label(db, run, vessel, values):
    rows = [
        ReferenceValueDraft(vessel_id=vessel.id, t=t, metric="germinated", value=v, source="Test plates")
        for t, v in zip(TIMES, values, strict=True)
    ]
    add_reference_values(db, run.id, rows)


def test_readings_are_set_against_the_labels_at_the_same_times(plate):
    db, run, vessels = plate
    for vessel in vessels.values():
        measure(db, run, vessel, ARGUS)
        label(db, run, vessel, LABELS)
    result = agreement(db, run.id, "germinated")
    assert result is not None and result.source == "Test plates" and result.metric == "germinated"
    a1 = result.vessels[0]
    assert (a1.label, a1.frames) == ("A1", 4)
    assert a1.mean_abs_diff == pytest.approx(0.25) and a1.exact_share == pytest.approx(0.75)
    assert a1.t50_labels == 3600.0  # half the final 5 is 2.5: the labels pass it at 3, Argus only at 5
    assert a1.t50_argus == 5400.0
    assert result.mean_abs_diff == pytest.approx(0.25) and result.exact_share == pytest.approx(0.75)


def test_a_run_without_labels_has_no_agreement(plate):
    db, run, vessels = plate
    measure(db, run, vessels["A1"], ARGUS)
    assert agreement(db, run.id, "germinated") is None


def test_a_frame_argus_left_as_a_gap_is_skipped_not_counted_as_zero(plate):
    db, run, vessels = plate
    measure(db, run, vessels["A1"], [0, 1, 5], times=[0.0, 1800.0, 5400.0])  # nothing measured at 3600 s
    label(db, run, vessels["A1"], LABELS)
    a1 = agreement(db, run.id, "germinated").vessels[0]
    assert a1.frames == 3 and a1.mean_abs_diff == 0.0 and a1.exact_share == 1.0


def test_a_reading_within_a_second_of_the_label_pairs_with_it(plate):
    db, run, vessels = plate
    measure(db, run, vessels["A1"], ARGUS, times=[t + 0.5 for t in TIMES])
    label(db, run, vessels["A1"], LABELS)
    assert agreement(db, run.id, "germinated").vessels[0].frames == 4


def test_reference_values_are_their_own_append_only_record(plate):
    db, run, vessels = plate
    label(db, run, vessels["A1"], LABELS)
    assert [r.value for r in reference_values_for_run(db, run.id, "germinated")] == LABELS
    with db.write() as c, pytest.raises(sqlite3.IntegrityError, match="evidence"):
        c.execute("UPDATE reference_values SET value = 9")
