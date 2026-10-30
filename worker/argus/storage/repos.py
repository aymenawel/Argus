"""Reading and writing records. Each function takes the Database first and returns domain records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from argus.domain import (
    Calibration,
    CalibrationDraft,
    Derived,
    DerivedDraft,
    Detection,
    DetectionDraft,
    EventKind,
    Experiment,
    ExperimentStatus,
    Frame,
    Measurement,
    MeasurementDraft,
    ModelCall,
    ModelCallDraft,
    NextRun,
    NextRunDraft,
    Note,
    NoteAttempt,
    NoteAttemptDraft,
    NoteDraft,
    Plan,
    PlanDraft,
    ReferenceValue,
    ReferenceValueDraft,
    Review,
    ReviewDraft,
    Run,
    RunEvent,
    RunMode,
    RunSource,
    RunStatus,
    Setup,
    Verdict,
    VerdictDraft,
    Vessel,
    VesselDraft,
    new_id,
    plan_sha256,
)
from argus.recipes.model import Recipe
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


def set_experiment_status(db: Database, experiment_id: str, status: ExperimentStatus) -> None:
    with db.write() as c:
        c.execute("UPDATE experiments SET status=? WHERE id=?", (status, experiment_id))


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


PLAN_COLUMNS = (
    "hypothesis",
    "prediction",
    "threshold",
    "rivals",
    "metric",
    "direction",
    "min_effect",
    "checkpoint_s",
    "treatment",
    "quantity",
)


def save_plan_draft(db: Database, experiment_id: str, draft: PlanDraft) -> Plan:
    """Update the latest unlocked version, or start a new version when the latest is locked."""
    values = draft.model_dump(mode="json")
    fields = tuple(_json(values[c]) if c == "rivals" else values[c] for c in PLAN_COLUMNS)
    with db.write() as c:
        latest = c.execute(
            "SELECT version, locked_at FROM plans WHERE experiment_id=? ORDER BY version DESC LIMIT 1",
            (experiment_id,),
        ).fetchone()
        if latest is not None and latest["locked_at"] is None:
            version = latest["version"]
            assignments = ", ".join(f"{column}=?" for column in PLAN_COLUMNS)
            c.execute(
                f"UPDATE plans SET {assignments} WHERE experiment_id=? AND version=?",
                (*fields, experiment_id, version),
            )
        else:
            version = 1 if latest is None else latest["version"] + 1
            c.execute(
                f"INSERT INTO plans(experiment_id, version, {', '.join(PLAN_COLUMNS)}) "
                f"VALUES ({','.join('?' * (len(PLAN_COLUMNS) + 2))})",
                (experiment_id, version, *fields),
            )
    return next(p for p in get_plans(db, experiment_id) if p.version == version)


def lock_plan(db: Database, experiment_id: str) -> Plan:
    """Freeze the latest version with a timestamp and hash; the experiment becomes locked.

    Reading, hashing and locking share one write transaction, so a draft saved meanwhile can't end up
    locked under the hash of other content.
    """
    with db.write() as c:
        row = c.execute(
            "SELECT * FROM plans WHERE experiment_id=? ORDER BY version DESC LIMIT 1", (experiment_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"experiment {experiment_id} has no plan to lock")
        latest = _plan(row)
        if latest.locked_at is None:
            draft = PlanDraft(**latest.model_dump(include=set(PlanDraft.model_fields)))
            c.execute(
                "UPDATE plans SET locked_at=?, sha256=? WHERE experiment_id=? AND version=? AND locked_at IS NULL",
                (_now(), plan_sha256(draft), experiment_id, latest.version),
            )
            c.execute("UPDATE experiments SET status=? WHERE id=?", (ExperimentStatus.LOCKED, experiment_id))
    return next(p for p in get_plans(db, experiment_id) if p.version == latest.version)


def save_recipe(db: Database, experiment_id: str, recipe: Recipe, origin: str) -> int:
    """A new version of the experiment's own recipe, now the one in use (D-73); versions never change."""
    with db.write() as c:
        row = c.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM experiment_recipes WHERE experiment_id=?", (experiment_id,)
        ).fetchone()
        version = int(row["v"]) + 1
        body = recipe.model_copy(update={"id": "own", "version": version}).model_dump_json(by_alias=True)
        c.execute(
            "INSERT INTO experiment_recipes(experiment_id, version, body, origin, created_at) VALUES (?,?,?,?,?)",
            (experiment_id, version, body, origin, _now()),
        )
        c.execute("UPDATE experiments SET recipe_id='own', recipe_version=? WHERE id=?", (version, experiment_id))
    return version


