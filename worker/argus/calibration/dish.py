"""The dish as the ruler (D-72): with no Argus Card in view, the rim of a dish whose diameter is published (or
known to the researcher) sets millimetres per pixel. Each vessel region should hold one dish; its outer rim is the
largest circle centred in the region, refined by an ellipse fit. A dish's real size is only known to a few percent,
and a top-down view may find the inner or the outer edge of its wall, so the uncertainty never drops below the two
together (about 5 %).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

NOMINAL_ALLOWANCE = 0.03  # a dish sold as one size differs from it by up to about 3 %
EDGE_ALLOWANCE = 0.04  # the inner and outer edges of a dish's wall, seen from above, are 4-5 % apart (Genze dishes)
MIN_AXIS_RATIO = 0.9  # a rim flatter than this is seen at a slant: its pixels aren't one scale
AGREEMENT = 0.15  # dishes whose scales differ from the median by more than this aren't the same dish size
RIM_BAND = 0.04  # edge points within this fraction of the circle's radius belong to the rim
CENTRED = 0.15  # the rim's centre lies within this fraction of the region's size from its middle


@dataclass(frozen=True)
class DishScale:
    mm_per_px: float
    rel_uncertainty: float
    dishes: list[tuple[float, float, float, float]]  # each dish's centre x, y, major and minor axis (frame px)


def _box(roi: Sequence[tuple[float, float]], shape: tuple[int, int]) -> tuple[int, int, int, int]:
    xs, ys = [p[0] for p in roi], [p[1] for p in roi]
    height, width = shape
    x0, y0 = max(0, math.floor(min(xs))), max(0, math.floor(min(ys)))
    x1, y1 = min(width, math.ceil(max(xs))), min(height, math.ceil(max(ys)))
    return x0, y0, x1, y1


def _rim(gray: np.ndarray) -> tuple[float, float, float, float] | None:
    """The dish's outer rim in one region: centre x, y and the ellipse's major and minor axes, in region px."""
    height, width = gray.shape
    size = min(height, width)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT_ALT,
        dp=1.5,
        minDist=size / 8,
        param1=100,
        param2=0.3,
        minRadius=int(0.25 * size),
        maxRadius=int(0.55 * max(height, width)),
    )
    if circles is None:
        return None
    centred = [c for c in circles[0] if math.hypot(c[0] - width / 2, c[1] - height / 2) <= CENTRED * size]
    if not centred:
        return None
    cx, cy, r = (float(v) for v in max(centred, key=lambda c: c[2]))  # the outer rim, not the paper inside it
    ys, xs = np.nonzero(cv2.Canny(blurred, 50, 150))
    # Hough's centre can be off by a few percent of the radius: fit in a wide band first, then in a tight one
    # around that fit.
    major = minor = 0.0
    for band in (2 * RIM_BAND, RIM_BAND):
        near = np.abs(np.hypot(xs - cx, ys - cy) - r) <= band * r
        if np.count_nonzero(near) < 50:
            return None
        (cx, cy), axes, _ = cv2.fitEllipse(np.column_stack([xs[near], ys[near]]).astype(np.float32))
        major, minor = float(max(axes)), float(min(axes))
        r = (major + minor) / 4
    return float(cx), float(cy), major, minor


def dish_scale(
    image_bgr: np.ndarray, rois: Sequence[Sequence[tuple[float, float]]], diameter_mm: float
) -> DishScale | None:
    """Millimetres per pixel from the dishes' rims, or None when it can't be trusted (dish_scale_or_reason says
    why)."""
    result = dish_scale_or_reason(image_bgr, rois, diameter_mm)
    return result if isinstance(result, DishScale) else None


def dish_scale_or_reason(
    image_bgr: np.ndarray, rois: Sequence[Sequence[tuple[float, float]]], diameter_mm: float
) -> DishScale | str:
    """The scale, or why there is none: a dish in no more than half the regions, a rim seen at a slant, or dishes
    whose sizes disagree."""
    if not rois or diameter_mm <= 0:
        return "no vessel regions or no dish diameter to measure against"
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    dishes: list[tuple[int, tuple[float, float, float, float]]] = []  # region number, rim
    for number, roi in enumerate(rois, start=1):
        x0, y0, x1, y1 = _box(roi, gray.shape[:2])
        if x1 - x0 < 32 or y1 - y0 < 32:
            continue
        rim = _rim(gray[y0:y1, x0:x1])
        if rim is not None:
            cx, cy, major, minor = rim
            dishes.append((number, (cx + x0, cy + y0, major, minor)))
    if 2 * len(dishes) <= len(rois):
        return f"a dish rim was found in only {len(dishes)} of {len(rois)} regions"
    slanted = next(((n, minor / major) for n, (_, _, major, minor) in dishes if minor / major < MIN_AXIS_RATIO), None)
    if slanted is not None:
        return f"region {slanted[0]} is seen at a slant (rim axis ratio {slanted[1]:.2f}, under {MIN_AXIS_RATIO})"
    scales = [diameter_mm / major for _, (_, _, major, _) in dishes]
    middle = statistics.median(scales)
    if any(abs(s - middle) / middle > AGREEMENT for s in scales):
        low, high = 1 / max(scales), 1 / min(scales)
        return f"the dishes disagree on the scale ({low:.1f} to {high:.1f} px/mm): they may not be the same size"
    spread = statistics.stdev(scales) / middle if len(scales) > 1 else 0.0
    rims = [rim for _, rim in dishes]
    return DishScale(middle, math.hypot(spread, NOMINAL_ALLOWANCE, EDGE_ALLOWANCE), rims)
