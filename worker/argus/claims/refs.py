"""Refs: the numbers a reasoning call may cite, each with an id the model writes as {ref:<id>} (spec §6, §7.2).

The model never writes a number; code renders each token as its ref's `display`. build_refs() (the numbers for a
run at a time t) is added in Task 4; the types live here so prompt assembly can use them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ref:
    id: str
    label: str
    value: float
    uncertainty: float
    unit: str
    display: str  # what a {ref:<id>} token renders as, formatted like the UI ("25.6 ± 0.1 dE00")
    kind: str  # measurement, change, difference, noise_floor, event, plan, time
    t: float | None
    vessel_id: str | None
    evidence: tuple[str, ...] = ()  # ids of the rows behind it: a measurement, a derived row, an event


@dataclass(frozen=True)
class RefTable:
    refs: Mapping[str, Ref] = field(default_factory=dict)

    def get(self, ref_id: str) -> Ref | None:
        return self.refs.get(ref_id)

    def ids(self) -> list[str]:
        return sorted(self.refs)

    def __contains__(self, ref_id: object) -> bool:
        return ref_id in self.refs
