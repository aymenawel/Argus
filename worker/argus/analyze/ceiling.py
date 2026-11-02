"""The verdict ceiling (spec §7.3, KB 08): code decides which verdicts the data allows; the model only explains.

The first rule that applies sets the allowed verdicts:
1. no locked plan, or before the plan's checkpoint → {TOO_EARLY};
2. the plan's metric unmeasured, no control, fewer than 2 treatment vessels, or no noise floor yet → {INCONCLUSIVE};
3. an open rival explanation, or a metric that never changed by the smallest effect in any compared vessel (Argus
   may not be seeing it at all) → {INCONCLUSIVE};
4. a treatment vessel shows a clear effect when its difference from the controls is larger than 3 × the noise
   floor, twice its own ± and at least the plan's smallest effect, in the predicted direction (against it:
   opposed); it is small when its ± rules out the smallest effect in the predicted direction. 2+ clear and none
   opposed → {SUPPORTED, INCONCLUSIVE}; every one small or opposed → {NOT_SUPPORTED, INCONCLUSIVE}; otherwise →
   {INCONCLUSIVE}. Without a smallest effect, nothing is small: no clear effect is not evidence of none.
A plan judged on a fitted half-way time or rate (D-78, D-79) needs 2 controls with a fitted value, has no noise floor
(each effect is judged by its own ± and the smallest effect: the readings' noise floor is in another unit), and stays
Inconclusive while any compared vessel has no fitted value: a dish that never germinated, or was still rising, is
evidence too.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from argus.claims.refs import Ref
from argus.domain import Direction, VerdictLevel
from argus.plain import metric_words

NOISE_FACTOR = 3.0  # an effect under ~3 × the noise floor is "not real yet" (KB 08)
K_UNCERTAINTY = 2.0  # within 2 × its own ± (about 95 %) a difference could still be zero, or the smallest effect
MIN_REPLICATES = 2
MIN_FITTED_CONTROLS = 2  # one control's fit ± says nothing of how dishes differ
FITTED = ("half_time", "rate")

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
    retrospective: bool = False  # published data judged after it existed (D-71): said so, never passed off as a test
    registered: bool = True  # some compared vessel's reading moved by the smallest effect: the measurement can see it
    quantity: str = "level"  # D-78: "half_time" or "rate" are judged on fitted curves, each with its fit's ±
    fit_notes: tuple[
        tuple[str, bool | None, str, str], ...
    ] = ()  # (check id, ok, text, prompt): refused or unreached fits, plateaus
    control_vessels: int = 0  # control vessels in the run, fitted or not
    # A level plan's vessels whose latest reading came before SAM stopped finding the object (D-91): measured, not now.
    lost_controls: int = 0
    lost_treatments: int = 0


def _effect(ref: Ref, inputs: VerdictInputs) -> Literal["clear", "opposed", "small", "unclear"]:
    size = abs(ref.value)
    toward = ref.value if inputs.direction is Direction.HIGHER else -ref.value  # signed: the predicted way is +
    big = (
        size > 0
        and size > K_UNCERTAINTY * ref.uncertainty
        and (inputs.quantity in FITTED or size > NOISE_FACTOR * (inputs.noise or 0.0))
        and size >= inputs.min_effect
    )
    if big:
        return "clear" if toward > 0 else "opposed"
    if inputs.min_effect > 0 and toward + K_UNCERTAINTY * ref.uncertainty < inputs.min_effect:
        return "small"
    return "unclear"


WOBBLE = "Normal wobble (how much readings jitter when nothing changes)"  # the noise floor, in plain words (D-95)


def without_digits(text: str) -> str:
    """A check's words for the model: its numbers are in the refs, never copied from text."""
    return " ".join(word for word in text.split() if not any(c.isdigit() for c in word))


def _hours(seconds: float) -> str:
    return f"{seconds / 3600:.0f} h" if seconds >= 3600 else f"{seconds / 60:.0f} min"


def _check(id_: str, ok: bool | None, text: str, refs: tuple[str, ...] = (), prompt: str | None = None) -> Check:
    return Check(id_, ok, text, refs, text if prompt is None else prompt)


def _vessels(n: int, role: str) -> str:
    return f"{n} {role} {'sample' if n == 1 else 'samples'}"


