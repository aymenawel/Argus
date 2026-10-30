"""The recipe schema. Fields are validated in declaration order, so later checks can see earlier fields."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from argus.analyze.rules import parse_rule

METHODS_BY_FAMILY = {
    "size": {"area", "height", "skeleton_length"},
    "colour": {"lab_mean", "delta_e"},
    "count": {"component_count", "event_count", "touching_count"},
    "state": {"threshold"},
}


MAX_CONCEPT_WORDS = 4  # SAM finds short noun phrases ("seed", "root hair"), not descriptions
# Processes and quantities, not things: SAM can't outline "growth" or "the change" (a recipe measures them from the
# things it finds). Matched on any word of the concept, articles ignored.
PROCESS_WORDS = frozenset(
    {
        "growth",
        "growing",
        "change",
        "changes",
        "germination",
        "rate",
        "speed",
        "progress",
        "development",
        "reaction",
        "difference",
        "increase",
        "decrease",
        "rising",
        "spreading",
        "browning",
    }
)


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
    touching: str | None = None  # touching_count: the concept an object must touch to count
    min_length_mm: float | None = Field(None, gt=0)  # touching_count: the touched component's minimum length

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

    @model_validator(mode="after")
    def touching_count_names_what_it_touches(self) -> MeasurementSpec:
        if self.method == "touching_count" and (self.touching is None or self.min_length_mm is None):
            raise ValueError(f"'{self.id}': touching_count needs `touching` (a concept) and `min_length_mm`")
        if self.method != "touching_count" and (self.touching is not None or self.min_length_mm is not None):
            raise ValueError(f"'{self.id}': only touching_count takes `touching` and `min_length_mm`")
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

    def stored_metrics(self) -> list[str]:
        """The metric names this recipe's readings are stored under (lab_mean stores three: _l, _a, _b); rule-based
        methods aren't measured yet, so they aren't listed."""
        names: list[str] = []
        for spec in self.measurements:
            if spec.rule is not None:
                continue
            names += [f"{spec.id}_{axis}" for axis in "lab"] if spec.method == "lab_mean" else [spec.id]
        return names

    @field_validator("concepts")
    @classmethod
    def one_concept_each(cls, concepts: list[Concept]) -> list[Concept]:
        for concept in concepts:
            name = concept.name.strip()
            if any(sep in name for sep in (",", "+", "/")) or " and " in f" {name.lower()} ":
                raise ValueError(
                    f"'{concept.name}' names more than one thing; give each thing its own concept (SAM takes one "
                    "concept per request)"
                )
            process = next((w for w in name.lower().split() if w in PROCESS_WORDS), None)
            if process is not None:
                raise ValueError(
                    f"'{concept.name}' names a process, not a thing a camera can outline ('{process}'): name the "
                    "objects to find (a seed, a root, foam) and measure the process from them"
                )
            if len(name.split()) > MAX_CONCEPT_WORDS:
                raise ValueError(f"'{concept.name}' is too long for SAM: use a short noun phrase (at most 4 words)")
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
            if m.touching is not None and m.touching not in names:
                raise ValueError(f"measurement '{m.id}' counts objects touching unknown concept '{m.touching}'")
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

    @field_validator("events")
    @classmethod
    def events_are_rules_on_known_metrics(cls, events: list[EventSpec], info: ValidationInfo) -> list[EventSpec]:
        measurements = info.data.get("measurements", [])
        known = {m.id for m in measurements} | {f"{m.id}_{axis}" for m in measurements for axis in "lab"}
        for event in events:
            rule = parse_rule(event.id, event.when)
            if rule.metric not in known:
                raise ValueError(f"event '{event.id}' uses '{rule.metric}', which this recipe doesn't measure")
        return events
