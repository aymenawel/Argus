"""A run's calibration: the Argus Card (or, without one, a two-click ruler, or the rims of dishes of a known
diameter) on the first good frame, and a check of whether the card has moved since (spec §6, KB 09, D-72)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import cv2
import numpy as np

from argus.calibration.colour import ColourReference, read_patches
from argus.calibration.detect import CardDetection, RulerScale, detect_card, ruler_scale, with_print_check
from argus.calibration.dish import DishScale, dish_scale, dish_scale_or_reason
from argus.domain import CalibrationDraft, CameraProperty, RulerInput  # RulerInput lives in domain (Setup holds one)


def _marker_corners_px(detection: CardDetection) -> np.ndarray:
    """Where the card's marker corners sit in the image, according to this detection's homography."""
    corners_mm = np.concatenate([m.corners_mm() for m in detection.spec.markers()]).astype(np.float64)
    card_to_image = np.linalg.inv(detection.image_to_card)
    return cv2.perspectiveTransform(corners_mm.reshape(-1, 1, 2), card_to_image).reshape(-1, 2)


@dataclass(frozen=True)
class RunCalibration:
    detection: CardDetection | None
    ruler: RulerScale | None
    reference: ColourReference | None
    marker_corners_px: np.ndarray | None
    dish: DishScale | None = None

    @property
    def _scale(self) -> CardDetection | RulerScale | DishScale:
        scale = self.detection or self.ruler or self.dish
        assert scale is not None, "a calibration has a card, a ruler or a dish"
        return scale

    @property
    def mm_per_px(self) -> float:
        return self._scale.mm_per_px

    @property
    def rel_uncertainty(self) -> float:
        return self._scale.rel_uncertainty

    @property
    def card_name(self) -> str:
        return self.detection.spec.name if self.detection else "ruler" if self.ruler else "dish"

    def to_draft(self, t: float, camera_properties: dict[str, CameraProperty]) -> CalibrationDraft:
        reference = None
        if self.reference is not None:
            reference = {"patches": [{"name": p.name, "lab": list(p.lab)} for p in self.reference.patches]}
        return CalibrationDraft(
            t=t,
            card=self.card_name,
            homography=self.detection.image_to_card.tolist() if self.detection else None,
            mm_per_px=self.mm_per_px,
            rel_uncertainty=self.rel_uncertainty,
            print_scale=self.detection.print_scale if self.detection else 1.0,
            colour_reference=reference,
            camera_properties=camera_properties,
        )


def calibrate(
    image_bgr: np.ndarray,
    *,
    print_check_mm: float | None = None,
    ruler: RulerInput | None = None,
    dish_diameter_mm: float | None = None,
    rois: Sequence[Sequence[tuple[float, float]]] = (),
) -> RunCalibration | None:
    """The card if it is in view (with the print check when given), else the ruler, else the dishes' rims in the
    vessel regions when their diameter is known, else None: no millimetres."""
    detection = detect_card(image_bgr)
    if detection is not None:
        if print_check_mm is not None:
            detection = with_print_check(detection, print_check_mm)
        reference = read_patches(image_bgr, detection)
        return RunCalibration(
            detection=detection,
            ruler=None,
            reference=reference if reference.neutrals() else None,
            marker_corners_px=_marker_corners_px(detection),
        )
    if ruler is not None:
        return RunCalibration(
            detection=None,
            ruler=ruler_scale(ruler.p1, ruler.p2, ruler.distance_mm),
            reference=None,
            marker_corners_px=None,
        )
    if dish_diameter_mm is not None and rois:
        dish = dish_scale(image_bgr, rois, dish_diameter_mm)
        if dish is not None:
            return RunCalibration(detection=None, ruler=None, reference=None, marker_corners_px=None, dish=dish)
    return None


def missing_scale(
    image_bgr: np.ndarray, *, dish_diameter_mm: float | None, rois: Sequence[Sequence[tuple[float, float]]]
) -> str:
    """Why a frame gave no millimetres, in words for the run's event."""
    if dish_diameter_mm is None or not rois:
        return "no Argus Card or ruler in view"
    result = dish_scale_or_reason(image_bgr, rois, dish_diameter_mm)
    reason = result if isinstance(result, str) else "the scale changed between checks"
    return f"no Argus Card or ruler, and the dish rims gave no scale: {reason}"


def plane_shift(old: RunCalibration, new: RunCalibration) -> np.ndarray | None:
    """Where a point of the bench in the old view lands in the new one (old image px -> card -> new image px); None
    for a ruler, which has no plane to go through."""
    if old.detection is None or new.detection is None:
        return None
    return np.linalg.inv(new.detection.image_to_card) @ old.detection.image_to_card


def card_moved(cal: RunCalibration, image_bgr: np.ndarray, *, tolerance_px: float = 3.0) -> bool | None:
    """Whether the card's markers shifted by more than the tolerance; None when the card isn't fully visible (or
    the run is calibrated by a ruler), since there is then nothing to compare: a hand over one marker refits the
    card from the others, a few pixels off, and must not count as a move."""
    if cal.detection is None or cal.marker_corners_px is None:
        return None
    current = detect_card(image_bgr, cards=(cal.detection.spec,))
    if current is None or len(current.marker_ids) < len(cal.detection.spec.marker_ids):
        return None
    shift = np.linalg.norm(_marker_corners_px(current) - cal.marker_corners_px, axis=1)
    return bool(shift.max() > tolerance_px)
