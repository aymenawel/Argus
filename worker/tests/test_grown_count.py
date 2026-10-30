"""grown_count: objects whose outline grew by at least min_length_mm since Argus first saw them there (a seed whose
sprout shows as part of SAM's seed outline, Q-18). Each object is compared with the earlier outline it overlaps most,
so it needs no stable track keys; an object seen for the first time never counts."""

import numpy as np
import pytest
from pydantic import ValidationError

from argus.calibration.run import calibrate
from argus.domain import Role, RulerInput, Vessel
from argus.measure.engine import measure_vessel
from argus.recipes.model import MeasurementSpec, Recipe

SIZE = 200
IMAGE = np.zeros((SIZE, SIZE, 3), np.uint8)
CAL = calibrate(IMAGE, ruler=RulerInput(p1=(0, 0), p2=(100, 0), distance_mm=10))  # 0.1 mm per px
VESSEL = Vessel(
    id="ves_A",
    run_id="run_1",
    label="A",
    role=Role.TREATMENT,
    roi=[(0.0, 0.0), (199.0, 0.0), (199.0, 199.0), (0.0, 199.0)],
)
RECIPE = Recipe.model_validate(
    {
        "id": "own",
        "version": 1,
        "title": "Germination",
        "default_mode": "continuous",
        "analysis_step_s": 1800,
        "curve": "logistic",
        "concepts": [{"name": "seed"}],
        "measurements": [
            {
                "id": "germinated",
                "family": "count",
                "method": "grown_count",
                "from": "seed",
                "unit": "count",
                "min_length_mm": 2,
            }
        ],
        "main_measurement": "germinated",
    }
)


def seed(y: int, length_px: int = 60, x: int = 20) -> np.ndarray:
    """A seed lying along x, 12 px thick; a longer one has its sprout in the same outline."""
    mask = np.zeros((SIZE, SIZE), bool)
    mask[y : y + 12, x : x + length_px] = True
    return mask


def measure(objects, first_seen=None, *, union=None):
    """One frame: SAM's per-object masks for 'seed' (or only their union, when `objects` is None)."""
    masks = {
        "seed": union
        if union is not None
        else np.logical_or.reduce(objects)
        if objects
        else np.zeros((SIZE, SIZE), bool)
    }
    return measure_vessel(
        RECIPE,
        VESSEL,
        masks,
        IMAGE,
        CAL,
        t=0.0,
        frame_id=None,
        baselines={},
        current_reference=None,
        objects={"seed": objects} if objects is not None else None,
        first_seen=first_seen or {},
    )


def germinated(result):
    return [(d.value, d.uncertainty, d.method_version) for d in result.drafts if d.metric == "germinated"]


def test_a_seed_whose_outline_grew_enough_counts():
    first = measure([seed(20), seed(80)])
    assert germinated(first) == [(0.0, 0.0, "grown_count/1")]  # first sighting: nothing has grown yet
    later = measure([seed(20, 60 + 30), seed(80, 60 + 10)], first.first_seen)  # 3 mm and 1 mm longer
    assert germinated(later) == [(1.0, 0.0, "grown_count/1")]


def test_an_object_first_seen_already_long_does_not_count():
    assert germinated(measure([seed(20, 160)])) == [(0.0, 0.0, "grown_count/1")]


def test_no_objects_found_is_a_gap_not_zero():
    assert germinated(measure([])) == []


def test_seeds_whose_outlines_touch_are_kept_apart_by_their_own_masks():
    a, b = seed(20), seed(32)  # stacked: their union is one blob
    first = measure([a, b])
    later = measure([seed(20, 95), seed(32, 95)], first.first_seen)
    assert germinated(later) == [(2.0, 0.0, "grown_count/1")]
    merged_first = measure(None, union=a | b)
    merged_later = measure(None, {**merged_first.first_seen}, union=seed(20, 95) | seed(32, 95))
    assert germinated(merged_later) == [(1.0, 0.0, "grown_count/1")]  # without masks per object: one blob


def test_grown_count_takes_a_minimum_length_and_nothing_to_touch():
    base = {"id": "g", "family": "count", "method": "grown_count", "from": "seed", "unit": "count"}
    with pytest.raises(ValidationError, match="min_length_mm"):
        MeasurementSpec.model_validate(base)
    with pytest.raises(ValidationError, match="touching"):
        MeasurementSpec.model_validate(base | {"min_length_mm": 2, "touching": "root"})
    assert MeasurementSpec.model_validate(base | {"min_length_mm": 2}).min_length_mm == 2
