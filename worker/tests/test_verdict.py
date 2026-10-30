"""The verdict pipeline: ceiling in code, a Wonder draft and critique, checked, the most cautious allowed choice."""

import time

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
    return db, fill(db, run)


def fill(db, run):
    """Two room-temperature controls (A, B) and two warm treatments (C, D) with clear effects by 600 s."""
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
    return run


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


@pytest.mark.anyio
async def test_a_plan_locked_after_the_run_started_is_not_judged_against(db, exp):
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    time.sleep(0.05)  # past the clock's tick (about 15 ms on Windows): the same instant counts as before
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)  # after the run began: written with the data in view, so not a prediction
    draft = verdict_draft("TOO_EARLY", explanation="The plan came after the data.", refs_used=[])
    verdict = await judge(db, run, FakeReasoner([draft, critique("TOO_EARLY")]))
    assert verdict.allowed == [VerdictLevel.TOO_EARLY] and verdict.checks[0]["id"] == "plan"


@pytest.mark.anyio
async def test_too_early_is_written_by_code_without_a_model_call(db, exp):
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    verdict = await judge(db, run, FakeReasoner([]))  # before the checkpoint: the only answer is Too early
    assert verdict.verdict is VerdictLevel.TOO_EARLY and verdict.allowed == [VerdictLevel.TOO_EARLY]
    assert verdict.body["written_by"] == "code" and "checkpoint" in verdict.body["explanation"]
    assert model_calls(db, run) == [] and verdict.model_call_ids == []


@pytest.mark.anyio
async def test_a_draft_with_an_unknown_verdict_is_retried(judged):
    db, run = judged
    reasoner = FakeReasoner([verdict_draft("PROVEN"), verdict_draft("SUPPORTED"), critique("SUPPORTED")])
    verdict = await judge(db, run, reasoner)
    assert (
        "verdict: 'PROVEN' is not one of" in reasoner.tasks[1].variable[-1]
        and verdict.verdict is VerdictLevel.SUPPORTED
    )


@pytest.mark.anyio
async def test_a_critique_with_an_unknown_verdict_is_dropped(judged):
    db, run = judged
    verdict = await judge(db, run, FakeReasoner([verdict_draft("SUPPORTED"), critique("MAYBE")]))
    assert verdict.critique is None
    assert any(r.startswith("revised_verdict: 'MAYBE' is not one of") for r in verdict.body["critique_dropped"])


@pytest.mark.anyio
async def test_a_malformed_draft_is_retried_and_a_malformed_critique_dropped(judged):
    db, run = judged
    broken = verdict_draft("SUPPORTED")
    del broken["explanation"]
    bad_critique = critique(
        "INCONCLUSIVE", findings=[{"item": "vibes", "problem": "x", "consequence": "y", "fix": "z"}]
    )
    reasoner = FakeReasoner([broken, verdict_draft("SUPPORTED"), bad_critique])
    verdict = await judge(db, run, reasoner)
    assert "missing field: explanation" in reasoner.tasks[1].variable[-1]
    assert verdict.critique is None and any(r.startswith("findings[0].item") for r in verdict.body["critique_dropped"])


@pytest.mark.anyio
async def test_the_rivals_shown_are_the_plans_with_codes_state(judged):
    db, run = judged
    draft = verdict_draft(
        "SUPPORTED",
        rivals=[
            {"name": "Lighting changes from lamps", "status": "open", "reason": "Paraphrased."},
            {"name": "a rival nobody planned", "status": "ruled_out", "reason": "Invented."},
        ],
    )
    verdict = await judge(db, run, FakeReasoner([draft, critique("SUPPORTED")]))
    # The plan names one rival, "lighting change", and code resolved it (colour was corrected throughout).
    assert [(r["name"], r["status"]) for r in verdict.body["rivals"]] == [("lighting change", "ruled_out")]
    assert "Paraphrased" not in str(verdict.body["rivals"]) and "Invented" not in str(verdict.body["rivals"])


@pytest.mark.anyio
async def test_a_rival_keeps_the_models_reason_when_name_and_status_agree(judged):
    db, run = judged
    draft = verdict_draft(
        "SUPPORTED",
        rivals=[{"name": "lighting change", "status": "ruled_out", "reason": "Colour was corrected throughout."}],
    )
    verdict = await judge(db, run, FakeReasoner([draft, critique("SUPPORTED")]))
    assert verdict.body["rivals"] == [
        {"name": "lighting change", "status": "ruled_out", "reason": "Colour was corrected throughout."}
    ]


