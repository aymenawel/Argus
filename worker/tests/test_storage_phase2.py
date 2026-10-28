import sqlite3

import pytest

from argus.domain import (
    CalibrationDraft,
    CameraProperty,
    DetectionDraft,
    EventKind,
    ExperimentStatus,
    ModelCallDraft,
    PlanDraft,
    RunMode,
    RunSource,
    RunStatus,
    SourceKind,
)
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_calibration,
    add_detections,
    add_event,
    add_frame,
    add_model_call,
    close_event,
    create_run,
    detections_for_frame,
    events_for_run,
    frames_for_run,
    get_experiment,
    get_run,
    latest_calibration,
    lock_plan,
    mark_frame_analyzed,
    run_spend_usd,
    runs_for_experiment,
    save_plan_draft,
    set_experiment_status,
    stop_interrupted_runs,
)


def detection(frame, vessel, key="A:root:1"):
    return DetectionDraft(
        frame_id=frame.id,
        vessel_id=vessel.id,
        track_key=key,
        concept="root",
        outline=[[(1.0, 1.0), (5.0, 1.0), (5.0, 4.0)]],
        bbox=(1.0, 1.0, 5.0, 4.0),
        area_px=12,
        confidence=0.93,
        backend="sam-3.1/image",
        mask_path="masks/x.png",
    )


def calibration(t=0.0):
    return CalibrationDraft(
        t=t,
        card="standard",
        homography=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        mm_per_px=0.2,
        rel_uncertainty=0.01,
        colour_reference=None,
        camera_properties={"exposure": CameraProperty.UNKNOWN},
    )


def call(cost, status="ok", error=None):
    return ModelCallDraft(
        function="segment",
        model="sam-3.1",
        tier="segment",
        images=1,
        cost_usd=cost,
        latency_s=6.4,
        status=status,
        error=error,
    )


def test_detections_and_calibrations_are_evidence(db, run, vessel, frame):
    d = add_detections(db, [detection(frame, vessel)])[0]
    assert detections_for_frame(db, frame.id) == [d]
    cal = add_calibration(db, run.id, calibration())
    assert latest_calibration(db, run.id, t=10.0) == cal
    replace_detection = (
        "INSERT OR REPLACE INTO detections(id, frame_id, vessel_id, track_key, concept, outline, bbox, area_px,"
        " confidence, backend, mask_path) VALUES (?, ?, ?, 'k', 'c', '[]', '[0,0,0,0]', 0, NULL, 'b', 'p')"
    )
    statements = [
        ("UPDATE detections SET area_px=0 WHERE id=?", (d.id,)),
        ("DELETE FROM detections WHERE id=?", (d.id,)),
        (replace_detection, (d.id, frame.id, vessel.id)),
        ("UPDATE calibrations SET mm_per_px=1 WHERE id=?", (cal.id,)),
        ("DELETE FROM calibrations WHERE id=?", (cal.id,)),
    ]
    for sql, params in statements:
        with pytest.raises(sqlite3.IntegrityError), db.write() as c:
            c.execute(sql, params)
    assert detections_for_frame(db, frame.id) == [d]


def test_the_latest_calibration_at_a_time_wins(db, run):
    first = add_calibration(db, run.id, calibration(t=0.0))
    moved = add_calibration(db, run.id, calibration(t=600.0))
    assert latest_calibration(db, run.id, t=599.0) == first and latest_calibration(db, run.id, t=600.0) == moved


def test_a_frame_only_changes_its_analyzed_flag(db, run):
    f = add_frame(db, run.id, 1.0, "p.jpg", [])
    assert frames_for_run(db, run.id)[0].analyzed is False
    mark_frame_analyzed(db, f.id)
    assert frames_for_run(db, run.id)[0].analyzed is True
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("UPDATE frames SET t=2 WHERE id=?", (f.id,))


def test_an_event_closes_once(db, run):
    e = add_event(
        db, run.id, vessel_id=None, t_start=5.0, kind=EventKind.CHANGE, source="watcher", detail={}, frame_ids=[]
    )
    assert close_event(db, e.id, 9.0).t_end == 9.0
    with pytest.raises(sqlite3.IntegrityError):
        close_event(db, e.id, 12.0)
    with pytest.raises(sqlite3.IntegrityError), db.write() as c:
        c.execute("DELETE FROM events WHERE id=?", (e.id,))
    assert events_for_run(db, run.id)[0].t_end == 9.0


def test_spend_sums_every_logged_call_including_failures(db, run):
    add_model_call(db, run.id, 1.0, call(0.0025))
    add_model_call(db, run.id, 2.0, call(0.0025, status="error", error="timeout"))
    add_model_call(db, None, None, call(0.0025))  # vessel detection outside a run
    assert run_spend_usd(db, run.id) == pytest.approx(0.005)


def test_runs_left_running_are_stopped_with_an_interrupted_event(db, exp):
    source = RunSource(kind=SourceKind.VIDEO, paths=["a b é.mp4"])
    r = create_run(db, exp.id, RunMode.IMPORTED, source, time_scale=600)
    assert get_run(db, r.id).source == source and runs_for_experiment(db, exp.id)[0].id == r.id
    assert stop_interrupted_runs(db) == [r.id]
    stopped = get_run(db, r.id)
    assert stopped.status is RunStatus.STOPPED and stopped.ended_at is not None
    assert [e.kind for e in events_for_run(db, r.id)] == [EventKind.INTERRUPTED]
    assert stop_interrupted_runs(db) == []


def test_run_files_live_under_experiment_and_run(tmp_path):
    files = RunFiles(tmp_path / "data é", "exp_1", "run_1")
    assert files.frame_path("frm_1") == tmp_path / "data é" / "exp_1" / "run_1" / "frames" / "frm_1.jpg"
    assert files.frame_path("frm_1").parent.is_dir()
    assert files.mask_path("det_1").name == "det_1.png"
    assert files.crop_path("A", "mung bean").name == "A-mung-bean.mp4"


@pytest.mark.parametrize("locked", [False, True])
def test_a_restart_settles_the_experiment_of_a_cut_off_run(db, exp, locked):
    if locked:
        save_plan_draft(
            db, exp.id, PlanDraft(hypothesis="Salt slows roots", prediction="shorter", threshold="10%", rivals=[])
        )
        lock_plan(db, exp.id)
    create_run(db, exp.id, RunMode.LIVE, RunSource(kind=SourceKind.WEBCAM, camera_index=0))
    set_experiment_status(db, exp.id, ExperimentStatus.RUNNING)  # what RunJobs does when the run starts
    stop_interrupted_runs(db)  # the worker was killed, so RunJobs never settled it
    assert get_experiment(db, exp.id).status is (ExperimentStatus.LOCKED if locked else ExperimentStatus.DRAFT)
