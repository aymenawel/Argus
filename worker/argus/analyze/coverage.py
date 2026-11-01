"""How often SAM found a vessel's object, counted from its recorded answers (D-90): what Results shows beside each
vessel's curve, so a dish SAM kept missing reads as poorly seen, not as measured."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from argus.domain import RunEvent, SamAnswer
from argus.recipes.model import MeasurementSpec


@dataclass(frozen=True)
class Coverage:
    concept: str
    asked: int  # frames SAM answered for this vessel and concept
    found: int  # of those, frames where it found at least one object
    first_found_t: float | None  # run time of the first find (s); None if never found
    missed_after: int  # frames after the first find where it found nothing


def lost_after(events: Sequence[RunEvent], vessel_id: str, spec: MeasurementSpec, t: float) -> str | None:
    """The concept SAM stopped finding in this vessel after time t, if it did, among those the measurement reads: a
    reading taken at t is then no reading of now (D-91). A quiet stretch without segmentation never makes a reading
    stale; only a miss does."""
    read = {spec.source, spec.touching}
    for event in events:
        concept = event.detail.get("concept")
        if event.kind == "missed" and event.vessel_id == vessel_id and event.t_start > t and concept in read:
            return concept
    return None


def detection_coverage(answers: Sequence[SamAnswer], vessel_id: str, concept: str) -> Coverage | None:
    """None when SAM's answers for this vessel and concept weren't recorded (a run from before D-90)."""
    mine = sorted((a for a in answers if a.vessel_id == vessel_id and a.concept == concept), key=lambda a: a.t)
    if not mine:
        return None
    first = next((a.t for a in mine if a.found), None)
    missed = 0 if first is None else sum(1 for a in mine if not a.found and a.t > first)
    return Coverage(concept, len(mine), sum(1 for a in mine if a.found), first, missed)
