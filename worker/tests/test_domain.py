import re

import pytest
from pydantic import ValidationError

from argus.domain import MeasurementDraft, PlanDraft, VerdictLevel, new_id, plan_sha256


def test_new_id_has_prefix_and_is_unique():
    ids = {new_id("mea") for _ in range(1000)}
    assert len(ids) == 1000 and all(re.fullmatch(r"mea_[0-9a-f]{12}", i) for i in ids)


def test_verdict_levels_are_the_four_spec_words():
    assert [v.value for v in VerdictLevel] == ["SUPPORTED", "NOT_SUPPORTED", "INCONCLUSIVE", "TOO_EARLY"]


NAN, INF = float("nan"), float("inf")


# NaN would reach SQLite as NULL and abort the whole batch; inf is not a measurement.
@pytest.mark.parametrize(
    "field,value",
    [
        ("uncertainty", -0.1),
        ("unit", ""),
        ("method_version", "area"),
        ("t", -1.0),
        ("value", NAN),
        ("value", INF),
        ("uncertainty", NAN),
        ("uncertainty", INF),
        ("t", INF),
    ],
)
def test_measurement_draft_rejects_bad_values(field, value):
    good = dict(
        vessel_id="ves_1",
        frame_id=None,
        t=0.0,
        metric="area",
        value=1.0,
        uncertainty=0.1,
        unit="mm2",
        method_version="area/1",
    )
    with pytest.raises(ValidationError):
        MeasurementDraft(**{**good, field: value})


def test_plan_hash_is_stable_and_order_independent():
    a = PlanDraft(hypothesis="h", prediction="p", threshold="12 h", rivals=["light", "position"])
    assert plan_sha256(a) == plan_sha256(PlanDraft(**a.model_dump()))
    assert plan_sha256(a) != plan_sha256(a.model_copy(update={"threshold": "13 h"}))
