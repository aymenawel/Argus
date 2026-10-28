import cv2
import numpy as np
import pytest

from argus.capture.quality import QualityGate, QualityThresholds, assess
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


@pytest.mark.parametrize("gain", [1.3, 0.7, 0.5])
def test_a_lamp_change_is_not_an_occlusion(gain):
    lamp = np.clip(frame().astype(np.float32) * gain, 0, 255).astype(np.uint8)
    report = assess(lamp, VESSELS, previous_good=frame())
    assert "occluded" not in report.flags and report.outside_change < 0.05


def box_on_the_bench() -> np.ndarray:
    moved = frame()
    moved[450:, :] = 30  # a box set down below both vessels, a third of the scene outside them
    return moved


def test_a_lasting_scene_change_becomes_the_new_reference():
    gate = QualityGate(VESSELS, QualityThresholds(settle_s=10.0))
    assert gate.check(0.0, frame()).ok
    assert not gate.check(1.0, box_on_the_bench()).ok  # at first it looks like a hand
    assert not gate.check(6.0, box_on_the_bench()).ok
    settled = gate.check(11.0, box_on_the_bench())
    assert settled.ok and "rebaselined" in settled.flags
    assert gate.check(12.0, box_on_the_bench()).flags == ()


def test_a_moving_hand_never_becomes_the_reference():
    gate = QualityGate(VESSELS, QualityThresholds(settle_s=10.0))
    gate.check(0.0, frame())
    right, low = frame(), box_on_the_bench()
    right[:, 560:] = 20
    for t in range(1, 40):
        assert not gate.check(float(t), right if t % 2 else low).ok
    assert gate.check(40.0, frame()).flags == ()  # the hand left: the old scene is still the reference
