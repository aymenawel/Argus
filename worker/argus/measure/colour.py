"""Colour inside a mask: mean CIELAB and the CIEDE2000 difference from a baseline."""

from __future__ import annotations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from argus.measure.geometry import MetricValue


def lab_mean(image_bgr: np.ndarray, mask: np.ndarray) -> tuple[float, float, float] | None:
    """Mean L*, a*, b* of the masked pixels, or None when the mask is empty."""
    pixels = image_bgr[np.asarray(mask, bool)]
    if pixels.size == 0:
        return None
    lab = rgb2lab(pixels[:, ::-1].astype(np.float64).reshape(-1, 1, 3) / 255.0).reshape(-1, 3).mean(axis=0)
    return float(lab[0]), float(lab[1]), float(lab[2])


def delta_e(lab1, lab2) -> float:
    return float(deltaE_ciede2000(np.asarray(lab1, np.float64), np.asarray(lab2, np.float64)))


def colour_metrics(image_bgr: np.ndarray, mask: np.ndarray, baseline_lab) -> list[MetricValue]:
    lab = lab_mean(image_bgr, mask)
    if lab is None:
        return []
    return [
        MetricValue("lab_l", lab[0], "L*", "lab_mean/1"),
        MetricValue("lab_a", lab[1], "a*", "lab_mean/1"),
        MetricValue("lab_b", lab[2], "b*", "lab_mean/1"),
        MetricValue("delta_e", delta_e(lab, baseline_lab), "dE00", "delta_e/1"),
    ]