def own_recipe(db: Database, experiment_id: str, version: int | None = None) -> Recipe | None:
    """The experiment's own recipe: a given version, or the newest."""
    query = "SELECT body FROM experiment_recipes WHERE experiment_id=?"
    params: tuple = (experiment_id,)
    if version is not None:
        query += " AND version=?"
        params += (version,)
    with db.read() as c:
        row = c.execute(query + " ORDER BY version DESC LIMIT 1", params).fetchone()
    return Recipe.model_validate_json(row["body"]) if row else None


def first_locked_plan(db: Database, experiment_id: str) -> Plan | None:
    """The plan a verdict is judged against: the first version that was locked (later edits are new versions)."""
    return next((p for p in get_plans(db, experiment_id) if p.locked_at is not None), None)


# ---- Setups (the wizard's draft; not evidence) ----


def save_setup(db: Database, experiment_id: str, setup: Setup) -> Setup:
    with db.write() as c:
        c.execute(
            "INSERT INTO setups(experiment_id, body, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(experiment_id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at",
            (experiment_id, setup.model_dump_json(), _now()),
        )
    return setup


def get_setup(db: Database, experiment_id: str) -> Setup:
    with db.read() as c:
        row = c.execute("SELECT body FROM setups WHERE experiment_id=?", (experiment_id,)).fetchone()
    return Setup() if row is None else Setup.model_validate_json(row["body"])


def get_preference(db: Database, key: str) -> str | None:
    with db.read() as c:
        row = c.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def set_preference(db: Database, key: str, value: str) -> None:
    with db.write() as c:
        c.execute(
            "INSERT INTO preferences(key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, _now()),
        )


# ---- Runs, vessels, frames ----


def create_run(db: Database, experiment_id: str, mode: RunMode, source: RunSource, time_scale: float = 1.0) -> Run:
    run = Run(
        id=new_id("run"),
        experiment_id=experiment_id,
        mode=mode,
        status=RunStatus.RUNNING,
        source=source,
        time_scale=time_scale,
        started_at=_now(),
    )
    with db.write() as c:
        c.execute(
            "INSERT INTO runs(id, experiment_id, mode, status, source, time_scale, round, started_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                run.id,
                experiment_id,
                run.mode,
                run.status,
                source.model_dump_json(),
                time_scale,
                run.round,
                run.started_at.isoformat(),
            ),
        )
    return run


def _run(row: sqlite3.Row) -> Run:
    return Run(**{**dict(row), "source": RunSource.model_validate_json(row["source"])})


def get_run(db: Database, run_id: str) -> Run | None:
    with db.read() as c:
        row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    return _run(row) if row else None


def runs_for_experiment(db: Database, experiment_id: str) -> list[Run]:
    """Newest first."""
    with db.read() as c:
        rows = c.execute(
            "SELECT * FROM runs WHERE experiment_id=? ORDER BY started_at DESC, rowid DESC", (experiment_id,)
        ).fetchall()
    return [_run(r) for r in rows]


def set_run_status(db: Database, run_id: str, status: RunStatus) -> Run:
    """A run that stops running gets its end time."""
    ended = None if status is RunStatus.RUNNING else _now()
    with db.write() as c:
        c.execute("UPDATE runs SET status=?, ended_at=? WHERE id=?", (status, ended, run_id))
    run = get_run(db, run_id)
    if run is None:
        raise ValueError(f"no run {run_id}")
    return run


