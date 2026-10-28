"""Masks become simplified vector outlines for the UI and the evidence record (D-43)."""

from __future__ import annotations

import cv2
import numpy as np

from argus.segment.types import MaskPatch


def outline_polygons(
    patch: MaskPatch, *, epsilon_px: float = 1.0, min_area_px: float = 4.0
) -> list[list[tuple[float, float]]]:
    """External contours of the mask in media pixels, simplified with Douglas-Peucker; specks are dropped."""
    if not patch.mask.any():
        return []
    contours, _ = cv2.findContours(patch.mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polygons = []
    for contour in contours:
        if cv2.contourArea(contour) < min_area_px:
            continue
        points = cv2.approxPolyDP(contour, epsilon_px, True).reshape(-1, 2)
        if len(points) >= 3:
            polygons.append([(float(x + patch.left), float(y + patch.top)) for x, y in points])
    return polygons
