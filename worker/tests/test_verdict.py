"""The verdict pipeline: ceiling in code, a Wonder draft and critique, checked, the most cautious allowed choice."""

import pytest
from pydantic import SecretStr

from argus.api.events import EventBroker
from argus.config import REPO_ROOT, Settings
from argus.domain import (
    Condition,
    Direction,
    EventKind,
    MeasurementDraft,
    PlanDraft,
    ReviewDraft,
    Role,
    RunMode,
    RunSource,
    SourceKind,
    VerdictLevel,
    VesselDraft,
)
from argus.pipeline.verdict import VerdictRefused, rival_states, run_verdict
from argus.reason import ReasonResult
from argus.recipes.loader import load_recipe
from argus.storage.repos import (
    add_event,
    add_measurements,
    add_model_call,
    add_review,
    add_vessels,
    create_run,
    get_run,
    latest_verdict,
    lock_plan,
    save_plan_draft,
)
from tests.reasoning import FakeReasoner, call, critique, verdict_draft

COLOUR = load_recipe(REPO_ROOT / "recipes" / "colour-reaction.toml")
SETTINGS = Settings(model_api_key=SecretStr("k"))
# delta_e per vessel: five still readings, a watcher change at 50 s, then the dye's effect.
LATE = {"A": (2.0, 4.0), "B": (3.0, 5.0), "C": (10.0, 25.6), "D": (9.0, 24.0)}


def plan(**overrides) -> PlanDraft:
    fields = dict(
        hypothesis="Warm water spreads dye faster.",
        prediction="Warm glasses change colour more.",
        threshold="Clearly more by the checkpoint.",
        rivals=["lighting change"],
        metric="delta_e",
        direction=Direction.HIGHER,
        min_effect=5.0,
        checkpoint_s=300.0,
        treatment="warm",
    )
    return PlanDraft(**(fields | overrides))


@pytest.fixture
def judged(db, exp):
    """A run with two room-temperature controls and two warm treatments, past its checkpoint."""
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    drafts = [
        VesselDraft(
            label=label,
            role=role,
            condition=Condition(factor="water temperature", value=value),
            roi=[(0, 0), (10, 0), (10, 10)],
        )
        for label, role, value in (
            ("A", Role.CONTROL, "room"),
            ("B", Role.CONTROL, "room"),
            ("C", Role.TREATMENT, "warm"),
            ("D", Role.TREATMENT, "warm"),
        )
    ]
    vessels = add_vessels(db, run.id, drafts)
    rows = []
    for v in vessels:
        still = [0.50, 0.52, 0.48, 0.51, 0.49]
        for i, value in enumerate(still):
            rows.append((v.id, i * 10.0, value))
        rows += [(v.id, 300.0, LATE[v.label][0]), (v.id, 600.0, LATE[v.label][1])]
        add_event(db, run.id, vessel_id=v.id, t_start=50.0, kind=EventKind.CHANGE, source="watcher", detail={})
    add_measurements(
        db,
        run.id,
        [
            MeasurementDraft(
                vessel_id=vid,
                frame_id=None,
                t=t,
                metric="delta_e",
                value=value,
                uncertainty=0.05,
                unit="dE00",
                method_version="delta_e/1",
            )
            for vid, t, value in rows
        ],
    )
    return db, run


def model_calls(db, run):
    with db.read() as c:
        return [
            (r["function"], r["status"])
            for r in c.execute("SELECT function, status FROM model_calls WHERE run_id=? ORDER BY rowid", (run.id,))
        ]


async def judge(db, run, reasoner, settings=SETTINGS):
    return await run_verdict(db, EventBroker(), settings, run, recipe=COLOUR, reasoner=reasoner)


@pytest.mark.anyio
async def test_a_verdict_is_drafted_critiqued_checked_and_stored(judged):
    db, run = judged
    reasoner = FakeReasoner([verdict_draft("SUPPORTED"), critique("INCONCLUSIVE")])
    verdict = await judge(db, run, reasoner)
    assert set(verdict.allowed) == {VerdictLevel.SUPPORTED, VerdictLevel.INCONCLUSIVE}
    assert verdict.verdict is VerdictLevel.INCONCLUSIVE and verdict.provisional is True  # the run is still going
    assert "dE00" in verdict.body["explanation"] and "{ref:" not in verdict.body["explanation"]
    assert (
        verdict.body["findings"][0]["item"] == "unit_of_analysis"
        and verdict.critique["revised_verdict"] == "INCONCLUSIVE"
    )
    assert {c["id"] for c in verdict.checks} >= {"checkpoint", "control", "replicates", "effect:C", "effect:D"}
    assert model_calls(db, run) == [("verdict_draft", "ok"), ("verdict_critique", "ok")]
    assert latest_verdict(db, run.id) == verdict
    assert [t.function for t in reasoner.tasks] == ["verdict_draft", "verdict_critique"]


