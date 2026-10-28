"""Recipe measurements from masks (spec §6). Each recipe measurement maps to a phase 1 metric, computed on the
vessel's region rectified to the card plane, with the ± one reading can know: the calibration's scale error
and the mask boundary. (The noise floor over a still period is a derived number, phase 4.)"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from argus.calibration.colour import ColourReference, correct_lab
from argus.calibration.detect import rectify
from argus.calibration.run import RunCalibration
from argus.domain import MeasurementDraft, Vessel
from argus.measure.geometry import MetricValue, area_mm2, component_count, height_mm, skeleton_length_mm
from argus.measure.uncertainty import combined_uncertainty
from argus.recipes.model import MeasurementSpec, Recipe
from argus.rois import roi_box, roi_mask

ALL_FAMILIES = frozenset({"size", "count", "colour"})
MIN_COUNT_AREA_MM2 = 1.0
LENGTH_BOUNDARY_PX = 2.0  # at least a pixel at each end of a skeleton
HEIGHT_BOUNDARY_PX = 1.0


@dataclass(frozen=True)
class ColourBaseline:
    """A vessel's mean colour in one frame, with the standard error of that mean (Lab units)."""

    lab: tuple[float, float, float]
    se: float


@dataclass(frozen=True)
class VesselMeasurements:
    drafts: list[MeasurementDraft]
    lab: dict[str, ColourBaseline]  # measurement id -> the colour reading used (the next ΔE baseline)


class _Region:
    """The vessel's ROI box, rectified to the card plane (card calibration) or cropped as is (ruler)."""

    def __init__(self, vessel: Vessel, image_bgr: np.ndarray, cal: RunCalibration) -> None:
        height, width = image_bgr.shape[:2]
        self.cal = cal
        self.box = roi_box(vessel, height, width)
        roi = roi_mask(vessel, height, width)
        if cal.detection is not None:
            first = rectify(roi, cal.detection, region_px=self.box, px_per_mm=1.0 / cal.mm_per_px)
            self.px_per_mm = first.px_per_mm
            roi_view = first.image
        else:
            self.px_per_mm = 1.0 / cal.mm_per_px
            roi_view = self.crop(roi)
        rows = np.flatnonzero(roi_view.any(axis=1))
        self.base_y_px = float(rows[-1]) if rows.size else float(roi_view.shape[0] - 1)

    @property
    def mm_per_px(self) -> float:
        return 1.0 / self.px_per_mm

    def crop(self, mask: np.ndarray) -> np.ndarray:
        x0, y0, x1, y1 = self.box
        return mask[y0:y1, x0:x1]

    def view(self, mask: np.ndarray) -> np.ndarray:
        if self.cal.detection is None:
            return self.crop(mask)
        return rectify(mask, self.cal.detection, region_px=self.box, px_per_mm=self.px_per_mm).image


def _perimeter_px(mask: np.ndarray) -> float:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return float(sum(cv2.arcLength(c, True) for c in contours))


def _length_boundary_px(mask: np.ndarray, length_px: float) -> float:
    """A thinning skeleton stops short of square ends and runs into round ones, so its ends are uncertain by
    about the object's width: the mean width (area / length), and never less than a pixel per end."""
    width_px = float(np.count_nonzero(mask)) / length_px if length_px > 0 else 0.0
    return max(LENGTH_BOUNDARY_PX, width_px)


