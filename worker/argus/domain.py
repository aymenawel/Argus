"""Records shared by every worker module: experiments, plans, runs, vessels, frames and measurements.

Vocabulary follows docs/knowledge-base/18-glossary.md. Times `t` are real seconds since the run started.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
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


class Run(Record):
    id: str
    experiment_id: str
    mode: RunMode
    status: RunStatus
    time_scale: float = Field(1.0, gt=0)
    round: int = 1
    started_at: datetime


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
