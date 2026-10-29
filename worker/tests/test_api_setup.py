"""The setup wizard's routes: the saved setup, the Muse draft, the measurement preview and the plan and its lock."""

import base64

import cv2
import numpy as np
import pytest

from argus.storage.repos import create_experiment
from tests.api_client import api_client, logged_functions, wait_for
from tests.helpers import rois_around_the_bar, write_growing_bar_clip
from tests.reasoning import FakeReasoner


@pytest.fixture
def reasoner():
    return FakeReasoner()


@pytest.fixture
def client(db, tmp_path, reasoner):
    with api_client(db, tmp_path, reasoner=reasoner) as test_client:
        yield test_client


@pytest.fixture
def experiment(client):
    return client.post("/api/experiments", json={"title": "Growing bar", "recipe_id": "general"}).json()["id"]


@pytest.fixture
def clip(tmp_path):
    return write_growing_bar_clip(tmp_path / "videos é" / "bar clip.mp4", frames=40)


def two_vessels():
    a, b = rois_around_the_bar()
    return [{"label": "A", "role": "treatment", "roi": a}, {"label": "B", "role": "control", "roi": b}]


def setup_with_video(clip, vessels=()):
    return {"source": {"kind": "video", "paths": [str(clip)]}, "time_scale": 60.0, "vessels": list(vessels)}


def plan(**overrides):
    body = {
        "hypothesis": "The bar grows.",
        "prediction": "A's area rises above B's.",
        "threshold": "Clearly above by the checkpoint.",
        "rivals": ["camera movement"],
        "metric": "area",
        "direction": "higher",
        "min_effect": 10.0,
        "checkpoint_s": 120.0,
    }
    return body | overrides


def recipe_draft(**overrides):
    draft = {
        "hypothesis": "Warm water spreads dye faster.",
        "prediction": "The warm glasses change colour more than the cold ones.",
        "threshold": "A clear difference by the checkpoint.",
        "metric": "delta_e",
        "direction": "higher",
        "min_effect": 5.0,
        "checkpoint_s": 300.0,
        "treatment": "warm",
        "factor": "water temperature",
        "factor_unit": "",
        "conditions": [{"value": "warm", "role": "treatment"}, {"value": "cold", "role": "control"}],
        "rivals": ["lighting change"],
        "question_for_researcher": "",
    }
    return draft | overrides


def test_the_setup_is_saved_and_read_back(client, experiment, clip):
    assert client.get(f"/api/experiments/{experiment}/setup").json()["vessels"] == []
    saved = client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, two_vessels()))
    assert saved.status_code == 200, saved.text
    back = client.get(f"/api/experiments/{experiment}/setup").json()
    assert [v["label"] for v in back["vessels"]] == ["A", "B"] and back["source"]["paths"] == [str(clip)]
    assert client.get("/api/experiments/nope/setup").status_code == 404


def test_a_run_started_without_vessels_takes_them_from_the_setup(client, experiment, clip):
    client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, two_vessels()))
    created = client.post(
        f"/api/experiments/{experiment}/runs", json={"mode": "imported", "paths": [str(clip)], "time_scale": 60.0}
    )
    assert created.status_code == 201, created.text
    assert [v["label"] for v in created.json()["vessels"]] == ["A", "B"]
    wait_for(lambda: not client.get(f"/api/runs/{created.json()['run']['id']}").json()["running"])


def test_a_run_without_vessels_anywhere_is_refused(client, experiment, clip):
    created = client.post(f"/api/experiments/{experiment}/runs", json={"mode": "imported", "paths": [str(clip)]})
    assert created.status_code == 422 and "vessel" in created.json()["detail"]


