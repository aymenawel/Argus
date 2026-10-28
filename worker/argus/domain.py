"""Records shared by every worker module: experiments, plans, runs, vessels, frames and measurements.

Vocabulary follows docs/knowledge-base/18-glossary.md. Times `t` are real seconds since the run started.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ExperimentStatus(StrEnum):
    DRAFT = "draft"
    LOCKED = "locked"
    RUNNING = "running"
    FINISHED = "finished"


class RunMode(StrEnum):
    LIVE = "live"
    IMPORTED = "imported"
    REPLAY = "replay"


class RunStatus(StrEnum):
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"


class Role(StrEnum):
    CONTROL = "control"
    TREATMENT = "treatment"


class VerdictLevel(StrEnum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    TOO_EARLY = "TOO_EARLY"


class Record(BaseModel):
    # NaN and inf are never evidence (SQLite would store NaN as NULL and refuse the batch).
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)


class Experiment(Record):
    id: str
    title: str
    recipe_id: str
    recipe_version: int
    status: ExperimentStatus
    created_at: datetime


class PlanDraft(Record):
    hypothesis: str
    prediction: str
    threshold: str
    rivals: list[str]


class Plan(PlanDraft):
    experiment_id: str
    version: int
    locked_at: datetime | None = None
    sha256: str | None = None


class SourceKind(StrEnum):
    WEBCAM = "webcam"
    VIDEO = "video"


class RunSource(Record):
    """Where a run's frames come from, and how its t = 0 was set."""

    kind: SourceKind
    camera_index: int | None = None
    paths: list[str] = []
    start_time: datetime | None = None
    start_time_source: Literal["researcher", "file", "run_start"] = "run_start"


class Run(Record):
    id: str
    experiment_id: str
    mode: RunMode
    status: RunStatus
    source: RunSource
    time_scale: float = Field(1.0, gt=0)
    round: int = 1
    started_at: datetime
    ended_at: datetime | None = None


class Condition(Record):
    factor: str
    value: float | str
    unit: str | None = None


class VesselDraft(Record):
    label: str
    role: Role
    blind_label: str | None = None
    condition: Condition | None = None
    roi: list[tuple[float, float]]


class Vessel(VesselDraft):
    id: str
    run_id: str


class Frame(Record):
    id: str
    run_id: str
    t: float = Field(ge=0)
    path: str
    quality_flags: list[str]
    analyzed: bool = False


class CameraProperty(StrEnum):
    """A camera setting as read back from the driver: a True from set() proves nothing (KB 09)."""

    LOCKED = "locked"
    NOT_LOCKED = "not_locked"
    UNKNOWN = "unknown"


class CalibrationDraft(Record):
    t: float = Field(ge=0)
    card: Literal["standard", "compact", "ruler"]
    homography: list[list[float]] | None = None
    mm_per_px: float = Field(gt=0)
    rel_uncertainty: float = Field(ge=0)
    print_scale: float = Field(1.0, gt=0)
    colour_reference: dict | None = None
    camera_properties: dict[str, CameraProperty] = {}


class Calibration(CalibrationDraft):
    id: str
    run_id: str


class DetectionDraft(Record):
    """One segmented object in one frame: the measurement layer's link back to SAM's output."""

    frame_id: str
    vessel_id: str
    track_key: str
    concept: str
    outline: list[list[tuple[float, float]]]
    bbox: tuple[float, float, float, float]
    area_px: int = Field(ge=0)
    confidence: float | None = None
    backend: str
    mask_path: str


class Detection(DetectionDraft):
    id: str


class EventKind(StrEnum):
    FIRST = "first"
    CHANGE = "change"
    CHECKIN = "checkin"
    TICK = "tick"
    INTERVENTION = "intervention"
    QUALITY = "quality"
    CAMERA_MOVED = "camera_moved"
    NO_CALIBRATION = "no_calibration"
    SEGMENT_FAILED = "segment_failed"
    SPEND = "spend"
    INTERRUPTED = "interrupted"


class RunEvent(Record):
    id: str
    run_id: str
    vessel_id: str | None = None
    t_start: float = Field(ge=0)
    t_end: float | None = None
    kind: EventKind
    source: Literal["watcher", "quality", "pipeline", "researcher"]
    detail: dict = {}
    frame_ids: list[str] = []


class ModelCallDraft(Record):
    function: str
    model: str
    tier: str
    input_tokens: int = Field(0, ge=0)
    cached_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    reasoning_tokens: int = Field(0, ge=0)
    images: int = Field(0, ge=0)
    frames: int = Field(0, ge=0)
    cost_usd: float = Field(ge=0)
    latency_s: float = Field(ge=0)
    cache_key: str | None = None
    status: Literal["ok", "error"]
    error: str | None = None


class ModelCall(ModelCallDraft):
    id: str
    run_id: str | None = None
    t: float | None = None
    created_at: datetime


class MeasurementDraft(Record):
    vessel_id: str
    frame_id: str | None
    t: float = Field(ge=0)
    metric: str
    value: float
    uncertainty: float = Field(ge=0)
    unit: str = Field(min_length=1)
    method_version: str = Field(pattern=r"^[a-z_]+/[0-9]+$")


class Measurement(MeasurementDraft):
    id: str


def plan_sha256(draft: PlanDraft) -> str:
    """Hash of the plan's own fields, stable across key order, so a locked plan can be checked later."""
    fields = PlanDraft.model_validate(draft.model_dump(include=set(PlanDraft.model_fields))).model_dump(mode="json")
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
