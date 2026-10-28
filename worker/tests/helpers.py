"""Synthetic camera frames with an Argus Card, for calibration and colour tests.

Card-plane millimetres map to frame pixels as  px = ORIGIN + mm * px_per_mm  before any tilt; TILT is a
perspective warp of the whole frame, like a camera that isn't square to the card.
"""

import cv2
import numpy as np

from argus.calibration.card import CardSpec, aruco_dictionary, render_raster

FRAME_W, FRAME_H = 1600, 1200
ORIGIN = np.array([200.0, 150.0])
TILT = cv2.getPerspectiveTransform(
    np.float32([[0, 0], [FRAME_W, 0], [FRAME_W, FRAME_H], [0, FRAME_H]]),
    np.float32([[60, 40], [1560, 90], [1520, 1170], [30, 1130]]),
)


def _blank() -> np.ndarray:
    return np.full((FRAME_H, FRAME_W, 3), 255, np.uint8)


def _tilted(frame: np.ndarray, tilt: np.ndarray | None) -> np.ndarray:
    if tilt is None:
        return frame
    return cv2.warpPerspective(frame, tilt, (FRAME_W, FRAME_H), borderValue=(255, 255, 255))


def _card_frame(spec: CardSpec, px_per_mm: float, cover_ids=()) -> np.ndarray:
    frame = _blank()
    card = render_raster(spec, px_per_mm)
    x0, y0 = ORIGIN.astype(int)
    frame[y0 : y0 + card.shape[0], x0 : x0 + card.shape[1]] = card
    for marker in spec.markers():
        if marker.id in cover_ids:
            mx, my = (ORIGIN + np.array([marker.x_mm, marker.y_mm]) * px_per_mm).astype(int)
            side = round(marker.size_mm * px_per_mm)
            frame[my - 2 : my + side + 2, mx - 2 : mx + side + 2] = 255
    return frame


def to_px(mm: np.ndarray, px_per_mm: float, tilt: np.ndarray | None = None) -> np.ndarray:
    px = ORIGIN + np.asarray(mm, float) * px_per_mm
    if tilt is None:
        return px
    return cv2.perspectiveTransform(px.reshape(-1, 1, 2), tilt).reshape(-1, 2)


def scene(spec: CardSpec, px_per_mm: float, tilt=None, cover_ids=()) -> np.ndarray:
    return _tilted(_card_frame(spec, px_per_mm, cover_ids), tilt)


def scene_with_patch_centres(spec: CardSpec, px_per_mm: float, tilt=None):
    centres_mm = np.array([[p.x_mm + p.size_mm / 2, p.y_mm + p.size_mm / 2] for p in spec.patches()])
    return scene(spec, px_per_mm, tilt), to_px(centres_mm, px_per_mm, tilt), centres_mm


def scene_both_cards(full: CardSpec, stray_compact_markers: int = 1, px_per_mm: float = 5.0) -> np.ndarray:
    from argus.calibration.card import COMPACT, STANDARD

    other = COMPACT if full is STANDARD else STANDARD
    frame = _card_frame(full, px_per_mm)
    side = round(other.marker_size_mm * px_per_mm)
    for k, marker_id in enumerate(other.marker_ids[:stray_compact_markers]):
        tile = cv2.aruco.generateImageMarker(aruco_dictionary(), marker_id, side)
        x, y = 1100 + k * (side + 40), 750
        frame[y : y + side, x : x + side] = tile[:, :, None]
    return frame


def scene_with_square_on_card_plane(spec: CardSpec, side_mm: float, tilt=None, px_per_mm: float = 5.0) -> np.ndarray:
    frame = _card_frame(spec, px_per_mm)
    x0, y0 = (ORIGIN + np.array([spec.width_mm + 20.0, 20.0]) * px_per_mm).astype(int)
    side = round(side_mm * px_per_mm)
    frame[y0 : y0 + side, x0 : x0 + side] = 0
    return _tilted(frame, tilt)


def bounding_box_of_dark_square(image: np.ndarray) -> tuple[int, int]:
    """Width and height of the largest dark blob: the test square, bigger than any card marker."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    count, _, stats, _ = cv2.connectedComponentsWithStats((gray < 100).astype(np.uint8))
    largest = max(range(1, count), key=lambda i: stats[i, cv2.CC_STAT_AREA])
    return int(stats[largest, cv2.CC_STAT_WIDTH]), int(stats[largest, cv2.CC_STAT_HEIGHT])
