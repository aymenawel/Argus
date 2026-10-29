"""The frame-quality gate, before the watcher (KB 03, KB 09): blurred, glaring and blocked frames are
logged, not measured. A hand or tool in the scene marks a likely intervention: across the scene it blocks the
frame; in the ring just around one vessel (a hand reaching for it, an arm in front of it) it blocks that vessel
only, since a hand seen through the glass would otherwise be measured as the experiment. A lamp change is not a
hand: frames are compared after matching brightness, and a change that then holds still (a box set down on the
bench) becomes the new reference instead of blocking the rest of the run."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import cv2
import numpy as np

from argus.domain import Vessel
from argus.rois import roi_box, roi_mask

SATURATED_LEVEL = 250
CHANGED_GREY = 40  # grey levels a pixel must move by to count as changed (after matching brightness)
REBASELINED = "the scene outside the vessels changed and held still: new reference"
GAIN_MIN_GREY = 16  # pixels darker than this are too noisy to estimate a lamp's gain from
RING_PX = 25  # width of the ring around a vessel watched for hands (full-size pixels)


@dataclass(frozen=True)
class QualityThresholds:
    blur_min: float = 60.0  # variance of the Laplacian around the vessels below this is blurred
    saturated_max: float = 0.05  # share of a vessel's ROI pixels at the top of the range
    occlusion_change_min: float = 0.25  # share of the scene outside the vessels that changed at once
    vessel_occlusion_min: float = 0.05  # share of the ring around a vessel that changed (still scenes read 0.00)
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
        """Glare and a hand by one vessel flag that vessel; blur and occlusion make the frame unusable."""
        return "blurred" not in self.flags and "occluded" not in self.flags

    @property
    def occluded_vessels(self) -> set[str]:
        return {f.split(":", 1)[1] for f in self.flags if f.startswith("occluded:")}


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

    # Sharpness where it matters: around the vessels. A plain wall, a good background, has no edges to measure, so
    # over the whole frame it pulls a sharp picture under the threshold.
    region = grey
    if vessels:
        boxes = [roi_box(vessel, height, width) for vessel in vessels]
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        if x1 - x0 >= 3 and y1 - y0 >= 3:
            region = grey[y0:y1, x0:x1]
    blur = float(cv2.Laplacian(region, cv2.CV_64F).var())
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
        changed, outside = _changed(grey, cv2.cvtColor(previous_good, cv2.COLOR_BGR2GRAY), inside)
        outside_change = _share(changed, outside)
        if outside_change > thresholds.occlusion_change_min:
            flags.append("occluded")
        else:
            for vessel in vessels:
                if _share(changed, _ring(vessel, inside, changed.shape)) > thresholds.vessel_occlusion_min:
                    flags.append(f"occluded:{vessel.id}")

    return QualityReport(blur=blur, saturated=saturated, outside_change=outside_change, flags=tuple(flags))


def _changed(grey: np.ndarray, before_grey: np.ndarray, inside: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Which pixels changed, and which lie outside the vessels, at half size. The lamp's gain is the median
    ratio between the frames outside the vessels, robust to a hand covering less than half of the scene."""
    height, width = grey.shape
    half = (width // 2, height // 2)
    now = cv2.resize(grey, half, interpolation=cv2.INTER_AREA).astype(np.float32)
    before = cv2.resize(before_grey, half, interpolation=cv2.INTER_AREA).astype(np.float32)
    outside = ~cv2.resize(inside.astype(np.uint8), half, interpolation=cv2.INTER_NEAREST).astype(bool)
    lit = outside & (before >= GAIN_MIN_GREY)
    gain = float(np.median(now[lit] / before[lit])) if lit.any() else 1.0
    return np.abs(now - gain * before) > CHANGED_GREY, outside


def _ring(vessel: Vessel, inside: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """The band just around a vessel, outside every vessel, at the size of `shape`."""
    height, width = inside.shape
    grown = cv2.dilate(roi_mask(vessel, height, width).astype(np.uint8), np.ones((2 * RING_PX + 1,) * 2, np.uint8))
    ring = (grown > 0) & ~inside
    return cv2.resize(ring.astype(np.uint8), shape[::-1], interpolation=cv2.INTER_NEAREST).astype(bool)


def _share(changed: np.ndarray, region: np.ndarray) -> float:
    pixels = int(region.sum())
    return float((changed & region).sum()) / pixels if pixels else 0.0


class QualityGate:
    """The gate's memory across frames: the last clean frame (nothing blocked, not even one vessel) is the
    reference a hand is noticed against. When a sharp frame differs from it but the change then holds still for
    `settle_s`, that scene becomes the reference and the frame passes with a 'rebaselined' flag (the caller logs
    it)."""

    def __init__(self, vessels: Sequence[Vessel], thresholds: QualityThresholds = DEFAULT_THRESHOLDS) -> None:
        self.vessels, self.thresholds = list(vessels), thresholds
        self._good: np.ndarray | None = None
        self._still: tuple[float, np.ndarray] | None = None  # since when the changed scene held still, and its look

    def check(self, t: float, image_bgr: np.ndarray) -> QualityReport:
        report = assess(image_bgr, self.vessels, previous_good=self._good, thresholds=self.thresholds)
        if "blurred" in report.flags:
            return report
        if report.ok and not report.occluded_vessels:
            self._good, self._still = image_bgr, None
            return report
        if self._still is not None:
            since, look = self._still
            steady = assess(image_bgr, self.vessels, previous_good=look, thresholds=self.thresholds)
            if steady.ok and not steady.occluded_vessels:
                if t - since < self.thresholds.settle_s:
                    return report
                self._good, self._still = image_bgr, None
                kept = (f for f in report.flags if f != "occluded" and not f.startswith("occluded:"))
                return replace(report, flags=(*kept, "rebaselined"))
        self._still = (t, image_bgr)
        return report
