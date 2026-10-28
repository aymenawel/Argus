"""Reading and writing records. Each function takes the Database first and returns domain records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from argus.domain import (
    Experiment,
    ExperimentStatus,
    Frame,
    Measurement,
    MeasurementDraft,
    Plan,
    PlanDraft,
    Run,
    RunMode,
    RunStatus,
    Vessel,
    VesselDraft,
    new_id,
    plan_sha256,
)
from argus.storage.audit import append_batch
from argus.storage.db import Database


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


# ---- Experiments ----


def create_experiment(db: Database, title: str, recipe_id: str, recipe_version: int) -> Experiment:
    experiment = Experiment(
        id=new_id("exp"),
        title=title,
        recipe_id=recipe_id,
        recipe_version=recipe_version,
        status=ExperimentStatus.DRAFT,
        created_at=_now(),
    )
    with db.write() as c:
        c.execute(
            "INSERT INTO experiments(id, title, recipe_id, recipe_version, status, created_at) VALUES (?,?,?,?,?,?)",
            (experiment.id, title, recipe_id, recipe_version, experiment.status, experiment.created_at.isoformat()),
        )
    return experiment


def _experiment(row: sqlite3.Row) -> Experiment:
    return Experiment(**dict(row))


def list_experiments(db: Database) -> list[Experiment]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM experiments ORDER BY created_at DESC, rowid DESC").fetchall()
    return [_experiment(r) for r in rows]


def get_experiment(db: Database, experiment_id: str) -> Experiment | None:
    with db.read() as c:
        row = c.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
    return _experiment(row) if row else None


# ---- Plans ----


def _plan(row: sqlite3.Row) -> Plan:
    return Plan(**{**dict(row), "rivals": json.loads(row["rivals"])})


def get_plans(db: Database, experiment_id: str) -> list[Plan]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM plans WHERE experiment_id=? ORDER BY version", (experiment_id,)).fetchall()
    return [_plan(r) for r in rows]


def save_plan_draft(db: Database, experiment_id: str, draft: PlanDraft) -> Plan:
    """Update the latest unlocked version, or start a new version when the latest is locked."""
    fields = (draft.hypothesis, draft.prediction, draft.threshold, _json(draft.rivals))
    with db.write() as c:
        latest = c.execute(
            "SELECT version, locked_at FROM plans WHERE experiment_id=? ORDER BY version DESC LIMIT 1",
            (experiment_id,),
        ).fetchone()
        if latest is not None and latest["locked_at"] is None:
            version = latest["version"]
            c.execute(
                "UPDATE plans SET hypothesis=?, prediction=?, threshold=?, rivals=? "
                "WHERE experiment_id=? AND version=?",
                (*fields, experiment_id, version),
            )
        else:
            version = 1 if latest is None else latest["version"] + 1
            c.execute(
                "INSERT INTO plans(experiment_id, version, hypothesis, prediction, threshold, rivals) "
                "VALUES (?,?,?,?,?,?)",
                (experiment_id, version, *fields),
            )
    return next(p for p in get_plans(db, experiment_id) if p.version == version)


def lock_plan(db: Database, experiment_id: str) -> Plan:
    """Freeze the latest version with a timestamp and hash; the experiment becomes locked."""
    plans = get_plans(db, experiment_id)
    if not plans:
        raise ValueError(f"experiment {experiment_id} has no plan to lock")
    latest = plans[-1]
    if latest.locked_at is None:
        draft = PlanDraft(**latest.model_dump(include=set(PlanDraft.model_fields)))
        with db.write() as c:
            c.execute(
                "UPDATE plans SET locked_at=?, sha256=? WHERE experiment_id=? AND version=?",
                (_now(), plan_sha256(draft), experiment_id, latest.version),
            )
            c.execute("UPDATE experiments SET status=? WHERE id=?", (ExperimentStatus.LOCKED, experiment_id))
    return get_plans(db, experiment_id)[-1]


# ---- Runs, vessels, frames ----


def create_run(db: Database, experiment_id: str, mode: RunMode, time_scale: float = 1.0) -> Run:
    run = Run(
        id=new_id("run"),
        experiment_id=experiment_id,
        mode=mode,
        status=RunStatus.RUNNING,
        time_scale=time_scale,
        started_at=_now(),
    )
    with db.write() as c:
        c.execute(
            "INSERT INTO runs(id, experiment_id, mode, status, time_scale, round, started_at) VALUES (?,?,?,?,?,?,?)",
            (run.id, experiment_id, run.mode, run.status, time_scale, run.round, run.started_at.isoformat()),
        )
    return run


def add_vessels(db: Database, run_id: str, drafts: Sequence[VesselDraft]) -> list[Vessel]:
    vessels = [Vessel(**d.model_dump(), id=new_id("ves"), run_id=run_id) for d in drafts]
    with db.write() as c:
        c.executemany(
            "INSERT INTO vessels(id, run_id, label, blind_label, role, condition, roi) VALUES (?,?,?,?,?,?,?)",
            [
                (
                    v.id,
                    run_id,
                    v.label,
                    v.blind_label,
                    v.role,
                    _json(v.condition.model_dump()) if v.condition else None,
                    _json(v.roi),
                )
                for v in vessels
            ],
        )
    return vessels


def add_frame(db: Database, run_id: str, t: float, path: str, quality_flags: Sequence[str]) -> Frame:
    frame = Frame(id=new_id("frm"), run_id=run_id, t=t, path=path, quality_flags=list(quality_flags))
    with db.write() as c:
        c.execute(
            "INSERT INTO frames(id, run_id, t, path, quality_flags) VALUES (?,?,?,?,?)",
            (frame.id, run_id, t, path, _json(frame.quality_flags)),
        )
    return frame


# ---- Measurements ----


def add_measurements(db: Database, run_id: str, drafts: Sequence[MeasurementDraft]) -> list[Measurement]:
    """Store one batch of measurements in a single transaction."""
    rows = [Measurement(**d.model_dump(), id=new_id("mea")) for d in drafts]
    with db.write() as c:
        c.executemany(
            "INSERT INTO measurements(id, run_id, vessel_id, frame_id, t, metric, value, uncertainty, unit, "
            "method_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (m.id, run_id, m.vessel_id, m.frame_id, m.t, m.metric, m.value, m.uncertainty, m.unit, m.method_version)
                for m in rows
            ],
        )
        append_batch(c, run_id, rows)
    return rows


def measurements_for_run(
    db: Database,
    run_id: str,
    *,
    t_from: float | None = None,
    t_to: float | None = None,
    metric: str | None = None,
) -> list[Measurement]:
    clauses, params = ["run_id=?"], [run_id]
    if t_from is not None:
        clauses.append("t>=?")
        params.append(t_from)
    if t_to is not None:
        clauses.append("t<=?")
        params.append(t_to)
    if metric is not None:
        clauses.append("metric=?")
        params.append(metric)
    sql = (
        "SELECT id, vessel_id, frame_id, t, metric, value, uncertainty, unit, method_version FROM measurements "
        f"WHERE {' AND '.join(clauses)} ORDER BY t, rowid"
    )
    with db.read() as c:
        return [Measurement(**dict(r)) for r in c.execute(sql, params).fetchall()]