@pytest.mark.anyio
async def test_treatment_vessels_without_readings_count_for_nothing(db, exp):
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    drafts = [
        VesselDraft(label=label, role=role, condition=Condition(factor="t", value=value), roi=[(0, 0), (9, 0), (9, 9)])
        for label, role, value in (
            ("A", Role.CONTROL, "room"),
            ("B", Role.CONTROL, "room"),
            ("C", Role.TREATMENT, "warm"),
            ("D", Role.TREATMENT, "warm"),
        )
    ]
    vessels = {v.label: v for v in add_vessels(db, run.id, drafts)}
    rows = [
        MeasurementDraft(
            vessel_id=vessels[label].id,
            frame_id=None,
            t=t,
            metric="delta_e",
            value=0.5 + 0.01 * (i % 3),
            uncertainty=0.05,
            unit="dE00",
            method_version="delta_e/1",
        )
        for label in ("A", "B")
        for i, t in enumerate((0.0, 10.0, 20.0, 30.0, 600.0))
    ]
    add_measurements(db, run.id, rows)  # the treatment vessels were never measured
    verdict = await judge(
        db,
        run,
        FakeReasoner([verdict_draft("INCONCLUSIVE", refs_used=[], explanation="None."), critique("INCONCLUSIVE")]),
    )
    replicates = next(c for c in verdict.checks if c["id"] == "replicates")
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE] and replicates["ok"] is False
    assert "0 of 2" in replicates["text"]


@pytest.mark.anyio
async def test_an_import_recorded_before_the_plan_was_locked_is_not_judged(db, exp):
    from datetime import UTC, datetime

    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)  # locked now, but the recording started yesterday
    source = RunSource(kind=SourceKind.VIDEO, paths=["run.mp4"], start_time=datetime(2026, 10, 28, 9, 0, tzinfo=UTC))
    run = create_run(db, exp.id, RunMode.IMPORTED, source, time_scale=1.0)
    verdict = await judge(db, run, FakeReasoner([]))
    assert verdict.allowed == [VerdictLevel.TOO_EARLY] and verdict.checks[0]["id"] == "plan"


@pytest.mark.anyio
async def test_an_import_without_a_recording_start_says_it_cant_confirm_the_plan_came_first(db, exp):
    save_plan_draft(db, exp.id, plan(checkpoint_s=0.0))
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.IMPORTED, RunSource(kind=SourceKind.VIDEO, paths=["run.mp4"]), time_scale=1.0)
    answers = [verdict_draft("INCONCLUSIVE", explanation="Nothing measured.", refs_used=[]), critique("INCONCLUSIVE")]
    verdict = await judge(db, run, FakeReasoner(answers))
    flag = next(c for c in verdict.checks if c["id"] == "preregistered")
    assert flag["ok"] is None and "recording" in flag["text"]


@pytest.mark.anyio
async def test_the_verdict_reads_and_writes_off_the_event_loop(judged, monkeypatch):
    import threading

    import argus.pipeline.verdict as module

    on_loop: list[bool] = []
    for name in ("build_refs", "add_verdict", "add_model_call", "run_spend_usd"):
        real = getattr(module, name)

        def spy(*args, _real=real, **kwargs):
            on_loop.append(threading.current_thread() is threading.main_thread())
            return _real(*args, **kwargs)

        monkeypatch.setattr(module, name, spy)
    db, run = judged
    await judge(db, run, FakeReasoner([verdict_draft(), critique("SUPPORTED")]))
    assert on_loop and not any(on_loop)  # live capture shares the loop: a long run's refs take seconds


@pytest.mark.anyio
async def test_only_one_verdict_is_written_at_a_time(judged):
    import asyncio

    db, run = judged
    release = asyncio.Event()

    class Slow(FakeReasoner):
        async def __call__(self, task, **kwargs):
            await release.wait()
            return await super().__call__(task, **kwargs)

    first = asyncio.create_task(judge(db, run, Slow([verdict_draft(), critique("SUPPORTED")])))
    await asyncio.sleep(0.5)
    with pytest.raises(VerdictRefused, match="being written"):
        await judge(db, run, FakeReasoner([]))
    release.set()
    assert (await first).verdict is VerdictLevel.SUPPORTED


@pytest.mark.anyio
async def test_the_spend_cap_is_checked_before_each_call(judged):
    db, run = judged
    add_model_call(db, run.id, 10.0, call(cost=SETTINGS.run_spend_cap_usd - 0.16))  # a verdict fits, just
    costly = ReasonResult(verdict_draft(), call("verdict_draft", tier="deep", cost=0.10), "muse-wonder-1.0", False)
    verdict = await judge(db, run, FakeReasoner([costly]))
    assert model_calls(db, run)[-1] == ("verdict_draft", "ok") and verdict.critique is None
    assert any("spend cap" in r for r in verdict.body["critique_dropped"])


def published_source(tmp_path, runs_by_label: dict[str, str]):
    """A published, retrospective import recorded yesterday, its tiles from the given source runs."""
    import json
    from datetime import UTC, datetime

    from argus.domain import Provenance

    tiles = [
        {"label": label, "condition": "x", "run": source_run, "dish": i, "box": [0, 0, 10, 10], "seeds": 10}
        for i, (label, source_run) in enumerate(runs_by_label.items())
    ]
    fields = {"dataset": "Plates", "doi": "10.0/x", "url": "https://example.org", "licence": "CC BY 4.0"}
    body = fields | {"credit": "Lab", "interval_s": 1800, "frames": ["f.jpg"], "tiles": tiles}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    provenance = Provenance(**fields, credit="Lab", assembled=True, retrospective=True)
    return RunSource(
        kind=SourceKind.IMAGES,
        manifest=str(path),
        provenance=provenance,
        start_time=datetime(2020, 5, 1, 9, 0, tzinfo=UTC),  # recorded long before the plan
    )


