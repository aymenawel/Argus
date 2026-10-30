"""Argus drafts a recipe from the researcher's words, within its measuring toolbox, checked by code (D-73)."""

import os

import pytest

from argus.config import REPO_ROOT, load_settings
from argus.reason import ReasonError, SettingsReasoner
from argus.recipes.draft import RecipeRefused, draft_recipe, safety_screen
from argus.recipes.loader import load_all
from argus.recipes.toolbox import TOOLBOX, recipe_spec_schema
from tests.reasoning import FakeReasoner, call

WORDS_GERMINATION = "I'll compare how fast rye and pearl millet seeds germinate in petri dishes"
TEMPLATES = load_all(REPO_ROOT / "recipes")


def answer(**overrides) -> dict:
    """A valid germination answer, with the given fields replaced (a plan field by its own name)."""
    plan = {
        "hypothesis": "Pearl millet germinates faster than rye.",
        "prediction": "Millet dishes count more seeds with a root than rye dishes at the checkpoint.",
        "threshold": "A clear difference at the checkpoint.",
        "metric": "germinated",
        "direction": "higher",
        "min_effect": 2,
        "checkpoint_s": 86400,
        "treatment": "pearl millet",
    }
    body = {
        "title": "Germination speed in petri dishes",
        "concepts": ["seed", "root"],
        "measurements": [
            {"id": "root_length", "method": "skeleton_length", "from": "root", "touching": None, "min_length_mm": None},
            {"id": "germinated", "method": "touching_count", "from": "seed", "touching": "root", "min_length_mm": 2},
        ],
        "main_measurement": "germinated",
        "analysis_step_s": 1800,
        "curve": "logistic",
        "rivals": ["position in the frame", "seed batch"],
        "plan": plan,
        "setup_hints": {
            "factor": "species",
            "factor_unit": "",
            "conditions": [{"value": "rye", "role": "control"}, {"value": "pearl millet", "role": "treatment"}],
        },
        "safety_notes": [],
        "question_for_researcher": "",
    }
    for key, value in overrides.items():
        if key in plan:
            body["plan"] = {**body["plan"], key: value}
        else:
            body[key] = value
    return body


@pytest.mark.anyio
async def test_a_valid_answer_becomes_a_recipe_and_a_plan():
    draft, calls = await draft_recipe(WORDS_GERMINATION, reasoner=FakeReasoner([answer()]), templates=TEMPLATES)
    assert draft.recipe.id == "own" and draft.recipe.concepts[0].name == "seed"
    assert draft.recipe.main_measurement == "germinated"
    germinated = next(m for m in draft.recipe.measurements if m.id == "germinated")
    assert (germinated.family, germinated.unit, germinated.touching) == ("count", "count", "root")
    assert draft.plan.metric in draft.recipe.stored_metrics() and draft.plan.treatment == "pearl millet"
    assert len(calls) == 1 and calls[0].function == "recipe"


@pytest.mark.anyio
async def test_an_unmeasurable_answer_is_retried_with_its_reasons():
    bad = answer(
        concepts=["growth of seeds and roots"],
        measurements=[{"id": "g", "method": "volume", "from": "x", "touching": None, "min_length_mm": None}],
    )
    reasoner = FakeReasoner([bad, answer()])
    draft, calls = await draft_recipe(WORDS_GERMINATION, reasoner=reasoner, templates=TEMPLATES)
    retry = reasoner.tasks[1].variable[-1]
    assert "method: 'volume' is not one of" in retry and "one thing" in retry
    assert len(calls) == 2 and draft.recipe.concepts[1].name == "root"


@pytest.mark.anyio
async def test_two_bad_answers_are_refused_with_the_reasons():
    with pytest.raises(RecipeRefused) as refused:
        await draft_recipe(
            WORDS_GERMINATION, reasoner=FakeReasoner([answer(metric="nonsense")] * 2), templates=TEMPLATES
        )
    assert any("metric" in r for r in refused.value.reasons) and len(refused.value.calls) == 2


@pytest.mark.anyio
async def test_a_failed_call_counts_as_a_failed_answer():
    error = ReasonError("timeout", call("recipe", status="error", error="timeout", cost=0.0))
    draft, calls = await draft_recipe(WORDS_GERMINATION, reasoner=FakeReasoner([error, answer()]), templates=TEMPLATES)
    assert [c.status for c in calls] == ["error", "ok"] and draft.recipe.concepts


@pytest.mark.anyio
async def test_hazardous_words_carry_the_fixed_warning():
    draft, _ = await draft_recipe(
        "I will heat sugar over a candle flame and film it", reasoner=FakeReasoner([answer()]), templates=TEMPLATES
    )
    assert any(n.startswith("Argus won't automate any hardware") and "flame" in n for n in draft.safety_notes)


def test_food_acids_are_not_hazards():
    assert safety_screen("apple slices dipped in ascorbic acid or citric acid", ["apple slice"]) == []
    assert safety_screen("drops of hydrochloric acid on chalk", ["chalk"]) != []


def test_a_touching_count_needs_a_known_concept_and_a_length():
    from argus.recipes.model import Recipe

    with pytest.raises(ValueError, match="touching"):
        Recipe.model_validate(
            {
                "id": "own",
                "version": 1,
                "title": "x",
                "default_mode": "smart_trigger",
                "analysis_step_s": 60,
                "curve": "linear",
                "concepts": [{"name": "seed"}],
                "measurements": [
                    {
                        "id": "n",
                        "family": "count",
                        "method": "touching_count",
                        "from": "seed",
                        "unit": "count",
                        "touching": "root",
                        "min_length_mm": 2,
                    }
                ],
                "main_measurement": "n",
            }
        )


def test_the_schema_offers_only_the_toolbox():
    schema = recipe_spec_schema()
    methods = schema["properties"]["measurements"]["items"]["properties"]["method"]["enum"]
    assert set(methods) == {t.method for t in TOOLBOX}


@pytest.mark.slow  # real Muse Spark calls; skipped without MODEL_API_KEY
@pytest.mark.skipif(not os.environ.get("MODEL_API_KEY"), reason="needs MODEL_API_KEY")
@pytest.mark.anyio
@pytest.mark.parametrize(
    "words",
    [
        WORDS_GERMINATION,
        "Dough rising in four jars, two with extra sugar",
        "Apple slices browning, half dipped in vitamin C",
    ],
)
async def test_real_drafts_validate_without_edits(words):
    reasoner = SettingsReasoner(load_settings())
    try:
        draft, _ = await draft_recipe(words, reasoner=reasoner, templates=TEMPLATES)
    finally:
        await reasoner.aclose()
    assert draft.recipe.concepts and draft.plan.metric in draft.recipe.stored_metrics()
