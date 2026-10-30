"""Notes, verdicts and reviews over the HTTP API, and the verdict a run gets when it ends. No network."""

import pytest

from argus.domain import Direction, PlanDraft, RunMode, RunSource, SourceKind
from argus.storage.repos import add_model_call, create_experiment, create_run, lock_plan, save_plan_draft
from tests.api_client import api_client, wait_for
from tests.helpers import rois_around_the_bar, write_growing_bar_clip
from tests.reasoning import FakeReasoner, call, clean_note, critique, verdict_draft


class ByFunction(FakeReasoner):
    """The same answer every time a function asks."""

    def __init__(self, answers_by_function):
        super().__init__()
        self.by_function = answers_by_function

    async def __call__(self, task, **kwargs):
        self.answers = [self.by_function[task.function]]
        return await super().__call__(task, **kwargs)


ANSWERS = {
    "note": clean_note(observation="The bar in A grew."),
    "verdict_draft": verdict_draft("SUPPORTED", explanation="A's area rose above B's.", refs_used=[]),
    "verdict_critique": critique("INCONCLUSIVE"),
}


@pytest.fixture
def reasoner():
    return ByFunction(ANSWERS)


@pytest.fixture
def client(db, tmp_path, reasoner):
    with api_client(db, tmp_path, reasoner=reasoner) as test_client:
        yield test_client


def lock(db, experiment_id, **overrides):
    fields = dict(
        hypothesis="The bar grows.",
        prediction="A's area rises above B's.",
        threshold="Clearly above by the checkpoint.",
        rivals=[],
        metric="area",
        direction=Direction.HIGHER,
        min_effect=10.0,
        checkpoint_s=60.0,
    )
    save_plan_draft(db, experiment_id, PlanDraft(**(fields | overrides)))
    lock_plan(db, experiment_id)


@pytest.fixture
def run_id(db):
    exp = create_experiment(db, "Growing bar", "general", 1)
    return create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0)).id


