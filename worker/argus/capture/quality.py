"""The frame-quality gate, before the watcher (KB 03, KB 09): blurred, glaring and blocked frames are
logged, not measured. A hand or tool in the scene marks a likely intervention. A lamp change is not a hand:
the scene outside the vessels is compared after matching brightness, and a change that then holds still
(a box set down on the bench) becomes the new reference instead of blocking the rest of the run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import cv2
import numpy as np

from argus.domain import Vessel
from argus.rois import roi_mask

SATURATED_LEVEL = 250
CHANGED_GREY = 40  # grey levels a pixel must move by to count as changed (after matching brightness)
REBASELINED = "the scene outside the vessels changed and held still: new reference"
GAIN_MIN_GREY = 16  # pixels darker than this are too noisy to estimate a lamp's gain from


@dataclass(frozen=True)
class QualityThresholds:
    blur_min: float = 60.0  # variance of the Laplacian below this is blurred
    saturated_max: float = 0.05  # share of a vessel's ROI pixels at the top of the range
    occlusion_change_min: float = 0.25  # share of the scene outside the vessels that changed at once
    settle_s: float = 60.0  # a change outside the vessels that holds still this long is the new scene


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
        outside_change = _outside_change(grey, cv2.cvtColor(previous_good, cv2.COLOR_BGR2GRAY), inside)
        if outside_change > thresholds.occlusion_change_min:
            flags.append("occluded")

    return QualityReport(blur=blur, saturated=saturated, outside_change=outside_change, flags=tuple(flags))


def _outside_change(grey: np.ndarray, before_grey: np.ndarray, inside: np.ndarray) -> float:
    """Share of the pixels outside the vessels that changed, at half size. The lamp's gain is the median
    ratio between the frames, robust to a hand covering less than half of the scene."""
    height, width = grey.shape
    half = (width // 2, height // 2)
    now = cv2.resize(grey, half, interpolation=cv2.INTER_AREA).astype(np.float32)
    before = cv2.resize(before_grey, half, interpolation=cv2.INTER_AREA).astype(np.float32)
    outside = ~cv2.resize(inside.astype(np.uint8), half, interpolation=cv2.INTER_NEAREST).astype(bool)
    outside_pixels = int(outside.sum())
    if outside_pixels == 0:
        return 0.0
    lit = outside & (before >= GAIN_MIN_GREY)
    gain = float(np.median(now[lit] / before[lit])) if lit.any() else 1.0
    changed = np.abs(now - gain * before) > CHANGED_GREY
    return float((changed & outside).sum()) / outside_pixels


class QualityGate:
    """The gate's memory across frames: the last good frame is the reference a hand is noticed against. When a
    sharp frame differs from it but the change then holds still for `settle_s`, that scene becomes the
    reference and the frame passes with a 'rebaselined' flag (the caller logs it)."""

    def __init__(self, vessels: Sequence[Vessel], thresholds: QualityThresholds = DEFAULT_THRESHOLDS) -> None:
        self.vessels, self.thresholds = list(vessels), thresholds
        self._good: np.ndarray | None = None
        self._still: tuple[float, np.ndarray] | None = None  # since when the changed scene held still, and its look

    def check(self, t: float, image_bgr: np.ndarray) -> QualityReport:
        report = assess(image_bgr, self.vessels, previous_good=self._good, thresholds=self.thresholds)
        if report.ok:
            self._good, self._still = image_bgr, None
            return report
        if "blurred" in report.flags:
            return report
        if self._still is not None:
            since, look = self._still
            steady = assess(image_bgr, self.vessels, previous_good=look, thresholds=self.thresholds)
            if steady.outside_change is not None and steady.outside_change <= self.thresholds.occlusion_change_min:
                if t - since < self.thresholds.settle_s:
                    return report
                self._good, self._still = image_bgr, None
                return replace(report, flags=(*(f for f in report.flags if f != "occluded"), "rebaselined"))
        self._still = (t, image_bgr)
        return report