def ceiling(inputs: VerdictInputs) -> tuple[set[VerdictLevel], list[Check]]:
    """The allowed verdicts and every check behind them, in words."""
    if not inputs.locked:  # a run with no locked plan at all is refused before this (D-67): this one came too late
        text = (
            "The plan was written after this run's data was recorded, so this data can't test it: "
            "a guess made after seeing the result isn't a real test."
        )
        return {TOO_EARLY}, [_check("plan", False, text)]
    if inputs.checkpoint_s is not None and inputs.t < inputs.checkpoint_s:
        if inputs.running:
            text = "It's before the plan's check time, so it's too early to judge."
            prompt = text
        else:  # a finished run will never get there: say so rather than "wait"
            text = (
                f"The run ended at {_hours(inputs.t)}, before the plan's check time ({_hours(inputs.checkpoint_s)}), "
                "so it can't be judged against this plan."
            )
            prompt = "The run ended before the plan's check time, so it can't be judged against this plan."
        return {TOO_EARLY}, [_check("checkpoint", False, text, ("plan:checkpoint",), prompt=prompt)]
    metric = metric_words(inputs.metric) if inputs.metric else "the plan's measurement"
    checks = [_check("checkpoint", True, "Past the plan's check time.", ("plan:checkpoint",))]
    if inputs.retrospective:
        checks.append(
            _check(
                "retrospective",
                None,
                "Looking back: this is published data, recorded before the plan was written, so Argus is checking "
                "old data rather than testing a fresh prediction. The plan was locked before Argus measured it.",
            )
        )
    elif not inputs.recording_start_known:
        checks.append(
            _check(
                "preregistered",
                None,
                "The video's start time wasn't given, so Argus can't confirm the plan was written before filming. "
                "Give the start time when you import to settle it.",
            )
        )
    named = metric[:1].upper() + metric[1:]  # a check is a sentence: "Area was measured", not "area was measured"
    if inputs.measured:
        measured = f"{named} was measured in this run."
    elif inputs.lost_controls or inputs.lost_treatments:
        measured = f"{named} was measured, but SAM stopped finding the object in every sample after its last reading."
    else:
        measured = f"{named} has no readings in this run."
    checks.append(_check("measured", inputs.measured, measured))
    fitted = inputs.quantity in FITTED
    present = max(inputs.controls, inputs.control_vessels)
    if fitted and present and inputs.controls < MIN_FITTED_CONTROLS:
        checks.append(
            _check(
                "control",
                False,
                f"{inputs.controls} of {_vessels(present, 'control')} have a fitted curve; at least "
                f"{MIN_FITTED_CONTROLS} are needed to see how much samples naturally differ.",
                prompt="Too few control samples with a fitted curve to see how much samples naturally differ.",
            )
        )
    elif inputs.controls:
        checks.append(
            _check(
                "control",
                True,
                f"{_vessels(inputs.controls, 'control')} to compare against.",
                prompt="There are control samples to compare against.",
            )
        )
    elif inputs.lost_controls:
        text = (
            "SAM stopped finding the object in every control sample after its last reading, so there's nothing "
            "to compare against and other causes can't be ruled out."
        )
        checks.append(_check("control", False, text))
    else:
        checks.append(
            _check("control", False, "There is no control sample, so a change can't be told apart from other causes.")
        )
    enough = inputs.treatments >= MIN_REPLICATES
    counted = "have a curve to compare with the controls" if fitted else "were measured"
    lost, lost_prompt = "", ""
    if inputs.lost_treatments:
        lost = f" SAM stopped finding the object in {inputs.lost_treatments} of them after its last reading."
        lost_prompt = " SAM stopped finding the object in some of them after its last reading."
    checks.append(
        _check(
            "replicates",
            enough,
            f"{inputs.treatments} of {_vessels(max(inputs.planned, inputs.treatments), 'test')} {counted}; "
            f"at least {MIN_REPLICATES} are needed, since one sample could be a fluke." + lost,
            prompt=(
                "Enough test samples were measured."
                if enough
                else "Too few test samples were measured: one sample could be a fluke."
            )
            + lost_prompt,
        )
    )
    if fitted:
        words = "time to get half-way" if inputs.quantity == "half_time" else "speed"
        text = f"Judged on each sample's {words}, from the curve fitted to its readings, each with its own ±."
        checks.append(_check("fits", True, text))
        for id_, ok, note, prompt in inputs.fit_notes:
            checks.append(_check(id_, ok, note, prompt=prompt))
    elif inputs.noise is not None:
        checks.append(
            _check(
                "noise",
                True,
                f"{WOBBLE}: {inputs.noise_display or inputs.noise}.",
                (f"noise:{inputs.metric}",),
                prompt=f"{WOBBLE}: {{ref:noise:{inputs.metric}}}.",
            )
        )
    else:
        checks.append(
            _check("noise", False, "Normal wobble not known yet: too few readings before anything changed to judge.")
        )
    for name, state in inputs.rivals.items():
        resolved = state == "resolved"
        checks.append(
            _check(
                f"rival:{name}",
                True if resolved else None,
                f"Other possible cause '{name}': {'ruled out' if resolved else 'not ruled out yet'}.",
            )
        )
    if not inputs.registered:
        checks.append(
            _check(
                "registered",
                False,
                f"{named} never changed by the smallest real difference in any sample compared: Argus may not be "
                "able to see it, so 'no difference' can't count as proof of no effect.",
            )
        )
    verdicts = {}
    words = {
        "clear": "a clear difference in the predicted direction",
        "opposed": "a clear difference the opposite way from the prediction",
        "small": "smaller than the smallest difference the plan counts as real, even allowing for its ±",
        "unclear": "not a clear difference, and its ± is too wide to rule out a real one",
    }
    for label, ref in inputs.effects.items():
        verdicts[label] = _effect(ref, inputs)
        smallest = inputs.min_effect_display or inputs.min_effect
        bar = (
            f"twice its ± and the smallest real difference ({smallest})"
            if fitted
            else f"3 × the normal wobble, twice its ± and the smallest real difference ({smallest})"
        )
        checks.append(
            _check(
                f"effect:{label}",
                verdicts[label] == "clear",
                f"Sample {label}: {ref.display} compared with the controls, {words[verdicts[label]]} "
                f"(clear needs more than {bar}).",
                (ref.id,),
                prompt=f"Sample {label}: {{ref:{ref.id}}} compared with the controls, {words[verdicts[label]]} (judged "
                + (
                    "against its own ± and the smallest real difference {ref:plan:min_effect})."
                    if fitted
                    else "against the normal wobble, its own ± and the smallest real difference {ref:plan:min_effect})."
                ),
            )
        )

    if (
        not inputs.measured
        or inputs.controls < (MIN_FITTED_CONTROLS if fitted else 1)
        or inputs.treatments < MIN_REPLICATES
        or (inputs.noise is None and not fitted)
    ):
        return {INCONCLUSIVE}, checks
    if any(state == "open" for state in inputs.rivals.values()):
        return {INCONCLUSIVE}, checks
    if not inputs.registered:
        return {INCONCLUSIVE}, checks
    if fitted and any(ok is False for _, ok, _, _ in inputs.fit_notes):  # a compared vessel without a fitted value
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
