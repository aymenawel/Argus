"""Records shared by every worker module: experiments, plans, runs, vessels, frames and measurements.

Vocabulary follows docs/knowledge-base/18-glossary.md. Times `t` are real seconds since the run started.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
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


class Direction(StrEnum):
    """Where the plan expects the treatment vessels' value to sit relative to the controls'."""

    HIGHER = "higher"
    LOWER = "lower"


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
    # The structured prediction the verdict ceiling is computed from (spec §7.3); a plan locks only with them.
    metric: str | None = None
    direction: Direction | None = None
    min_effect: float | None = Field(None, ge=0)  # the smallest effect that matters, in the metric's unit
    checkpoint_s: float | None = Field(None, ge=0)  # run time from which a verdict may be given
    treatment: str | None = None  # a condition value; None: every treatment vessel


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


class RulerInput(Record):
    """A two-click ruler: two image points and the true distance between them."""

    p1: tuple[float, float]
    p2: tuple[float, float]
    distance_mm: float = Field(gt=0)


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


class SetupVessel(Record):
    """A vessel as the wizard draws it: its role comes a step later."""

    label: str
    role: Role | None = None
    blind_label: str | None = None
    condition: Condition | None = None
    roi: list[tuple[float, float]]


class Setup(Record):
    """An experiment's setup while the wizard fills it in: a draft, not evidence."""

    source: RunSource | None = None
    time_scale: float = Field(1.0, gt=0)
    vessels: list[SetupVessel] = []
    print_check_mm: float | None = Field(None, ge=90, le=110)
    ruler: RulerInput | None = None
    factor: str | None = None
    factor_unit: str | None = None


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
    RULE = "rule"


class RunEvent(Record):
    id: str
    run_id: str
    vessel_id: str | None = None
    t_start: float = Field(ge=0)
    t_end: float | None = None
    kind: EventKind
    source: Literal["watcher", "quality", "pipeline", "researcher", "rule"]
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


class DerivedDraft(Record):
    """A number computed in code from other rows (a change, a difference, a noise floor), with its inputs."""

    t: float = Field(ge=0)
    kind: str
    label: str
    value: float
    uncertainty: float = Field(ge=0)
    unit: str = Field(min_length=1)
    inputs: list[str]
    method_version: str = Field(pattern=r"^[a-z_]+/[0-9]+$")


class Derived(DerivedDraft):
    id: str
    run_id: str


class NoteDraft(Record):
    t: float = Field(ge=0)
    t_end: float | None = None
    author: Literal["ai", "researcher"]
    level: Literal["event", "checkpoint", "insight"] | None
    tag: Literal["observation", "intervention", "question"] | None
    body: dict[str, Any]  # rendered sections, never raw {ref} tokens
    refs: list[str]
    evidence: list[str]
    check_status: Literal["passed", "fallback", "researcher"]
    model_call_id: str | None


class Note(NoteDraft):
    id: str
    run_id: str


class NoteAttemptDraft(Record):
    """Every AI note answer with its claim-check result, the rejected ones included (spec §5)."""

    t: float = Field(ge=0)
    attempt: int = Field(ge=1)
    raw: dict[str, Any]
    reasons: list[str]
    passed: bool
    model_call_id: str | None


class NoteAttempt(NoteAttemptDraft):
    id: str
    run_id: str


class VerdictDraft(Record):
    t: float = Field(ge=0)
    provisional: bool
    allowed: list[VerdictLevel]
    checks: list[dict[str, Any]]
    verdict: VerdictLevel
    body: dict[str, Any]
    draft: dict[str, Any]
    critique: dict[str, Any] | None
    refs: list[str]
    model_call_ids: list[str]
    fell_back: bool


class Verdict(VerdictDraft):
    id: str
    run_id: str


class ReviewDraft(Record):
    t: float = Field(ge=0)
    target_kind: Literal["note", "verdict", "rival", "event"]
    target_id: str
    action: Literal["confirm", "dismiss", "correct", "resolve"]
    comment: str


class Review(ReviewDraft):
    id: str
    run_id: str


def plan_sha256(draft: PlanDraft) -> str:
    """Hash of the plan's own fields, stable across key order, so a locked plan can be checked later. Unset
    structured fields are left out, so a plan locked before they existed keeps its hash."""
    fields = PlanDraft.model_validate(draft.model_dump(include=set(PlanDraft.model_fields))).model_dump(
        mode="json", exclude_none=True
    )
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
