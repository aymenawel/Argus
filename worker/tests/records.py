"""Small builders for records used across the storage tests."""

from argus.domain import MeasurementDraft, PlanDraft

DRAFT = PlanDraft(
    hypothesis="More salt makes mung beans sprout slower and less",
    prediction="High-salt beans reach 50% sprouted at least 12 hours later than no-salt beans",
    threshold="12 h",
    rivals=["temperature", "uneven watering", "position in the row", "seed batch"],
)


def draft(vessel_id: str, t: float, value: float = 1.0) -> MeasurementDraft:
    return MeasurementDraft(
        vessel_id=vessel_id,
        frame_id=None,
        t=t,
        metric="area",
        value=value,
        uncertainty=0.1,
        unit="mm2",
        method_version="area/1",
    )
