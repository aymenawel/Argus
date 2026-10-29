"""Every model answer is checked against its schema in code: types, enums, required and unexpected fields."""

import pytest

from argus.claims.schema import schema_errors
from argus.reason.prompts import load_schema
from tests.reasoning import clean_note, critique, verdict_draft

NOTE = load_schema("note")


def test_a_clean_answer_has_no_errors():
    assert schema_errors(clean_note(), NOTE) == []
    assert schema_errors(verdict_draft(), load_schema("verdict")) == []
    assert schema_errors(critique(), load_schema("verdict_critique")) == []


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"observation": 42}, "observation: expected a string"),
        ({"confidence": "90%"}, "confidence: '90%' is not one of"),
        ({"level": "headline"}, "level: 'headline' is not one of"),
        ({"rival_explanations": [{"name": "lamp"}]}, "rival_explanations[0]: expected a string"),
        ({"hypothesis_status": ["SUPPORTED"]}, "hypothesis_status: expected a string"),
        ({"extra": "x"}, "unexpected field: extra"),
    ],
)
def test_a_malformed_note_is_described_not_crashed_on(overrides, error):
    errors = schema_errors(clean_note(**overrides), NOTE)
    assert any(e.startswith(error) for e in errors), errors


def test_missing_fields_and_wrong_shapes_in_nested_items():
    draft = verdict_draft()
    del draft["explanation"]
    draft["rivals"] = [{"name": "lamp", "status": "gone"}]
    errors = schema_errors(draft, load_schema("verdict"))
    assert "missing field: explanation" in errors
    assert "rivals[0]: missing field: reason" in errors and any(e.startswith("rivals[0].status:") for e in errors)
    assert schema_errors("not an object", NOTE) == ["answer: expected an object"]
