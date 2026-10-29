"""The claim checker (spec §7.2): numbers only as refs, refs that exist, the ceiling, known evidence."""

import pytest

from argus.claims.checker import check_note, check_text_fields, render, render_note
from argus.claims.fallback import fallback_note
from argus.claims.refs import Ref, RefTable
from argus.domain import VerdictLevel

ALL = set(VerdictLevel)


def refs_table(displays: dict[str, str]) -> RefTable:
    return RefTable(
        {
            i: Ref(
                id=i,
                label=i,
                value=1.0,
                uncertainty=0.1,
                unit="dE00",
                display=d,
                kind="measurement" if i.startswith("m:") else "change",
                t=10.0,
                vessel_id=None,
            )
            for i, d in displays.items()
        }
    )


REFS = refs_table({"m:A:delta_e": "3.7 ± 0.1 dE00", "chg:C:delta_e": "25.1 ± 0.1 dE00", "ev:1": "2:05"})


def clean_note(**overrides) -> dict:
    note = {
        "level": "checkpoint",
        "observation": "No change.",
        "interpretation": "",
        "hypothesis_status": "TOO_EARLY",
        "confidence": "low",
        "confidence_reason": "",
        "rival_explanations": [],
        "next_step": "",
        "refs_used": [],
        "evidence_ids": [],
        "question_for_researcher": "",
    }
    return note | overrides


def test_a_clean_note_passes_and_renders():
    note = clean_note(
        observation="Glass C changed by {ref:chg:C:delta_e} after {ref:ev:1}.", refs_used=["chg:C:delta_e", "ev:1"]
    )
    assert check_note(note, REFS, allowed=ALL, evidence=set()) == []
    body = render_note(note, REFS)
    assert body["observation"] == "Glass C changed by 25.1 ± 0.1 dE00 after 2:05."
    assert body["hypothesis_status"] == "TOO_EARLY" and body["refs_used"] == ["chg:C:delta_e", "ev:1"]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("Changed by 25 dE.", "number outside a ref in observation: '25'"),
        ("Changed by {ref:chg:Z:delta_e}.", "unknown ref: chg:Z:delta_e"),
        ("Warm water was twice as fast.", "quantity in words in observation: 'twice'"),
        ("About forty minutes later.", "quantity in words in observation: 'forty'"),
        ("A 50% rise.", "number outside a ref in observation: '50'"),
        ("A rise of fifty percent.", "quantity in words in observation: 'percent'"),
        ("Half of the glasses changed.", "quantity in words in observation: 'half'"),
        ("At 0.5 s.", "number outside a ref in observation: '0.5'"),
    ],
)
def test_numbers_outside_refs_are_rejected(text, reason):
    assert reason in check_note(clean_note(observation=text), REFS, allowed=ALL, evidence=set())


def test_every_text_field_is_checked():
    note = clean_note(
        interpretation="Likely 3 times faster.",
        rival_explanations=["lamp at 2 m"],
        next_step="Wait 10 minutes.",
        question_for_researcher="Was the lid off for 5 min?",
        confidence_reason="Only 2 vessels.",
    )
    reasons = check_note(note, REFS, allowed=ALL, evidence=set())
    for field in ("interpretation", "rival_explanations", "next_step", "question_for_researcher", "confidence_reason"):
        assert any(f"in {field}" in r for r in reasons), field


def test_model_names_and_the_word_one_are_allowed():
    note = clean_note(observation="SAM 3.1 found one glass; Muse Spark 1.3 wrote this.")
    assert check_note(note, REFS, allowed=ALL, evidence=set()) == []


def test_refs_used_must_exist_too():
    assert "unknown ref: m:Q:delta_e" in check_note(
        clean_note(refs_used=["m:Q:delta_e"]), REFS, allowed=ALL, evidence=set()
    )


def test_a_status_above_the_ceiling_is_rejected():
    note = clean_note(hypothesis_status="SUPPORTED")
    reasons = check_note(note, REFS, allowed={VerdictLevel.TOO_EARLY}, evidence=set())
    assert "status above the ceiling: SUPPORTED" in reasons


def test_unknown_evidence_is_rejected():
    reasons = check_note(clean_note(evidence_ids=["frm_x"]), REFS, allowed=ALL, evidence={"frm_a"})
    assert "unknown evidence: frm_x" in reasons


def test_a_note_missing_a_field_is_rejected():
    note = clean_note()
    del note["observation"]
    assert "missing field: observation" in check_note(note, REFS, allowed=ALL, evidence=set())


def test_text_fields_of_any_shape_can_be_checked():
    verdict = {
        "explanation": "C rose by {ref:chg:C:delta_e}.",
        "rivals": [{"name": "lamp", "status": "open", "reason": "It moved 3 cm."}],
    }
    reasons = check_text_fields(verdict, ["explanation", "rivals[*].reason"], REFS)
    assert reasons == ["number outside a ref in rivals[*].reason: '3'"]


def test_render_leaves_unknown_tokens_visible():
    assert render("{ref:chg:C:delta_e} and {ref:nope}", REFS) == "25.1 ± 0.1 dE00 and {ref:nope}"


def test_a_code_note_uses_only_refs_and_says_so():
    body = fallback_note("checkpoint", REFS, reason="notes paused: spend cap")
    assert body["written_by"] == "code" and body["reason"] == "notes paused: spend cap"
    assert "3.7 ± 0.1 dE00" in body["observation"] and "25.1 ± 0.1 dE00" in body["observation"]
    assert fallback_note("checkpoint", RefTable({}), reason="x")["observation"] == "No readings yet."
