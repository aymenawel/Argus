"""Everything a video of a run shows, read once from the database (D-85): stored records only."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from argus.analyze.fits import fits_view
from argus.config import Settings
from argus.domain import Experiment, Frame, NextRun, Note, Plan, Run, RunEvent, RunStatus, Verdict, Vessel
from argus.media import MediaRefused
from argus.recipes.model import Recipe
from argus.storage import repos
from argus.storage.db import Database
from argus.storage.files import RunFiles

Polygon = list[tuple[float, float]]


@dataclass(frozen=True)
class RunRecords:
    run: Run
    experiment: Experiment
    plan: Plan | None  # the plan the run is judged against: the first locked version
    vessels: list[Vessel]
    frames: list[Frame]  # in t order
    outlines: dict[str, list[tuple[str, list[Polygon]]]]  # frame id → each detection's (vessel id, polygons)
    fits: dict  # fits_view of the plan's metric (else the recipe's main measurement)
    notes: list[Note]
    events: list[RunEvent]
    verdict: Verdict | None
    next_run: NextRun | None
    files: RunFiles


def refusal(db: Database, run_id: str) -> str | None:
    """Why this run can't be made into a video now, or None."""
    run = repos.get_run(db, run_id)
    if run is None:
        return "run not found"
    if run.status is RunStatus.RUNNING:
        return "the run is still running: make its videos once it has finished or been stopped"
    if not repos.frames_for_run(db, run_id):
        return "the run has no frames"
    return None


def load_records(db: Database, settings: Settings, recipes: Mapping[str, Recipe], run_id: str) -> RunRecords:
    reason = refusal(db, run_id)
    if reason is not None:
        raise MediaRefused(reason)
    run = repos.get_run(db, run_id)
    experiment = repos.get_experiment(db, run.experiment_id)
    frames = sorted(repos.frames_for_run(db, run_id), key=lambda f: f.t)
    outlines = {
        f.id: [(d.vessel_id, d.outline) for d in repos.detections_for_frame(db, f.id)]  # the drawer has no database
        for f in frames
    }
    return RunRecords(
        run=run,
        experiment=experiment,
        plan=repos.first_locked_plan(db, run.experiment_id),
        vessels=repos.vessels_for_run(db, run_id),
        frames=frames,
        outlines=outlines,
        fits=fits_view(db, recipes, run_id),
        notes=sorted(repos.notes_for_run(db, run_id), key=lambda n: n.t),
        events=repos.events_for_run(db, run_id),
        verdict=repos.latest_verdict(db, run_id),
        next_run=repos.latest_next_run(db, run_id),
        files=RunFiles(settings.data_dir, run.experiment_id, run.id),
    )
