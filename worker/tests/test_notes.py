"""The note writer: refs, a routine call, the claim check, one retry, a note written by code, quiet stretches."""

import numpy as np
import pytest
from pydantic import SecretStr

from argus.api.events import EventBroker
from argus.config import REPO_ROOT, Settings
from argus.domain import EventKind, MeasurementDraft, Role, RunMode, RunSource, SourceKind, VesselDraft
from argus.pipeline.analyzer import RunContext
from argus.pipeline.notes import note_interval_s
from argus.reason import ReasonError
from argus.recipes.loader import load_recipe
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_event,
    add_measurements,
    add_model_call,
    add_vessels,
    create_run,
    note_attempts_for_run,
    notes_for_run,
)
from tests.reasoning import FakeReasoner, call, clean_note
from tests.test_analyzer import FakeSegmenter

COLOUR = load_recipe(REPO_ROOT / "recipes" / "colour-reaction.toml")
GERMINATION = load_recipe(REPO_ROOT / "recipes" / "seed-germination.toml")
FRAME = np.full((480, 640, 3), 128, np.uint8)
ERROR_CALL = call(status="error", error="incomplete", cost=0.0)
STILL = (0.50, 0.52, 0.48, 0.51, 0.49)
FOUR = (("A", Role.CONTROL), ("B", Role.CONTROL), ("C", Role.TREATMENT), ("D", Role.TREATMENT))
LATE = {"A": 2.0, "B": 3.0, "C": 25.6, "D": 24.0}


def context(db, exp, tmp_path, vessels, readings) -> RunContext:
    """A live run whose delta_e readings are stored already: readings(label) -> [(t, value)]."""
    run = create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    drafts = [VesselDraft(label=label, role=role, roi=[(0, 0), (10, 0), (10, 10)]) for label, role in vessels]
    stored = add_vessels(db, run.id, drafts)
    rows = [
        MeasurementDraft(
            vessel_id=v.id,
            frame_id=None,
            t=t,
            metric="delta_e",
            value=value,
            uncertainty=0.05,
            unit="dE00",
            method_version="delta_e/1",
        )
        for v in stored
        for t, value in readings(v.label)
    ]
    add_measurements(db, run.id, rows)
    settings = Settings(model_api_key=SecretStr("k"), data_dir=tmp_path / "data")
    return RunContext(
        db=db,
        broker=EventBroker(),
        settings=settings,
        files=RunFiles(settings.data_dir, exp.id, run.id),
        recipe=COLOUR,
        run=run,
        vessels=stored,
        segmenter=FakeSegmenter(),
        reasoner=FakeReasoner(),
    )


def rising(label):
    return [(i * 10.0, v) for i, v in enumerate(STILL)] + [(300.0, LATE[label] / 2), (600.0, LATE[label])]


def still(label):
    return [(i * 10.0, STILL[i % len(STILL)]) for i in range(25)]


@pytest.fixture
def ctx(db, exp, tmp_path):
    return context(db, exp, tmp_path, FOUR, rising)


@pytest.fixture
def ctx_still(db, exp, tmp_path):
    ctx = context(db, exp, tmp_path, FOUR, still)
    ctx.reasoner = FakeReasoner([clean_note(observation="Nothing changed beyond the noise floor.")])
    return ctx


@pytest.fixture
def ctx_one_vessel(db, exp, tmp_path):
    return context(db, exp, tmp_path, (("A", Role.TREATMENT),), rising)


@pytest.fixture
def ctx_at_cap(db, exp, tmp_path):
    ctx = context(db, exp, tmp_path, FOUR, rising)
    add_model_call(db, ctx.run.id, 10.0, call(cost=ctx.settings.run_spend_cap_usd - 0.001))
    return ctx


def model_call_statuses(ctx):
    with ctx.db.read() as c:
        rows = c.execute(
            "SELECT status FROM model_calls WHERE run_id=? AND function='note' ORDER BY rowid", (ctx.run.id,)
        )
        return [r["status"] for r in rows]


def event(ctx, t, kind, source):
    return add_event(ctx.db, ctx.run.id, vessel_id=None, t_start=t, kind=kind, source=source, detail={})


def published(ctx, kind):
    return [e.data for e in ctx.broker.since(0) if e.type == kind]


def test_the_note_interval_follows_the_recipe():
    assert note_interval_s(COLOUR) == 120.0 and note_interval_s(GERMINATION) == 7200.0


