"""A worker without MODEL_API_KEY: SAM 3.1 runs through the Meta Model API, so anything that segments says so plainly
(503, as recipe drafting does) instead of failing on a stack trace; nothing is started and no call is logged."""

import pytest

from argus.domain import Role, VesselDraft
from argus.pipeline.analyzer import SamSegmenter
from argus.storage import repos
from tests.api_client import api_client, logged_functions

OFF = "segmentation is off: MODEL_API_KEY is not set (SAM 3.1 runs through the Meta Model API)"
SQUARE = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]


@pytest.fixture
def client(db, tmp_path):
    with api_client(db, tmp_path, segmenter=lambda settings: SamSegmenter(settings)) as test_client:
        yield test_client


@pytest.fixture
def experiment(db):
    return repos.create_experiment(db, "No key", "colour-reaction", 1)


def test_detecting_vessels_says_segmentation_is_off(client, db, experiment):
    answer = client.post(
        f"/api/experiments/{experiment.id}/vessels/detect", json={"camera_index": 0, "concept": "glass"}
    )
    assert (answer.status_code, answer.json()["detail"]) == (503, OFF)
    assert logged_functions(db) == []


def test_the_setup_preview_says_segmentation_is_off(client, db, experiment):
    client.put(
        f"/api/experiments/{experiment.id}/setup",
        json={"vessels": [VesselDraft(label="A", role=Role.CONTROL, roi=SQUARE).model_dump(mode="json")]},
    )
    answer = client.post(f"/api/experiments/{experiment.id}/preview", json={"camera_index": 0})
    assert (answer.status_code, answer.json()["detail"]) == (503, OFF)
    assert logged_functions(db) == []


def test_a_run_is_not_started(client, db, experiment):
    vessels = [{"label": "A", "role": "control", "roi": SQUARE}]
    answer = client.post(
        f"/api/experiments/{experiment.id}/runs", json={"mode": "live", "camera_index": 0, "vessels": vessels}
    )
    assert (answer.status_code, answer.json()["detail"]) == (503, OFF)
    assert repos.runs_for_experiment(db, experiment.id) == []
