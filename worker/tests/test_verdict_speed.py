"""The verdict on a half-way time (D-78, D-79): each vessel's fitted time to half its plateau, each treatment's
difference from the controls' mean, judged with the same rules as a level; refused or unreached fits are named and
count for nothing."""

import numpy as np
import pytest

from argus.api.events import EventBroker
from argus.domain import (
    Condition,
    Direction,
    MeasurementDraft,
    PlanDraft,
    Role,
    RunMode,
    RunSource,
    SourceKind,
    VerdictLevel,
    VesselDraft,
)
from argus.pipeline.verdict import run_verdict
from argus.recipes.model import Recipe
from argus.storage.repos import add_measurements, add_vessels, create_run, lock_plan, save_plan_draft
from tests.reasoning import FakeReasoner, critique, verdict_draft
from tests.test_verdict import SETTINGS

RECIPE = Recipe.model_validate(
    {
        "id": "own",
        "version": 1,
        "title": "Germination",
        "default_mode": "continuous",
        "analysis_step_s": 1800,
        "curve": "logistic",
        "concepts": [{"name": "seed"}],
        "measurements": [
            {"id": "germinated", "family": "count", "method": "component_count", "from": "seed", "unit": "count"}
        ],
        "main_measurement": "germinated",
    }
)
TIMES_H = np.arange(0.0, 48.01, 0.5)


def logistic(K, t50, r=0.5):
    return K / (1 + np.exp(-r * (TIMES_H - t50)))


def run_with(db, exp, curves: dict[str, np.ndarray], *, quantity="half_time"):
    """Vessels A, B (rye, control) and C, D (millet, treatment) with the given readings, and a locked plan."""
    plan = PlanDraft(
        hypothesis="Millet germinates faster than rye.",
        prediction="Millet dishes reach half their final count sooner.",
        threshold="At least two hours sooner.",
        rivals=[],
        metric="germinated",
        direction=Direction.LOWER if quantity == "half_time" else Direction.HIGHER,
        min_effect=2.0 if quantity == "half_time" else 1.0,
        checkpoint_s=86400.0,
        treatment=None,
        quantity=quantity,
    )
    save_plan_draft(db, exp.id, plan)
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    roles = {"A": Role.CONTROL, "B": Role.CONTROL, "C": Role.TREATMENT, "D": Role.TREATMENT}
    drafts = [
        VesselDraft(
            label=label,
            role=roles[label],
            condition=Condition(factor="species", value="rye" if roles[label] is Role.CONTROL else "millet"),
            roi=[(0, 0), (9, 0), (9, 9)],
        )
        for label in curves
    ]
    vessels = {v.label: v for v in add_vessels(db, run.id, drafts)}
    rng = np.random.default_rng(3)
    rows = [
        MeasurementDraft(
            vessel_id=vessels[label].id,
            frame_id=None,
            t=float(t * 3600),
            metric="germinated",
            value=float(v + rng.normal(0, 0.1)) if np.ptp(values) > 0 else 0.0,
            uncertainty=0.0,
            unit="count",
            method_version="component_count/1",
        )
        for label, values in curves.items()
        for t, v in zip(TIMES_H, values, strict=True)
    ]
    add_measurements(db, run.id, rows)
    return run


async def judge(db, run):
    answers = [verdict_draft("INCONCLUSIVE", refs_used=[], explanation="Judged."), critique("INCONCLUSIVE")]
    return await run_verdict(db, EventBroker(), SETTINGS, run, recipe=RECIPE, reasoner=FakeReasoner(answers))


def check(verdict, id_):
    return next((c for c in verdict.checks if c["id"] == id_), None)


@pytest.mark.anyio
async def test_clearly_faster_treatments_allow_supported(db, exp):
    run = run_with(
        db, exp, {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}
    )
    verdict = await judge(db, run)
    assert VerdictLevel.SUPPORTED in verdict.allowed
    assert check(verdict, "fits")["ok"] is True and "half-way times" in check(verdict, "fits")["text"]
    assert check(verdict, "noise") is None
    assert check(verdict, "effect:C")["ok"] is True and "h" in check(verdict, "effect:C")["text"]


@pytest.mark.anyio
async def test_equal_speeds_with_tight_fits_allow_not_supported(db, exp):
    run = run_with(
        db, exp, {"A": logistic(10, 20), "B": logistic(10, 20), "C": logistic(10, 20), "D": logistic(10, 20)}
    )
    verdict = await judge(db, run)
    assert VerdictLevel.NOT_SUPPORTED in verdict.allowed and check(verdict, "fits") is not None


@pytest.mark.anyio
async def test_a_refused_or_unreached_fit_is_named_and_counts_for_nothing(db, exp):
    flat = np.zeros_like(TIMES_H)
    run = run_with(db, exp, {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": flat})
    verdict = await judge(db, run)
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]
    named = check(verdict, "fit:D")
    assert named is not None and named["ok"] is False and "never rose" in named["text"]


@pytest.mark.anyio
async def test_very_different_plateaus_are_named(db, exp):
    run = run_with(db, exp, {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(5, 14), "D": logistic(10, 14)})
    verdict = await judge(db, run)
    plateaus = check(verdict, "plateaus")
    assert plateaus is not None and plateaus["ok"] is None and "plateaus differ" in plateaus["text"]


@pytest.mark.anyio
async def test_a_level_plan_is_judged_as_before(db, exp):
    curves = {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}
    run = run_with(db, exp, curves, quantity=None)
    verdict = await judge(db, run)
    assert check(verdict, "fits") is None and check(verdict, "noise") is not None
    assert not any(r.startswith("t50:") for r in verdict.refs)


@pytest.mark.parametrize(("quantity", "unit"), [("half_time", "h"), ("rate", "count/h"), ("level", "count")])
def test_the_smallest_effect_is_in_the_judged_quantitys_unit(db, exp, quantity, unit):
    from argus.claims.refs import build_refs
    from argus.storage.repos import first_locked_plan

    run = run_with(db, exp, {"A": logistic(10, 22), "C": logistic(10, 14)}, quantity=quantity)
    refs = build_refs(db, run.id, 48 * 3600.0, recipe=RECIPE, plan=first_locked_plan(db, exp.id))
    ref = refs.get("plan:min_effect")
    assert ref is not None and ref.unit == unit
    if unit != "count":  # a count prints bare
        assert ref.display.endswith(f" {unit}")
