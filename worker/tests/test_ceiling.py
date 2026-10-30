"""The verdict ceiling (spec §7.3, KB 08): code decides which verdicts the data allows, and says why in words."""

import pytest

from argus.analyze.ceiling import VerdictInputs, ceiling, choose_verdict
from argus.claims.refs import Ref
from argus.domain import Direction, VerdictLevel

SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE, TOO_EARLY = (
    VerdictLevel.SUPPORTED,
    VerdictLevel.NOT_SUPPORTED,
    VerdictLevel.INCONCLUSIVE,
    VerdictLevel.TOO_EARLY,
)


def diff(value: float, label: str = "C", u: float = 0.1) -> Ref:
    return Ref(
        id=f"diff:{label}:delta_e",
        label=label,
        value=value,
        uncertainty=u,
        unit="dE00",
        display=f"{value:g} ± {u:g} dE00",
        kind="difference",
        t=600.0,
        vessel_id=f"ves_{label}",
    )


def inputs(**overrides) -> VerdictInputs:
    fields = dict(
        t=600.0,
        running=False,
        locked=True,
        checkpoint_s=300.0,
        controls=2,
        treatments=2,
        effects={"C": diff(20.0, "C"), "D": diff(18.0, "D")},
        noise=1.0,
        min_effect=5.0,
        direction=Direction.HIGHER,
        rivals={},
        measured=True,
    )
    fields |= overrides
    if "effects" in overrides:
        fields["effects"] = {k: diff(v.value, k, v.uncertainty) for k, v in fields["effects"].items()}
    return VerdictInputs(**fields)


@pytest.mark.parametrize(
    "case, allowed",
    [
        (dict(t=200.0), {TOO_EARLY}),
        (dict(locked=False), {TOO_EARLY}),
        (dict(controls=0), {INCONCLUSIVE}),
        (dict(treatments=1), {INCONCLUSIVE}),
        (dict(measured=False), {INCONCLUSIVE}),
        (dict(noise=None), {INCONCLUSIVE}),
        (dict(rivals={"temperature": "open"}), {INCONCLUSIVE}),
        (dict(rivals={"temperature": "resolved"}), {SUPPORTED, INCONCLUSIVE}),
        (dict(effects={"C": diff(20.0), "D": diff(18.0)}), {SUPPORTED, INCONCLUSIVE}),
        (dict(effects={"C": diff(0.2), "D": diff(-0.3)}), {NOT_SUPPORTED, INCONCLUSIVE}),
        (dict(effects={"C": diff(20.0), "D": diff(0.1)}), {INCONCLUSIVE}),
        (dict(effects={"C": diff(20.0), "D": diff(-20.0)}), {INCONCLUSIVE}),
        (dict(effects={"C": diff(4.0), "D": diff(4.5)}), {NOT_SUPPORTED, INCONCLUSIVE}),  # under the smallest effect
        # With no smallest effect, the absence of a clear effect isn't evidence of none.
        (dict(effects={"C": diff(2.5), "D": diff(2.9)}, min_effect=0.0), {INCONCLUSIVE}),
        # An effect within twice its own ± is not clear, however big it reads.
        (dict(effects={"C": diff(6.0, u=5.0), "D": diff(7.0, u=5.0)}, noise=0.1), {INCONCLUSIVE}),
        (dict(effects={"C": diff(0.01, u=5.0), "D": diff(0.02, u=5.0)}, noise=0.0, min_effect=0.0), {INCONCLUSIVE}),
        # Not supported needs the ± to rule out the smallest effect, not just no clear effect.
        (dict(effects={"C": diff(1.0, u=3.0), "D": diff(1.0, u=3.0)}), {INCONCLUSIVE}),
        (dict(effects={"C": diff(-20.0), "D": diff(-18.0)}, direction=Direction.LOWER), {SUPPORTED, INCONCLUSIVE}),
        (dict(effects={"C": diff(-20.0), "D": diff(-18.0)}), {NOT_SUPPORTED, INCONCLUSIVE}),  # clear but opposite
    ],
)
def test_the_ceiling_table(case, allowed):
    assert ceiling(inputs(**case))[0] == allowed


def test_every_ceiling_says_why_in_words():
    _, checks = ceiling(inputs(controls=0))
    control = next(c for c in checks if c.id == "control")
    assert control.ok is False and "no control vessel" in control.text
    _, checks = ceiling(inputs(rivals={"temperature": "open"}))
    rival = next(c for c in checks if c.id == "rival:temperature")
    assert rival.ok is None and "temperature" in rival.text and "open" in rival.text


def test_effect_checks_cite_their_refs():
    _, checks = ceiling(inputs())
    effect = next(c for c in checks if c.id == "effect:C")
    assert effect.ok is True and effect.refs == ("diff:C:delta_e",) and "20 ± 0.1 dE00" in effect.text


def test_before_the_checkpoint_only_the_checkpoint_is_judged():
    allowed, checks = ceiling(inputs(t=200.0, controls=0))
    assert allowed == {TOO_EARLY} and checks[0].id == "checkpoint" and checks[0].ok is False


@pytest.mark.parametrize(
    "allowed, draft, critique, final",
    [
        ({SUPPORTED, INCONCLUSIVE}, SUPPORTED, INCONCLUSIVE, INCONCLUSIVE),
        ({SUPPORTED, INCONCLUSIVE}, SUPPORTED, NOT_SUPPORTED, SUPPORTED),
        ({SUPPORTED, INCONCLUSIVE}, SUPPORTED, None, SUPPORTED),
        ({INCONCLUSIVE}, SUPPORTED, SUPPORTED, INCONCLUSIVE),
        ({TOO_EARLY}, SUPPORTED, None, TOO_EARLY),
        ({NOT_SUPPORTED, INCONCLUSIVE}, SUPPORTED, TOO_EARLY, INCONCLUSIVE),
    ],
)
def test_choosing_the_final_verdict(allowed, draft, critique, final):
    assert choose_verdict(allowed, draft, critique) is final


def test_a_metric_that_never_changed_cannot_support_no_effect():
    """Every reading 0 ± 0 (a count Argus never saw rise): "small" would read as evidence of no effect."""
    zero = {"C": diff(0.0, "C", 0.0), "D": diff(0.0, "D", 0.0)}
    allowed, checks = ceiling(inputs(effects=zero, noise=0.0, min_effect=2.0, registered=False))
    assert allowed == {INCONCLUSIVE}
    flag = next(c for c in checks if c.id == "registered")
    assert flag.ok is False and "never changed" in flag.text


def test_a_finished_run_that_ended_before_its_checkpoint_says_so():
    allowed, checks = ceiling(inputs(t=169200.0, checkpoint_s=172800.0, running=False))
    assert allowed == {TOO_EARLY}
    assert "ended" in checks[0].text and "47 h" in checks[0].text and "48 h" in checks[0].text
    _, live = ceiling(inputs(t=200.0, running=True))
    assert "Before the plan's checkpoint" in live[0].text
