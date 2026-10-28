import cv2
import numpy as np

from argus.capture.quality import QualityThresholds, assess
from argus.domain import Role, Vessel

A = Vessel(
    id="ves_A", run_id="run_1", label="A", role=Role.TREATMENT, roi=[(100, 100), (250, 100), (250, 400), (100, 400)]
)
B = Vessel(
    id="ves_B", run_id="run_1", label="B", role=Role.TREATMENT, roi=[(400, 100), (550, 100), (550, 400), (400, 400)]
)
VESSELS = [A, B]


def frame() -> np.ndarray:
    """A sharp, textured 800x600 scene: a checkerboard of mid greys (nothing saturated)."""
    y, x = np.mgrid[0:600, 0:800]
    grey = np.where(((x // 20) + (y // 20)) % 2 == 0, 80, 180).astype(np.uint8)
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)


def test_a_sharp_frame_passes():
    report = assess(frame(), VESSELS, previous_good=frame())
    assert report.ok and report.flags == () and report.outside_change == 0.0


def test_blur_is_flagged():
    report = assess(cv2.GaussianBlur(frame(), (31, 31), 10), VESSELS, previous_good=None)
    assert "blurred" in report.flags and not report.ok and report.outside_change is None


def test_glare_in_one_vessel_is_flagged_for_that_vessel():
    glare = frame()
    glare[100:401, 400:551] = 255
    report = assess(glare, VESSELS, previous_good=frame())
    assert report.flags == ("saturated:ves_B",) and report.ok
    assert report.saturated["ves_B"] > 0.9 and report.saturated["ves_A"] == 0.0


def test_a_hand_outside_the_vessels_is_an_occlusion():
    hand = frame()
    hand[:, 560:] = 20  # a dark arm over the right side, outside both vessels
    report = assess(hand, VESSELS, previous_good=frame())
    assert "occluded" in report.flags and not report.ok and report.outside_change > 0.25


def test_thresholds_are_adjustable():
    blurred = cv2.GaussianBlur(frame(), (31, 31), 10)
    assert assess(blurred, VESSELS, previous_good=None, thresholds=QualityThresholds(blur_min=0.0)).ok
