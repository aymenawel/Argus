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


def run_with(db, exp, curves: dict[str, np.ndarray], *, quantity="half_time", unit="count"):
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
    roles = {"A": Role.CONTROL, "B": Role.CONTROL, "F": Role.CONTROL}
    roles |= {label: Role.TREATMENT for label in ("C", "D", "E", "pg1-1")}
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
            unit=unit,
            method_version="component_count/1",
        )
        for label, values in curves.items()
        for t, v in zip(TIMES_H, values, strict=True)
    ]
    add_measurements(db, run.id, rows)
    return run


def answers() -> FakeReasoner:
    return FakeReasoner([verdict_draft("INCONCLUSIVE", refs_used=[], explanation="Judged."), critique("INCONCLUSIVE")])


async def judge(db, run):
    return await run_verdict(db, EventBroker(), SETTINGS, run, recipe=RECIPE, reasoner=answers())


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


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("label", "curve"),
    [("E", "flat"), ("E", "unreached"), ("F", "flat")],
)
async def test_a_dish_with_no_half_way_time_caps_the_verdict(db, exp, label, curve):
    """A treatment dish where nothing germinated, or that was still rising, is evidence against "faster": dropping it
    would let the others carry the claim. Same for a control."""
    failed = np.zeros_like(TIMES_H) if curve == "flat" else logistic(10, 60)
    curves = {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}
    curves |= {"E": logistic(10, 14), label: failed}
    verdict = await judge(db, run_with(db, exp, curves))
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]
    named = check(verdict, f"fit:{label}")
    assert named is not None and named["ok"] is False and "Inconclusive" in named["text"]


def test_the_noise_floor_does_not_judge_fitted_effects():
    """The readings' noise floor is in counts; a half-way time's effect is in hours: only its own ± judges it."""
    from argus.analyze.ceiling import VerdictInputs, ceiling
    from argus.claims.refs import Ref

    def effect(label):
        return Ref(f"dt50:{label}:germinated", label, -8.0, 0.5, "h", "-8.0 ± 0.5 h", "difference", None, None)

    inputs = VerdictInputs(
        t=48 * 3600.0,
        running=False,
        locked=True,
        checkpoint_s=24 * 3600.0,
        controls=2,
        treatments=2,
        effects={"C": effect("C"), "D": effect("D")},
        noise=5.0,  # counts
        min_effect=2.0,
        direction=Direction.LOWER,
        rivals={},
        measured=True,
        quantity="half_time",
    )
    allowed, checks = ceiling(inputs)
    assert VerdictLevel.SUPPORTED in allowed
    assert all("noise floor" not in c.prompt for c in checks if c.id.startswith("effect:"))


@pytest.mark.anyio
async def test_a_rate_plan_ignores_the_rate_of_a_dish_still_rising(db, exp):
    curves = {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}
    verdict = await judge(db, run_with(db, exp, curves | {"E": logistic(10, 60)}, quantity="rate"))
    assert check(verdict, "effect:E") is None
    assert check(verdict, "fit:E") is not None and verdict.allowed == [VerdictLevel.INCONCLUSIVE]


@pytest.mark.anyio
async def test_fitted_plans_need_two_controls(db, exp):
    verdict = await judge(db, run_with(db, exp, {"A": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}))
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]
    assert check(verdict, "control")["ok"] is False and "2" in check(verdict, "control")["text"]


def test_a_dishs_uncertainty_includes_how_dishes_differ(db, exp):
    """A fit's ± covers the fit only; dishes of one condition differ by more (cumulative readings are autocorrelated),
    so each treatment's difference carries the spread between dishes."""
    import statistics

    from argus.claims.refs import build_refs
    from argus.storage.repos import first_locked_plan

    curves = {"A": logistic(10, 20), "B": logistic(10, 22), "C": logistic(10, 15), "D": logistic(10, 15.2)}
    run = run_with(db, exp, curves)
    refs = build_refs(db, run.id, 48 * 3600.0, recipe=RECIPE, plan=first_locked_plan(db, exp.id))
    t50 = {label: refs.get(f"t50:{label}:germinated").value for label in curves}
    pooled = ((statistics.variance([t50["A"], t50["B"]]) + statistics.variance([t50["C"], t50["D"]])) / 2) ** 0.5
    assert refs.get("dt50:C:germinated").uncertainty >= pooled


@pytest.mark.anyio
async def test_the_model_is_told_which_dish_has_no_fit(db, exp):
    """A note's numbers stay in the refs, but a dish's name is not a number: the model must know which dish failed."""
    curves = {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14), "D": logistic(10, 14)}
    run = run_with(db, exp, curves | {"pg1-1": np.zeros_like(TIMES_H)})
    reasoner = answers()
    await run_verdict(db, EventBroker(), SETTINGS, run, recipe=RECIPE, reasoner=reasoner)
    checks = next(block for block in reasoner.tasks[0].variable if block.startswith("CHECKS"))
    assert "No fit for pg1-1" in checks


@pytest.mark.anyio
@pytest.mark.parametrize(("quantity", "words"), [("half_time", "half-way times"), ("rate", "rates")])
async def test_the_plateau_note_names_the_judged_quantity_and_unit(db, exp, quantity, words):
    curves = {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(5, 14), "D": logistic(10, 14)}
    run = run_with(db, exp, curves, quantity=quantity, unit="mm")
    reasoner = answers()
    verdict = await run_verdict(db, EventBroker(), SETTINGS, run, recipe=RECIPE, reasoner=reasoner)
    text = check(verdict, "plateaus")["text"]
    assert words in text and " mm)" in text
    checks = next(block for block in reasoner.tasks[0].variable if block.startswith("CHECKS"))
    line = next(line for line in checks.splitlines() if "plateaus" in line)
    assert words in line and not any(c.isdigit() for c in line)
    assert all(word not in line for word in ("quarter", "halves")), line  # words the claim checker rejects


@pytest.mark.anyio
async def test_controls_without_a_fit_are_not_called_missing(db, exp):
    """The control dishes are there and measured; it's their curves that failed. The checks must say so."""
    flat = np.zeros_like(TIMES_H)
    verdict = await judge(db, run_with(db, exp, {"A": flat, "B": flat, "C": logistic(10, 14), "D": logistic(10, 14)}))
    control, replicates = check(verdict, "control")["text"], check(verdict, "replicates")["text"]
    assert "no control vessel" not in control.lower() and "2 control" in control and "fitted" in control
    assert "fitted" in replicates and "measured" not in replicates
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]


def test_a_fitted_plan_needs_the_recipe(db, exp):
    """Without the recipe there is no curve to fit, so no dish could be named as failed: refuse, don't skip."""
    from argus.claims.refs import build_refs
    from argus.pipeline.verdict import verdict_inputs
    from argus.storage.repos import first_locked_plan

    run = run_with(db, exp, {"A": logistic(10, 22), "B": logistic(10, 22), "C": logistic(10, 14)})
    plan = first_locked_plan(db, exp.id)
    refs = build_refs(db, run.id, 48 * 3600.0, recipe=RECIPE, plan=plan)
    with pytest.raises(ValueError, match="recipe"):
        verdict_inputs(db, run, refs, plan=plan, t=48 * 3600.0, recipe=None)
