import cv2
import numpy as np
import pytest

from argus.measure.geometry import area_mm2, component_count, height_mm, skeleton_length_mm


def line_mask(kind: str, thickness: int) -> np.ndarray:
    canvas = np.zeros((200, 200), np.uint8)
    segments = {
        "horizontal": [((50, 100), (149, 100))],
        "diagonal": [((50, 50), (149, 149))],
        "l_shape": [((40, 150), (139, 150)), ((40, 150), (40, 91))],
    }[kind]
    for start, end in segments:
        cv2.line(canvas, start, end, 1, thickness)
    return canvas.astype(bool)


def blobs(circles: list[tuple[int, int, int]]) -> np.ndarray:
    canvas = np.zeros((160, 160), np.uint8)
    for x, y, r in circles:
        cv2.circle(canvas, (x, y), r, 1, -1)
    return canvas.astype(bool)


def test_area_of_a_rectangle():
    m = np.zeros((100, 100), bool)
    m[10:30, 10:50] = True
    assert area_mm2(m, 0.25).value == pytest.approx(50.0)


def test_height_from_the_base():
    m = np.zeros((200, 50), bool)
    m[120:180, 10:40] = True
    assert height_mm(m, 0.5, base_y_px=180).value == pytest.approx(30.0)


@pytest.mark.parametrize(
    "draw,expected_px", [("horizontal", 99.0), ("diagonal", 99 * np.sqrt(2)), ("l_shape", 99.0 + 59.0)]
)
def test_skeleton_length(draw, expected_px):
    assert skeleton_length_mm(line_mask(draw, thickness=5), 0.25).value == pytest.approx(expected_px * 0.25, rel=0.03)


def test_count_ignores_specks():
    m = blobs([(20, 20, 6), (60, 60, 6), (100, 30, 6)])
    m[5, 5] = True
    assert component_count(m, 0.25, min_area_mm2=1.0).value == 3


def test_empty_mask_gives_zeros_not_errors():
    e = np.zeros((40, 40), bool)
    values = [
        area_mm2(e, 0.25),
        height_mm(e, 0.25, base_y_px=39),
        skeleton_length_mm(e, 0.25),
        component_count(e, 0.25, min_area_mm2=1.0),
    ]
    assert [v.value for v in values] == [0.0, 0.0, 0.0, 0.0]