@pytest.fixture
def capped_run(db):
    exp = create_experiment(db, "Growing bar", "general", 1)
    lock(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    add_model_call(db, run.id, 10.0, call(cost=10.0))
    return run.id


@pytest.fixture
def imported(client, db, tmp_path):
    """An import of the growing bar under a locked plan: A grows, B stays empty."""
    clip = write_growing_bar_clip(tmp_path / "videos" / "bar.mp4", frames=40)
    exp = client.post("/api/experiments", json={"title": "Growing bar", "recipe_id": "general"}).json()["id"]
    lock(db, exp)
    a, b = rois_around_the_bar()
    vessels = [{"label": "A", "role": "treatment", "roi": a}, {"label": "B", "role": "control", "roi": b}]
    body = {"mode": "imported", "paths": [str(clip)], "time_scale": 60.0, "vessels": vessels}
    run = client.post(f"/api/experiments/{exp}/runs", json=body).json()["run"]["id"]
    wait_for(lambda: not client.get(f"/api/runs/{run}").json()["running"])
    return run


def timeline(client, run_id):
    return client.get(f"/api/runs/{run_id}/timeline").json()


def test_a_researcher_note_is_saved_and_listed(client, run_id):
    posted = client.post(f"/api/runs/{run_id}/notes", json={"t": 30.0, "tag": "observation", "text": "Foam at 2 cm"})
    assert posted.status_code == 201, posted.text
    note = posted.json()
    assert note["author"] == "researcher" and note["check_status"] == "researcher" and note["tag"] == "observation"
    assert note["body"]["text"] == "Foam at 2 cm"  # the researcher's own words, numbers and all
    assert client.get(f"/api/runs/{run_id}/notes").json() == {"notes": [note], "rejected": 0, "models": {}}


def test_a_researcher_intervention_note_is_also_an_event(client, run_id):
    client.post(f"/api/runs/{run_id}/notes", json={"t": 30.0, "tag": "intervention", "text": "Added dye"})
    events = timeline(client, run_id)["events"]
    assert any(e["kind"] == "intervention" and e["source"] == "researcher" and e["t_start"] == 30.0 for e in events)


def test_notes_need_a_known_run_and_tag(client, run_id):
    assert client.get("/api/runs/nope/notes").status_code == 404
    bad = client.post(f"/api/runs/{run_id}/notes", json={"t": 30.0, "tag": "rumour", "text": "x"})
    assert bad.status_code == 422


def test_asking_for_a_verdict_at_the_spend_cap_says_why(client, capped_run):
    answer = client.post(f"/api/runs/{capped_run}/verdict")
    assert answer.status_code == 409 and "spend cap" in answer.json()["detail"]


def test_asking_for_a_verdict_without_a_locked_plan_says_why(client, run_id):
    answer = client.post(f"/api/runs/{run_id}/verdict")
    assert answer.status_code == 409 and "locked plan" in answer.json()["detail"]
    assert client.get(f"/api/runs/{run_id}/verdict").json() is None


def test_a_finished_run_gets_its_final_verdict_and_notes(client, imported):
    verdict = wait_for(lambda: client.get(f"/api/runs/{imported}/verdict").json())
    assert verdict["provisional"] is False and verdict["verdict"] in {"SUPPORTED", "INCONCLUSIVE", "NOT_SUPPORTED"}
    notes = client.get(f"/api/runs/{imported}/notes").json()["notes"]
    assert notes and notes[-1]["level"] == "checkpoint"  # the import's closing note


def test_a_verdict_asked_for_again_is_a_new_one(client, imported):
    first = wait_for(lambda: client.get(f"/api/runs/{imported}/verdict").json())
    again = client.post(f"/api/runs/{imported}/verdict")
    assert again.status_code == 200, again.text
    assert again.json()["id"] != first["id"] and client.get(f"/api/runs/{imported}/verdict").json() == again.json()


def test_a_review_is_saved(client, imported):
    verdict = wait_for(lambda: client.get(f"/api/runs/{imported}/verdict").json())
    body = {"t": 700.0, "target_kind": "verdict", "target_id": verdict["id"], "action": "confirm", "comment": "Agreed."}
    review = client.post(f"/api/runs/{imported}/reviews", json=body)
    assert review.status_code == 201, review.text
    assert review.json()["target_id"] == verdict["id"] and review.json()["action"] == "confirm"


def test_without_reasoning_a_verdict_is_unavailable(db, tmp_path, capped_run):
    with api_client(db, tmp_path, reasoner=None) as client:
        assert client.post(f"/api/runs/{capped_run}/verdict").status_code == 503


def test_the_worker_reasons_only_with_an_api_key(db, tmp_path):
    from argus.api.app import create_app
    from argus.api.events import EventBroker
    from argus.config import load_settings
    from argus.reason import SettingsReasoner

    keyed = load_settings({"ARGUS_DATA_DIR": str(tmp_path / "data"), "MODEL_API_KEY": "test-key"})
    keyless = keyed.model_copy(update={"model_api_key": None})
    assert isinstance(create_app(keyed, db, EventBroker(), {}).state.jobs.reasoner, SettingsReasoner)
    assert create_app(keyless, db, EventBroker(), {}).state.jobs.reasoner is None


def test_reviews_are_listed_for_the_verdict_panel(client, run_id):
    body = {
        "t": 10.0,
        "target_kind": "rival",
        "target_id": "lighting change",
        "action": "resolve",
        "comment": "Lamp off.",
    }
    assert client.get(f"/api/runs/{run_id}/reviews").json() == []
    saved = client.post(f"/api/runs/{run_id}/reviews", json=body).json()
    assert client.get(f"/api/runs/{run_id}/reviews").json() == [saved]


def test_each_ai_note_says_which_model_wrote_it(client, imported):
    wait_for(lambda: client.get(f"/api/runs/{imported}/verdict").json())
    view = client.get(f"/api/runs/{imported}/notes").json()
    written = [n for n in view["notes"] if n["model_call_id"]]
    assert written and all(view["models"][n["model_call_id"]] == "muse-spark-1.3" for n in written)