def test_the_setup_is_frozen_once_the_plan_is_locked_and_a_run_exists(client, experiment, clip):
    client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, two_vessels()))
    client.put(f"/api/experiments/{experiment}/plan", json=plan())
    assert client.post(f"/api/experiments/{experiment}/plan/lock").status_code == 200
    still_open = setup_with_video(clip, two_vessels()) | {"time_scale": 30.0}
    assert client.put(f"/api/experiments/{experiment}/setup", json=still_open).status_code == 200  # no run yet
    run = client.post(f"/api/experiments/{experiment}/runs", json={"mode": "imported", "paths": [str(clip)]})
    wait_for(lambda: not client.get(f"/api/runs/{run.json()['run']['id']}").json()["running"])
    frozen = client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip))
    assert frozen.status_code == 409


def test_the_plan_locks_only_with_its_structured_fields(client, experiment):
    client.put(f"/api/experiments/{experiment}/plan", json=plan(metric=None, checkpoint_s=None))
    lock = client.post(f"/api/experiments/{experiment}/plan/lock")
    assert lock.status_code == 422 and "metric" in lock.json()["detail"] and "checkpoint_s" in lock.json()["detail"]
    assert client.get(f"/api/experiments/{experiment}/plan").json()[0]["locked_at"] is None


def test_a_locked_plan_is_kept_and_an_edit_is_a_new_version(client, experiment):
    assert client.post(f"/api/experiments/{experiment}/plan/lock").status_code == 422  # nothing to lock yet
    client.put(f"/api/experiments/{experiment}/plan", json=plan())
    locked = client.post(f"/api/experiments/{experiment}/plan/lock").json()
    assert locked["version"] == 1 and locked["locked_at"] and locked["sha256"]
    edited = client.put(f"/api/experiments/{experiment}/plan", json=plan(hypothesis="A later idea.")).json()
    versions = client.get(f"/api/experiments/{experiment}/plan").json()
    assert edited["version"] == 2 and [p["locked_at"] is not None for p in versions] == [True, False]
    assert versions[0]["hypothesis"] == "The bar grows."
    assert client.get(f"/api/experiments/{experiment}").json()["status"] == "locked"


def test_a_plan_metric_must_be_one_the_recipe_measures(client, experiment):
    answer = client.put(f"/api/experiments/{experiment}/plan", json=plan(metric="delta_e"))
    assert answer.status_code == 422 and "delta_e" in answer.json()["detail"]


def test_describe_returns_a_draft_and_logs_the_call(client, db, reasoner):
    dye = client.post("/api/experiments", json={"title": "Dye", "recipe_id": "colour-reaction"}).json()["id"]
    reasoner.answers.append(recipe_draft())
    answer = client.post(f"/api/experiments/{dye}/describe", json={"words": "Does warm water spread dye faster?"})
    assert answer.status_code == 200, answer.text
    draft = answer.json()
    assert draft["metric"] in {"delta_e"} and logged_functions(db) == ["describe"]
    task = reasoner.tasks[0]
    assert task.function == "describe" and "Does warm water spread dye faster?" in task.variable[-1]
    assert client.get(f"/api/experiments/{dye}/plan").json() == []  # nothing is saved


def test_describe_says_when_the_model_fails(client, db, reasoner):
    from argus.reason import ReasonError
    from tests.reasoning import call

    dye = client.post("/api/experiments", json={"title": "Dye", "recipe_id": "colour-reaction"}).json()["id"]
    reasoner.answers.append(ReasonError("timeout", call("describe", status="error", error="timeout", cost=0.0)))
    answer = client.post(f"/api/experiments/{dye}/describe", json={"words": "Warm water and dye."})
    assert answer.status_code == 502 and "timeout" in answer.json()["detail"]
    assert logged_functions(db) == ["describe"]


def test_describe_without_reasoning_is_unavailable(db, tmp_path):
    with api_client(db, tmp_path, reasoner=None) as client:
        exp = create_experiment(db, "Dye", "colour-reaction", 1)
        answer = client.post(f"/api/experiments/{exp.id}/describe", json={"words": "Warm water and dye."})
    assert answer.status_code == 503