@pytest.mark.anyio
async def test_the_verdict_uses_the_first_locked_plan(judged):
    db, run = judged
    save_plan_draft(db, run.experiment_id, plan(hypothesis="A later idea."))
    lock_plan(db, run.experiment_id)
    reasoner = FakeReasoner([verdict_draft(), critique("SUPPORTED")])
    await judge(db, run, reasoner)
    assert (
        "version 1" in reasoner.tasks[0].stable[2] and "Warm water spreads dye faster." in reasoner.tasks[0].stable[2]
    )


@pytest.mark.anyio
async def test_a_draft_with_free_numbers_is_retried_then_written_by_code(judged):
    db, run = judged
    reasoner = FakeReasoner(
        [
            verdict_draft(explanation="C rose by 20."),
            verdict_draft(explanation="C rose by about twenty."),
            critique("INCONCLUSIVE"),
        ]
    )
    verdict = await judge(db, run, reasoner)
    assert "number outside a ref" in reasoner.tasks[1].variable[-1]
    assert verdict.body["written_by"] == "code" and verdict.verdict is VerdictLevel.INCONCLUSIVE
    assert "20" not in verdict.draft.get("explanation", "")


@pytest.mark.anyio
async def test_a_critique_with_free_numbers_is_dropped(judged):
    db, run = judged
    verdict = await judge(
        db,
        run,
        FakeReasoner([verdict_draft("SUPPORTED"), critique("INCONCLUSIVE", confidence_reason="Only 2 vessels.")]),
    )
    assert verdict.critique is None and verdict.verdict is VerdictLevel.SUPPORTED
    assert any("number outside a ref" in r for r in verdict.body["critique_dropped"])


@pytest.mark.anyio
async def test_a_deep_fallback_is_recorded(judged):
    db, run = judged
    fell_back = ReasonResult(
        verdict_draft(),
        call("verdict_draft", model="muse-spark-1.3", tier="deep"),
        "muse-spark-1.3",
        fell_back=True,
        failed_calls=(
            call("verdict_draft", status="error", model="muse-wonder-1.0", tier="deep", error="boom", cost=0.0),
        ),
    )
    verdict = await judge(db, run, FakeReasoner([fell_back, critique("SUPPORTED")]))
    assert verdict.fell_back is True
    assert model_calls(db, run)[:2] == [("verdict_draft", "error"), ("verdict_draft", "ok")]


@pytest.mark.anyio
async def test_no_locked_plan_is_refused(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    with pytest.raises(VerdictRefused, match="no locked plan"):
        await judge(db, run, FakeReasoner())


@pytest.mark.anyio
async def test_the_spend_cap_is_refused(judged):
    db, run = judged
    add_model_call(db, run.id, 10.0, call(cost=9.95))
    with pytest.raises(VerdictRefused, match="spend cap"):
        await judge(db, run, FakeReasoner())


@pytest.mark.anyio
async def test_a_stopped_run_gets_a_final_verdict(judged):
    db, run = judged
    from argus.domain import RunStatus
    from argus.storage.repos import set_run_status

    set_run_status(db, run.id, RunStatus.STOPPED)
    verdict = await judge(db, get_run(db, run.id), FakeReasoner([verdict_draft(), critique("SUPPORTED")]))
    assert verdict.provisional is False and verdict.verdict is VerdictLevel.SUPPORTED


def test_rivals_are_resolved_by_their_checks_or_by_the_researcher(judged):
    db, run = judged
    assert rival_states(db, run, ["lighting change", "camera exposure"]) == {
        "lighting change": "resolved",
        "camera exposure": "resolved",
    }
    add_event(
        db,
        run.id,
        vessel_id=None,
        t_start=50.0,
        kind=EventKind.QUALITY,
        source="quality",
        detail={"message": "colour not corrected: the card is not in view"},
    )
    assert rival_states(db, run, ["lighting change", "temperature"]) == {
        "lighting change": "open",
        "temperature": "open",
    }
    add_review(
        db,
        run.id,
        ReviewDraft(
            t=60.0,
            target_kind="rival",
            target_id="temperature",
            action="resolve",
            comment="All four glasses sat side by side in one room.",
        ),
    )
    assert rival_states(db, run, ["temperature"]) == {"temperature": "resolved"}
    add_event(
        db,
        run.id,
        vessel_id=None,
        t_start=70.0,
        kind=EventKind.CAMERA_MOVED,
        source="quality",
        detail={"message": "card moved: recalibrated"},
    )
    add_event(db, run.id, vessel_id=None, t_start=80.0, kind=EventKind.INTERVENTION, source="researcher", detail={})
    assert rival_states(db, run, ["camera movement", "handling"]) == {"camera movement": "open", "handling": "open"}
