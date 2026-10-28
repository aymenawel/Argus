import numpy as np
import pytest
from pydantic import ValidationError
from skimage.color import deltaE_ciede2000, rgb2lab

from argus.calibration.card import STANDARD
from argus.calibration.run import calibrate
from argus.config import REPO_ROOT
from argus.domain import Role, Vessel
from argus.measure.engine import ColourBaseline, measure_vessel
from argus.recipes.loader import load_recipe
from argus.recipes.model import MeasurementSpec, Recipe
from tests.helpers import TILT, scene_with_bar_on_card_plane

RECIPE = Recipe.model_validate(
    {
        "id": "test",
        "version": 1,
        "title": "Test",
        "default_mode": "smart_trigger",
        "analysis_step_s": 60,
        "curve": "linear",
        "concepts": [{"name": "root"}],
        "measurements": [
            {"id": "length", "family": "size", "method": "skeleton_length", "from": "root", "unit": "mm"},
            {"id": "area", "family": "size", "method": "area", "from": "root", "unit": "mm2"},
            {"id": "height", "family": "size", "method": "height", "from": "root", "unit": "mm"},
            {"id": "pieces", "family": "count", "method": "component_count", "from": "root", "unit": "count"},
            {"id": "colour", "family": "colour", "method": "lab_mean", "from": "root", "unit": "Lab"},
            {"id": "change", "family": "colour", "method": "delta_e", "from": "root", "unit": "dE00"},
        ],
        "main_measurement": "length",
    }
)


def vessel_around(mask: np.ndarray, margin: int = 30) -> Vessel:
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = xs.min() - margin, ys.min() - margin, xs.max() + margin, ys.max() + margin
    roi = [(float(x0), float(y0)), (float(x1), float(y0)), (float(x1), float(y1)), (float(x0), float(y1))]
    return Vessel(id="ves_A", run_id="run_1", label="A", role=Role.TREATMENT, roi=roi)


def measure(image, mask, *, baselines=None, families=frozenset({"size", "count", "colour"}), masks=None):
    return measure_vessel(
        RECIPE,
        vessel_around(mask),
        {"root": mask} if masks is None else masks,
        image,
        calibrate(image),
        t=0.0,
        frame_id="frm_1",
        baselines=baselines or {},
        current_reference=None,
        families=families,
    )


def test_a_known_bar_on_a_tilted_card_measures_true():
    image, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2, tilt=TILT)
    m = {d.metric: d for d in measure(image, mask).drafts}
    # A skeleton's ends are uncertain by about the object's width: the ± says so, and the truth is inside it.
    assert m["length"].value == pytest.approx(40, abs=m["length"].uncertainty) and m["length"].uncertainty >= 1.8
    assert m["length"].value == pytest.approx(40, rel=0.03) and m["length"].unit == "mm"
    assert m["length"].method_version == "skeleton_length/1"
    assert m["area"].value == pytest.approx(80, rel=0.03) and m["area"].unit == "mm2"
    assert m["height"].value > 0 and m["pieces"].value == 1 and m["pieces"].uncertainty == 0
    assert all(d.t == 0.0 and d.frame_id == "frm_1" and d.vessel_id == "ves_A" for d in m.values())


def test_empty_masks_store_zeros_for_size_and_nothing_for_colour():
    image, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)
    out = measure(image, mask, masks={})
    values = {d.metric: d.value for d in out.drafts}
    assert values == {"length": 0.0, "area": 0.0, "height": 0.0, "pieces": 0.0} and out.lab == {}


def test_lab_mean_gives_three_readings_with_their_spread():
    image, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=4, colour=(40, 140, 50))
    m = {d.metric: d for d in measure(image, mask, families=frozenset({"colour"})).drafts}
    expected = rgb2lab(np.array([[[50, 140, 40]]], np.float64) / 255.0)[0, 0]
    assert set(m) == {"colour_l", "colour_a", "colour_b"}
    assert [m["colour_l"].unit, m["colour_a"].unit, m["colour_b"].unit] == ["L*", "a*", "b*"]
    assert m["colour_a"].value == pytest.approx(expected[1], abs=1.0) and m["colour_a"].uncertainty < 1.0


def test_delta_e_waits_for_a_baseline_then_measures_change():
    green, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=4, colour=(40, 140, 50))
    first = measure(green, mask, families=frozenset({"colour"}))
    assert "change" not in {d.metric for d in first.drafts} and isinstance(first.lab["change"], ColourBaseline)
    blue, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=4, colour=(160, 60, 40))
    second = measure(blue, mask, baselines=first.lab, families=frozenset({"colour"}))
    change = next(d for d in second.drafts if d.metric == "change")
    lab_green = rgb2lab(np.array([[[50, 140, 40]]], np.float64) / 255.0)[0, 0]
    lab_blue = rgb2lab(np.array([[[40, 60, 160]]], np.float64) / 255.0)[0, 0]
    assert change.value == pytest.approx(float(deltaE_ciede2000(lab_green, lab_blue)), abs=1.0)
    assert change.unit == "dE00" and change.method_version == "delta_e/1"


def test_families_limit_what_is_measured():
    image, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)
    assert {d.metric for d in measure(image, mask, families=frozenset({"colour"})).drafts} == {
        "colour_l",
        "colour_a",
        "colour_b",
    }


def test_rule_based_methods_are_not_measured_yet():
    recipe = load_recipe(REPO_ROOT / "recipes" / "seed-germination.toml")
    image, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=40, width_mm=2)
    out = measure_vessel(
        recipe,
        vessel_around(mask),
        {"root": mask},
        image,
        calibrate(image),
        t=0.0,
        frame_id="f",
        baselines={},
        current_reference=None,
    )
    assert {d.metric for d in out.drafts} == {"root_length"}


def test_lab_mean_requires_the_lab_unit():
    with pytest.raises(ValidationError, match="Lab"):
        MeasurementSpec.model_validate(
            {"id": "c", "family": "colour", "method": "lab_mean", "from": "object", "unit": "L*"}
        )
