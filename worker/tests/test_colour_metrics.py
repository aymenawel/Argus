import numpy as np
import pytest

from argus.measure.colour import colour_metrics, lab_mean


def test_colour_metrics_and_empty_mask():
    img = np.zeros((20, 20, 3), np.uint8)
    img[:, :10] = (40, 160, 220)
    m = np.zeros((20, 20), bool)
    m[:, :10] = True
    base = lab_mean(img, m)
    out = {x.metric: x for x in colour_metrics(img, m, base)}
    assert out["delta_e"].value == pytest.approx(0.0, abs=1e-6) and out["lab_l"].unit == "L*"
    assert colour_metrics(img, np.zeros_like(m), base) == [] and lab_mean(img, np.zeros_like(m)) is None


def test_no_baseline_yet_gives_colour_without_delta_e():
    # Nothing was segmented in the first frame, so there is no baseline colour to compare with.
    img = np.full((10, 10, 3), (40, 160, 220), np.uint8)
    out = {x.metric for x in colour_metrics(img, np.ones((10, 10), bool), None)}
    assert out == {"lab_l", "lab_a", "lab_b"}
