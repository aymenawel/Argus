"""The recipe schema. Fields are validated in declaration order, so later checks can see earlier fields."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

METHODS_BY_FAMILY = {
    "size": {"area", "height", "skeleton_length"},
    "colour": {"lab_mean", "delta_e"},
    "count": {"component_count", "event_count"},
    "state": {"threshold"},
}


class Spec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class Concept(Spec):
    name: str = Field(min_length=1)


class MeasurementSpec(Spec):
    id: str
    family: Literal["size", "colour", "count", "motion", "state"]
    method: str
    source: str = Field(alias="from")
    unit: str = Field(min_length=1)
    rule: str | None = None

    @field_validator("method")
    @classmethod
    def method_fits_family(cls, method: str, info: ValidationInfo) -> str:
        family = info.data.get("family")
        allowed = METHODS_BY_FAMILY.get(family, set())
        if method not in allowed:
            raise ValueError(f"'{method}' is not a {family} method (allowed: {', '.join(sorted(allowed)) or 'none'})")
        return method

    @model_validator(mode="after")
    def lab_mean_reports_three_values(self) -> MeasurementSpec:
        if self.method == "lab_mean" and self.unit != "Lab":
            raise ValueError('lab_mean reports L*, a* and b*: use unit "Lab"')
        return self


class EventSpec(Spec):
    id: str
    when: str


class WatcherSpec(Spec):
    signals: list[Literal["ssim", "colour"]] = ["ssim", "colour"]
    light_normalization: Literal["normal", "strong"] = "normal"
    day_night: bool = False


class Recipe(Spec):
    id: str
    version: int = Field(ge=1)
    title: str
    default_mode: Literal["continuous", "smart_trigger", "hybrid"]
    analysis_step_s: float = Field(gt=0)
    curve: Literal["logistic", "gompertz", "exponential", "first_order", "linear"]
    rivals: list[str] = []
    default_views: list[str] = []
    watcher: WatcherSpec = WatcherSpec()
    concepts: list[Concept] = Field(min_length=1)
    measurements: list[MeasurementSpec] = Field(min_length=1)
    events: list[EventSpec] = []
    main_measurement: str

    @field_validator("concepts")
    @classmethod
    def one_concept_each(cls, concepts: list[Concept]) -> list[Concept]:
        for concept in concepts:
            if "," in concept.name or "+" in concept.name:
                raise ValueError(f"'{concept.name}' holds several concepts; SAM takes one concept per request")
        if len({c.name for c in concepts}) != len(concepts):
            raise ValueError("concept names must be unique")
        return concepts

    @field_validator("measurements")
    @classmethod
    def measurements_use_known_concepts(cls, measurements: list[MeasurementSpec], info: ValidationInfo):
        names = {c.name for c in info.data.get("concepts", [])}
        for m in measurements:
            if m.source not in names:
                raise ValueError(f"measurement '{m.id}' reads from unknown concept '{m.source}'")
        if len({m.id for m in measurements}) != len(measurements):
            raise ValueError("measurement ids must be unique")
        return measurements

    @field_validator("main_measurement")
    @classmethod
    def main_measurement_exists(cls, main: str, info: ValidationInfo) -> str:
        ids = {m.id for m in info.data.get("measurements", [])}
        if main not in ids:
            raise ValueError(f"'{main}' is not one of this recipe's measurements")
        return main