def settle_experiment(db: Database, experiment_id: str, run_status: RunStatus) -> None:
    """After a run ends, the experiment follows: finished with it, else back to locked (plan locked) or draft."""
    if run_status is RunStatus.FINISHED:
        settled = ExperimentStatus.FINISHED
    elif any(plan.locked_at for plan in get_plans(db, experiment_id)):
        settled = ExperimentStatus.LOCKED
    else:
        settled = ExperimentStatus.DRAFT
    set_experiment_status(db, experiment_id, settled)


def stop_interrupted_runs(db: Database) -> list[str]:
    """At startup, runs still marked running were cut off (the worker stopped): mark them stopped, with an event,
    and settle every experiment still marked running (nothing runs before startup ends)."""
    with db.read() as c:
        rows = c.execute("SELECT id FROM runs WHERE status=?", (RunStatus.RUNNING,)).fetchall()
    ids = [r["id"] for r in rows]
    for run_id in ids:
        set_run_status(db, run_id, RunStatus.STOPPED)
        last = _last_t(db, run_id)
        add_event(
            db,
            run_id,
            vessel_id=None,
            t_start=last,
            kind=EventKind.INTERRUPTED,
            source="pipeline",
            detail={"reason": "the worker stopped while the run was running"},
        )
    with db.read() as c:
        running = c.execute("SELECT id FROM experiments WHERE status=?", (ExperimentStatus.RUNNING,)).fetchall()
    for row in running:
        settle_experiment(db, row["id"], RunStatus.STOPPED)
    return ids


def _last_t(db: Database, run_id: str) -> float:
    with db.read() as c:
        row = c.execute("SELECT MAX(t) AS t FROM frames WHERE run_id=?", (run_id,)).fetchone()
    return float(row["t"]) if row and row["t"] is not None else 0.0


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


def vessels_for_run(db: Database, run_id: str) -> list[Vessel]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM vessels WHERE run_id=? ORDER BY rowid", (run_id,)).fetchall()
    return [
        Vessel(
            **{
                **dict(r),
                "condition": json.loads(r["condition"]) if r["condition"] else None,
                "roi": json.loads(r["roi"]),
            }
        )
        for r in rows
    ]


def add_frame(
    db: Database, run_id: str, t: float, path: str, quality_flags: Sequence[str], *, frame_id: str | None = None
) -> Frame:
    """Store a frame record; pass `frame_id` when the image file was written under that id first."""
    frame = Frame(id=frame_id or new_id("frm"), run_id=run_id, t=t, path=path, quality_flags=list(quality_flags))
    with db.write() as c:
        c.execute(
            "INSERT INTO frames(id, run_id, t, path, quality_flags) VALUES (?,?,?,?,?)",
            (frame.id, run_id, t, path, _json(frame.quality_flags)),
        )
    return frame


def mark_frame_analyzed(db: Database, frame_id: str) -> None:
    with db.write() as c:
        c.execute("UPDATE frames SET analyzed=1 WHERE id=?", (frame_id,))


def _frame(row: sqlite3.Row) -> Frame:
    return Frame(**{**dict(row), "quality_flags": json.loads(row["quality_flags"]), "analyzed": bool(row["analyzed"])})


def get_frame(db: Database, frame_id: str) -> Frame | None:
    with db.read() as c:
        row = c.execute("SELECT * FROM frames WHERE id=?", (frame_id,)).fetchone()
    return _frame(row) if row else None


def frames_for_run(db: Database, run_id: str, t_from: float | None = None, t_to: float | None = None) -> list[Frame]:
    clauses, params = _time_window("t", run_id, t_from, t_to)
    with db.read() as c:
        rows = c.execute(f"SELECT * FROM frames WHERE {clauses} ORDER BY t, rowid", params).fetchall()
    return [_frame(r) for r in rows]


def _time_window(column: str, run_id: str, t_from: float | None, t_to: float | None) -> tuple[str, list[Any]]:
    clauses, params = ["run_id=?"], [run_id]
    if t_from is not None:
        clauses.append(f"{column}>=?")
        params.append(t_from)
    if t_to is not None:
        clauses.append(f"{column}<=?")
        params.append(t_to)
    return " AND ".join(clauses), params


# ---- Calibrations ----


