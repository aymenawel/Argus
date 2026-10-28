"""Find the Argus Card in a frame and turn pixels into millimetres on the card's plane.

The card's ArUco corners give a homography from image pixels to card millimetres. That corrects the
viewing angle and gives the scale; the 100 mm print check corrects a printer that scaled the page.
Without a card, two clicks on a ruler give a scale (no angle correction).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import cv2
import numpy as np

from argus.calibration.card import CARDS, CardSpec, aruco_dictionary

UNCHECKED_PRINT_REL = 0.01  # a home printer's scale error before the 100 mm line is measured
RULER_READING_MM = 0.5  # how precisely a person reads the 100 mm line
PRINT_CHECK_RANGE_MM = (90.0, 110.0)
# A corner further than this from the fitted card does not belong to it: a loose or falsely decoded marker.
FIT_TOLERANCE_MM = 1.0
FIT_TOLERANCE_PX = 3.0  # at low resolution a few pixels of corner error is still an honest detection


@dataclass(frozen=True)
class CardDetection:
    spec: CardSpec
    marker_ids: tuple[int, ...]
    image_to_card: np.ndarray  # 3x3 homography, image px -> printed card mm
    mm_per_px: float  # true mm per px at the card centre (print scale applied)
    reprojection_error_mm: float
    print_scale: float = 1.0
    rel_uncertainty: float = UNCHECKED_PRINT_REL

    def px_to_mm(self, points_px: np.ndarray) -> np.ndarray:
        points = np.asarray(points_px, np.float64).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(points, self.image_to_card).reshape(-1, 2) * self.print_scale


def _marker_span_mm(spec: CardSpec) -> float:
    markers = spec.markers()
    x0, y0 = min(m.x_mm for m in markers), min(m.y_mm for m in markers)
    x1, y1 = max(m.x_mm + m.size_mm for m in markers), max(m.y_mm + m.size_mm for m in markers)
    return math.hypot(x1 - x0, y1 - y0)


def _fit_tolerance_mm(spec: CardSpec, corners_px: list[np.ndarray]) -> float:
    side_px = float(np.mean([np.linalg.norm(np.roll(c, -1, axis=0) - c, axis=1).mean() for c in corners_px]))
    return max(FIT_TOLERANCE_MM, FIT_TOLERANCE_PX * spec.marker_size_mm / side_px)


def _detector() -> cv2.aruco.ArucoDetector:
    params = cv2.aruco.DetectorParameters()
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(aruco_dictionary(), params)


def detect_card(
    image_bgr: np.ndarray, cards: Sequence[CardSpec] = CARDS, *, min_markers: int = 2
) -> CardDetection | None:
    """The card with the most markers in view, or None.

    Markers of other cards are never mixed in. A marker id seen twice (two prints of the card) makes the
    frame ambiguous, so it gives None; a marker that doesn't sit where the others put it is left out.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    corners, ids, _ = _detector().detectMarkers(gray)
    if ids is None:
        return None
    seen = [int(i) for i in ids.flatten()]
    found = {i: c.reshape(4, 2) for i, c in zip(seen, corners, strict=True)}
    spec = max(cards, key=lambda s: sum(i in found for i in s.marker_ids))
    if any(seen.count(i) > 1 for i in spec.marker_ids):
        return None
    markers = [m for m in spec.markers() if m.id in found]
    if not markers:
        return None
    tolerance = _fit_tolerance_mm(spec, [found[m.id] for m in markers])

    def points(ms: list) -> tuple[np.ndarray, np.ndarray]:
        image = np.concatenate([found[m.id] for m in ms]).astype(np.float64)
        return image, np.concatenate([m.corners_mm() for m in ms]).astype(np.float64)

    if len(markers) >= 3:  # with three or more, the honest markers outvote a stray one
        _, inliers = cv2.findHomography(*points(markers), cv2.RANSAC, tolerance)
        if inliers is None:
            return None
        markers = [m for m, ok in zip(markers, inliers.reshape(-1, 4).all(axis=1), strict=True) if ok]
    if len(markers) < min_markers:
        return None

    image_pts, card_pts = points(markers)
    homography, _ = cv2.findHomography(image_pts, card_pts, 0)
    if homography is None:
        return None

    mapped = cv2.perspectiveTransform(image_pts.reshape(-1, 1, 2), homography).reshape(-1, 2)
    rms = float(np.sqrt(np.mean(np.sum((mapped - card_pts) ** 2, axis=1))))
    if rms > tolerance:
        return None

    centre_mm = np.array([[[spec.width_mm / 2, spec.height_mm / 2]]])
    cx, cy = cv2.perspectiveTransform(centre_mm, np.linalg.inv(homography))[0, 0]
    probe = np.array([[[cx, cy]], [[cx + 1.0, cy]], [[cx, cy + 1.0]]], np.float64)
    p0, px, py = cv2.perspectiveTransform(probe, homography).reshape(3, 2)
    mm_per_px = math.sqrt(abs(np.linalg.det(np.column_stack([px - p0, py - p0]))))

    return CardDetection(
        spec=spec,
        marker_ids=tuple(sorted(m.id for m in markers)),
        image_to_card=homography,
        mm_per_px=mm_per_px,
        reprojection_error_mm=rms,
        rel_uncertainty=math.hypot(rms / _marker_span_mm(spec), UNCHECKED_PRINT_REL),
    )


