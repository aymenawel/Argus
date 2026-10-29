"""Prompt files, strict schemas and the assembly of a reasoning call's input (spec §7.1, prompts/README.md)."""

import shutil
from datetime import UTC, datetime

import cv2
import numpy as np
import pytest

import argus.reason.prompts as prompts
from argus.claims.refs import Ref, RefTable
from argus.domain import Direction, Experiment, ExperimentStatus, Plan
from argus.reason.prompts import (
    describe_task,
    load_prompt,
    load_schema,
    measurements_block,
    note_task,
    plan_block,
    prompt_version,
    snapshot_jpeg,
    verdict_task,
)
from argus.recipes.loader import load_recipe

COLOUR = load_recipe(prompts.REPO_ROOT / "recipes" / "colour-reaction.toml")
PLAN = Plan(
    experiment_id="exp_1",
    version=1,
    hypothesis="Warm water spreads dye faster.",
    prediction="Warm glasses change colour sooner than room-temperature ones.",
    threshold="A clear difference by the checkpoint.",
    rivals=["lighting change", "temperature"],
    metric="delta_e",
    direction=Direction.HIGHER,
    min_effect=5.0,
    checkpoint_s=300.0,
    treatment="warm",
    locked_at=datetime(2026, 10, 29, 12, 0, tzinfo=UTC),
    sha256="ab" * 32,
)
EXPERIMENT = Experiment(
    id="exp_1",
    title="Dye",
    recipe_id="colour-reaction",
    recipe_version=1,
    status=ExperimentStatus.LOCKED,
    created_at=datetime(2026, 10, 29, tzinfo=UTC),
)


def ref(id_: str, display: str) -> Ref:
    return Ref(
        id=id_,
        label=id_.replace(":", " "),
        value=1.0,
        uncertainty=0.1,
        unit="dE00",
        display=display,
        kind="measurement",
        t=10.0,
        vessel_id=None,
        evidence=(),
    )


def refs_at(t: float) -> RefTable:
    return RefTable(
        {r.id: r for r in (ref("m:C:delta_e", f"{t:.1f} ± 0.1 dE00"), ref("chg:C:delta_e", "2.0 ± 0.1 dE00"))}
    )


def objects_in(node):
    if isinstance(node, dict):
        if node.get("type") == "object":
            yield node
        for value in node.values():
            yield from objects_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from objects_in(value)


@pytest.mark.parametrize("name", ["note", "verdict", "verdict_critique", "recipe_draft"])
def test_schemas_are_strict(name):
    schema = load_schema(name)
    assert "$comment" not in str(schema)
    for node in objects_in(schema):
        assert node["additionalProperties"] is False and set(node["required"]) == set(node["properties"])


def test_note_schema_v2_cites_refs_not_numbers():
    schema = load_schema("note")
    assert "refs_used" in schema["properties"] and "numbers_used" not in schema["properties"]


def test_the_stable_prefix_comes_first_and_is_identical_across_calls():
    a = note_task("checkpoint", COLOUR, PLAN, refs_at(10.0), [], [])
    b = note_task("event", COLOUR, PLAN, refs_at(20.0), [], [])
    assert a.stable == b.stable and a.stable[0].startswith("# Argus scientific rules")
    assert "<!--" not in a.stable[0]  # HTML comments are for people, not the model
    assert "MEASUREMENTS (cite only as" not in "".join(a.stable)  # data never sits in the cached prefix
    assert a.function == "note" and a.experiment_id == "exp_1" and a.prompt_version == prompt_version(COLOUR)
    assert "checkpoint" in a.variable[-1] and "event" in b.variable[-1]


def test_the_plan_block_says_which_version_and_cites_plan_values_as_refs():
    block = plan_block(PLAN)
    assert "LOCKED PLAN (version 1" in block and "{ref:plan:min_effect}" in block and "{ref:plan:checkpoint}" in block
    assert "lighting change" in block and plan_block(None) == "NO LOCKED PLAN"


def test_the_measurements_block_lists_every_ref_once_sorted():
    block = measurements_block(refs_at(10.0))
    lines = block.splitlines()
    assert lines[0] == "MEASUREMENTS (cite only as {ref:<id>})"
    assert lines[1:] == [
        "chg:C:delta_e | chg C delta_e | 2.0 ± 0.1 dE00",
        "m:C:delta_e | m C delta_e | 10.0 ± 0.1 dE00",
    ]


def test_a_rejected_note_is_retried_with_its_reasons():
    task = note_task("event", COLOUR, PLAN, refs_at(10.0), [], [], rejected=["unknown ref: x1"])
    assert "unknown ref: x1" in task.variable[-1] and "rejected" in task.variable[-1]


def test_the_verdict_task_carries_the_checks_and_the_allowed_verdicts():
    task = verdict_task(
        COLOUR,
        PLAN,
        refs_at(400.0),
        checks=["Past the checkpoint."],
        allowed=["SUPPORTED", "INCONCLUSIVE"],
        events=[],
        notes=[],
    )
    text = "\n".join(task.variable)
    assert task.function == "verdict_draft" and "Past the checkpoint." in text and "SUPPORTED, INCONCLUSIVE" in text


def test_describe_fills_the_recipes_metrics_into_the_schema():
    task, schema = describe_task(EXPERIMENT, COLOUR, "Does warm water spread dye faster?")
    assert task.function == "describe" and "Does warm water spread dye faster?" in task.variable[-1]
    assert schema["properties"]["metric"]["enum"] == ["delta_e"]


def test_prompt_version_changes_when_a_prompt_changes(tmp_path, monkeypatch):
    before = prompt_version(COLOUR)
    copy = tmp_path / "prompts"
    shutil.copytree(prompts.PROMPTS_DIR, copy)
    monkeypatch.setattr(prompts, "PROMPTS_DIR", copy)
    assert prompt_version(COLOUR) == before
    card = copy / "recipes" / "colour-reaction" / "method.md"
    card.write_text(card.read_text(encoding="utf-8") + "\nOne more line.", encoding="utf-8")
    assert prompt_version(COLOUR) != before


def test_every_recipe_has_a_short_method_card():
    for recipe in ("seed-germination", "colour-reaction", "foam-height", "general"):
        card = load_prompt(f"recipes/{recipe}/method.md")
        assert 40 < len(card.split()) <= 250


def test_the_rules_say_numbers_come_only_as_refs():
    rules = load_prompt("system/scientific-rules.md")
    assert "{ref:" in rules and "Safety" in rules


def test_snapshots_are_jpegs_768_px_on_the_long_side():
    image = np.zeros((1200, 1600, 3), np.uint8)
    decoded = cv2.imdecode(np.frombuffer(snapshot_jpeg(image), np.uint8), cv2.IMREAD_COLOR)
    assert max(decoded.shape[:2]) == 768 and decoded.shape[1] == 768
