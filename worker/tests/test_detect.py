import numpy as np
import pytest

from argus.calibration.card import COMPACT, STANDARD
from argus.calibration.detect import detect_card, rectify, ruler_scale, with_print_check
from tests.helpers import (
    TILT,
    bounding_box_of_dark_square,
    scene,
    scene_both_cards,
    scene_two_identical_cards,
    scene_with_patch_centres,
    scene_with_square_on_card_plane,
    scene_with_stray_marker,
)


def test_standard_card_scale():
    d = detect_card(scene(STANDARD, 5.0))
    assert d.spec is STANDARD and d.marker_ids == (0, 1, 2, 3) and d.mm_per_px == pytest.approx(0.2, rel=0.005)


def test_points_map_to_card_mm_under_perspective():
    img, centres_px, centres_mm = scene_with_patch_centres(STANDARD, 6.0, tilt=TILT)
    assert np.abs(detect_card(img).px_to_mm(centres_px) - centres_mm).max() < 0.2


def test_three_markers_are_enough():
    d = detect_card(scene(COMPACT, 6.0, cover_ids=(5,)))
    assert len(d.marker_ids) == 3 and d.mm_per_px == pytest.approx(1 / 6, rel=0.01)


def test_both_cards_in_frame_never_mix():
    d = detect_card(scene_both_cards(full=STANDARD, stray_compact_markers=1))
    assert d.spec is STANDARD and set(d.marker_ids) <= {0, 1, 2, 3}


def test_no_card_returns_none():
    assert detect_card(np.full((600, 800, 3), 255, np.uint8)) is None


def test_print_check_rescales_and_bounds():
    d = detect_card(scene(STANDARD, 5.0))
    c = with_print_check(d, 98.0)
    pts = c.px_to_mm(np.array([[700.0, 600.0], [800.0, 600.0]]))
    assert np.linalg.norm(pts[1] - pts[0]) == pytest.approx(20.0 * 98 / 100, rel=0.01)
    with pytest.raises(ValueError):
        with_print_check(d, 80.0)


def test_print_check_recovers_true_size_from_a_shrunken_print():
    # The printer shrank the page to 98 %, so its 100 mm line measures 98 mm with a ruler.
    d = with_print_check(detect_card(scene(STANDARD, 5.0 * 0.98)), 98.0)
    ends_px = np.array([[700.0, 600.0], [950.0, 600.0]])  # 250 px apart: 50 mm at 5 px per real mm
    assert np.linalg.norm(np.diff(d.px_to_mm(ends_px), axis=0)) == pytest.approx(50.0, rel=0.005)
    assert d.mm_per_px == pytest.approx(0.2, rel=0.005)


def test_two_prints_of_the_same_card_are_refused():
    # Every id shows up on one print or the other: no way to tell which corners belong together.
    assert detect_card(scene_two_identical_cards(STANDARD, cover_first=(3,), cover_second=(1,))) is None


def test_a_marker_out_of_place_is_left_out():
    d = detect_card(scene_with_stray_marker(STANDARD, stray_id=3, cover_ids=(3,)))
    assert d.marker_ids == (0, 1, 2) and d.mm_per_px == pytest.approx(0.2, rel=0.01)


def test_ruler_scale():
    r = ruler_scale((0, 0), (400, 0), 100.0)
    assert r.mm_per_px == 0.25 and r.rel_uncertainty == pytest.approx(np.sqrt(2) / 400)


def test_rectify_makes_a_tilted_square_square():
    img = scene_with_square_on_card_plane(STANDARD, side_mm=30.0, tilt=TILT)
    rect = rectify(img, detect_card(img), px_per_mm=10.0)
    w, h = bounding_box_of_dark_square(rect.image)
    assert w == pytest.approx(300, abs=4) and h == pytest.approx(300, abs=4)
