"""A vessel's region of interest as a pixel mask, shared by the quality gate, tracking and the watcher."""

from __future__ import annotations

import cv2
import numpy as np

from argus.domain import Vessel


def roi_mask(vessel: Vessel, height: int, width: int) -> np.ndarray:
    canvas = np.zeros((height, width), np.uint8)
    cv2.fillPoly(canvas, [np.round(np.asarray(vessel.roi, np.float64)).astype(np.int32)], 1)
    return canvas.astype(bool)


def roi_box(vessel: Vessel, height: int, width: int, *, margin: int = 0) -> tuple[int, int, int, int]:
    """The ROI's bounding box (x0, y0, x1, y1), widened by a margin and clipped to the frame."""
    points = np.asarray(vessel.roi, np.float64)
    x0, y0 = np.floor(points.min(axis=0)).astype(int) - margin
    x1, y1 = np.ceil(points.max(axis=0)).astype(int) + margin
    return max(int(x0), 0), max(int(y0), 0), min(int(x1), width), min(int(y1), height)
