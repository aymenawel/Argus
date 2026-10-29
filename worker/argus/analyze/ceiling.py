"""The verdict ceiling (spec §7.3, KB 08): code decides which verdicts the data allows; the model only explains.

The first rule that applies sets the allowed verdicts:
1. no locked plan, or before the plan's checkpoint → {TOO_EARLY};
2. the plan's metric unmeasured, no control, fewer than 2 treatment vessels, or no noise floor yet → {INCONCLUSIVE};
3. an open rival explanation → {INCONCLUSIVE};
4. a treatment vessel shows a clear effect when its difference from the controls is in the predicted direction,
   larger than 3 × the noise floor and at least the plan's smallest effect (clear against the prediction:
   opposed). 2+ clear and none opposed → {SUPPORTED, INCONCLUSIVE}; none clear → {NOT_SUPPORTED, INCONCLUSIVE};
   otherwise → {INCONCLUSIVE}.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from argus.claims.refs import Ref
from argus.domain import Direction, VerdictLevel

NOISE_FACTOR = 3.0  # an effect under ~3 × the noise floor is "not real yet" (KB 08)
MIN_REPLICATES = 2

SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE, TOO_EARLY = (
    VerdictLevel.SUPPORTED,
    VerdictLevel.NOT_SUPPORTED,
    VerdictLevel.INCONCLUSIVE,
    VerdictLevel.TOO_EARLY,
)


@dataclass(frozen=True)
class Check:
    id: str
    ok: bool | None  # None: open (a rival nobody has resolved yet)
    text: str  # for the UI, numbers rendered
    refs: tuple[str, ...] = ()
    prompt: str = ""  # for the verdict prompt: numbers only as {ref:<id>} tokens, no digits a model could copy

    def as_dict(self) -> dict:
        return {"id": self.id, "ok": self.ok, "text": self.text, "refs": list(self.refs)}


@dataclass(frozen=True)
class VerdictInputs:
    t: float
    running: bool
    locked: bool
    checkpoint_s: float | None
    controls: int
    treatments: int
    effects: Mapping[str, Ref]  # treatment vessel label → its difference from the controls' mean
    noise: float | None
    min_effect: float
    direction: Direction | None
    rivals: Mapping[str, Literal["resolved", "open"]]
    measured: bool
    noise_display: str = ""
    min_effect_display: str = ""
    metric: str = ""


def _effect(ref: Ref, inputs: VerdictInputs) -> Literal["clear", "opposed", "unclear"]:
    big = abs(ref.value) > NOISE_FACTOR * (inputs.noise or 0.0) and abs(ref.value) >= inputs.min_effect
    if not big or ref.value == 0:
        return "unclear"
    predicted = ref.value > 0 if inputs.direction is Direction.HIGHER else ref.value < 0
    return "clear" if predicted else "opposed"


def _check(id_: str, ok: bool | None, text: str, refs: tuple[str, ...] = (), prompt: str | None = None) -> Check:
    return Check(id_, ok, text, refs, text if prompt is None else prompt)


def ceiling(inputs: VerdictInputs) -> tuple[set[VerdictLevel], list[Check]]:
    """The allowed verdicts and every check behind them, in words."""
    if not inputs.locked:
        return {TOO_EARLY}, [_check("plan", False, "No plan was locked before the run, so nothing can be judged.")]
    if inputs.checkpoint_s is not None and inputs.t < inputs.checkpoint_s:
        return {TOO_EARLY}, [
            _check(
                "checkpoint", False, "Before the plan's checkpoint: a verdict would be too early.", ("plan:checkpoint",)
            )
        ]
    metric = inputs.metric or "the plan's metric"
    checks = [_check("checkpoint", True, "Past the plan's checkpoint.", ("plan:checkpoint",))]
    checks.append(
        _check(
            "measured",
            inputs.measured,
            f"{metric} was measured in this run." if inputs.measured else f"{metric} has no readings in this run.",
        )
    )
    if inputs.controls:
        checks.append(
            _check(
                "control",
                True,
                f"{inputs.controls} control vessel(s) to compare against.",
                prompt="There are control vessels to compare against.",
            )
        )
    else:
        checks.append(
            _check("control", False, "There is no control vessel, so a treatment can't be told from other causes.")
        )
    enough = inputs.treatments >= MIN_REPLICATES
    checks.append(
        _check(
            "replicates",
            enough,
            f"{inputs.treatments} treatment vessel(s) in the comparison; at least {MIN_REPLICATES} are needed.",
            prompt="Enough treatment vessels in the comparison."
            if enough
            else "Too few treatment vessels in the comparison to count replicates.",
        )
    )
    if inputs.noise is not None:
        checks.append(
            _check(
                "noise",
                True,
                f"Noise floor: {inputs.noise_display or inputs.noise}.",
                (f"noise:{inputs.metric}",),
                prompt=f"Noise floor: {{ref:noise:{inputs.metric}}}.",
            )
        )
    else:
        checks.append(_check("noise", False, "No noise floor yet: too few still readings to judge an effect."))
    for name, state in inputs.rivals.items():
        resolved = state == "resolved"
        checks.append(
            _check(
                f"rival:{name}",
                True if resolved else None,
                f"Rival explanation '{name}': {'resolved' if resolved else 'open'}.",
            )
        )
    verdicts = {}
    words = {
        "clear": "a clear effect in the predicted direction",
        "opposed": "a clear effect against the prediction",
        "unclear": "no clear effect",
    }
    for label, ref in inputs.effects.items():
        verdicts[label] = _effect(ref, inputs)
        bar = f"3 × the noise floor and the smallest effect ({inputs.min_effect_display or inputs.min_effect})"
        checks.append(
            _check(
                f"effect:{label}",
                verdicts[label] == "clear",
                f"Vessel {label}: {ref.display} against the controls, {words[verdicts[label]]} "
                f"(needs more than {bar}).",
                (ref.id,),
                prompt=f"Vessel {label}: {{ref:{ref.id}}} against the controls, {words[verdicts[label]]} (judged "
                "against the noise floor and the smallest effect {ref:plan:min_effect}).",
            )
        )

    if not inputs.measured or inputs.controls == 0 or inputs.treatments < MIN_REPLICATES or inputs.noise is None:
        return {INCONCLUSIVE}, checks
    if any(state == "open" for state in inputs.rivals.values()):
        return {INCONCLUSIVE}, checks
    clear = sum(v == "clear" for v in verdicts.values())
    opposed = sum(v == "opposed" for v in verdicts.values())
    if clear >= MIN_REPLICATES and opposed == 0:
        return {SUPPORTED, INCONCLUSIVE}, checks
    if clear == 0:
        return {NOT_SUPPORTED, INCONCLUSIVE}, checks
    return {INCONCLUSIVE}, checks


def choose_verdict(allowed: set[VerdictLevel], draft: VerdictLevel, critique: VerdictLevel | None) -> VerdictLevel:
    """The critique's verdict if allowed, else the draft's if allowed, else the most cautious allowed one."""
    for candidate in (critique, draft):
        if candidate is not None and candidate in allowed:
            return candidate
    return TOO_EARLY if TOO_EARLY in allowed else INCONCLUSIVE
