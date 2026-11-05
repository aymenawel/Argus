"""Microscope mode (D-103): a USB microscope is a camera; a stage micrometer gives the scale through the two-click
ruler; cells are counted and their area reported in µm², so things far below a square millimetre still count."""

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from argus.calibration.run import calibrate
from argus.config import REPO_ROOT
from argus.domain import Role, RulerInput, Vessel
from argus.measure.engine import measure_vessel
from argus.recipes.loader import load_recipe
from argus.recipes.model import MeasurementSpec

MICROSCOPE = load_recipe(REPO_ROOT / "recipes" / "microscope.toml")


def three_cells() -> tuple[np.ndarray, np.ndarray]:
    """A grey field with three round cells, 10 px in radius."""
    image = np.full((240, 320, 3), 200, np.uint8)
    mask = np.zeros((240, 320), np.uint8)
    for x in (80, 160, 240):
        cv2.circle(mask, (x, 120), 10, 1, -1)
    image[mask > 0] = 90
    return image, mask.astype(bool)


def field_vessel() -> Vessel:
    roi = [(0.0, 0.0), (319.0, 0.0), (319.0, 239.0), (0.0, 239.0)]
    return Vessel(id="ves_F", run_id="run_1", label="Field", role=Role.TREATMENT, roi=roi)


def measure(recipe, image, mask):
    # A stage micrometer: two marks 0.1 mm apart are 200 px apart, so 0.5 µm a pixel.
    cal = calibrate(image, ruler=RulerInput(p1=(20.0, 20.0), p2=(220.0, 20.0), distance_mm=0.1))
    out = measure_vessel(
        recipe,
        field_vessel(),
        {"cell": mask},
        image,
        cal,
        t=0.0,
        frame_id="frm_1",
        baselines={},
        current_reference=None,
        families=frozenset({"size", "count"}),
    )
    return {d.metric: d for d in out.drafts}


def test_the_microscope_recipe_counts_cells_and_measures_their_area_in_square_micrometres():
    assert MICROSCOPE.id == "microscope" and MICROSCOPE.main_measurement == "cells"
    units = {m.id: m.unit for m in MICROSCOPE.measurements}
    assert units == {"cells": "count", "cell_area": "um2"}
    assert MICROSCOPE.min_count_area_mm2 < 1e-5  # a cell is a few square micrometres


def test_cells_far_below_a_square_millimetre_are_counted_and_sized_in_micrometres():
    image, mask = three_cells()
    m = measure(MICROSCOPE, image, mask)
    assert m["cells"].value == 3 and m["cells"].unit == "count"
    expected_um2 = np.count_nonzero(mask) * 0.5**2  # 0.5 µm a pixel
    assert m["cell_area"].unit == "um2"
    assert m["cell_area"].value == pytest.approx(expected_um2, rel=0.01)
    assert 0 < m["cell_area"].uncertainty < m["cell_area"].value


def test_other_recipes_keep_their_one_square_millimetre_count_filter():
    image, mask = three_cells()
    plain = MICROSCOPE.model_copy(update={"min_count_area_mm2": 1.0})
    assert measure(plain, image, mask)["cells"].value == 0  # specks under 1 mm² never counted before


def test_micrometre_units_belong_to_size_methods_of_the_right_dimension():
    MeasurementSpec(id="a", family="size", method="area", source="cell", unit="um2")
    MeasurementSpec(id="h", family="size", method="height", source="cell", unit="um")
    with pytest.raises(ValidationError):
        MeasurementSpec(id="a", family="size", method="area", source="cell", unit="um")
    with pytest.raises(ValidationError):
        MeasurementSpec(id="h", family="size", method="height", source="cell", unit="um2")
    with pytest.raises(ValidationError):
        MeasurementSpec(id="n", family="count", method="component_count", source="cell", unit="um2")
