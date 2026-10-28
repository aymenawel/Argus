import numpy as np
import pytest

from argus.calibration.card import STANDARD
from argus.calibration.run import RulerInput, calibrate, card_moved
from argus.domain import CameraProperty
from tests.helpers import scene

BLANK = np.full((600, 800, 3), 255, np.uint8)


def test_calibrate_prefers_the_card_and_applies_the_print_check():
    cal = calibrate(scene(STANDARD, 5.0 * 0.98), print_check_mm=98.0)
    assert cal.card_name == "standard" and cal.mm_per_px == pytest.approx(0.2, rel=0.01)
    assert cal.reference is not None and cal.rel_uncertainty < 0.01


def test_no_card_and_no_ruler_means_no_millimetres():
    assert calibrate(BLANK) is None


def test_ruler_fallback():
    cal = calibrate(BLANK, ruler=RulerInput(p1=(0, 0), p2=(400, 0), distance_mm=100))
    assert cal.card_name == "ruler" and cal.mm_per_px == 0.25 and cal.detection is None


def test_card_moved():
    still = scene(STANDARD, 5.0)
    cal = calibrate(still)
    assert card_moved(cal, still) is False
    assert card_moved(cal, np.roll(still, 8, axis=1)) is True
    assert card_moved(cal, np.full((1200, 1600, 3), 255, np.uint8)) is None


def test_a_calibration_becomes_a_storable_draft():
    draft = calibrate(scene(STANDARD, 5.0)).to_draft(t=0.0, camera_properties={"exposure": CameraProperty.UNKNOWN})
    assert draft.card == "standard" and len(draft.homography) == 3 and draft.mm_per_px == pytest.approx(0.2, rel=0.01)
    assert set(draft.colour_reference) >= {"patches"}


def test_a_card_cut_off_by_the_frame_edge_gives_no_nan_colours():
    cal = calibrate(scene(STANDARD, 5.0)[:340])  # top 38 mm of the card: the neutral row is in, the colour row cut off
    assert cal is not None and cal.reference is not None and len(cal.reference.neutrals()) == 6
    assert all(np.isfinite(p.lab).all() for p in cal.reference.patches)
