"""Experiments keep their own recipe: drafted from words, editable until the plan locks, then frozen (D-73)."""

import sqlite3

import pytest

from argus.config import REPO_ROOT
from argus.recipes.loader import load_all
from argus.recipes.resolve import recipe_for
from argus.storage.repos import create_experiment, get_experiment
from tests.api_client import api_client, logged_functions
from tests.reasoning import FakeReasoner
from tests.test_recipe_draft import WORDS_GERMINATION, answer

TEMPLATES = load_all(REPO_ROOT / "recipes")


@pytest.fixture
def reasoner():
    return FakeReasoner()


@pytest.fixture
def client(db, tmp_path, reasoner):
    with api_client(db, tmp_path, reasoner=reasoner) as test_client:
        yield test_client


def drafted(client, reasoner) -> dict:
    reasoner.answers.append(answer())
    response = client.post("/api/experiments/draft", json={"words": WORDS_GERMINATION})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def own_experiment(client, reasoner) -> str:
    draft = drafted(client, reasoner)
    created = client.post("/api/experiments", json={"title": "Seeds", "recipe": draft["recipe"], "plan": draft["plan"]})
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_a_drafted_recipe_creates_an_experiment_that_uses_it(client, db, reasoner):
    draft = drafted(client, reasoner)
    assert draft["recipe"]["concepts"][0]["name"] == "seed" and draft["setup_hints"]["factor"] == "species"
    exp = client.post(
        "/api/experiments", json={"title": "Seeds", "recipe": draft["recipe"], "plan": draft["plan"]}
    ).json()
    assert exp["recipe_id"] == "own" and exp["recipe_version"] == 1
    assert client.get(f"/api/experiments/{exp['id']}/recipe").json()["concepts"][0]["name"] == "seed"
    assert client.get(f"/api/experiments/{exp['id']}/plan").json()[0]["metric"] == draft["plan"]["metric"]
    assert logged_functions(db) == ["recipe"]


def test_an_edit_before_the_lock_is_a_new_version(client, own_experiment):
    recipe = client.get(f"/api/experiments/{own_experiment}/recipe").json()
    edited = client.put(f"/api/experiments/{own_experiment}/recipe", json=recipe | {"analysis_step_s": 900})
    assert edited.status_code == 200, edited.text
    assert client.get(f"/api/experiments/{own_experiment}/recipe").json()["analysis_step_s"] == 900
    assert client.get(f"/api/experiments/{own_experiment}").json()["recipe_version"] == 2


def test_the_recipe_freezes_when_the_plan_locks(client, own_experiment):
    assert client.post(f"/api/experiments/{own_experiment}/plan/lock").status_code == 200
    recipe = client.get(f"/api/experiments/{own_experiment}/recipe").json()
    edited = client.put(f"/api/experiments/{own_experiment}/recipe", json=recipe | {"analysis_step_s": 60})
    assert edited.status_code == 409 and "locked" in edited.json()["detail"]
    assert client.get(f"/api/experiments/{own_experiment}/recipe").json()["analysis_step_s"] == 1800


def test_an_invalid_edit_says_why(client, own_experiment):
    recipe = client.get(f"/api/experiments/{own_experiment}/recipe").json()
    bad = client.put(f"/api/experiments/{own_experiment}/recipe", json=recipe | {"main_measurement": "nothing"})
    assert bad.status_code == 422 and "nothing" in str(bad.json()["detail"])


def test_recipe_for_reads_own_recipes_and_templates(db, client, own_experiment):
    assert recipe_for(db, TEMPLATES, get_experiment(db, own_experiment)).concepts[1].name == "root"
    template = create_experiment(db, "Dye", "colour-reaction", 1)
    assert recipe_for(db, TEMPLATES, template) is TEMPLATES["colour-reaction"]


def test_a_refused_draft_answers_422_with_reasons(client, db, reasoner):
    reasoner.answers += [answer(metric="nonsense")] * 2
    refused = client.post("/api/experiments/draft", json={"words": WORDS_GERMINATION})
    assert refused.status_code == 422 and "metric" in str(refused.json()["detail"])
    assert logged_functions(db) == ["recipe", "recipe"]


def test_drafting_without_reasoning_is_unavailable(db, tmp_path):
    with api_client(db, tmp_path, reasoner=None) as client:
        assert client.post("/api/experiments/draft", json={"words": "Seeds in dishes"}).status_code == 503


def test_saved_recipe_versions_are_evidence(db, client, own_experiment):
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE experiment_recipes SET body='{}' WHERE experiment_id=?", (own_experiment,))


def test_the_toolbox_lists_what_argus_can_measure(client):
    tools = {t["method"]: t for t in client.get("/api/toolbox").json()}
    assert tools["touching_count"]["family"] == "count" and tools["touching_count"]["unit"] == "count"
    assert tools["skeleton_length"]["unit"] == "mm" and tools["skeleton_length"]["words"]


def test_the_recipe_detail_serves_own_recipes_and_templates(client, own_experiment):
    detail = client.get(f"/api/experiments/{own_experiment}/recipe/detail").json()
    assert detail["id"] == "own" and detail["concepts"] == ["seed", "root"]
    assert detail["main_measurement"] == "germinated" and {"id": "germinated", "unit": "count"} in detail["metrics"]
    template = client.post("/api/experiments", json={"title": "Dye", "recipe_id": "colour-reaction"}).json()
    assert client.get(f"/api/experiments/{template['id']}/recipe/detail").json()["id"] == "colour-reaction"
