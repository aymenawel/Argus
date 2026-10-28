"""Size measurements from boolean masks rectified to the card plane (Rectified.px_per_mm)."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from skimage.morphology import skeletonize


@dataclass(frozen=True)
class MetricValue:
    metric: str
    value: float
    unit: str
    method_version: str


def area_mm2(mask: np.ndarray, mm_per_px: float) -> MetricValue:
    return MetricValue("area", float(np.count_nonzero(mask)) * mm_per_px**2, "mm2", "area/1")


def height_mm(mask: np.ndarray, mm_per_px: float, *, base_y_px: float) -> MetricValue:
    """Height of the mask's top edge above the vessel base (image y grows downward)."""
    rows = np.flatnonzero(np.asarray(mask).any(axis=1))
    height_px = max(0.0, base_y_px - rows[0]) if rows.size else 0.0
    return MetricValue("height", float(height_px) * mm_per_px, "mm", "height/1")


def skeleton_length_mm(mask: np.ndarray, mm_per_px: float) -> MetricValue:
    """Centre-line length: 1 per straight neighbour pair, √2 per diagonal pair not already joined by a corner."""
    skel = skeletonize(np.asarray(mask, bool))
    straight = np.count_nonzero(skel[:, :-1] & skel[:, 1:]) + np.count_nonzero(skel[:-1, :] & skel[1:, :])
    down_right = skel[:-1, :-1] & skel[1:, 1:] & ~(skel[:-1, 1:] | skel[1:, :-1])
    down_left = skel[:-1, 1:] & skel[1:, :-1] & ~(skel[:-1, :-1] | skel[1:, 1:])
    length_px = straight + math.sqrt(2) * (np.count_nonzero(down_right) + np.count_nonzero(down_left))
    return MetricValue("skeleton_length", float(length_px) * mm_per_px, "mm", "skeleton_length/1")


def component_count(mask: np.ndarray, mm_per_px: float, *, min_area_mm2: float) -> MetricValue:
    """8-connected objects at or above the size filter."""
    count, _, stats, _ = cv2.connectedComponentsWithStats(np.asarray(mask, np.uint8), connectivity=8)
    areas_mm2 = stats[1:count, cv2.CC_STAT_AREA] * mm_per_px**2
    return MetricValue(
        "component_count", float(np.count_nonzero(areas_mm2 >= min_area_mm2)), "count", "component_count/1"
    )