def add_calibration(db: Database, run_id: str, draft: CalibrationDraft) -> Calibration:
    cal = Calibration(**draft.model_dump(), id=new_id("cal"), run_id=run_id)
    with db.write() as c:
        c.execute(
            "INSERT INTO calibrations(id, run_id, t, card, homography, mm_per_px, rel_uncertainty, print_scale, "
            "colour_reference, camera_properties) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                cal.id,
                run_id,
                cal.t,
                cal.card,
                _json(cal.homography) if cal.homography is not None else None,
                cal.mm_per_px,
                cal.rel_uncertainty,
                cal.print_scale,
                _json(cal.colour_reference) if cal.colour_reference is not None else None,
                _json({k: str(v) for k, v in cal.camera_properties.items()}),
            ),
        )
    return cal


def latest_calibration(db: Database, run_id: str, t: float) -> Calibration | None:
    """The calibration in force at time t: the newest one taken at or before t."""
    with db.read() as c:
        row = c.execute(
            "SELECT * FROM calibrations WHERE run_id=? AND t<=? ORDER BY t DESC, rowid DESC LIMIT 1", (run_id, t)
        ).fetchone()
    if row is None:
        return None
    values = dict(row)
    for key in ("homography", "colour_reference", "camera_properties"):
        values[key] = json.loads(values[key]) if values[key] is not None else None
    values["camera_properties"] = values["camera_properties"] or {}
    return Calibration(**values)


# ---- Detections ----


def add_detections(db: Database, drafts: Sequence[DetectionDraft]) -> list[Detection]:
    rows = [Detection(**d.model_dump(), id=new_id("det")) for d in drafts]
    return add_detection_rows(db, rows)


def add_detection_rows(db: Database, rows: Sequence[Detection]) -> list[Detection]:
    """Store detections whose ids were chosen first (their mask files are named after them)."""
    with db.write() as c:
        c.executemany(
            "INSERT INTO detections(id, frame_id, vessel_id, track_key, concept, outline, bbox, area_px, confidence, "
            "backend, mask_path) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    d.id,
                    d.frame_id,
                    d.vessel_id,
                    d.track_key,
                    d.concept,
                    _json(d.outline),
                    _json(d.bbox),
                    d.area_px,
                    d.confidence,
                    d.backend,
                    d.mask_path,
                )
                for d in rows
            ],
        )
    return list(rows)


def detections_for_frame(db: Database, frame_id: str) -> list[Detection]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM detections WHERE frame_id=? ORDER BY rowid", (frame_id,)).fetchall()
    return [
        Detection(**{**dict(r), "outline": json.loads(r["outline"]), "bbox": tuple(json.loads(r["bbox"]))})
        for r in rows
    ]


# ---- Events ----


def add_event(
    db: Database,
    run_id: str,
    *,
    vessel_id: str | None,
    t_start: float,
    kind: EventKind,
    source: str,
    detail: dict,
    frame_ids: Sequence[str] = (),
    t_end: float | None = None,
) -> RunEvent:
    event = RunEvent(
        id=new_id("evt"),
        run_id=run_id,
        vessel_id=vessel_id,
        t_start=t_start,
        t_end=t_end,
        kind=kind,
        source=source,
        detail=detail,
        frame_ids=list(frame_ids),
    )
    with db.write() as c:
        c.execute(
            "INSERT INTO events(id, run_id, vessel_id, t_start, t_end, kind, source, detail, frame_ids) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                event.id,
                run_id,
                vessel_id,
                t_start,
                t_end,
                event.kind,
                event.source,
                _json(event.detail),
                _json(event.frame_ids),
            ),
        )
    return event


def _event(row: sqlite3.Row) -> RunEvent:
    return RunEvent(**{**dict(row), "detail": json.loads(row["detail"]), "frame_ids": json.loads(row["frame_ids"])})


def close_event(db: Database, event_id: str, t_end: float) -> RunEvent:
    """An open event gets its end time, once."""
    with db.write() as c:
        c.execute("UPDATE events SET t_end=? WHERE id=?", (t_end, event_id))
        row = c.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return _event(row)


