"""The README's validation table (D-86): every number printed by code from stored records, naming its run."""

import pytest

from argus.analyze.validation import Row, render_table, validation_rows
from argus.config import REPO_ROOT
from argus.domain import (
    CalibrationDraft,
    DerivedDraft,
    ModelCallDraft,
    NoteAttemptDraft,
    NoteDraft,
    ReferenceValueDraft,
    RunMode,
    RunSource,
    RunStatus,
    Setup,
    SourceKind,
)
from argus.measure.uncertainty import format_measurement
from argus.recipes.loader import load_all
from argus.storage import repos
from tests.records import finished_run


@pytest.fixture
def recipes():
    return load_all(REPO_ROOT / "recipes")


@pytest.fixture
def run(db, tmp_path):
    return finished_run(db, tmp_path / "data")


def results(db, recipes, run, check: str) -> list[str]:
    return [r.result for r in validation_rows(db, recipes, [run.id]) if r.check == check]


def calibration(card: str, print_scale: float = 1.0) -> CalibrationDraft:
    return CalibrationDraft(t=0.0, card=card, mm_per_px=0.2, rel_uncertainty=0.01, print_scale=print_scale)


def test_rows_name_their_run(db, recipes, run):
    assert {r.run for r in validation_rows(db, recipes, [run.id])} == {f"Dye in warm and room water ({run.id})"}


def test_scale_from_a_card_with_its_print_check(db, recipes, run):
    repos.add_calibration(db, run.id, calibration("standard", print_scale=0.98))
    scale = format_measurement(0.2, 0.002, "mm/px")
    assert results(db, recipes, run, "Scale") == [f"standard card · {scale} · print check 98.0 mm of 100 mm"]


def test_scale_from_dish_rims(db, recipes, run):
    repos.add_calibration(db, run.id, calibration("dish"))
    repos.save_setup(db, run.experiment_id, Setup(dish_diameter_mm=90))
    scale = format_measurement(0.2, 0.002, "mm/px")
    assert results(db, recipes, run, "Scale") == [f"dish rims at the dataset's stated 90 mm diameter · {scale}"]


def test_noise_floor_names_its_method(db, recipes, run):
    def floor(t: float, value: float, method: str) -> DerivedDraft:
        return DerivedDraft(
            t=t,
            kind="noise_floor",
            label="Noise floor of delta_e (median over vessels)",
            value=value,
            uncertainty=0.0,
            unit="dE00",
            inputs=[],
            method_version=method,
        )

    repos.add_derived(db, run.id, [floor(10.0, 0.5, "noise_floor/1"), floor(20.0, 0.21, "noise_floor/1")])
    assert results(db, recipes, run, "Noise floor") == ["delta_e: 0.21 dE00 (still period)"]
    repos.add_derived(db, run.id, [floor(30.0, 0.34, "noise_floor_wobble/1")])
    assert results(db, recipes, run, "Noise floor") == ["delta_e: 0.34 dE00 (wobble of all readings)"]


def test_a_noise_floor_labelled_in_plain_words_is_found(db, recipes, run):
    """Since D-95 the label names the metric as people say it ("colour change"), not by its id."""
    row = DerivedDraft(
        t=30.0,
        kind="noise_floor",
        label="Normal wobble of colour change: how far readings jitter when nothing changes (median over samples)",
        value=0.13,
        uncertainty=0.0,
        unit="dE00",
        inputs=[],
        method_version="noise_floor/1",
    )
    repos.add_derived(db, run.id, [row])
    assert results(db, recipes, run, "Noise floor") == ["delta_e: 0.13 dE00 (still period)"]


def test_counting_against_labels(db, recipes, run):
    control = next(v for v in repos.vessels_for_run(db, run.id) if v.label == "A")
    labels = [
        ReferenceValueDraft(vessel_id=control.id, t=f.t, metric="delta_e", value=1.0, source="test labels")
        for f in repos.frames_for_run(db, run.id)
    ]
    repos.add_reference_values(db, run.id, labels)
    # A reads 1.2 and 0.8 in turn against labels of 1.0: off by 0.2 each time, within half a unit of every label.
    assert results(db, recipes, run, "Counting against labels") == [
        "delta_e: mean absolute error 0.20 dE00, exact on 100% of 12 paired readings across 1 vessel"
    ]


