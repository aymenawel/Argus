"""What changed in a vessel since its start, found by code alone (D-92). No model is asked anything here.

A faint swarm is hard to see in one picture and obvious against the same dish at the start. The start reference is
the per-pixel median of a vessel's first kept crops; each later crop's colour distance (ΔE, CIE76) from it, with the
rim left out and light that changed everywhere taken out, is thresholded from the reference's own noise: a strong
core, grown into the fainter pixels connected to it. What remains, region by region, is where to point SAM, or the
outline itself when SAM still finds nothing.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np
from skimage.filters import apply_hysteresis_threshold
from skimage.measure import label

REFERENCE_FRAMES = 3  # kept crops the start reference is the median of
RIM_ERODE = 0.06  # of the vessel's equivalent radius: the rim's glare and condensation are left out
MIN_OUTSIDE_PX = 500  # crop pixels outside the vessel needed to take out light that changed everywhere
CORE_NOISE, CORE_MIN = 8.0, 6.0  # a region's core: above max(8 x noise, 6 ΔE)
FRINGE_NOISE, FRINGE_MIN = 4.0, 3.0  # grown into connected pixels above max(4 x noise, 3 ΔE)
MIN_AREA_FRACTION, MIN_AREA_PX = 0.002, 25  # smaller regions are specks: max(0.2% of the vessel, 25 px)
MAX_REGIONS = 16  # SAM takes at most 16 prompted objects per request


@dataclass(frozen=True)
class ChangeRegion:
    box: tuple[int, int, int, int]  # x0, y0, x1, y1 in crop pixels, x1 and y1 exclusive
    peak: tuple[int, int]  # x, y of the strongest change
    mask: np.ndarray  # bool, crop-sized


@dataclass(frozen=True)
class ChangeReference:
    lab: np.ndarray  # float32 H x W x 3, the median of the reference crops
    noise: float  # ΔE: how far the reference crops sit from their median
    inside: np.ndarray  # bool: the vessel without its rim
    outside: np.ndarray  # bool: crop pixels outside the vessel's region
    roi: tuple[tuple[float, float], ...]  # the vessel's region the reference was taken with


def _lab(crop: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(crop.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)


def _delta_e(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sqrt(((a - b) ** 2).sum(axis=2))


def change_reference(
    crops: Sequence[np.ndarray], vessel_mask: np.ndarray, roi: Sequence[tuple[float, float]]
) -> ChangeReference:
    """The start reference from a vessel's first crops (BGR, one shape); `vessel_mask` is its region in the crop."""
    if not crops or any(c.shape != crops[0].shape for c in crops) or vessel_mask.shape != crops[0].shape[:2]:
        raise ValueError("a change reference needs crops of one shape and a vessel mask of that size")
    labs = np.stack([_lab(c) for c in crops])
    median = np.median(labs, axis=0).astype(np.float32)
    vessel = vessel_mask.astype(bool)
    k = round(RIM_ERODE * math.sqrt(vessel.sum() / math.pi))
    inside = vessel
    if k > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        inside = cv2.erode(vessel.astype(np.uint8), kernel).astype(bool)
    spread = np.concatenate([_delta_e(lab, median)[inside] for lab in labs])
    noise = 1.4826 * float(np.median(spread)) if spread.size else 0.0
    return ChangeReference(median, noise, inside, ~vessel, tuple((float(x), float(y)) for x, y in roi))


def change_regions(reference: ChangeReference, crop: np.ndarray) -> list[ChangeRegion]:
    """Where the vessel changed since its start, largest region first; [] when nothing did."""
    lab = _lab(crop)
    if reference.outside.sum() >= MIN_OUTSIDE_PX:  # light that changed outside the vessel changed inside it too
        lab = lab - np.median(lab[reference.outside] - reference.lab[reference.outside], axis=0)
    delta = np.where(reference.inside, _delta_e(lab, reference.lab), 0.0)
    high = max(CORE_NOISE * reference.noise, CORE_MIN)
    low = max(FRINGE_NOISE * reference.noise, FRINGE_MIN)
    changed = apply_hysteresis_threshold(delta, low, high)
    floor = max(MIN_AREA_FRACTION * reference.inside.sum(), MIN_AREA_PX)
    labels = label(changed, connectivity=2)
    masks = [labels == i for i in range(1, labels.max() + 1)]
    masks = sorted((m for m in masks if m.sum() >= floor), key=lambda m: int(m.sum()), reverse=True)
    regions = []
    for mask in masks[:MAX_REGIONS]:
        ys, xs = np.nonzero(mask)
        strongest = int(np.argmax(delta[ys, xs]))
        box = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        regions.append(ChangeRegion(box, (int(xs[strongest]), int(ys[strongest])), mask))
    return regions
