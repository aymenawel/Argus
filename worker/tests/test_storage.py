import sqlite3

import pytest

from argus.domain import plan_sha256
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
        assert c.execute("PRAGMA user_version").fetchone()[0] == 1


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


def test_reads_are_not_blocked_by_an_open_write(db, run, vessel):
    add_measurements(db, run.id, [draft(vessel.id, t=0.0, value=1.0)])
    with db.write() as w:
        w.execute(
            "INSERT INTO frames(id, run_id, t, path, quality_flags) VALUES ('frm_x', ?, 1.0, 'p', '[]')", (run.id,)
        )
        assert len(measurements_for_run(db, run.id)) == 1