def _colour(
    image_bgr: np.ndarray, mask: np.ndarray, cal: RunCalibration, current: ColourReference | None
) -> tuple[ColourBaseline, np.ndarray] | None:
    pixels = image_bgr[mask]
    if pixels.size == 0:
        return None
    lab = rgb2lab(pixels[:, ::-1].astype(np.float64).reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    mean = lab.mean(axis=0)
    se = lab.std(axis=0, ddof=1) / math.sqrt(len(lab)) if len(lab) > 1 else np.zeros(3)
    if cal.reference is not None and current is not None:
        mean = correct_lab(mean, cal.reference, current)
    reading = ColourBaseline((float(mean[0]), float(mean[1]), float(mean[2])), float(np.linalg.norm(se)))
    return reading, se


def measure_vessel(
    recipe: Recipe,
    vessel: Vessel,
    masks: Mapping[str, np.ndarray],
    image_bgr: np.ndarray,
    cal: RunCalibration,
    *,
    t: float,
    frame_id: str | None,
    baselines: Mapping[str, ColourBaseline],
    current_reference: ColourReference | None,
    families: frozenset[str] = ALL_FAMILIES,
) -> VesselMeasurements:
    """`masks` maps a concept to its frame-sized union inside this vessel; a missing concept is an empty mask.
    Size and count metrics of an empty mask are 0; colour metrics of an empty mask are absent."""
    height, width = image_bgr.shape[:2]
    empty = np.zeros((height, width), bool)
    region: _Region | None = None
    views: dict[str, np.ndarray] = {}
    drafts: list[MeasurementDraft] = []
    lab: dict[str, ColourBaseline] = {}

    def draft(metric: str, value: float, uncertainty: float, unit: str, method_version: str) -> None:
        drafts.append(
            MeasurementDraft(
                vessel_id=vessel.id,
                frame_id=frame_id,
                t=t,
                metric=metric,
                value=value,
                uncertainty=uncertainty,
                unit=unit,
                method_version=method_version,
            )
        )

    def sized(spec: MeasurementSpec, metric: MetricValue, boundary_mm: float, power: int) -> None:
        u = combined_uncertainty(metric.value, boundary_mm, cal.rel_uncertainty, power=power)
        draft(spec.id, metric.value, u, metric.unit, metric.method_version)

    for spec in recipe.measurements:
        if spec.family not in families:
            continue
        mask = np.asarray(masks.get(spec.source, empty), bool)
        if spec.family in ("size", "count"):
            if spec.method not in ("area", "height", "skeleton_length", "component_count"):
                continue  # rule-based counts and thresholds are evaluated in phase 4
            region = region or _Region(vessel, image_bgr, cal)
            if spec.source not in views:
                views[spec.source] = region.view(mask)
            view, mmpp = views[spec.source], region.mm_per_px
            present = bool(view.any())
            if spec.method == "area":
                sized(spec, area_mm2(view, mmpp), 0.5 * _perimeter_px(view) * mmpp**2, power=2)
            elif spec.method == "height":
                metric = height_mm(view, mmpp, base_y_px=region.base_y_px)
                sized(spec, metric, HEIGHT_BOUNDARY_PX * mmpp if present else 0.0, power=1)
            elif spec.method == "skeleton_length":
                metric = skeleton_length_mm(view, mmpp)
                sized(spec, metric, _length_boundary_px(view, metric.value / mmpp) * mmpp if present else 0.0, power=1)
            else:
                metric = component_count(view, mmpp, min_area_mm2=MIN_COUNT_AREA_MM2)
                draft(spec.id, metric.value, 0.0, metric.unit, metric.method_version)
        elif spec.family == "colour":
            reading = _colour(image_bgr, mask, cal, current_reference)
            if reading is None:
                continue
            colour, se = reading
            lab[spec.id] = colour
            if spec.method == "lab_mean":
                for i, (suffix, unit) in enumerate((("l", "L*"), ("a", "a*"), ("b", "b*"))):
                    draft(f"{spec.id}_{suffix}", colour.lab[i], float(se[i]), unit, "lab_mean/1")
            elif spec.method == "delta_e" and spec.id in baselines:
                base = baselines[spec.id]
                value = float(deltaE_ciede2000(np.array(colour.lab), np.array(base.lab)))
                draft(spec.id, value, math.hypot(colour.se, base.se), "dE00", "delta_e/1")
    return VesselMeasurements(drafts, lab)
