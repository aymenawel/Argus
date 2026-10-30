"""The dish as the ruler (D-72): with no card in view, the rim of a dish of known diameter sets millimetres per
pixel, with the uncertainty a dish's real size allows."""

import math

import cv2
import numpy as np
import pytest

from argus.calibration.dish import NOMINAL_ALLOWANCE, dish_scale
from argus.calibration.run import calibrate

TILE = 640
DIAMETER_PX = 600


def rim_points(cx: float, cy: float, rx: float, ry: float, rng: np.random.Generator) -> np.ndarray:
    angles = np.linspace(0, 2 * math.pi, 720, endpoint=False)
    jitter = rng.uniform(-2, 2, angles.size)  # a real rim is not a perfect circle
    xs = cx + (rx + jitter) * np.cos(angles)
    ys = cy + (ry + jitter) * np.sin(angles)
    return np.round(np.column_stack([xs, ys])).astype(np.int32)


def plate(*, tilted: int | None = None, blank: tuple[int, ...] = ()) -> tuple[np.ndarray, list]:
    """Six tiles in two rows, a light rim of 600 px in each on a dark background (tile `tilted` foreshortened to an
    axis ratio of 0.8)."""
    rng = np.random.default_rng(1)
    image = np.full((2 * TILE, 3 * TILE, 3), 30, np.uint8)
    rois = []
    for i in range(6):
        x0, y0 = (i % 3) * TILE, (i // 3) * TILE
        rois.append([(x0, y0), (x0 + TILE, y0), (x0 + TILE, y0 + TILE), (x0, y0 + TILE)])
        if i in blank:
            continue
        r = DIAMETER_PX / 2
        ry = r * 0.8 if i == tilted else r
        points = rim_points(x0 + TILE / 2, y0 + TILE / 2, r, ry, rng)
        cv2.polylines(image, [points], isClosed=True, color=(210, 210, 210), thickness=3)
    return image, rois


def test_six_rims_give_the_scale_within_one_percent():
    image, rois = plate()
    scale = dish_scale(image, rois, 85.0)
    assert scale is not None and len(scale.dishes) == 6
    assert scale.mm_per_px == pytest.approx(85 / DIAMETER_PX, rel=0.01)
    assert scale.rel_uncertainty >= NOMINAL_ALLOWANCE  # a dish's real size is known to a few percent at best


def test_a_rim_seen_at_a_slant_is_refused():
    image, rois = plate(tilted=2)
    assert dish_scale(image, rois, 85.0) is None


def test_too_few_dishes_found_is_refused():
    image, rois = plate(blank=(0, 2, 4))
    assert dish_scale(image, rois, 85.0) is None


def test_dishes_of_different_sizes_disagree_and_are_refused():
    image, rois = plate()
    x0, y0 = TILE, 0
    image[y0 : y0 + TILE, x0 : x0 + TILE] = 30
    cv2.circle(image, (x0 + TILE // 2, y0 + TILE // 2), 220, (210, 210, 210), 3)  # a 440 px dish among 600 px ones
    assert dish_scale(image, rois, 85.0) is None


def test_calibrate_uses_the_dish_when_there_is_no_card_or_ruler():
    image, rois = plate()
    cal = calibrate(image, dish_diameter_mm=85.0, rois=rois)
    assert cal is not None and cal.card_name == "dish"
    draft = cal.to_draft(0.0, {})
    assert draft.card == "dish" and draft.mm_per_px == pytest.approx(85 / DIAMETER_PX, rel=0.01)
    assert calibrate(image, rois=rois) is None  # no diameter, no millimetres
