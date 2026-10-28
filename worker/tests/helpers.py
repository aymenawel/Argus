"""Synthetic camera frames with an Argus Card, for calibration and colour tests.

Card-plane millimetres map to frame pixels as  px = ORIGIN + mm * px_per_mm  before any tilt; TILT is a
perspective warp of the whole frame, like a camera that isn't square to the card.
"""

import cv2
import numpy as np

from argus.calibration.card import STANDARD, CardSpec, aruco_dictionary, render_raster

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


def _card(spec: CardSpec, px_per_mm: float, cover_ids=()) -> np.ndarray:
    card = render_raster(spec, px_per_mm).copy()
    for marker in spec.markers():
        if marker.id in cover_ids:
            mx, my = (np.array([marker.x_mm, marker.y_mm]) * px_per_mm).astype(int)
            side = round(marker.size_mm * px_per_mm)
            card[max(my - 2, 0) : my + side + 2, max(mx - 2, 0) : mx + side + 2] = 255
    return card


def _place(frame: np.ndarray, card: np.ndarray, x0: int, y0: int) -> None:
    frame[y0 : y0 + card.shape[0], x0 : x0 + card.shape[1]] = card


def _card_frame(spec: CardSpec, px_per_mm: float, cover_ids=()) -> np.ndarray:
    frame = _blank()
    _place(frame, _card(spec, px_per_mm, cover_ids), *ORIGIN.astype(int))
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


def scene_two_identical_cards(spec: CardSpec, px_per_mm: float = 5.0, cover_first=(), cover_second=()) -> np.ndarray:
    """Two prints of the same card, each with a marker hidden, so every visible id belongs to one card or the other."""
    frame = _card_frame(spec, px_per_mm, cover_first)
    _place(frame, _card(spec, px_per_mm, cover_second), 850, 650)
    return frame


def scene_with_stray_marker(spec: CardSpec, stray_id: int, cover_ids=(), px_per_mm: float = 5.0) -> np.ndarray:
    """A card plus a loose copy of one of its markers away from the card (or a falsely decoded pattern)."""
    frame = _card_frame(spec, px_per_mm, cover_ids)
    side = round(spec.marker_size_mm * px_per_mm)
    tile = cv2.aruco.generateImageMarker(aruco_dictionary(), stray_id, side)
    frame[750 : 750 + side, 1100 : 1100 + side] = tile[:, :, None]
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


def bbox_of_dark_square_in_image(image: np.ndarray, margin: int = 20) -> tuple[float, float, float, float]:
    """Image-space box (x0, y0, x1, y1) around the largest dark blob, widened by a margin."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    count, _, stats, _ = cv2.connectedComponentsWithStats((gray < 100).astype(np.uint8))
    i = max(range(1, count), key=lambda k: stats[k, cv2.CC_STAT_AREA])
    x, y, w, h = (int(stats[i, k]) for k in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
    return (float(x - margin), float(y - margin), float(x + w + margin), float(y + h + margin))


def scene_with_bar_on_card_plane(
    spec: CardSpec, length_mm: float, width_mm: float, tilt=None, px_per_mm: float = 5.0, colour=(0, 0, 0)
) -> tuple[np.ndarray, np.ndarray]:
    """A card plus a filled bar of exactly length x width mm lying on the card's plane beside it, and the bar's
    mask, both seen through the same tilt (the mask is warped smoothly, then thresholded, like a camera edge)."""
    frame = _card_frame(spec, px_per_mm)
    x0, y0 = ORIGIN + np.array([spec.width_mm + 20.0, 30.0]) * px_per_mm
    rows = slice(round(y0), round(y0 + width_mm * px_per_mm))
    cols = slice(round(x0), round(x0 + length_mm * px_per_mm))
    mask = np.zeros(frame.shape[:2], np.float32)
    mask[rows, cols] = 1.0
    frame[mask > 0.5] = colour
    if tilt is not None:
        mask = cv2.warpPerspective(mask, tilt, (FRAME_W, FRAME_H), flags=cv2.INTER_LINEAR)
    return _tilted(frame, tilt), mask > 0.5


def write_growing_bar_clip(path, *, frames: int = 40, fps: int = 10, start_mm: float = 10.0, end_mm: float = 40.0):
    """An MP4 (mp4v) of the card with a bar on its plane that grows from start_mm to end_mm."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    for i in range(frames):
        length = start_mm + (end_mm - start_mm) * i / max(frames - 1, 1)
        image, _ = scene_with_bar_on_card_plane(STANDARD, length_mm=length, width_mm=2)
        if writer is None:
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, image.shape[1::-1])
        writer.write(image)
    writer.release()
    return path


def rois_around_the_bar(length_mm: float = 40.0, margin: int = 40):
    """Vessel A's ROI around the full-grown bar, and vessel B's, the same box 300 px lower (empty)."""
    _, mask = scene_with_bar_on_card_plane(STANDARD, length_mm=length_mm, width_mm=2)
    ys, xs = np.nonzero(mask)
    a = [
        (xs.min() - margin, ys.min() - margin),
        (xs.max() + margin, ys.min() - margin),
        (xs.max() + margin, ys.max() + margin),
        (xs.min() - margin, ys.max() + margin),
    ]
    a = [(float(x), float(y)) for x, y in a]
    return a, [(x, y + 300.0) for x, y in a]
