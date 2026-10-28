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
    card_to_image = np.linalg.inv(detection.image_to_card)
    readings = []
    for patch in detection.spec.patches():
        inset = patch.size_mm * (1 - INNER_FRACTION) / 2
        x0, y0 = patch.x_mm + inset, patch.y_mm + inset
        x1, y1 = patch.x_mm + patch.size_mm - inset, patch.y_mm + patch.size_mm - inset
        corners_mm = np.array([[[x0, y0]], [[x1, y0]], [[x1, y1]], [[x0, y1]]], np.float64)
        corners_px = cv2.perspectiveTransform(corners_mm, card_to_image).reshape(-1, 2)
        mask = np.zeros(image_bgr.shape[:2], np.uint8)
        cv2.fillConvexPoly(mask, np.round(corners_px).astype(np.int32), 1)
        pixels_rgb = image_bgr[mask.astype(bool)][:, ::-1].astype(np.float64) / 255.0
        lab = rgb2lab(pixels_rgb.reshape(-1, 1, 3)).reshape(-1, 3).mean(axis=0)
        readings.append(PatchReading(patch.name, (float(lab[0]), float(lab[1]), float(lab[2]))))
    return ColourReference(tuple(readings))


def neutral_drift(reference: ColourReference, current: ColourReference) -> float:
    """Mean CIEDE2000 between the reference and current neutral patches."""
    ref, cur = reference.neutrals(), current.neutrals()
    return float(np.mean([deltaE_ciede2000(ref[name], cur[name]) for name in ref]))


def correct_lab(lab: np.ndarray, reference: ColourReference, current: ColourReference) -> np.ndarray:
    """Remove the mean shift the neutral patches show between the reference and the current frame."""
    ref, cur = reference.neutrals(), current.neutrals()
    offset = np.mean([cur[name] - ref[name] for name in ref], axis=0)
    return np.asarray(lab, np.float64) - offset
