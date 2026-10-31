"""Small builders for records used across the storage tests."""

import math
from pathlib import Path

import cv2
import numpy as np

from argus.domain import (
    Condition,
    EventKind,
    MeasurementDraft,
    NoteDraft,
    PlanDraft,
    Provenance,
    Role,
    Run,
    RunMode,
    RunSource,
    RunStatus,
    SourceKind,
    VesselDraft,
    new_id,
)
from argus.storage import repos
from argus.storage.files import RunFiles

DRAFT = PlanDraft(
    hypothesis="More salt makes mung beans sprout slower and less",
    prediction="High-salt beans reach 50% sprouted at least 12 hours later than no-salt beans",
    threshold="12 h",
    rivals=["temperature", "uneven watering", "position in the row", "seed batch"],
)

PROVENANCE = Provenance(
    dataset="Seed germination plates",
    doi="10.5281/zenodo.0000000",
    url="https://example.org/dataset",
    licence="CC BY 4.0",
    credit="Example Lab et al.",
    assembled=True,
    retrospective=True,
)


def draft(vessel_id: str, t: float, value: float = 1.0) -> MeasurementDraft:
    return MeasurementDraft(
        vessel_id=vessel_id,
        frame_id=None,
        t=t,
        metric="area",
        value=value,
        uncertainty=0.1,
        unit="mm2",
        method_version="area/1",
    )


def finished_run(
    db,
    data_dir: Path,
    *,
    frames: int = 12,
    t_step: float = 600.0,
    provenance: Provenance | None = None,
    status: RunStatus = RunStatus.FINISHED,
    size: tuple[int, int] = (640, 480),
    readings: bool = True,
) -> Run:
    """A colour-change run of two glasses: A (control) stays flat, B (warm water) darkens along a logistic. Frames are
    grey JPEGs under data_dir; the dye goes in at frame 2 and B's change is detected at frame 4."""
    experiment = repos.create_experiment(db, "Dye in warm and room water", "colour-reaction", 1)
    kind = SourceKind.IMAGES if provenance else SourceKind.VIDEO
    run = repos.create_run(
        db, experiment.id, RunMode.IMPORTED, RunSource(kind=kind, paths=["run.mp4"], provenance=provenance)
    )
    square = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
    control, treatment = repos.add_vessels(
        db,
        run.id,
        [
            VesselDraft(label="A", role=Role.CONTROL, roi=square),
            VesselDraft(
                label="B",
                role=Role.TREATMENT,
                condition=Condition(factor="temperature", value=40, unit="°C"),
                roi=square,
            ),
        ],
    )
    files = RunFiles(data_dir, experiment.id, run.id)
    image = np.full((size[1], size[0], 3), 128, np.uint8)
    middle = (frames - 1) * t_step / 2
    keep_readings, readings = readings, []
    for i in range(frames):
        t = i * t_step
        frame_id = new_id("frm")
        path = files.frame_path(frame_id)
        cv2.imwrite(str(path), image)
        repos.add_frame(db, run.id, t, path.relative_to(data_dir).as_posix(), [], frame_id=frame_id)
        repos.mark_frame_analyzed(db, frame_id)
        rise = 30.0 / (1.0 + math.exp(-(t - middle) / max(t_step, 1.0)))
        for vessel, value in ((control, 1.0 + 0.2 * (-1) ** i), (treatment, rise)):
            readings.append(
                MeasurementDraft(
                    vessel_id=vessel.id,
                    frame_id=frame_id,
                    t=t,
                    metric="delta_e",
                    value=value,
                    uncertainty=0.1,
                    unit="dE00",
                    method_version="delta_e/1",
                )
            )
    if keep_readings:
        repos.add_measurements(db, run.id, readings)
    dye = repos.add_event(
        db,
        run.id,
        vessel_id=None,
        t_start=min(2, frames - 1) * t_step,
        kind=EventKind.INTERVENTION,
        source="researcher",
        detail={"message": "Dye added"},
    )
    repos.add_event(
        db,
        run.id,
        vessel_id=treatment.id,
        t_start=min(4, frames - 1) * t_step,
        kind=EventKind.CHANGE,
        source="watcher",
        detail={},
    )
    repos.add_note(
        db,
        run.id,
        NoteDraft(
            t=dye.t_start,
            author="researcher",
            level=None,
            tag="intervention",
            body={"text": "Dye added"},
            refs=[],
            evidence=[dye.id],
            check_status="researcher",
            model_call_id=None,
        ),
    )
    return repos.set_run_status(db, run.id, status)
