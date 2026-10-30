"""touching_count: objects of one concept that touch another concept at least min_length_mm long ("seeds with a
root"), the germination count Genze's labels give (D-73)."""

import numpy as np

from argus.calibration.run import calibrate
from argus.domain import Role, RulerInput, Vessel
from argus.measure.engine import measure_vessel
from argus.measure.geometry import touching_count
from argus.pipeline.analyzer import due_measurements
from argus.recipes.model import Recipe

MMPP = 0.1  # 10 px per mm


def blank() -> np.ndarray:
    return np.zeros((200, 200), bool)


def seed(x: int, y: int) -> np.ndarray:
    mask = blank()
    mask[y : y + 10, x : x + 10] = True
    return mask


def root(x: int, y: int, length: int) -> np.ndarray:
    """A 3-px-wide root running right from (x, y)."""
    mask = blank()
    mask[y : y + 3, x : x + length] = True
    return mask


def test_a_seed_with_a_long_enough_root_counts():
    assert touching_count([seed(20, 20)], root(30, 23, 30), MMPP, min_length_mm=2) == 1  # 3 mm root


def test_a_root_shorter_than_the_minimum_does_not_count():
    assert touching_count([seed(20, 20)], root(30, 23, 10), MMPP, min_length_mm=2) == 0  # 1 mm root


def test_a_seed_near_but_not_touching_a_root_does_not_count():
    assert touching_count([seed(20, 20)], root(35, 23, 30), MMPP, min_length_mm=2) == 0  # a 5 px gap


def test_a_seed_with_three_roots_counts_once():
    roots = root(30, 20, 30) | root(30, 26, 30) | root(0, 23, 20)
    assert touching_count([seed(20, 20)], roots, MMPP, min_length_mm=2) == 1


def test_two_seeds_sharing_one_root_count_twice():
    seeds = [seed(20, 20), seed(80, 20)]
    assert touching_count(seeds, root(30, 23, 50), MMPP, min_length_mm=2) == 2


GERMINATION = Recipe.model_validate(
    {
        "id": "own",
        "version": 1,
        "title": "Germination",
        "default_mode": "continuous",
        "analysis_step_s": 1800,
        "curve": "logistic",
        "concepts": [{"name": "seed"}, {"name": "root"}],
        "measurements": [
            {"id": "root_length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"},
            {
                "id": "germinated",
                "family": "count",
                "method": "touching_count",
                "from": "seed",
                "unit": "count",
                "touching": "root",
                "min_length_mm": 2,
            },
        ],
        "main_measurement": "germinated",
    }
)


def test_the_engine_stores_seeds_with_a_root_as_an_exact_count():
    image = np.zeros((200, 200, 3), np.uint8)
    cal = calibrate(image, ruler=RulerInput(p1=(0, 0), p2=(100, 0), distance_mm=10))
    roi = [(0.0, 0.0), (199.0, 0.0), (199.0, 199.0), (0.0, 199.0)]
    vessel = Vessel(id="ves_A", run_id="run_1", label="A", role=Role.TREATMENT, roi=roi)
    seeds = seed(20, 20) | seed(20, 120)  # the second has no root
    result = measure_vessel(
        GERMINATION,
        vessel,
        {"seed": seeds, "root": root(30, 23, 30)},
        image,
        cal,
        t=0.0,
        frame_id="frm_1",
        baselines={},
        current_reference=None,
    )
    germinated = next(d for d in result.drafts if d.metric == "germinated")
    assert (germinated.value, germinated.uncertainty, germinated.unit) == (1.0, 0.0, "count")
    assert germinated.method_version == "touching_count/1"


def test_a_touching_count_is_due_only_when_both_concepts_were_segmented():
    assert [m.id for m in due_measurements(GERMINATION, {"seed"})] == []
    assert [m.id for m in due_measurements(GERMINATION, {"root"})] == ["root_length"]
    assert [m.id for m in due_measurements(GERMINATION, {"seed", "root"})] == ["root_length", "germinated"]
