"""Phase 3 storage: structured plans, setups, derived numbers, notes, note attempts, verdicts and reviews."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import argus.storage
from argus.domain import (
    DerivedDraft,
    Direction,
    NoteAttemptDraft,
    NoteDraft,
    PlanDraft,
    ReviewDraft,
    Role,
    RunSource,
    Setup,
    SetupVessel,
    SourceKind,
    VerdictDraft,
    VerdictLevel,
    plan_sha256,
)
from argus.storage.db import Database
from argus.storage.repos import (
    add_derived,
    add_note,
    add_note_attempt,
    add_review,
    add_verdict,
    derived_for_run,
    extend_note,
    first_locked_plan,
    get_plans,
    get_setup,
    latest_verdict,
    lock_plan,
    note_attempts_for_run,
    notes_for_run,
    reviews_for_run,
    save_plan_draft,
    save_setup,
)

MIGRATIONS = Path(argus.storage.__file__).parent / "migrations"


def note(t=10.0, **overrides):
    fields = dict(
        t=t,
        t_end=None,
        author="ai",
        level="checkpoint",
        tag=None,
        body={"observation": "No change."},
        refs=[],
        evidence=[],
        check_status="passed",
        model_call_id=None,
    )
    return NoteDraft(**{**fields, **overrides})


def derived(t=10.0):
    return DerivedDraft(
        t=t,
        kind="change",
        label="A change since start",
        value=2.5,
        uncertainty=0.1,
        unit="dE00",
        inputs=["mea_1", "mea_2"],
        method_version="change/1",
    )


def attempt(t=10.0):
    return NoteAttemptDraft(
        t=t, attempt=1, raw={"observation": "25"}, reasons=["number"], passed=False, model_call_id=None
    )


def verdict(t=10.0):
    return VerdictDraft(
        t=t,
        provisional=True,
        allowed=[VerdictLevel.TOO_EARLY],
        checks=[{"id": "checkpoint", "ok": False, "text": "Before the checkpoint."}],
        verdict=VerdictLevel.TOO_EARLY,
        body={"explanation": "Too early."},
        draft={"verdict": "TOO_EARLY"},
        critique=None,
        refs=[],
        model_call_ids=[],
        fell_back=False,
    )


def review(t=10.0):
    return ReviewDraft(t=t, target_kind="rival", target_id="temperature", action="resolve", comment="Same room.")


def phase_1_hash(draft: PlanDraft) -> str:
    """The hash as phase 1 computed it, over the four fields that existed then."""
    fields = {
        "hypothesis": draft.hypothesis,
        "prediction": draft.prediction,
        "threshold": draft.threshold,
        "rivals": draft.rivals,
    }
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_structured_plan_fields_keep_old_hashes(db, exp):
    old = PlanDraft(hypothesis="Salt slows roots", prediction="shorter", threshold="10 %", rivals=["lighting change"])
    assert plan_sha256(old) == phase_1_hash(old)  # plans locked in phase 1 still verify
    full = old.model_copy(
        update={
            "metric": "delta_e",
            "direction": Direction.HIGHER,
            "min_effect": 5.0,
            "checkpoint_s": 600.0,
            "treatment": "warm",
        }
    )
    assert plan_sha256(full) != plan_sha256(old)
    save_plan_draft(db, exp.id, full)
    locked = lock_plan(db, exp.id)
    assert locked.direction is Direction.HIGHER and locked.checkpoint_s == 600.0 and locked.treatment == "warm"
    assert lock_plan(db, exp.id).sha256 == locked.sha256 == plan_sha256(full)  # idempotent


def test_edits_after_the_lock_leave_the_first_locked_plan(db, exp):
    assert first_locked_plan(db, exp.id) is None
    save_plan_draft(db, exp.id, PlanDraft(hypothesis="h1", prediction="p", threshold="t", rivals=[]))
    lock_plan(db, exp.id)
    save_plan_draft(db, exp.id, PlanDraft(hypothesis="h2", prediction="p", threshold="t", rivals=[]))
    lock_plan(db, exp.id)
    assert first_locked_plan(db, exp.id).hypothesis == "h1"


def test_setup_round_trips_and_defaults_empty(db, exp):
    assert get_setup(db, exp.id) == Setup()
    setup = Setup(
        source=RunSource(kind=SourceKind.WEBCAM, camera_index=1),
        print_check_mm=100.0,
        factor="water temperature",
        vessels=[SetupVessel(label="A", role=Role.CONTROL, roi=[(0, 0), (10, 0), (10, 10)])],
    )
    assert save_setup(db, exp.id, setup) == setup
    assert get_setup(db, exp.id) == setup
    changed = setup.model_copy(update={"print_check_mm": 99.5})
    save_setup(db, exp.id, changed)  # a draft: saving again replaces it
    assert get_setup(db, exp.id).print_check_mm == 99.5


def test_rows_round_trip(db, run):
    d = add_derived(db, run.id, [derived()])[0]
    assert derived_for_run(db, run.id) == [d] and d.inputs == ["mea_1", "mea_2"]
    n = add_note(db, run.id, note())
    assert notes_for_run(db, run.id) == [n] and n.body == {"observation": "No change."}
    a = add_note_attempt(db, run.id, attempt())
    assert note_attempts_for_run(db, run.id) == [a] and a.reasons == ["number"]
    v = add_verdict(db, run.id, verdict())
    assert latest_verdict(db, run.id) == v and v.allowed == [VerdictLevel.TOO_EARLY]
    r = add_review(db, run.id, review())
    assert reviews_for_run(db, run.id) == [r]
    assert notes_for_run(db, run.id, t_from=11.0) == []


@pytest.mark.parametrize(
    "table, add",
    [
        ("derived", lambda db, run: add_derived(db, run.id, [derived()])),
        ("note_attempts", lambda db, run: add_note_attempt(db, run.id, attempt())),
        ("verdicts", lambda db, run: add_verdict(db, run.id, verdict())),
        ("reviews", lambda db, run: add_review(db, run.id, review())),
    ],
)
def test_reasoning_evidence_is_append_only(db, run, table, add):
    add(db, run)
    for sql in (f"UPDATE {table} SET t = t + 1", f"DELETE FROM {table}"):
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql)
    with db.read() as c:
        row = dict(c.execute(f"SELECT * FROM {table}").fetchone())
    columns = ",".join(row)
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute(f"INSERT OR REPLACE INTO {table}({columns}) VALUES ({','.join('?' * len(row))})", list(row.values()))


def test_a_note_may_only_move_its_end_time_later(db, run):
    n = add_note(db, run.id, note())
    assert extend_note(db, n.id, 50.0).t_end == 50.0
    assert extend_note(db, n.id, 90.0).t_end == 90.0  # a quiet stretch goes on
    with pytest.raises(sqlite3.IntegrityError):
        extend_note(db, n.id, 60.0)
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE notes SET body='{}' WHERE id=?", (n.id,))
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("DELETE FROM notes")


def test_a_version_3_database_upgrades(tmp_path):
    path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(path)
    for name in ("001_core.sql", "002_no_replace.sql", "003_watch_and_measure.sql"):
        conn.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version = 3")
    conn.execute(
        "INSERT INTO experiments(id, title, recipe_id, recipe_version, status, created_at) "
        "VALUES ('exp_old', 'Old', 'general', 1, 'draft', '2026-10-28T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO plans(experiment_id, version, hypothesis, prediction, threshold, rivals) "
        "VALUES ('exp_old', 1, 'h', 'p', 't', '[]')"
    )
    conn.commit()
    conn.close()
    database = Database(path)
    with database.read() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == 5
    [plan] = get_plans(database, "exp_old")
    assert plan.hypothesis == "h" and plan.metric is None and plan.direction is None
    database.close()
