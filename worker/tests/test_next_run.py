"""The next run (D-80): replicates per condition and run length computed in code from the run's own spread and curves,
explained by Muse Wonder through the claim checker, stored append-only. Never for a run that is still going."""

import math
import sqlite3

import numpy as np
import pytest

from argus.analyze.fits import Fit
from argus.analyze.next_run import replicates_needed, replicates_with_reason, run_length_h
from argus.domain import (
    Condition,
    Direction,
    MeasurementDraft,
    PlanDraft,
    Role,
    RunMode,
    RunSource,
    RunStatus,
    SourceKind,
    VesselDraft,
)
from argus.pipeline.next_run import NextRunRefused, suggest_next_run
from argus.recipes.model import Recipe
from argus.storage.repos import (
    add_measurements,
    add_vessels,
    create_experiment,
    create_run,
    lock_plan,
    save_plan_draft,
    set_run_status,
)
from tests.api_client import api_client, logged_functions
from tests.reasoning import FakeReasoner
from tests.test_verdict import SETTINGS

RECIPE = Recipe.model_validate(
    {
        "id": "seed-germination",
        "version": 1,
        "title": "Germination",
        "default_mode": "continuous",
        "analysis_step_s": 1800,
        "curve": "logistic",
        "concepts": [{"name": "root"}],
        "measurements": [
            {"id": "root_length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"}
        ],
        "main_measurement": "root_length",
    }
)
TIMES_H = np.arange(0.0, 48.01, 0.5)


def logistic_fit(t50: float, *, K: float = 10.0, r: float = 0.5, reached: bool = True, ok: bool = True) -> Fit:
    return Fit(
        "logistic",
        ok=ok,
        reached=reached,
        half_time_h=(t50, 0.2) if reached else None,
        rate_per_h=(K * r / 4, 0.05),
        plateau=(K, 0.1) if reached else None,
    )


def finished_run(db, *, status=RunStatus.FINISHED, halves=None):
    """Rye controls A, B and millet treatments C, D, half-way at 22, 23, 15 and 17 h, judged on half-way time."""
    exp = create_experiment(db, "Rye vs millet", "seed-germination", 1)
    plan = PlanDraft(
        hypothesis="Millet germinates faster than rye.",
        prediction="Millet roots reach half their final length sooner.",
        threshold="At least two hours sooner.",
        rivals=["seed batch"],
        metric="root_length",
        direction=Direction.LOWER,
        min_effect=2.0,
        checkpoint_s=86400.0,
        treatment=None,
        quantity="half_time",
    )
    save_plan_draft(db, exp.id, plan)
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    halves = halves or {"A": 22.0, "B": 23.0, "C": 15.0, "D": 17.0}
    drafts = [
        VesselDraft(
            label=label,
            role=Role.CONTROL if label in "AB" else Role.TREATMENT,
            condition=Condition(factor="species", value="rye" if label in "AB" else "millet"),
            roi=[(0, 0), (9, 0), (9, 9)],
        )
        for label in halves
    ]
    vessels = {v.label: v for v in add_vessels(db, run.id, drafts)}
    rng = np.random.default_rng(5)
    rows = [
        MeasurementDraft(
            vessel_id=vessels[label].id,
            frame_id=None,
            t=float(t * 3600),
            metric="root_length",
            value=float(10 / (1 + math.exp(-0.5 * (t - half))) + rng.normal(0, 0.1)),
            uncertainty=0.1,
            unit="mm",
            method_version="skeleton_length/1",
        )
        for label, half in halves.items()
        for t in TIMES_H
    ]
    add_measurements(db, run.id, rows)
    return set_run_status(db, run.id, status)


def answer(**overrides) -> dict:
    return {
        "why": "With {ref:next:replicates} per condition, a gap the size of the plan's smallest effect would show.",
        "change": "Put both species in the same run, so seed batch is not mixed in.",
        "watch_for": "If the controls level off early, stop at {ref:next:hours}.",
        "refs_used": ["next:replicates", "next:hours"],
    } | overrides