def events_for_run(db: Database, run_id: str, t_from: float | None = None, t_to: float | None = None) -> list[RunEvent]:
    clauses, params = _time_window("t_start", run_id, t_from, t_to)
    with db.read() as c:
        rows = c.execute(f"SELECT * FROM events WHERE {clauses} ORDER BY t_start, rowid", params).fetchall()
    return [_event(r) for r in rows]


# ---- Model calls ----


def add_model_call(db: Database, run_id: str | None, t: float | None, draft: ModelCallDraft) -> ModelCall:
    call = ModelCall(**draft.model_dump(), id=new_id("call"), run_id=run_id, t=t, created_at=_now())
    fields = list(ModelCall.model_fields)
    values = [call.created_at.isoformat() if f == "created_at" else getattr(call, f) for f in fields]
    with db.write() as c:
        c.execute(
            f"INSERT INTO model_calls({', '.join(fields)}) VALUES ({','.join('?' * len(fields))})",
            values,
        )
    return call


def run_last_t(db: Database, run_id: str) -> float:
    """The run's time now: its newest frame or reading, 0 before any."""
    with db.read() as c:
        row = c.execute(
            "SELECT MAX(t) AS t FROM (SELECT MAX(t) AS t FROM frames WHERE run_id=? "
            "UNION ALL SELECT MAX(t) FROM measurements WHERE run_id=?)",
            (run_id, run_id),
        ).fetchone()
    return float(row["t"] or 0.0)


def run_spend_usd(db: Database, run_id: str) -> float:
    """Every logged call counts, failed ones included: they can still be billed."""
    with db.read() as c:
        row = c.execute("SELECT COALESCE(SUM(cost_usd), 0) AS spent FROM model_calls WHERE run_id=?", (run_id,))
        return float(row.fetchone()["spent"])


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


def add_reference_values(db: Database, run_id: str, drafts: Sequence[ReferenceValueDraft]) -> list[ReferenceValue]:
    rows = [ReferenceValue(**d.model_dump(), id=new_id("ref"), run_id=run_id) for d in drafts]
    with db.write() as c:
        c.executemany(
            "INSERT INTO reference_values(id, run_id, vessel_id, t, metric, value, source) VALUES (?,?,?,?,?,?,?)",
            [(r.id, run_id, r.vessel_id, r.t, r.metric, r.value, r.source) for r in rows],
        )
    return rows


def reference_values_for_run(db: Database, run_id: str, metric: str) -> list[ReferenceValue]:
    with db.read() as c:
        found = c.execute(
            "SELECT * FROM reference_values WHERE run_id=? AND metric=? ORDER BY vessel_id, t", (run_id, metric)
        ).fetchall()
    return [ReferenceValue(**dict(r)) for r in found]


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


# ---- The explanation layer: derived numbers, notes, attempts, verdicts, reviews ----


def _insert(c: sqlite3.Connection, table: str, record: Any, json_fields: Sequence[str]) -> None:
    values = record.model_dump(mode="json")
    columns = list(values)
    row = [_json(values[k]) if k in json_fields else values[k] for k in columns] + [_now()]
    c.execute(
        f"INSERT INTO {table}({', '.join(columns)}, created_at) VALUES ({','.join('?' * (len(columns) + 1))})",
        row,
    )


def _load(cls: Any, row: sqlite3.Row, json_fields: Sequence[str]) -> Any:
    values = {k: row[k] for k in cls.model_fields}
    return cls(**{k: json.loads(v) if k in json_fields and v is not None else v for k, v in values.items()})


DERIVED_JSON = ("inputs",)
NOTE_JSON = ("body", "refs", "evidence")
ATTEMPT_JSON = ("raw", "reasons")
VERDICT_JSON = ("allowed", "checks", "body", "draft", "critique", "refs", "model_call_ids")
NEXT_RUN_JSON = ("numbers", "body", "refs", "model_call_ids")


def add_derived(db: Database, run_id: str, drafts: Sequence[DerivedDraft]) -> list[Derived]:
    rows = [Derived(**d.model_dump(), id=new_id("drv"), run_id=run_id) for d in drafts]
    with db.write() as c:
        for row in rows:
            _insert(c, "derived", row, DERIVED_JSON)
    return rows


