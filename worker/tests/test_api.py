import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.api.events import EventBroker
from argus.config import REPO_ROOT, load_settings
from argus.recipes.loader import load_all


@pytest.fixture
def broker():
    return EventBroker()


@pytest.fixture
def client(db, broker, tmp_path):
    settings = load_settings({"ARGUS_DATA_DIR": str(tmp_path)})
    with TestClient(create_app(settings, db, broker, load_all(REPO_ROOT / "recipes"))) as test_client:
        yield test_client


def test_create_list_get_experiment_and_event(client, broker):
    r = client.post("/api/experiments", json={"title": "Iodine clock timing", "recipe_id": "colour-reaction"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    assert client.get("/api/experiments").json()[0]["id"] == r.json()["id"]
    assert client.get(f"/api/experiments/{r.json()['id']}").status_code == 200
    assert broker.since(0)[-1].type == "experiment"


def test_unknown_recipe_and_missing_experiment(client):
    response = client.post("/api/experiments", json={"title": "x", "recipe_id": "nope"})
    assert response.status_code == 422 and response.json() == {"detail": "unknown recipe: nope"}
    assert client.get("/api/experiments/exp_000000000000").status_code == 404


def test_cors_allows_the_web_origin(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