@pytest.mark.anyio
async def test_a_checkpoint_note_is_checked_rendered_and_saved(ctx):
    ctx.reasoner = FakeReasoner([clean_note(observation="C changed by {ref:chg:C:delta_e}.")])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed" and "dE00" in note.body["observation"] and "{ref:" not in str(note.body)
    assert note.author == "ai" and note.level == "checkpoint" and "chg:C:delta_e" in note.refs
    assert [a.passed for a in note_attempts_for_run(ctx.db, ctx.run.id)] == [True]
    assert notes_for_run(ctx.db, ctx.run.id) == [note]
    assert published(ctx, "note")[0]["note"]["id"] == note.id
    task = ctx.reasoner.tasks[0]
    assert task.function == "note" and "MEASUREMENTS" in task.variable[0] and "checkpoint" in task.variable[-1]


@pytest.mark.anyio
async def test_a_rejected_note_is_retried_once_with_its_reasons(ctx):
    ctx.reasoner = FakeReasoner(
        [clean_note(observation="Changed by 25."), clean_note(observation="Changed by {ref:chg:C:delta_e}.")]
    )
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed" and "number outside a ref" in ctx.reasoner.tasks[1].variable[-1]
    attempts = note_attempts_for_run(ctx.db, ctx.run.id)
    assert [a.passed for a in attempts] == [False, True]
    assert published(ctx, "note_rejected") == [
        {"run_id": ctx.run.id, "t": 600.0, "attempt_id": attempts[0].id, "reasons": attempts[0].reasons}
    ]


@pytest.mark.anyio
async def test_two_failures_save_a_code_note(ctx):
    ctx.reasoner = FakeReasoner([ReasonError("incomplete", ERROR_CALL), clean_note(observation="Changed by 25.")])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "fallback" and note.body["written_by"] == "code"
    assert "Vessel C: delta_e" in note.body["observation"]  # from the refs alone
    assert model_call_statuses(ctx) == ["error", "ok"]
    assert [a.reasons for a in note_attempts_for_run(ctx.db, ctx.run.id)][0] == ["incomplete"]


@pytest.mark.anyio
async def test_a_status_above_the_ceiling_is_rejected(ctx):
    ctx.reasoner = FakeReasoner([clean_note(hypothesis_status="SUPPORTED"), clean_note()])
    note = await ctx.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed" and note.body["hypothesis_status"] == "TOO_EARLY"  # no locked plan
    assert "status above the ceiling: SUPPORTED" in note_attempts_for_run(ctx.db, ctx.run.id)[0].reasons


@pytest.mark.anyio
async def test_quiet_stretches_collapse_into_one_note(ctx_still):
    first = await ctx_still.notes.write(120.0, "checkpoint", image_bgr=FRAME)
    again = await ctx_still.notes.write(180.0, "checkpoint", image_bgr=FRAME)
    still_again = await ctx_still.notes.write(240.0, "checkpoint", image_bgr=FRAME)
    assert again.id == first.id == still_again.id and still_again.t_end == 240.0
    assert ctx_still.reasoner.calls == 1 and len(notes_for_run(ctx_still.db, ctx_still.run.id)) == 1


@pytest.mark.anyio
async def test_a_change_after_a_quiet_note_gets_its_own_note(ctx_still):
    ctx_still.reasoner.answers.append(clean_note(observation="A rose to {ref:m:A:delta_e}."))
    first = await ctx_still.notes.write(120.0, "checkpoint", image_bgr=FRAME)
    a = ctx_still.vessels[0]
    add_measurements(
        ctx_still.db,
        ctx_still.run.id,
        [
            MeasurementDraft(
                vessel_id=a.id,
                frame_id=None,
                t=250.0,
                metric="delta_e",
                value=5.0,
                uncertainty=0.05,
                unit="dE00",
                method_version="delta_e/1",
            )
        ],
    )
    second = await ctx_still.notes.write(260.0, "checkpoint", image_bgr=FRAME)
    assert second.id != first.id and ctx_still.reasoner.calls == 2


@pytest.mark.anyio
async def test_a_single_vessel_run_still_gets_notes(ctx_one_vessel):
    ctx_one_vessel.reasoner = FakeReasoner([clean_note(observation="A reads {ref:m:A:delta_e}.")])
    note = await ctx_one_vessel.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert note.check_status == "passed"  # no control: no diff refs, and nothing raises


def test_watcher_changes_alone_never_trigger_a_note(ctx):
    assert ctx.notes.due(30.0, [event(ctx, 30.0, EventKind.CHANGE, "watcher")]) is None
    assert ctx.notes.due(40.0, [event(ctx, 40.0, EventKind.INTERVENTION, "quality")]) == "event"


def test_notes_are_due_on_schedule_and_on_events(ctx):
    assert ctx.notes.due(119.0, []) is None and ctx.notes.due(120.0, []) == "checkpoint"
    assert ctx.notes.due(10.0, [event(ctx, 10.0, EventKind.RULE, "rule")]) is None  # too soon after the start
    assert ctx.notes.due(30.0, []) == "event"  # the rule crossing waited for the gap, it wasn't forgotten


def test_without_a_reasoner_no_note_is_ever_due(ctx):
    ctx.reasoner = None
    assert ctx.notes.due(600.0, [event(ctx, 600.0, EventKind.CAMERA_MOVED, "quality")]) is None


@pytest.mark.anyio
async def test_the_spend_cap_pauses_notes_once(ctx_at_cap):
    first = await ctx_at_cap.notes.write(600.0, "checkpoint", image_bgr=FRAME)
    assert first.check_status == "fallback" and "spend cap" in first.body["reason"]
    assert await ctx_at_cap.notes.write(720.0, "checkpoint", image_bgr=FRAME) is None
    assert ctx_at_cap.reasoner.calls == 0 and len(notes_for_run(ctx_at_cap.db, ctx_at_cap.run.id)) == 1