def test_the_preview_measures_the_saved_vessels_on_one_frame(client, db, experiment, clip):
    client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, two_vessels()))
    answer = client.post(f"/api/experiments/{experiment}/preview", json={"path": str(clip), "video_s": 3.0})
    assert answer.status_code == 200, answer.text
    preview = answer.json()
    image = cv2.imdecode(np.frombuffer(base64.b64decode(preview["frame_jpeg_b64"]), np.uint8), cv2.IMREAD_COLOR)
    assert image is not None and image.shape[0] > 100
    assert preview["calibration"]["card"] == "standard" and preview["calibration"]["px_per_mm"] > 1
    assert "blur" in preview["quality"] and isinstance(preview["quality"]["flags"], list)
    a, b = preview["vessels"]
    assert (
        a["label"] == "A"
        and a["outlines"]
        and any(r["metric"] == "area" and "±" in r["display"] for r in a["readings"])
    )
    assert b["label"] == "B" and all(r["value"] == 0 for r in b["readings"] if r["metric"] == "area")  # SAM: none
    assert logged_functions(db) == ["preview"]  # one SAM call: the general recipe has one concept


def test_a_preview_before_any_vessel_makes_no_sam_call(client, db, experiment, clip):
    preview = client.post(f"/api/experiments/{experiment}/preview", json={"path": str(clip), "video_s": 1.0}).json()
    assert preview["vessels"] == [] and preview["calibration"]["card"] == "standard"
    assert logged_functions(db) == []


def test_a_recipe_tells_the_wizard_its_concepts_metrics_and_rivals(client):
    recipe = client.get("/api/recipes/colour-reaction").json()
    assert recipe["concepts"] == ["liquid"] and "lighting change" in " ".join(recipe["rivals"]).lower()
    metrics = {m["id"]: m["unit"] for m in recipe["metrics"]}
    assert metrics["delta_e"] == "dE00" and all(metrics.values())  # every stored metric with its unit
    assert client.get("/api/recipes/nope").status_code == 404


def test_vessels_are_saved_before_their_roles_and_a_run_needs_every_role(client, experiment, clip):
    a, b = (v["roi"] for v in two_vessels())
    unroled = [{"label": "A", "role": "treatment", "roi": a}, {"label": "B", "role": None, "roi": b}]
    saved = client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, unroled))
    assert saved.status_code == 200 and saved.json()["vessels"][1]["role"] is None
    run = client.post(f"/api/experiments/{experiment}/runs", json={"mode": "imported", "paths": [str(clip)]})
    assert run.status_code == 422 and "role" in run.json()["detail"]


def test_a_plain_frame_to_draw_vessels_on_costs_nothing(client, db, experiment, clip):
    client.put(f"/api/experiments/{experiment}/setup", json=setup_with_video(clip, two_vessels()))
    answer = client.post(f"/api/experiments/{experiment}/frame", json={"path": str(clip), "video_s": 1.0})
    assert answer.status_code == 200 and answer.headers["content-type"] == "image/jpeg"
    image = cv2.imdecode(np.frombuffer(answer.content, np.uint8), cv2.IMREAD_COLOR)
    assert image.shape[0] > 100 and logged_functions(db) == []


def test_a_colour_change_preview_starts_at_zero(client, clip):
    dye = client.post("/api/experiments", json={"title": "Dye", "recipe_id": "colour-reaction"}).json()["id"]
    client.put(f"/api/experiments/{dye}/setup", json=setup_with_video(clip, two_vessels()))
    preview = client.post(f"/api/experiments/{dye}/preview", json={"path": str(clip), "video_s": 3.0}).json()
    a = next(v for v in preview["vessels"] if v["label"] == "A")
    delta = [r for r in a["readings"] if r["metric"] == "delta_e"]
    assert delta and delta[0]["value"] == 0 and "±" in delta[0]["display"]  # measured against itself: the start
