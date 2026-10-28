"""Colour reference from the card's patches: read them, measure lighting drift, correct for it.

Home printers aren't colour-accurate, so the first frame's patch readings are the reference and later
frames are corrected relative to it (spec §6), not to the sRGB values the card was printed with.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

from argus.calibration.detect import CardDetection

INNER_FRACTION = 0.6  # sample the middle of each patch, away from its printed edges
MIN_PATCH_PIXELS = 9  # fewer than this (patch cut off by the frame edge) and the patch is left out


@dataclass(frozen=True)
class PatchReading:
    name: str
    lab: tuple[float, float, float]


@dataclass(frozen=True)
class ColourReference:
    patches: tuple[PatchReading, ...]

    def neutrals(self) -> dict[str, np.ndarray]:
        return {p.name: np.array(p.lab) for p in self.patches if p.name.startswith("neutral_")}


def read_patches(image_bgr: np.ndarray, detection: CardDetection) -> ColourReference:
    """Lab means of the patches in view; a patch whose middle is outside the frame is left out, never NaN."""
    card_to_image = np.linalg.inv(detection.image_to_card)
    height, width = image_bgr.shape[:2]
    readings = []
    for patch in detection.spec.patches():
        inset = patch.size_mm * (1 - INNER_FRACTION) / 2
        x0, y0 = patch.x_mm + inset, patch.y_mm + inset
        x1, y1 = patch.x_mm + patch.size_mm - inset, patch.y_mm + patch.size_mm - inset
        corners_mm = np.array([[[x0, y0]], [[x1, y0]], [[x1, y1]], [[x0, y1]]], np.float64)
        corners_px = cv2.perspectiveTransform(corners_mm, card_to_image).reshape(-1, 2)
        if (corners_px < 0).any() or (corners_px[:, 0] >= width).any() or (corners_px[:, 1] >= height).any():
            continue
        mask = np.zeros(image_bgr.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, np.round(corners_px).astype(np.int32), 1)
        if int(mask.sum()) < MIN_PATCH_PIXELS:
            continue
        pixels_rgb = image_bgr[mask.astype(bool)][:, ::-1].astype(np.float64) / 255.0
        lab = rgb2lab(pixels_rgb.reshape(-1, 1, 3)).reshape(-1, 3).mean(axis=0)
        readings.append(PatchReading(patch.name, (float(lab[0]), float(lab[1]), float(lab[2]))))
    return ColourReference(tuple(readings))


def _shared_neutrals(reference: ColourReference, current: ColourReference):
    ref, cur = reference.neutrals(), current.neutrals()
    names = sorted(ref.keys() & cur.keys())
    return ref, cur, names


def neutral_drift(reference: ColourReference, current: ColourReference) -> float | None:
    """Mean CIEDE2000 between the reference and current neutral patches; None if no neutral is in both."""
    ref, cur, names = _shared_neutrals(reference, current)
    if not names:
        return None
    return float(np.mean([deltaE_ciede2000(ref[name], cur[name]) for name in names]))


def correct_lab(lab: np.ndarray, reference: ColourReference, current: ColourReference) -> np.ndarray:
    """Remove the mean shift the neutral patches show between the reference and the current frame (no shared
    neutral in view: nothing to correct with, so the reading is returned as it is)."""
    ref, cur, names = _shared_neutrals(reference, current)
    if not names:
        return np.asarray(lab, np.float64)
    offset = np.mean([cur[name] - ref[name] for name in names], axis=0)
    return np.asarray(lab, np.float64) - offset
