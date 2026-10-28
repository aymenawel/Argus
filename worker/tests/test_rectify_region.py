import pytest

from argus.calibration.card import STANDARD
from argus.calibration.detect import detect_card, rectify
from tests.helpers import (
    TILT,
    bbox_of_dark_square_in_image,
    bounding_box_of_dark_square,
    scene,
    scene_with_square_on_card_plane,
)


def test_a_region_on_a_tilted_frame_stays_small_and_square():
    img = scene_with_square_on_card_plane(STANDARD, side_mm=30.0, tilt=TILT)
    rect = rectify(img, detect_card(img), region_px=bbox_of_dark_square_in_image(img), px_per_mm=10.0)
    assert max(rect.image.shape[:2]) < 800
    w, h = bounding_box_of_dark_square(rect.image)
    assert w == pytest.approx(300, abs=4) and h == pytest.approx(300, abs=4)


def test_output_is_capped_by_lowering_the_scale():
    img = scene(STANDARD, 5.0, tilt=TILT)
    rect = rectify(img, detect_card(img), px_per_mm=40.0, max_side_px=2000)
    assert max(rect.image.shape[:2]) <= 2000 and rect.px_per_mm < 40.0
