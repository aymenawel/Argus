"""Recipe rule events: `when = "<metric> <op> <number>"`, parsed without eval, fired once per vessel."""

import pytest
from pydantic import ValidationError

from argus.analyze.rules import Rule, RuleEvaluator, parse_rule
from argus.config import REPO_ROOT
from argus.domain import Measurement
from argus.pipeline.analyzer import analyze_frame
from argus.recipes.loader import load_recipe
from argus.recipes.model import Recipe
from argus.storage.repos import events_for_run
from tests.test_analyzer import RECIPE, ctx, scene  # noqa: F401  (pytest fixtures)

COLOUR = load_recipe(REPO_ROOT / "recipes" / "colour-reaction.toml")


def reading(vessel: str, t: float, value: float, metric: str = "delta_e") -> Measurement:
    return Measurement(
        id=f"mea_{vessel}{t}",
        vessel_id=vessel,
        frame_id=None,
        t=t,
        metric=metric,
        value=value,
        uncertainty=0.1,
        unit="dE00",
        method_version="delta_e/1",
    )


def colour_with_event(when: str) -> dict:
    data = COLOUR.model_dump(by_alias=True)
    data["events"] = [{"id": "switch", "when": when}]
    return data


@pytest.mark.parametrize(
    "when, rule",
    [
        ("delta_e > 20", Rule("switch", "delta_e", ">", 20.0)),
        ("delta_e>=20.5", Rule("switch", "delta_e", ">=", 20.5)),
        ("  delta_e <  -1 ", Rule("switch", "delta_e", "<", -1.0)),
        ("delta_e <= 3", Rule("switch", "delta_e", "<=", 3.0)),
    ],
)
def test_rules_parse(when, rule):
    assert parse_rule("switch", when) == rule


@pytest.mark.parametrize("when", ["delta_e >", "__import__('os')", "delta_e > 20 or 1", "delta_e == 3", "> 3"])
def test_bad_rules_dont_parse(when):
    with pytest.raises(ValueError):
        parse_rule("switch", when)


@pytest.mark.parametrize("when", ["delta_e >", "__import__('os')", "unknown > 3"])
def test_bad_rules_are_refused_at_load(when):
    with pytest.raises(ValidationError):
        Recipe.model_validate(colour_with_event(when))


def test_a_rule_on_a_not_yet_measured_method_loads_and_never_fires():
    germination = load_recipe(REPO_ROOT / "recipes" / "seed-germination.toml")  # first_sprout: sprouted >= 1
    assert RuleEvaluator(germination).fired([reading("A", 10.0, 5.0, metric="root_length")]) == []


def test_a_rule_fires_once_per_vessel_at_its_first_crossing():
    evaluator = RuleEvaluator(COLOUR)  # switch: delta_e > 20
    assert evaluator.fired([reading("A", 10.0, 3.0)]) == []
    [(rule, m)] = evaluator.fired([reading("A", 11.0, 21.0), reading("B", 11.0, 2.0)])
    assert rule.id == "switch" and m.vessel_id == "A" and m.t == 11.0
    assert evaluator.fired([reading("A", 12.0, 25.0)]) == []
    [(rule, m)] = evaluator.fired([reading("B", 13.0, 30.0)])
    assert m.vessel_id == "B"


@pytest.mark.anyio
async def test_the_analyzer_stores_and_publishes_rule_events(ctx, scene):  # noqa: F811
    image, _ = scene
    data = RECIPE.model_dump(by_alias=True)
    data["events"] = [{"id": "long_root", "when": "length > 30"}]
    ctx.recipe = Recipe.model_validate(data)
    ctx.rules = RuleEvaluator(ctx.recipe)
    for t in (0.0, 60.0):
        await analyze_frame(ctx, t, image, segment=True)
    [event] = [e for e in events_for_run(ctx.db, ctx.run.id) if e.kind == "rule"]
    assert event.detail["rule"] == "long_root" and event.source == "rule" and event.t_start == 0.0
    assert event.vessel_id == ctx.vessels[0].id and event.detail["measurement_id"].startswith("mea_")
    assert [e.data["kind"] for e in ctx.broker.since(0) if e.type == "event"].count("rule") == 1
