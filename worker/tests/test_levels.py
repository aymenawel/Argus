"""The next levels of a numeric factor (D-80): Ax proposes them from each finished vessel's level and judged outcome,
inside the tested range widened by half its width (never below 0). A categorical factor gets none, and says so."""

import pytest

from argus.analyze import next_run
from argus.analyze.levels import level_bounds, suggest_levels
from argus.analyze.next_run import next_run_numbers
from argus.domain import (
    Condition,
    Direction,
    MeasurementDraft,
    PlanDraft,
    Role,
    RunMode,
    RunSource,
    RunStatus,
    SourceKind,
    VesselDraft,
)
from argus.recipes.model import Recipe
from argus.storage.repos import (
    add_measurements,
    add_vessels,
    create_experiment,
    create_run,
    first_locked_plan,
    lock_plan,
    save_plan_draft,
    set_run_status,
)

RECIPE = Recipe.model_validate(
    {
        "id": "foam-height",
        "version": 1,
        "title": "Foam",
        "default_mode": "continuous",
        "analysis_step_s": 60,
        "curve": "logistic",
        "concepts": [{"name": "foam"}],
        "measurements": [{"id": "foam_mm", "family": "size", "method": "height", "from": "foam", "unit": "mm"}],
        "main_measurement": "foam_mm",
    }
)


def run_with(db, conditions: dict[str, float | str], final: dict[str, float]):
    """One vessel per label at its condition, reading `final` mm at the checkpoint, with a locked 'higher' plan."""
    exp = create_experiment(db, "Yeast foam", "foam-height", 1)
    save_plan_draft(
        db,
        exp.id,
        PlanDraft(
            hypothesis="Warmer water makes more foam.",
            prediction="Warmer vessels foam higher.",
            threshold="By at least five millimetres.",
            rivals=[],
            metric="foam_mm",
            direction=Direction.HIGHER,
            min_effect=5.0,
            checkpoint_s=600.0,
            treatment=None,
        ),
    )
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    factor = "temperature" if all(isinstance(v, float) for v in conditions.values()) else "species"
    vessels = add_vessels(
        db,
        run.id,
        [
            VesselDraft(
                label=label,
                role=Role.CONTROL if i == 0 else Role.TREATMENT,
                condition=Condition(factor=factor, value=value, unit="°C" if factor == "temperature" else None),
                roi=[(0, 0), (9, 0), (9, 9)],
            )
            for i, (label, value) in enumerate(conditions.items())
        ],
    )
    rows = [
        MeasurementDraft(
            vessel_id=v.id,
            frame_id=None,
            t=float(t),
            metric="foam_mm",
            value=final[v.label] * t / 600,
            uncertainty=0.5,
            unit="mm",
            method_version="height/1",
        )
        for v in vessels
        for t in range(0, 601, 60)
    ]
    add_measurements(db, run.id, rows)
    return set_run_status(db, run.id, RunStatus.FINISHED), first_locked_plan(db, exp.id)


def test_bounds_widen_the_tested_range_and_stay_non_negative():
    assert level_bounds([20.0, 40.0]) == (10.0, 50.0)
    assert level_bounds([0.0, 10.0]) == (0.0, 15.0)
    low, high = level_bounds([20.0, 20.0])  # one level: still a range around it
    assert 0 <= low < 20.0 < high


def test_ax_suggests_levels_inside_the_bounds():
    tested = [(level, 100 - (level - 30) ** 2) for level in (10.0, 15.0, 20.0, 25.0, 35.0, 40.0)]
    bounds = level_bounds([level for level, _ in tested])
    levels = suggest_levels(tested, minimize=False, bounds=bounds, count=3, seed=0)
    assert len(levels) == 3
    assert all(bounds[0] <= level <= bounds[1] for level in levels)
    assert levels == sorted(levels)


def test_a_categorical_factor_gets_no_levels(db):
    run, plan = run_with(db, {"A": "rye", "B": "pearl millet", "C": "pearl millet"}, {"A": 20, "B": 30, "C": 31})
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert numbers.levels == [] and "isn't numeric" in numbers.levels_reason


