"""GET /runs/{id}/fits: each vessel's readings of a metric and its fitted curve, for the Results page."""

import numpy as np
import pytest

from argus.domain import Direction, MeasurementDraft, PlanDraft, Role, RunMode, RunSource, SourceKind, VesselDraft
from argus.storage.repos import add_measurements, add_vessels, create_run, lock_plan, save_plan_draft
from tests.api_client import api_client

TIMES_H = np.arange(0.0, 48.01, 0.5)


@pytest.fixture
def client(db, tmp_path):
    with api_client(db, tmp_path) as test_client:
        yield test_client


@pytest.fixture
def experiment(client):
    return client.post("/api/experiments", json={"title": "Seeds", "recipe_id": "seed-germination"}).json()["id"]


def run_of(db, experiment_id, curves: dict[str, np.ndarray]) -> str:
    run = create_run(db, experiment_id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    drafts = [VesselDraft(label=label, role=Role.CONTROL, roi=[(0, 0), (9, 0), (9, 9)]) for label in curves]
    vessels = {v.label: v for v in add_vessels(db, run.id, drafts)}
    rng = np.random.default_rng(5)
    add_measurements(
        db,
        run.id,
        [
            MeasurementDraft(
                vessel_id=vessels[label].id,
                frame_id=None,
                t=float(t * 3600),
                metric="root_length",
                value=float(v + (rng.normal(0, 0.1) if np.ptp(values) else 0.0)),
                uncertainty=0.1,
                unit="mm",
                method_version="skeleton_length/1",
            )
            for label, values in curves.items()
            for t, v in zip(TIMES_H, values, strict=True)
        ],
    )
    return run.id


def logistic(t50: float) -> np.ndarray:
    return 10 / (1 + np.exp(-0.5 * (TIMES_H - t50)))


def test_fits_of_a_run_come_from_that_run_only(client, db, experiment):
    early = run_of(db, experiment, {"A": logistic(10)})
    late = run_of(db, experiment, {"A": logistic(30)})
    for run_id, t50 in ((early, 10), (late, 30)):
        view = client.get(f"/api/runs/{run_id}/fits", params={"metric": "root_length"}).json()
        fit = view["vessels"][0]["fit"]
        assert fit["ok"] and abs(fit["half_time_h"][0] - t50) < 1, (run_id, fit["half_time_h"])
        assert len(view["vessels"][0]["readings"]) == len(TIMES_H) and len(fit["samples"]) == 100


def test_fits_default_to_the_plans_metric_and_name_refused_fits(client, db, experiment):
    plan = PlanDraft(
        hypothesis="h",
        prediction="p",
        threshold="t",
        rivals=[],
        metric="root_length",
        direction=Direction.LOWER,
        min_effect=2.0,
        checkpoint_s=3600.0,
        quantity="half_time",
    )
    save_plan_draft(db, experiment, plan)
    lock_plan(db, experiment)
    run_id = run_of(db, experiment, {"A": logistic(20), "B": np.zeros_like(TIMES_H)})
    view = client.get(f"/api/runs/{run_id}/fits").json()
    assert (view["metric"], view["unit"], view["curve"], view["quantity"]) == (
        "root_length",
        "mm",
        "logistic",
        "half_time",
    )
    by_label = {v["label"]: v for v in view["vessels"]}
    assert by_label["A"]["fit"]["ok"] and by_label["A"]["role"] == "control"
    assert not by_label["B"]["fit"]["ok"] and "never rose" in by_label["B"]["fit"]["reason"]


def test_an_unknown_metric_is_a_422(client, db, experiment):
    run_id = run_of(db, experiment, {"A": logistic(20)})
    assert client.get(f"/api/runs/{run_id}/fits", params={"metric": "height"}).status_code == 422
    assert client.get("/api/runs/run_000000000000/fits").status_code == 404
