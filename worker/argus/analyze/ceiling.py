"""The verdict ceiling (spec §7.3, KB 08): code decides which verdicts the data allows; the model only explains.

The first rule that applies sets the allowed verdicts:
1. no locked plan, or before the plan's checkpoint → {TOO_EARLY};
2. the plan's metric unmeasured, no control, fewer than 2 treatment vessels, or no noise floor yet → {INCONCLUSIVE};
3. an open rival explanation → {INCONCLUSIVE};
4. a treatment vessel shows a clear effect when its difference from the controls is larger than 3 × the noise
   floor, twice its own ± and at least the plan's smallest effect, in the predicted direction (against it:
   opposed); it is small when its ± rules out the smallest effect in the predicted direction. 2+ clear and none
   opposed → {SUPPORTED, INCONCLUSIVE}; every one small or opposed → {NOT_SUPPORTED, INCONCLUSIVE}; otherwise →
   {INCONCLUSIVE}. Without a smallest effect, nothing is small: no clear effect is not evidence of none.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from argus.claims.refs import Ref
from argus.domain import Direction, VerdictLevel

NOISE_FACTOR = 3.0  # an effect under ~3 × the noise floor is "not real yet" (KB 08)
K_UNCERTAINTY = 2.0  # within 2 × its own ± (about 95 %) a difference could still be zero, or the smallest effect
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
    planned: int = 0  # treatment vessels in the comparison, measured or not
    recording_start_known: bool = True  # an import whose recording start nobody gave can't show the plan came first


def _effect(ref: Ref, inputs: VerdictInputs) -> Literal["clear", "opposed", "small", "unclear"]:
    size = abs(ref.value)
    toward = ref.value if inputs.direction is Direction.HIGHER else -ref.value  # signed: the predicted way is +
    big = (
        size > 0
        and size > K_UNCERTAINTY * ref.uncertainty
        and size > NOISE_FACTOR * (inputs.noise or 0.0)
        and size >= inputs.min_effect
    )
    if big:
        return "clear" if toward > 0 else "opposed"
    if inputs.min_effect > 0 and toward + K_UNCERTAINTY * ref.uncertainty < inputs.min_effect:
        return "small"
    return "unclear"


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
    if not inputs.recording_start_known:
        checks.append(
            _check(
                "preregistered",
                None,
                "The recording's start time wasn't given, so Argus can't confirm the plan was locked before the data "
                "was recorded. Give the start time when you import to settle it.",
            )
        )
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
            f"{inputs.treatments} of {max(inputs.planned, inputs.treatments)} treatment vessel(s) in the comparison "
            f"measured; at least {MIN_REPLICATES} are needed.",
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
        "small": "smaller than the smallest effect that matters, its ± included",
        "unclear": "no clear effect, and its ± can't rule out the smallest effect",
    }
    for label, ref in inputs.effects.items():
        verdicts[label] = _effect(ref, inputs)
        smallest = inputs.min_effect_display or inputs.min_effect
        bar = f"3 × the noise floor, twice its ± and the smallest effect ({smallest})"
        checks.append(
            _check(
                f"effect:{label}",
                verdicts[label] == "clear",
                f"Vessel {label}: {ref.display} against the controls, {words[verdicts[label]]} "
                f"(clear needs more than {bar}).",
                (ref.id,),
                prompt=f"Vessel {label}: {{ref:{ref.id}}} against the controls, {words[verdicts[label]]} (judged "
                "against the noise floor, its own ± and the smallest effect {ref:plan:min_effect}).",
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
    if verdicts and all(v in ("small", "opposed") for v in verdicts.values()):
        return {NOT_SUPPORTED, INCONCLUSIVE}, checks
    return {INCONCLUSIVE}, checks


def choose_verdict(allowed: set[VerdictLevel], draft: VerdictLevel, critique: VerdictLevel | None) -> VerdictLevel:
    """The critique's verdict if allowed, else the draft's if allowed, else the most cautious allowed one."""
    for candidate in (critique, draft):
        if candidate is not None and candidate in allowed:
            return candidate
    return TOO_EARLY if TOO_EARLY in allowed else INCONCLUSIVE