ONE_RUN = {"A": "sc1", "B": "sc1", "C": "sc1", "D": "sc1"}
TWO_RUNS = {"A": "sc1", "B": "sc1", "C": "pg2", "D": "pg2"}


def answers():
    return FakeReasoner([verdict_draft("INCONCLUSIVE", refs_used=[], explanation="Judged."), critique("INCONCLUSIVE")])


@pytest.mark.anyio
async def test_published_data_is_judged_retrospectively(db, exp, tmp_path):
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)  # long after the data was recorded, but before Argus measured it
    run = fill(db, create_run(db, exp.id, RunMode.IMPORTED, published_source(tmp_path, ONE_RUN)))
    verdict = await judge(db, run, answers())
    assert verdict.allowed == [VerdictLevel.SUPPORTED, VerdictLevel.INCONCLUSIVE]
    flag = next(c for c in verdict.checks if c["id"] == "retrospective")
    assert flag["ok"] is None and "after" in flag["text"]
    assert not any(c["id"] == "preregistered" for c in verdict.checks) and verdict.body["retrospective"] is True


@pytest.mark.anyio
async def test_the_same_import_without_provenance_stays_too_early(db, exp, tmp_path):
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)
    source = published_source(tmp_path, ONE_RUN).model_copy(update={"provenance": None, "kind": SourceKind.VIDEO})
    run = fill(db, create_run(db, exp.id, RunMode.IMPORTED, source))
    verdict = await judge(db, run, FakeReasoner([]))
    assert verdict.allowed == [VerdictLevel.TOO_EARLY] and verdict.body.get("retrospective") is False


@pytest.mark.anyio
async def test_a_plan_locked_after_argus_measured_published_data_is_not_judged(db, exp, tmp_path):
    run = fill(db, create_run(db, exp.id, RunMode.IMPORTED, published_source(tmp_path, ONE_RUN)))
    time.sleep(0.05)
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)  # written with Argus's numbers in view
    verdict = await judge(db, run, FakeReasoner([]))
    assert verdict.allowed == [VerdictLevel.TOO_EARLY]


@pytest.mark.anyio
async def test_dishes_from_different_source_runs_add_an_open_rival_until_resolved(db, exp, tmp_path):
    save_plan_draft(db, exp.id, plan())
    lock_plan(db, exp.id)
    run = fill(db, create_run(db, exp.id, RunMode.IMPORTED, published_source(tmp_path, TWO_RUNS)))
    assert rival_states(db, run, [])["run-to-run differences"] == "open"
    verdict = await judge(db, run, answers())
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]
    assert next(c for c in verdict.checks if c["id"] == "rival:run-to-run differences")["ok"] is None
    review = ReviewDraft(
        t=600.0,
        target_kind="rival",
        target_id="run-to-run differences",
        action="resolve",
        comment="Same rig, same paper and same lab conditions in every run, per the paper's methods.",
    )
    add_review(db, run.id, review)
    verdict = await judge(db, run, answers())
    assert verdict.allowed == [VerdictLevel.SUPPORTED, VerdictLevel.INCONCLUSIVE]


def test_dishes_from_one_source_run_add_no_rival(db, exp, tmp_path):
    run = create_run(db, exp.id, RunMode.IMPORTED, published_source(tmp_path, ONE_RUN))
    fill(db, run)
    assert "run-to-run differences" not in rival_states(db, run, ["lighting change"])


@pytest.mark.anyio
async def test_readings_that_never_moved_give_no_not_supported_even_with_rivals_resolved(db, exp, tmp_path):
    """The Genze state: every count 0 ± 0 (SAM saw no roots); resolving every rival must not make it a finding."""
    save_plan_draft(db, exp.id, plan(rivals=[], min_effect=2.0))
    lock_plan(db, exp.id)
    run = create_run(db, exp.id, RunMode.IMPORTED, published_source(tmp_path, ONE_RUN))
    drafts = [
        VesselDraft(label=label, role=role, condition=Condition(factor="t", value=value), roi=[(0, 0), (9, 0), (9, 9)])
        for label, role, value in (
            ("A", Role.CONTROL, "room"),
            ("B", Role.CONTROL, "room"),
            ("C", Role.TREATMENT, "warm"),
            ("D", Role.TREATMENT, "warm"),
        )
    ]
    vessels = add_vessels(db, run.id, drafts)
    rows = [
        MeasurementDraft(
            vessel_id=v.id,
            frame_id=None,
            t=t,
            metric="delta_e",
            value=0.0,
            uncertainty=0.0,
            unit="dE00",
            method_version="delta_e/1",
        )
        for v in vessels
        for t in (0.0, 100.0, 200.0, 300.0, 600.0)
    ]
    add_measurements(db, run.id, rows)
    verdict = await judge(db, run, answers())
    assert verdict.allowed == [VerdictLevel.INCONCLUSIVE]
    assert next(c for c in verdict.checks if c["id"] == "registered")["ok"] is False
