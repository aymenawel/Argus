"""Run routes (spec §10): start a live or imported run, stop it, and read its timeline, frames and outlines."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, model_validator

from argus.analyze.agreement import agreement
from argus.calibration.run import RulerInput
from argus.capture.webcam import CameraSettings
from argus.config import Settings
from argus.datasets.manifest import Manifest, ManifestError, load_manifest
from argus.domain import (
    Calibration,
    Condition,
    Role,
    Run,
    RunMode,
    RunSource,
    RunStatus,
    SourceKind,
    Vessel,
    VesselDraft,
)
from argus.measure.uncertainty import format_measurement
from argus.pipeline.imported import ImportRequest
from argus.pipeline.jobs import RunJobs
from argus.pipeline.live import CameraHub
from argus.segment import SegmentError
from argus.segment.outline import outline_polygons
from argus.storage import repos
from argus.storage.db import Database

# A stored frame never changes (it is evidence), so browsers may keep it: scrubbing back doesn't refetch.
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}
MAX_VESSELS = 16


def unique_labels(labels: list[str]) -> None:
    if len(set(labels)) != len(labels):
        raise ValueError("vessel labels must be unique")


class VesselIn(BaseModel):
    label: str = Field(min_length=1, max_length=8)
    role: Role
    condition: Condition | None = None
    roi: list[tuple[float, float]] = Field(min_length=3)


class RunCreate(BaseModel):
    mode: Literal["live", "imported"]
    camera_index: int | None = Field(None, ge=0)
    paths: list[str] = []
    manifest: str | None = None  # a published image sequence: its vessels come from the manifest's tiles
    roles: dict[str, Role] | None = None  # with a manifest: each condition's role
    # With a manifest: which of this experiment's metrics each of the dataset's labels measures (its "germinated"
    # is the recipe's "germination_count"); a label not named here keeps its own name.
    labels: dict[str, str] = {}
    time_scale: float = Field(1.0, gt=0)
    start_time: datetime | None = None
    vessels: list[VesselIn] | None = None  # None: the experiment's saved setup's vessels
    print_check_mm: float | None = Field(None, ge=90, le=110)  # None: the saved setup's
    ruler: RulerInput | None = None  # None: the saved setup's

    @model_validator(mode="after")
    def source_fits_mode(self) -> RunCreate:
        if self.mode == "live" and self.camera_index is None:
            raise ValueError("a live run needs camera_index")
        if self.mode == "imported" and not self.paths and self.manifest is None:
            raise ValueError("an imported run needs paths or a manifest")
        if self.vessels is not None:
            if not 1 <= len(self.vessels) <= MAX_VESSELS:
                raise ValueError(f"a run has 1 to {MAX_VESSELS} vessels")
            unique_labels([v.label for v in self.vessels])
        return self


class RunView(BaseModel):
    run: Run
    vessels: list[Vessel]
    calibration: Calibration | None
    spend_usd: float
    running: bool


class FrameRequest(BaseModel):
    """One frame from a camera, or from a video at video_s."""

    camera_index: int | None = Field(None, ge=0)
    path: str | None = None
    video_s: float = Field(0.0, ge=0)

    @model_validator(mode="after")
    def one_source(self) -> FrameRequest:
        if (self.camera_index is None) == (self.path is None):
            raise ValueError("give either camera_index or path")
        return self


class VesselDetect(FrameRequest):
    concept: str = Field(min_length=1)


class VesselProposal(BaseModel):
    roi: list[tuple[float, float]]
    confidence: float | None


def vessels_from_tiles(manifest: Manifest, roles: dict[str, Role] | None, factor: str) -> list[VesselDraft]:
    """One vessel per tile, its region the tile's box; ValueError unless every condition has a role and one is
    the control."""
    roles = roles or {}
    conditions = list(dict.fromkeys(tile.condition for tile in manifest.tiles))
    missing = [c for c in conditions if c not in roles]
    if missing:
        raise ValueError(f"give every condition a role: {', '.join(missing)} has none")
    if Role.CONTROL not in {roles[c] for c in conditions}:
        raise ValueError("one condition must be the control")
    if not 1 <= len(manifest.tiles) <= MAX_VESSELS:
        raise ValueError(f"a run has 1 to {MAX_VESSELS} vessels")
    unique_labels([tile.label for tile in manifest.tiles])
    return [
        VesselDraft(
            label=tile.label,
            role=roles[tile.condition],
            condition=Condition(factor=factor, value=tile.condition),
            roi=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        )
        for tile in manifest.tiles
        for x0, y0, x1, y1 in [tile.box]
    ]


def register_run_routes(app: FastAPI, *, db: Database, settings: Settings, jobs: RunJobs, hub: CameraHub) -> None:
    def view(run: Run) -> RunView:
        return RunView(
            run=run,
            vessels=repos.vessels_for_run(db, run.id),
            calibration=repos.latest_calibration(db, run.id, float("inf")),
            spend_usd=round(repos.run_spend_usd(db, run.id), 4),
            running=jobs.running(run.id),
        )

    def run_or_404(run_id: str) -> Run:
        run = repos.get_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return run

    @app.post("/api/experiments/{experiment_id}/runs", status_code=201)
    async def start_run(experiment_id: str, body: RunCreate) -> RunView:
        experiment = await asyncio.to_thread(repos.get_experiment, db, experiment_id)
        if experiment is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        for path in body.paths:
            if not Path(path).is_file():
                raise HTTPException(status_code=422, detail=f"file not found: {path}")
        if any(jobs.running(r.id) for r in await asyncio.to_thread(repos.runs_for_experiment, db, experiment_id)):
            raise HTTPException(status_code=409, detail="a run is already running for this experiment")
        live = body.mode == "live"
        manifest = None
        if body.manifest is not None:
            try:
                manifest = await asyncio.to_thread(load_manifest, body.manifest)
            except ManifestError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        source = RunSource(
            kind=SourceKind.WEBCAM if live else SourceKind.IMAGES if manifest else SourceKind.VIDEO,
            camera_index=body.camera_index,
            paths=body.paths,
            start_time=body.start_time,
            start_time_source="researcher" if body.start_time else "run_start",
            manifest=body.manifest if manifest else None,
            provenance=manifest.provenance() if manifest else None,
        )
        setup = await asyncio.to_thread(repos.get_setup, db, experiment_id)
        if manifest is not None:
            try:
                drafts = vessels_from_tiles(manifest, body.roles, setup.factor or "condition")
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        elif body.vessels is not None:
            drafts = [VesselDraft(**v.model_dump()) for v in body.vessels]
        elif setup.vessels:
            unroled = [v.label for v in setup.vessels if v.role is None]
            if unroled:
                detail = f"give every vessel a role first: {', '.join(unroled)} has none"
                raise HTTPException(status_code=422, detail=detail)
            drafts = [VesselDraft(**v.model_dump()) for v in setup.vessels]
        else:
            raise HTTPException(status_code=422, detail="no vessels: draw them in the setup or send them with the run")
        print_check_mm = body.print_check_mm if body.print_check_mm is not None else setup.print_check_mm
        ruler = body.ruler if body.ruler is not None else setup.ruler
        mode = RunMode.LIVE if live else RunMode.IMPORTED
        run = await asyncio.to_thread(repos.create_run, db, experiment_id, mode, source, body.time_scale)
        vessels = await asyncio.to_thread(repos.add_vessels, db, run.id, drafts)
        try:
            if live:
                jobs.start_live(
                    run,
                    vessels,
                    body.camera_index,
                    CameraSettings(),
                    print_check_mm=print_check_mm,
                    ruler=ruler,
                )
            else:
                request = ImportRequest(
                    paths=[Path(p) for p in body.paths],
                    time_scale=body.time_scale,
                    print_check_mm=print_check_mm,
                    ruler=ruler,
                    manifest=Path(body.manifest) if body.manifest else None,
                    labels=body.labels,
                    dish_diameter_mm=(manifest.dish_diameter_mm if manifest else None) or setup.dish_diameter_mm,
                )
                jobs.start_import(run, vessels, request)
        except RuntimeError as error:  # the camera didn't open
            await asyncio.to_thread(repos.set_run_status, db, run.id, RunStatus.STOPPED)
            raise HTTPException(status_code=422, detail=str(error)) from error
        return await asyncio.to_thread(view, run)

    @app.get("/api/experiments/{experiment_id}/runs")
    def list_runs(experiment_id: str) -> list[RunView]:
        return [view(r) for r in repos.runs_for_experiment(db, experiment_id)]

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> RunView:
        return view(run_or_404(run_id))

    @app.post("/api/runs/{run_id}/stop")
    async def stop_run(run_id: str) -> RunView:
        await asyncio.to_thread(run_or_404, run_id)
        if not await jobs.stop(run_id):
            raise HTTPException(status_code=409, detail="the run is not running")
        return await asyncio.to_thread(view, run_or_404(run_id))

    @app.get("/api/runs/{run_id}/agreement")
    def get_agreement(run_id: str, metric: str) -> dict | None:
        """Argus's readings against the dataset's labels for this metric; null when there are no labels."""
        run_or_404(run_id)
        result = agreement(db, run_id, metric)
        return asdict(result) if result is not None else None

    @app.get("/api/runs/{run_id}/timeline")
    def timeline(run_id: str, t_from: float | None = None, t_to: float | None = None) -> dict:
        run_or_404(run_id)
        measurements = repos.measurements_for_run(db, run_id, t_from=t_from, t_to=t_to)
        return {
            "frames": [
                f.model_dump(include={"id", "t", "analyzed", "quality_flags"})
                for f in repos.frames_for_run(db, run_id, t_from, t_to)
            ],
            "measurements": [
                {**m.model_dump(), "display": format_measurement(m.value, m.uncertainty, m.unit)} for m in measurements
            ],
            "events": [e.model_dump(mode="json") for e in repos.events_for_run(db, run_id, t_from, t_to)],
        }

    def frame_or_404(run_id: str, frame_id: str):
        frame = repos.get_frame(db, frame_id)
        if frame is None or frame.run_id != run_id:
            raise HTTPException(status_code=404, detail="frame not found")
        return frame

    @app.get("/api/runs/{run_id}/frames/{frame_id}.jpg")
    def frame_jpeg(run_id: str, frame_id: str, w: int | None = Query(None, ge=16, le=1920)) -> Response:
        path = settings.data_dir / frame_or_404(run_id, frame_id).path
        if w is None:
            return Response(path.read_bytes(), media_type="image/jpeg", headers=IMMUTABLE)
        image = cv2.imread(str(path))
        height = max(1, round(image.shape[0] * w / image.shape[1]))
        ok, encoded = cv2.imencode(
            ".jpg", cv2.resize(image, (w, height), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 80]
        )
        return Response(encoded.tobytes(), media_type="image/jpeg", headers=IMMUTABLE)

    @app.get("/api/runs/{run_id}/frames/{frame_id}/detections")
    def detections(run_id: str, frame_id: str) -> list[dict]:
        frame_or_404(run_id, frame_id)
        fields = {"vessel_id", "track_key", "concept", "outline", "confidence"}
        return [d.model_dump(include=fields) for d in repos.detections_for_frame(db, frame_id)]

    @app.post("/api/experiments/{experiment_id}/vessels/detect")
    async def detect_vessels(experiment_id: str, body: VesselDetect) -> list[VesselProposal]:
        if await asyncio.to_thread(repos.get_experiment, db, experiment_id) is None:
            raise HTTPException(status_code=404, detail="experiment not found")
        image = await asyncio.to_thread(frame_from, hub, body)
        try:
            result = await jobs.segmenter.image(image, body.concept)
        except SegmentError as error:
            await asyncio.to_thread(
                repos.add_model_call, db, None, None, error.call.model_copy(update={"function": "vessel_detect"})
            )
            raise HTTPException(status_code=502, detail=f"segmentation failed: {error}") from error
        await asyncio.to_thread(
            repos.add_model_call, db, None, None, result.call.model_copy(update={"function": "vessel_detect"})
        )
        proposals = []
        for track in result.tracks:
            frame = track.frames[0]
            polygons = outline_polygons(frame.patch, epsilon_px=3.0)
            if polygons:
                largest = max(polygons, key=lambda p: cv2.contourArea(_contour(p)))
                proposals.append(VesselProposal(roi=largest, confidence=frame.confidence))
        return proposals


def _contour(polygon: list[tuple[float, float]]) -> np.ndarray:
    return np.asarray(polygon, np.float32).reshape(-1, 1, 2)


def frame_from(hub: CameraHub, body: FrameRequest) -> np.ndarray:
    if body.path is not None:
        if not Path(body.path).is_file():
            raise HTTPException(status_code=422, detail=f"file not found: {body.path}")
        capture = cv2.VideoCapture(body.path)
        capture.set(cv2.CAP_PROP_POS_MSEC, body.video_s * 1000.0)
        ok, image = capture.read()
        capture.release()
        if not ok:
            raise HTTPException(status_code=422, detail=f"no frame at {body.video_s} s in {body.path}")
        return image
    try:
        source, _ = hub.acquire(body.camera_index)
    except RuntimeError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        image = source.read()
    finally:
        source.close()
    if image is None:
        raise HTTPException(status_code=503, detail=f"camera {body.camera_index} gave no frame")
    return image