def test_replicates_match_the_t_test():
    assert replicates_needed(2.0, 2.0, cap=None) == 17  # d = 1: the two-sample t-test needs 17 per group
    assert replicates_needed(2.0, 2.0) == 16  # capped at 16 per run
    assert replicates_needed(1.0, 2.0) == 6  # d = 2
    n, reason = replicates_with_reason(2.0, 2.0, "h")
    assert n == 16 and "17" in reason and "16" in reason


def test_no_spread_means_unknown_replicates():
    assert replicates_needed(0.0, 2.0) is None
    assert replicates_needed(float("nan"), 2.0) is None
    n, reason = replicates_with_reason(None, 2.0, "h")
    assert n is None and "spread" in reason


def test_run_length_is_when_the_slowest_curve_plateaus():
    fits = {"a": logistic_fit(20.0), "b": logistic_fit(24.0), "c": Fit("logistic", ok=False, reason="flat")}
    assert run_length_h(fits) == pytest.approx((24.0 + math.log(19) / 0.5) * 1.2, rel=1e-6)
    assert run_length_h({"a": logistic_fit(20.0), "b": logistic_fit(0.0, reached=False)}) is None
    assert run_length_h({}) is None


def test_a_finished_run_gets_a_checked_suggestion(db, tmp_path):
    run = finished_run(db)
    with api_client(db, tmp_path, reasoner=FakeReasoner([answer()])) as client:
        assert client.get(f"/api/runs/{run.id}/next-run").json() is None
        made = client.post(f"/api/runs/{run.id}/next-run")
        assert made.status_code == 201
        body = made.json()
        assert body["body"]["written_by"] == "model" and "{ref:" not in body["body"]["why"]
        assert body["numbers"]["replicates"] is not None and f"{body['numbers']['replicates']} " in body["body"]["why"]
        assert body["numbers"]["hours"] is not None and "next:replicates" in body["refs"]
        assert client.get(f"/api/runs/{run.id}/next-run").json()["id"] == body["id"]
    assert logged_functions(db) == ["next_run"]


@pytest.mark.anyio
async def test_an_answer_with_free_numbers_is_retried_then_written_by_code(db):
    run = finished_run(db)
    free = answer(why="Use 12 dishes per species next time.")
    reasoner = FakeReasoner([free, free])
    suggestion = await suggest_next_run(db, run, RECIPE, reasoner, SETTINGS)
    assert reasoner.calls == 2 and len(suggestion.model_call_ids) == 2
    assert suggestion.body["written_by"] == "code"
    assert str(suggestion.numbers["replicates"]) in suggestion.body["why"]
    assert "rejected" in reasoner.tasks[1].variable[-1]


def test_a_running_run_gets_409(db, tmp_path):
    run = finished_run(db)
    with api_client(db, tmp_path, reasoner=FakeReasoner([])) as client:
        set_run_status(db, run.id, RunStatus.RUNNING)  # after start-up, which closes runs left running
        refused = client.post(f"/api/runs/{run.id}/next-run")
    assert refused.status_code == 409 and "still going" in refused.json()["detail"]


@pytest.mark.anyio
async def test_a_running_run_is_refused_in_the_pipeline(db):
    run = finished_run(db, status=RunStatus.RUNNING)
    with pytest.raises(NextRunRefused, match="still going"):
        await suggest_next_run(db, run, RECIPE, FakeReasoner([]), SETTINGS)


@pytest.mark.anyio
async def test_next_runs_are_evidence(db):
    run = finished_run(db)
    suggestion = await suggest_next_run(db, run, RECIPE, FakeReasoner([answer()]), SETTINGS)
    with pytest.raises(sqlite3.IntegrityError, match="evidence"), db.write() as c:
        c.execute("UPDATE next_runs SET body='{}' WHERE id=?", (suggestion.id,))
    with pytest.raises(sqlite3.IntegrityError, match="evidence"), db.write() as c:
        c.execute("DELETE FROM next_runs WHERE id=?", (suggestion.id,))


def test_a_vessel_still_rising_leaves_the_run_length_unknown(db):
    from argus.analyze.next_run import next_run_numbers
    from argus.storage.repos import first_locked_plan

    run = finished_run(db, halves={"A": 22.0, "B": 23.0, "C": 15.0, "D": 47.0})
    numbers = next_run_numbers(db, run, RECIPE, first_locked_plan(db, run.experiment_id))
    assert numbers.hours is None and "still rising" in numbers.hours_reason