def with_print_check(detection: CardDetection, measured_line_mm: float) -> CardDetection:
    """Apply the researcher's measurement of the printed 100 mm line."""
    low, high = PRINT_CHECK_RANGE_MM
    if not low <= measured_line_mm <= high:
        raise ValueError(f"the print check line should measure close to 100 mm, got {measured_line_mm} mm")
    # A line that measures 98 mm means the page printed at 98 %: card millimetres are 0.98 real ones.
    scale = measured_line_mm / 100.0
    return replace(
        detection,
        print_scale=scale,
        mm_per_px=detection.mm_per_px / detection.print_scale * scale,
        rel_uncertainty=math.hypot(
            detection.reprojection_error_mm / _marker_span_mm(detection.spec), RULER_READING_MM / measured_line_mm
        ),
    )


@dataclass(frozen=True)
class RulerScale:
    mm_per_px: float
    rel_uncertainty: float


def ruler_scale(
    p1: tuple[float, float], p2: tuple[float, float], distance_mm: float, *, click_error_px: float = 1.0
) -> RulerScale:
    pixels = math.dist(p1, p2)
    if pixels <= 0 or distance_mm <= 0:
        raise ValueError("the two ruler points must differ and the distance must be positive")
    return RulerScale(mm_per_px=distance_mm / pixels, rel_uncertainty=click_error_px * math.sqrt(2) / pixels)


@dataclass(frozen=True)
class Rectified:
    image: np.ndarray
    px_per_mm: float
    origin_mm: tuple[float, float]  # card-plane mm at the image's top-left pixel


def rectify(image_or_mask: np.ndarray, detection: CardDetection, *, px_per_mm: float = 10.0) -> Rectified:
    """Warp the whole frame onto the card plane at a fixed scale, so lengths read straight in mm."""
    h, w = image_or_mask.shape[:2]
    corners_mm = detection.px_to_mm(np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float64))
    x0, y0 = corners_mm.min(axis=0)
    x1, y1 = corners_mm.max(axis=0)
    to_canvas = np.array([[px_per_mm, 0, -x0 * px_per_mm], [0, px_per_mm, -y0 * px_per_mm], [0, 0, 1]])
    print_scale = np.diag([detection.print_scale, detection.print_scale, 1.0])
    matrix = to_canvas @ print_scale @ detection.image_to_card
    size = (math.ceil((x1 - x0) * px_per_mm), math.ceil((y1 - y0) * px_per_mm))
    if image_or_mask.dtype == bool:
        warped = cv2.warpPerspective(image_or_mask.astype(np.uint8), matrix, size, flags=cv2.INTER_NEAREST) > 0
    else:
        border = (255,) * (image_or_mask.shape[2] if image_or_mask.ndim == 3 else 1)
        warped = cv2.warpPerspective(image_or_mask, matrix, size, flags=cv2.INTER_LINEAR, borderValue=border)
    return Rectified(image=warped, px_per_mm=px_per_mm, origin_mm=(float(x0), float(y0)))
