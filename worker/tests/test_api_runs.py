"""Runs over the HTTP API, with the fake segmenter from the import tests and a fake camera. No network."""

import json
import time

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from argus import cli
from argus.api.app import create_app
from argus.api.events import EventBroker
from argus.calibration.card import STANDARD
from argus.config import REPO_ROOT, load_settings
from argus.domain import EventKind, RunMode, RunSource, RunStatus, SourceKind
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.recipes.loader import load_all
from argus.storage.db import Database
from argus.storage.repos import create_experiment, create_run, events_for_run, get_run
from tests.helpers import rois_around_the_bar, scene_with_bar_on_card_plane, write_growing_bar_clip
from tests.test_import import FakeSegmenter

SCENE, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=30, width_mm=2)


class FakeCapture:
    def read(self):
        time.sleep(0.01)
        return True, SCENE

    def release(self):
        pass


def fake_opener(index, settings):
    if index != 0:
        raise RuntimeError(f"camera {index} did not open")
    return FakeCapture(), {}


@pytest.fixture
def app_parts(db, tmp_path):
    settings = load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data")})
    broker = EventBroker()
    recipes = load_all(REPO_ROOT / "recipes")
    hub = CameraHub(opener=fake_opener)
    jobs = RunJobs(db, broker, settings, recipes, hub, segmenter=FakeSegmenter())
    return settings, broker, recipes, hub, jobs


@pytest.fixture
def client(db, app_parts):
    settings, broker, recipes, hub, jobs = app_parts
    with TestClient(create_app(settings, db, broker, recipes, jobs=jobs, hub=hub)) as test_client:
        yield test_client


@pytest.fixture
def experiment(client):
    return client.post("/api/experiments", json={"title": "Growing bar", "recipe_id": "general"}).json()


@pytest.fixture
def clip(tmp_path):
    return write_growing_bar_clip(tmp_path / "videos é" / "bar clip.mp4", frames=40)


def run_body(**overrides):
    a, b = rois_around_the_bar()
    body = {
        "mode": "imported",
        "time_scale": 60.0,
        "vessels": [{"label": "A", "role": "treatment", "roi": a}, {"label": "B", "role": "control", "roi": b}],
    }
    return {**body, **overrides}


