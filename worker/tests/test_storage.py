import sqlite3
import threading

import pytest

from argus.domain import plan_sha256
from argus.storage import repos
from argus.storage.repos import (
    add_measurements,
    create_experiment,
    get_experiment,
    get_plans,
    list_experiments,
    lock_plan,
    measurements_for_run,
    save_plan_draft,
)
from tests.records import DRAFT, draft


def test_wal_mode_and_schema_version(db):
    with db.read() as c:
        assert c.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert c.execute("PRAGMA user_version").fetchone()[0] == 4


def test_path_with_space_and_accent_round_trips(db):
    exp = create_experiment(db, "Salt-stress germination", "seed-germination", 1)
    assert get_experiment(db, exp.id) == exp and list_experiments(db)[0].id == exp.id


def test_editing_a_locked_plan_creates_a_new_version(db, exp):
    save_plan_draft(db, exp.id, DRAFT)
    v1 = lock_plan(db, exp.id)
    v2 = save_plan_draft(db, exp.id, DRAFT.model_copy(update={"threshold": "13 h"}))
    plans = get_plans(db, exp.id)
    assert (v1.version, v2.version) == (1, 2) and plans[0] == v1 and plans[0].sha256 == plan_sha256(DRAFT)
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE plans SET threshold='x' WHERE experiment_id=? AND version=1", (exp.id,))


def test_measurements_are_queryable_and_immutable(db, run, vessel):
    rows = add_measurements(db, run.id, [draft(vessel.id, t=t, value=t / 10) for t in (0.0, 300.0, 600.0)])
    assert [m.t for m in measurements_for_run(db, run.id, t_from=300.0)] == [300.0, 600.0]
    for sql in ("UPDATE measurements SET value=0 WHERE id=?", "DELETE FROM measurements WHERE id=?"):
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql, (rows[0].id,))


def test_a_save_racing_a_lock_never_breaks_the_hash(db, exp, monkeypatch):
    # The setup wizard autosaves while the researcher presses Lock: the save lands mid-lock.
    save_plan_draft(db, exp.id, DRAFT)
    racer = threading.Thread(target=save_plan_draft, args=(db, exp.id, DRAFT.model_copy(update={"threshold": "13 h"})))

    original_get_plans = repos.get_plans

    def read_then_let_a_save_in(db_, experiment_id):
        plans = original_get_plans(db_, experiment_id)
        if not racer.is_alive() and racer.ident is None:
            racer.start()
            racer.join(timeout=0.5)  # finishes at once unless lock_plan holds the writer
        return plans

    monkeypatch.setattr(repos, "get_plans", read_then_let_a_save_in)
    locked = lock_plan(db, exp.id)
    racer.join()
    plans = get_plans(db, exp.id)
    assert locked.version == 1 and plans[0].sha256 == plan_sha256(plans[0]) == plan_sha256(DRAFT)
    assert [p.threshold for p in plans] == ["12 h", "13 h"]


def test_replace_cannot_overwrite_a_measurement(db, run, vessel):
    row = add_measurements(db, run.id, [draft(vessel.id, t=0.0, value=1.0)])[0]
    sql = (
        "INSERT OR REPLACE INTO measurements(id, run_id, vessel_id, frame_id, t, metric, value, uncertainty, unit,"
        " method_version) VALUES (?, ?, ?, NULL, 0, 'area', 999, 0.1, 'mm2', 'area/1')"
    )
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute(sql, (row.id, run.id, vessel.id))
    assert measurements_for_run(db, run.id)[0].value == 1.0


def test_a_locked_plan_cannot_be_replaced_or_deleted(db, exp):
    save_plan_draft(db, exp.id, DRAFT)
    lock_plan(db, exp.id)
    replace = (
        "INSERT OR REPLACE INTO plans(experiment_id, version, hypothesis, prediction, threshold, rivals)"
        " VALUES (?, 1, 'x', 'x', 'x', '[]')"
    )
    for sql in (replace, "DELETE FROM plans WHERE experiment_id=? AND version=1"):
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql, (exp.id,))
    assert get_plans(db, exp.id)[0].sha256 == plan_sha256(DRAFT)


def test_reads_are_not_blocked_by_an_open_write(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0, value=1.0)])
    with db.write() as w:
        w.execute(
            "INSERT INTO frames(id, run_id, t, path, quality_flags) VALUES ('frm_x', ?, 1.0, 'p', '[]')", (run.id,)
        )
        assert len(measurements_for_run(db, run.id)) == 1