def test_a_numeric_factor_gets_three_levels_inside_the_bounds(db):
    conditions = {"A": 20.0, "B": 25.0, "C": 30.0, "D": 35.0, "E": 40.0, "F": 45.0}
    final = {label: 50 - (value - 35) ** 2 / 10 for label, value in conditions.items()}
    run, plan = run_with(db, conditions, final)
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert len(numbers.levels) == 3 and numbers.levels_unit == "°C"
    assert all(7.5 <= level <= 57.5 for level in numbers.levels)
    assert "Ax" in numbers.levels_reason


def test_a_failing_level_search_says_why(db, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("no model fitted")

    monkeypatch.setattr(next_run, "suggest_levels", broken)
    run, plan = run_with(db, {"A": 20.0, "B": 30.0, "C": 40.0}, {"A": 20, "B": 30, "C": 25})
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert numbers.levels == [] and numbers.levels_reason == "the level search failed: no model fitted"
    assert numbers.hours is not None or numbers.hours_reason  # the rest of the suggestion stands


@pytest.mark.parametrize("levels", [[20.0], [20.0, 20.0]])
def test_one_tested_level_is_too_few_to_search(db, levels):
    conditions = {label: value for label, value in zip("ABC", levels, strict=False)}
    run, plan = run_with(db, conditions, {label: 30 for label in conditions})
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert numbers.levels == [] and "two" in numbers.levels_reason


@pytest.mark.anyio
async def test_levels_are_refs_the_model_may_cite(db):
    from argus.pipeline.next_run import suggest_next_run
    from tests.reasoning import FakeReasoner
    from tests.test_verdict import SETTINGS

    conditions = {"A": 20.0, "B": 25.0, "C": 30.0, "D": 35.0, "E": 40.0, "F": 45.0}
    run, _ = run_with(db, conditions, {label: 50 - (value - 35) ** 2 / 10 for label, value in conditions.items()})
    cited = {
        "why": "Try {ref:next:level:1} next, then {ref:next:level:3}.",
        "change": "Keep the vessels side by side.",
        "watch_for": "If the foam spills, stop early.",
        "refs_used": ["next:level:1", "next:level:3"],
    }
    suggestion = await suggest_next_run(db, run, RECIPE, FakeReasoner([cited]), SETTINGS)
    first, third = suggestion.numbers["levels"][0], suggestion.numbers["levels"][2]
    assert suggestion.body["written_by"] == "model"
    assert f"{first:g} °C" in suggestion.body["why"] and f"{third:g} °C" in suggestion.body["why"]


def test_numeric_conditions_stored_as_text_get_levels(db):
    """The setup stores a condition as the researcher typed it ("20 °C"), so a numeric factor arrives as text."""
    conditions = {"A": "20 °C", "B": "25 °C", "C": "30 °C", "D": "35 °C", "E": "40 °C", "F": "45 °C"}
    final = {label: 50 - (float(value.split()[0]) - 35) ** 2 / 10 for label, value in conditions.items()}
    run, plan = run_with(db, conditions, final)
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert len(numbers.levels) == 3 and numbers.levels_unit == "°C"


def test_a_text_control_is_left_out_of_the_level_search(db):
    conditions = {"A": "water", "B": "5 g/L", "C": "10 g/L", "D": "15,5 g/L"}
    run, plan = run_with(db, conditions, {"A": 20, "B": 25, "C": 30, "D": 28})
    numbers = next_run_numbers(db, run, RECIPE, plan)
    assert len(numbers.levels) == 3 and numbers.levels_unit == "g/L"
    assert all(0 <= level <= 20.75 for level in numbers.levels)


def test_ax_picks_come_from_its_model_on_a_small_plate():
    """Without the change, Ax spends its first picks on quasi-random exploration and they read as optimised."""
    from argus.analyze.levels import level_picks

    tested = [(level, 100 - (level - 30) ** 2) for level in (20.0, 25.0, 30.0, 40.0)]
    picks = level_picks(tested, minimize=False, bounds=level_bounds([t for t, _ in tested]), count=3, seed=0)
    assert len(picks) == 3 and all(how == "MBM" for _, how in picks)