def test_events_caught(db, recipes, run):
    assert results(db, recipes, run, "Events caught") == ["'Dye added' at 20 min in → change after 1200 s"]
    repos.add_event(
        db,
        run.id,
        vessel_id=None,
        t_start=6000.0,
        kind="intervention",
        source="researcher",
        detail={"message": "Lid on"},
    )
    assert results(db, recipes, run, "Events caught")[-1] == "'Lid on' at 1.7 h in → no change detected after it"


def test_claim_checker_counts(db, recipes, run):
    def attempt(t: float, n: int, passed: bool, reasons: list[str]) -> NoteAttemptDraft:
        return NoteAttemptDraft(t=t, attempt=n, raw={}, reasons=reasons, passed=passed, model_call_id=None)

    repos.add_note_attempt(db, run.id, attempt(10, 1, True, []))
    repos.add_note_attempt(
        db, run.id, attempt(20, 1, False, ["number outside a ref in observation: '25'", "unknown ref: x"])
    )
    repos.add_note_attempt(db, run.id, attempt(20, 2, True, []))
    repos.add_note_attempt(db, run.id, attempt(30, 1, False, ["number outside a ref in interpretation: '3'"]))
    repos.add_note_attempt(db, run.id, attempt(30, 2, False, ["quantity in words in observation: 'twice'"]))
    repos.add_note(
        db,
        run.id,
        NoteDraft(
            t=30,
            author="ai",
            level="checkpoint",
            tag=None,
            body={"observation": "No readings yet."},
            refs=[],
            evidence=[],
            check_status="fallback",
            model_call_id=None,
        ),
    )
    assert results(db, recipes, run, "Claim checker") == [
        "1 accepted first try, 1 after a retry, 1 written by code; "
        "3 answers rejected: number outside a ref ×2, quantity in words ×1, unknown ref ×1"
    ]


def test_models_and_spend(db, recipes, run):
    for status in ["ok", "ok", "ok", "ok", "error"]:
        call = ModelCallDraft(
            function="segment", model="sam-3.1", tier="sam", cost_usd=0.03, latency_s=1.0, status=status
        )
        repos.add_model_call(db, run.id, 0.0, call)
    assert results(db, recipes, run, "Models") == ["SAM 4 of 5 calls succeeded · spend $0.15"]


def test_a_run_with_nothing_stored_reads_not_measured_yet(db, recipes):
    experiment = repos.create_experiment(db, "Empty", "colour-reaction", 1)
    bare = repos.create_run(db, experiment.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    repos.set_run_status(db, bare.id, RunStatus.STOPPED)
    rows = validation_rows(db, recipes, [bare.id])
    assert [r.check for r in rows] == [
        "Scale",
        "Noise floor",
        "Counting against labels",
        "Events caught",
        "Claim checker",
        "Models",
    ]
    assert {r.result for r in rows} == {"not measured yet"}


def test_by_default_every_finished_or_stopped_run_is_listed(db, recipes, run, tmp_path):
    live = finished_run(db, tmp_path / "data", status=RunStatus.RUNNING)
    listed = {r.run for r in validation_rows(db, recipes)}
    assert any(run.id in name for name in listed) and not any(live.id in name for name in listed)


def test_the_table_is_markdown():
    assert render_table([Row("Scale", "Dye (r1)", "x | y")]).splitlines() == [
        "| Check | Run | Result |",
        "|---|---|---|",
        "| Scale | Dye (r1) | x \\| y |",
    ]


def test_only_interventions_the_researcher_logged_are_timed(db, recipes, run):
    """The quality check logs a hand in view as an intervention too; it isn't one the researcher made."""
    repos.add_event(
        db,
        run.id,
        vessel_id=None,
        t_start=3000.0,
        kind="intervention",
        source="quality",
        detail={"flags": ["occluded"]},
    )
    assert results(db, recipes, run, "Events caught") == ["'Dye added' at 20 min in → change after 1200 s"]
