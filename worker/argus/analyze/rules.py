"""Recipe rule events (spec §4.1 step 5, §6): `when = "<metric> <op> <number>"`, parsed by a pattern, never eval'd.

A rule fires once per vessel per run, at the first reading that crosses it, and becomes an event with
source "rule" that notes can cite.
"""

from __future__ import annotations

import operator
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from argus.domain import Measurement

if TYPE_CHECKING:
    from argus.recipes.model import Recipe

RULE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|>|<)\s*([-+]?\d+(?:\.\d+)?)\s*$")
OPERATORS: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


@dataclass(frozen=True)
class Rule:
    id: str
    metric: str
    op: str
    value: float

    def holds(self, reading: float) -> bool:
        return OPERATORS[self.op](reading, self.value)


def parse_rule(event_id: str, when: str) -> Rule:
    match = RULE.match(when)
    if match is None:
        raise ValueError(f"rule '{event_id}' must read '<metric> <op> <number>' with op >, >=, < or <=: {when!r}")
    metric, op, value = match.groups()
    return Rule(event_id, metric, op, float(value))


class RuleEvaluator:
    """The recipe's rules over stored readings; remembers which (rule, vessel) pairs already fired."""

    def __init__(self, recipe: Recipe) -> None:
        measured = set(recipe.stored_metrics())
        rules = [parse_rule(e.id, e.when) for e in recipe.events]
        self.rules = [r for r in rules if r.metric in measured]  # rules on rule-based methods wait for them
        self._fired: set[tuple[str, str]] = set()

    def fired(self, readings: Sequence[Measurement]) -> list[tuple[Rule, Measurement]]:
        crossings = []
        for reading in sorted(readings, key=lambda r: r.t):
            for rule in self.rules:
                key = (rule.id, reading.vessel_id)
                if reading.metric == rule.metric and key not in self._fired and rule.holds(reading.value):
                    self._fired.add(key)
                    crossings.append((rule, reading))
        return crossings