def wait_until_done(client, run_id, timeout_s=60.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        view = client.get(f"/api/runs/{run_id}").json()
        if not view["running"]:
            return view
        time.sleep(0.2)
    raise AssertionError("the run did not finish")


def test_import_run_end_to_end_over_the_api(client, experiment, clip):
    created = client.post(f"/api/experiments/{experiment['id']}/runs", json=run_body(paths=[str(clip)]))
    assert created.status_code == 201, created.text
    run_id = created.json()["run"]["id"]
    assert client.get(f"/api/experiments/{experiment['id']}").json()["status"] == "running"
    view = wait_until_done(client, run_id)
    assert view["run"]["status"] == "finished" and view["calibration"]["card"] == "standard"
    assert client.get(f"/api/experiments/{experiment['id']}").json()["status"] == "finished"
    assert client.get(f"/api/experiments/{experiment['id']}/runs").json()[0]["run"]["id"] == run_id

    timeline = client.get(f"/api/runs/{run_id}/timeline").json()
    areas = [
        m for m in timeline["measurements"] if m["metric"] == "area" and m["vessel_id"] == view["vessels"][0]["id"]
    ]
    assert len(areas) >= 3 and all("±" in m["display"] and m["display"].endswith("mm2") for m in areas)
    assert areas[-1]["value"] > areas[0]["value"]
    frame = timeline["frames"][-1]
    image = client.get(f"/api/runs/{run_id}/frames/{frame['id']}.jpg", params={"w": 160})
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    assert "immutable" in image.headers["cache-control"]  # frames are evidence: they never change
    decoded = cv2.imdecode(np.frombuffer(image.content, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[1] == 160
    detections = client.get(f"/api/runs/{run_id}/frames/{frame['id']}/detections").json()
    assert detections and detections[0]["outline"] and detections[0]["vessel_id"] == view["vessels"][0]["id"]
    windowed = client.get(f"/api/runs/{run_id}/timeline", params={"t_from": 60, "t_to": 120}).json()
    assert all(60 <= f["t"] <= 120 for f in windowed["frames"])


def test_bad_requests(client, experiment, tmp_path):
    url = f"/api/experiments/{experiment['id']}/runs"
    missing = client.post(url, json=run_body(paths=[str(tmp_path / "nope.mp4")]))
    assert missing.status_code == 422 and "nope.mp4" in missing.json()["detail"]
    assert client.post(url, json=run_body(mode="live")).status_code == 422  # no camera_index
    assert client.post(url, json=run_body(mode="live", camera_index=3)).status_code == 422  # camera won't open
    assert client.post("/api/experiments/exp_000000000000/runs", json=run_body(paths=["x"])).status_code == 404
    live = client.post(url, json=run_body(mode="live", camera_index=0))
    assert live.status_code == 201, live.text
    second = client.post(url, json=run_body(mode="live", camera_index=0))
    assert second.status_code == 409 and second.json()["detail"] == "a run is already running for this experiment"
    run_id = live.json()["run"]["id"]
    stopped = client.post(f"/api/runs/{run_id}/stop")
    assert stopped.status_code == 200 and stopped.json()["run"]["status"] == "stopped"
    assert client.post(f"/api/runs/{run_id}/stop").status_code == 409


def test_the_camera_stream_and_list(client):
    with client.stream("GET", "/api/cameras/0/stream.mjpg") as response:
        assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
        chunk = next(response.iter_bytes())
        assert b"Content-Type: image/jpeg" in chunk
    assert client.get("/api/cameras/3/stream.mjpg").status_code == 404


def test_vessel_detection_proposes_rois(client, experiment, clip):
    response = client.post(
        f"/api/experiments/{experiment['id']}/vessels/detect",
        json={"path": str(clip), "video_s": 3.5, "concept": "bar"},
    )
    assert response.status_code == 200, response.text
    proposals = response.json()
    assert proposals and len(proposals[0]["roi"]) >= 3


def test_runs_left_running_are_stopped_at_startup(db, app_parts):
    settings, broker, recipes, hub, jobs = app_parts
    exp = create_experiment(db, "Interrupted", "general", 1)
    run = create_run(db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.VIDEO, paths=["a.mp4"]))
    with TestClient(create_app(settings, db, broker, recipes, jobs=jobs, hub=hub)):
        assert get_run(db, run.id).status is RunStatus.STOPPED
        assert [e.kind for e in events_for_run(db, run.id)] == [EventKind.INTERRUPTED]


def test_cli_run_posts_the_file(monkeypatch, tmp_path, capsys):
    sent = {}

    class Response:
        status_code = 201

        def json(self):
            return {"run": {"id": "run_abc"}}

    def fake_post(url, json, timeout):
        sent.update(url=url, json=json)
        return Response()

    monkeypatch.setattr(cli.requests, "post", fake_post)
    path = tmp_path / "run é.json"
    path.write_text(json.dumps({"experiment_id": "exp_1", **run_body(paths=["v.mp4"])}), encoding="utf-8")
    assert cli.main(["run", str(path), "--api", "http://worker:8000"]) == 0
    assert sent["url"] == "http://worker:8000/api/experiments/exp_1/runs" and "experiment_id" not in sent["json"]
    out = capsys.readouterr().out
    assert "run_abc" in out and "http://localhost:3000/experiments/exp_1/run" in out


def test_a_database_left_by_another_process_is_tidied_too(tmp_path, app_parts):
    settings, broker, recipes, hub, jobs = app_parts
    db = Database(tmp_path / "other" / "argus.sqlite")
    try:
        exp = create_experiment(db, "x", "general", 1)
        run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
        with TestClient(create_app(settings, db, broker, recipes, jobs=RunJobs(db, broker, settings, recipes, hub))):
            assert get_run(db, run.id).status is RunStatus.STOPPED
    finally:
        db.close()


def test_a_published_plate_runs_with_vessels_from_its_tiles(client, experiment, tmp_path):
    from tests.test_images_source import PROVENANCE, write_manifest

    manifest = write_manifest(tmp_path / "plate")
    roles = {"rye": "control", "millet": "treatment"}
    created = client.post(
        f"/api/experiments/{experiment['id']}/runs", json={"mode": "imported", "manifest": manifest, "roles": roles}
    )
    assert created.status_code == 201, created.text
    view = wait_until_done(client, created.json()["run"]["id"])
    assert view["run"]["status"] == "finished" and view["run"]["source"]["kind"] == "images"
    assert view["run"]["source"]["provenance"] == PROVENANCE | {"assembled": True, "retrospective": True}
    vessels = {v["label"]: v for v in view["vessels"]}
    assert vessels["A1"]["role"] == "control" and vessels["B1"]["role"] == "treatment"
    assert vessels["B1"]["roi"] == [[40, 0], [80, 0], [80, 40], [40, 40]]
    assert vessels["B1"]["condition"]["value"] == "millet"
    assert len(client.get(f"/api/runs/{view['run']['id']}/timeline").json()["frames"]) == 3


def test_a_published_plate_needs_a_role_for_every_condition_and_a_control(client, experiment, tmp_path):
    from tests.test_images_source import write_manifest

    url = f"/api/experiments/{experiment['id']}/runs"
    manifest = write_manifest(tmp_path / "plate")
    missing = client.post(url, json={"mode": "imported", "manifest": manifest, "roles": {"rye": "control"}})
    assert missing.status_code == 422 and "millet" in missing.json()["detail"]
    no_control = {"rye": "treatment", "millet": "treatment"}
    assert client.post(url, json={"mode": "imported", "manifest": manifest, "roles": no_control}).status_code == 422
    broken = write_manifest(tmp_path / "broken", skip="frame_001.jpg")
    roles = {"rye": "control", "millet": "treatment"}
    answer = client.post(url, json={"mode": "imported", "manifest": broken, "roles": roles})
    assert answer.status_code == 422 and "frame_001.jpg" in answer.json()["detail"]


def test_a_published_plates_labels_are_kept_for_the_agreement(client, experiment, tmp_path):
    from tests.test_images_source import write_manifest

    tiles = [
        {
            "label": "A1",
            "condition": "rye",
            "run": "sc1",
            "dish": 1,
            "box": [0, 0, 40, 40],
            "seeds": 5,
            "labels": {"germinated": [0, 1, 3]},
        },
        {
            "label": "B1",
            "condition": "millet",
            "run": "pg1",
            "dish": 4,
            "box": [40, 0, 80, 40],
            "seeds": 5,
            "labels": {"germinated": [0, 2, 4]},
        },
    ]
    manifest = write_manifest(tmp_path / "plate", tiles=tiles)
    roles = {"rye": "control", "millet": "treatment"}
    url = f"/api/experiments/{experiment['id']}/runs"
    created = client.post(url, json={"mode": "imported", "manifest": manifest, "roles": roles})
    view = wait_until_done(client, created.json()["run"]["id"])
    result = client.get(f"/api/runs/{view['run']['id']}/agreement", params={"metric": "germinated"}).json()
    assert result["source"] == "Test plates" and [v["label"] for v in result["vessels"]] == ["A1", "B1"]
    assert all(v["frames"] == 0 for v in result["vessels"])  # nothing measured: no calibration in this plate
    assert client.get(f"/api/runs/{view['run']['id']}/agreement", params={"metric": "area"}).json() is None
