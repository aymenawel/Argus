"""A TestClient on the whole worker app: fake camera, fake segmenter, a scripted reasoner (or none). No network."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.api.events import EventBroker
from argus.config import REPO_ROOT, load_settings
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.recipes.loader import load_all
from tests.test_api_runs import fake_opener
from tests.test_import import FakeSegmenter


@contextmanager
def api_client(db, tmp_path, *, reasoner=None, env=None) -> Iterator[TestClient]:
    settings = load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data"), **(env or {})})
    broker, recipes = EventBroker(), load_all(REPO_ROOT / "recipes")
    hub = CameraHub(opener=fake_opener)
    jobs = RunJobs(db, broker, settings, recipes, hub, segmenter=FakeSegmenter(), reasoner=reasoner)
    with TestClient(create_app(settings, db, broker, recipes, jobs=jobs, hub=hub)) as client:
        yield client


def logged_functions(db) -> list[str]:
    with db.read() as c:
        return [r["function"] for r in c.execute("SELECT function FROM model_calls ORDER BY rowid")]


def wait_for(check, timeout_s: float = 60.0):
    """Polls check() until it returns something truthy."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError("timed out")