def derived_for_run(db: Database, run_id: str) -> list[Derived]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM derived WHERE run_id=? ORDER BY t, rowid", (run_id,)).fetchall()
    return [_load(Derived, r, DERIVED_JSON) for r in rows]


def add_note(db: Database, run_id: str, draft: NoteDraft) -> Note:
    note = Note(**draft.model_dump(), id=new_id("note"), run_id=run_id)
    with db.write() as c:
        _insert(c, "notes", note, NOTE_JSON)
    return note


def extend_note(db: Database, note_id: str, t_end: float) -> Note:
    """A quiet "no change" note covers a longer stretch: its end time is set, once."""
    with db.write() as c:
        c.execute("UPDATE notes SET t_end=? WHERE id=?", (t_end, note_id))
        row = c.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    return _load(Note, row, NOTE_JSON)


def notes_for_run(db: Database, run_id: str, t_from: float | None = None, t_to: float | None = None) -> list[Note]:
    clauses, params = _time_window("t", run_id, t_from, t_to)
    with db.read() as c:
        rows = c.execute(f"SELECT * FROM notes WHERE {clauses} ORDER BY t, rowid", params).fetchall()
    return [_load(Note, r, NOTE_JSON) for r in rows]


def models_of_calls(db: Database, call_ids: Sequence[str]) -> dict[str, str]:
    """The model that answered each logged call (for showing who wrote a note)."""
    if not call_ids:
        return {}
    marks = ",".join("?" * len(call_ids))
    with db.read() as c:
        rows = c.execute(f"SELECT id, model FROM model_calls WHERE id IN ({marks})", list(call_ids)).fetchall()
    return {r["id"]: r["model"] for r in rows}


def add_note_attempt(db: Database, run_id: str, draft: NoteAttemptDraft) -> NoteAttempt:
    attempt = NoteAttempt(**draft.model_dump(), id=new_id("att"), run_id=run_id)
    with db.write() as c:
        _insert(c, "note_attempts", attempt, ATTEMPT_JSON)
    return attempt


def note_attempts_for_run(db: Database, run_id: str) -> list[NoteAttempt]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM note_attempts WHERE run_id=? ORDER BY t, rowid", (run_id,)).fetchall()
    return [_load(NoteAttempt, r, ATTEMPT_JSON) for r in rows]


def add_verdict(db: Database, run_id: str, draft: VerdictDraft) -> Verdict:
    verdict = Verdict(**draft.model_dump(), id=new_id("vrd"), run_id=run_id)
    with db.write() as c:
        _insert(c, "verdicts", verdict, VERDICT_JSON)
    return verdict


def latest_verdict(db: Database, run_id: str) -> Verdict | None:
    with db.read() as c:
        row = c.execute(
            "SELECT * FROM verdicts WHERE run_id=? ORDER BY t DESC, rowid DESC LIMIT 1", (run_id,)
        ).fetchone()
    return None if row is None else _load(Verdict, row, VERDICT_JSON)


def add_next_run(db: Database, run_id: str, draft: NextRunDraft) -> NextRun:
    suggestion = NextRun(**draft.model_dump(), id=new_id("nxt"), run_id=run_id)
    with db.write() as c:
        _insert(c, "next_runs", suggestion, NEXT_RUN_JSON)
    return suggestion


def latest_next_run(db: Database, run_id: str) -> NextRun | None:
    with db.read() as c:
        row = c.execute(
            "SELECT * FROM next_runs WHERE run_id=? ORDER BY t DESC, rowid DESC LIMIT 1", (run_id,)
        ).fetchone()
    return None if row is None else _load(NextRun, row, NEXT_RUN_JSON)


def add_review(db: Database, run_id: str, draft: ReviewDraft) -> Review:
    review = Review(**draft.model_dump(), id=new_id("rev"), run_id=run_id)
    with db.write() as c:
        _insert(c, "reviews", review, ())
    return review


def reviews_for_run(db: Database, run_id: str) -> list[Review]:
    with db.read() as c:
        rows = c.execute("SELECT * FROM reviews WHERE run_id=? ORDER BY t, rowid", (run_id,)).fetchall()
    return [_load(Review, r, ()) for r in rows]
