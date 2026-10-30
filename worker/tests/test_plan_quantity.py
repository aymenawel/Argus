"""The plan says what it predicts (D-78): a level, a half-way time or a rate. Unset means a level, so plans locked
before keep their hash."""

import pytest

from argus.domain import Direction, PlanDraft, plan_sha256
from argus.recipes.draft import draft_recipe
from tests.api_client import api_client
from tests.reasoning import FakeReasoner
from tests.test_recipe_draft import TEMPLATES, WORDS_GERMINATION, answer

# plan_sha256 of this plan before `quantity` existed (computed on Oct 30, 2026).
HASH_BEFORE = "8f979a606094fdbd00d02b0d93606c0024b3df37292eef07154bf7e1910ad2ac"


def sample(**overrides) -> PlanDraft:
    fields = dict(
        hypothesis="h",
        prediction="p",
        threshold="t",
        rivals=["light"],
        metric="area",
        direction=Direction.HIGHER,
        min_effect=1.0,
        checkpoint_s=60.0,
        treatment=None,
    )
    return PlanDraft(**(fields | overrides))


def plan_body(**overrides) -> dict:
    return sample(**overrides).model_dump(mode="json")


@pytest.fixture
def client(db, tmp_path):
    with api_client(db, tmp_path) as test_client:
        yield test_client


def test_an_unset_quantity_keeps_a_locked_plans_hash():
    assert sample().quantity is None and plan_sha256(sample()) == HASH_BEFORE
    assert plan_sha256(sample(quantity="half_time")) != HASH_BEFORE


def test_a_quantity_is_saved_and_read_back(client):
    exp = client.post("/api/experiments", json={"title": "Seeds", "recipe_id": "seed-germination"}).json()
    body = plan_body(metric="root_length", quantity="half_time", direction="lower", min_effect=2.0)
    saved = client.put(f"/api/experiments/{exp['id']}/plan", json=body)
    assert saved.status_code == 200, saved.text
    assert client.get(f"/api/experiments/{exp['id']}/plan").json()[-1]["quantity"] == "half_time"


def test_a_linear_recipe_has_no_half_way_time(client):
    exp = client.post("/api/experiments", json={"title": "Anything", "recipe_id": "general"}).json()
    refused = client.put(f"/api/experiments/{exp['id']}/plan", json=plan_body(quantity="half_time"))
    assert refused.status_code == 422 and "has no half-way time" in refused.json()["detail"]
    assert client.put(f"/api/experiments/{exp['id']}/plan", json=plan_body(quantity="rate")).status_code == 200


@pytest.mark.anyio
async def test_a_draft_carries_the_quantity():
    plan = answer()["plan"] | {"quantity": "half_time", "direction": "lower", "min_effect": 2}
    draft, _ = await draft_recipe(WORDS_GERMINATION, reasoner=FakeReasoner([answer(plan=plan)]), templates=TEMPLATES)
    assert draft.plan.quantity == "half_time"


def test_the_prompts_state_a_fitted_prediction_in_its_own_terms():
    from datetime import UTC, datetime

    from argus.domain import Plan
    from argus.reason.prompts import plan_block

    def block(quantity):
        fields = sample(quantity=quantity, direction=Direction.LOWER).model_dump()
        locked = datetime(2026, 10, 30, tzinfo=UTC)
        return plan_block(Plan(**fields, experiment_id="exp", version=1, locked_at=locked, sha256="x"))

    assert "reads lower than the controls" in block("level")
    half = block("half_time")
    assert "half-way time" in half and "sooner" in half and "reads lower" not in half
    assert "fitted rate" in block("rate")


@pytest.mark.parametrize("name", ["setup/describe.md", "setup/recipe.md"])
def test_the_drafting_prompts_put_the_smallest_effect_in_the_judged_quantitys_unit(name):
    """A half-way plan's smallest effect is in hours: a draft in seeds would be judged against hours."""
    from argus.reason.prompts import load_prompt

    line = next(line for line in load_prompt(name).splitlines() if "smallest difference" in line)
    assert "hours" in line and "per hour" in line, line
