"""The frame-quality gate, before the watcher (KB 03, KB 09): blurred, glaring and blocked frames are
logged, not measured. A hand or tool in the scene marks a likely intervention."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from argus.domain import Vessel
from argus.rois import roi_mask

SATURATED_LEVEL = 250
CHANGED_GREY = 40  # grey levels a pixel must move by to count as changed


@dataclass(frozen=True)
class QualityThresholds:
    blur_min: float = 60.0  # variance of the Laplacian below this is blurred
    saturated_max: float = 0.05  # share of a vessel's ROI pixels at the top of the range
    occlusion_change_min: float = 0.25  # share of the scene outside the vessels that changed at once


DEFAULT_THRESHOLDS = QualityThresholds()


@dataclass(frozen=True)
class QualityReport:
    blur: float
    saturated: dict[str, float]
    outside_change: float | None
    flags: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Glare only flags its vessel; blur and occlusion make the frame unusable."""
        return "blurred" not in self.flags and "occluded" not in self.flags


def assess(
    image_bgr: np.ndarray,
    vessels: Sequence[Vessel],
    *,
    previous_good: np.ndarray | None,
    thresholds: QualityThresholds = DEFAULT_THRESHOLDS,
) -> QualityReport:
    height, width = image_bgr.shape[:2]
    grey = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    flags: list[str] = []

    blur = float(cv2.Laplacian(grey, cv2.CV_64F).var())
    if blur < thresholds.blur_min:
        flags.append("blurred")

    saturated: dict[str, float] = {}
    hot = (image_bgr >= SATURATED_LEVEL).any(axis=2)
    inside = np.zeros((height, width), bool)
    for vessel in vessels:
        roi = roi_mask(vessel, height, width)
        inside |= roi
        pixels = int(roi.sum())
        saturated[vessel.id] = float((hot & roi).sum()) / pixels if pixels else 0.0
        if saturated[vessel.id] > thresholds.saturated_max:
            flags.append(f"saturated:{vessel.id}")

    outside_change = None
    if previous_good is not None and previous_good.shape == image_bgr.shape:
        half = (width // 2, height // 2)
        now = cv2.resize(grey, half, interpolation=cv2.INTER_AREA).astype(np.int16)
        before = cv2.resize(cv2.cvtColor(previous_good, cv2.COLOR_BGR2GRAY), half, interpolation=cv2.INTER_AREA)
        outside = ~cv2.resize(inside.astype(np.uint8), half, interpolation=cv2.INTER_NEAREST).astype(bool)
        changed = np.abs(now - before.astype(np.int16)) > CHANGED_GREY
        outside_pixels = int(outside.sum())
        outside_change = float((changed & outside).sum()) / outside_pixels if outside_pixels else 0.0
        if outside_change > thresholds.occlusion_change_min:
            flags.append("occluded")

    return QualityReport(blur=blur, saturated=saturated, outside_change=outside_change, flags=tuple(flags))
