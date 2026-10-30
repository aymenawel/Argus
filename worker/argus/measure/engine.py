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
from argus.measure.geometry import (
    MetricValue,
    area_mm2,
    component_count,
    height_mm,
    skeleton_length_mm,
    touching_count,
)
from argus.measure.uncertainty import combined_uncertainty
from argus.recipes.model import MeasurementSpec, Recipe
from argus.rois import roi_box, roi_mask

ALL_FAMILIES = frozenset({"size", "count", "colour"})
MIN_COUNT_AREA_MM2 = 1.0
LENGTH_BOUNDARY_PX = 2.0  # at least a pixel at each end of a skeleton
HEIGHT_BOUNDARY_PX = 1.0


@dataclass(frozen=True)
class ColourBaseline:
    """A vessel's mean colour in one frame, with the standard error of that mean (Lab units), and whether it was
    corrected against the card (readings of the two kinds are labelled apart and never compared)."""

    lab: tuple[float, float, float]
    se: float
    corrected: bool


def baseline_key(measurement_id: str, corrected: bool) -> str:
    """Where a reading's ΔE baseline is kept: corrected and uncorrected readings each have their own."""
    return measurement_id if corrected else f"{measurement_id}:uncorrected"


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


def _length_boundary_px(mask: np.ndarray) -> float:
    """A thinning skeleton stops short of square ends and runs into round ones, so each object's ends are
    uncertain by about its width: its mean width (area / length), never less than a pixel per end. The bias
    has the same sign for every object, so a vessel's objects (ten roots in a dish) add up linearly."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    total = 0.0
    for i in range(1, count):
        x, y, w, h = (
            int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT)
        )
        own = labels[y : y + h, x : x + w] == i
        length_px = skeleton_length_mm(own, 1.0).value
        width_px = float(stats[i, cv2.CC_STAT_AREA]) / length_px if length_px > 0 else 0.0
        total += max(LENGTH_BOUNDARY_PX, width_px)
    return total


def _objects(view: np.ndarray, mm_per_px: float) -> list[np.ndarray]:
    """The separate objects in a concept's mask, as component_count sees them (specks below its size filter out)."""
    count, labels, stats, _ = cv2.connectedComponentsWithStats(np.asarray(view, np.uint8), connectivity=8)
    return [labels == i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] * mm_per_px**2 >= MIN_COUNT_AREA_MM2]


def _colour(
    image_bgr: np.ndarray, mask: np.ndarray, cal: RunCalibration, current: ColourReference | None
) -> tuple[ColourBaseline, ColourBaseline, np.ndarray] | None:
    """The reading (corrected when the card allows), the uncorrected reading, and the standard error per axis."""
    pixels = image_bgr[mask]
    if pixels.size == 0:
        return None
    lab = rgb2lab(pixels[:, ::-1].astype(np.float64).reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    mean = lab.mean(axis=0)
    se = lab.std(axis=0, ddof=1) / math.sqrt(len(lab)) if len(lab) > 1 else np.zeros(3)
    spread = float(np.linalg.norm(se))
    raw = ColourBaseline((float(mean[0]), float(mean[1]), float(mean[2])), spread, False)
    if cal.reference is None or current is None:
        return raw, raw, se
    fixed = correct_lab(mean, cal.reference, current)
    return ColourBaseline((float(fixed[0]), float(fixed[1]), float(fixed[2])), spread, True), raw, se


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
            if spec.method not in ("area", "height", "skeleton_length", "component_count", "touching_count"):
                continue  # rule-based counts and thresholds are evaluated in phase 4
            region = region or _Region(vessel, image_bgr, cal)
            for concept in (spec.source, spec.touching):
                if concept is not None and concept not in views:
                    views[concept] = region.view(np.asarray(masks.get(concept, empty), bool))
            view, mmpp = views[spec.source], region.mm_per_px
            present = bool(view.any())
            if spec.method == "area":
                sized(spec, area_mm2(view, mmpp), 0.5 * _perimeter_px(view) * mmpp**2, power=2)
            elif spec.method == "height":
                metric = height_mm(view, mmpp, base_y_px=region.base_y_px)
                sized(spec, metric, HEIGHT_BOUNDARY_PX * mmpp if present else 0.0, power=1)
            elif spec.method == "skeleton_length":
                metric = skeleton_length_mm(view, mmpp)
                sized(spec, metric, _length_boundary_px(view) * mmpp if present else 0.0, power=1)
            elif spec.method == "touching_count" and spec.touching is not None and spec.min_length_mm is not None:
                touched = views[spec.touching]
                n = touching_count(_objects(view, mmpp), touched, mmpp, min_length_mm=spec.min_length_mm)
                draft(spec.id, float(n), 0.0, "count", "touching_count/1")  # an exact count of what was seen
            else:
                metric = component_count(view, mmpp, min_area_mm2=MIN_COUNT_AREA_MM2)
                draft(spec.id, metric.value, 0.0, metric.unit, metric.method_version)
        elif spec.family == "colour":
            reading = _colour(image_bgr, mask, cal, current_reference)
            if reading is None:
                continue
            colour, raw, se = reading
            key = baseline_key(spec.id, colour.corrected)
            lab[key] = colour
            lab[baseline_key(spec.id, False)] = raw  # so an uncorrected baseline exists from the start too
            kind = "" if colour.corrected else "_uncorrected"
            if spec.method == "lab_mean":
                for i, (suffix, unit) in enumerate((("l", "L*"), ("a", "a*"), ("b", "b*"))):
                    draft(f"{spec.id}_{suffix}", colour.lab[i], float(se[i]), unit, f"lab_mean{kind}/1")
            elif spec.method == "delta_e" and key in baselines:
                base = baselines[key]
                value = float(deltaE_ciede2000(np.array(colour.lab), np.array(base.lab)))
                draft(spec.id, value, math.hypot(colour.se, base.se), "dE00", f"delta_e{kind}/1")
    return VesselMeasurements(drafts, lab)
