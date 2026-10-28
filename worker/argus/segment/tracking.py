"""Which vessel a detection belongs to, and which earlier detection it continues (spec §4.1 step 4)."""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from argus.domain import Vessel
from argus.segment.types import MaskPatch

MIN_VESSEL_SHARE = 0.5  # a detection belongs to a vessel whose ROI holds at least half of it
MIN_IOU = 0.3


def _roi_mask(vessel: Vessel, height: int, width: int) -> np.ndarray:
    canvas = np.zeros((height, width), np.uint8)
    cv2.fillPoly(canvas, [np.round(np.asarray(vessel.roi, np.float64)).astype(np.int32)], 1)
    return canvas.astype(bool)


def assign_to_vessels(
    patches: Sequence[MaskPatch], vessels: Sequence[Vessel], frame_shape: tuple[int, int]
) -> dict[str, list[int]]:
    """Patch indices per vessel id. A patch goes to the vessel whose ROI covers most of it, if that is at least
    half; otherwise (between vessels, or outside them all) to none."""
    height, width = frame_shape
    rois = [_roi_mask(v, height, width) for v in vessels]
    assigned: dict[str, list[int]] = {v.id: [] for v in vessels}
    for i, patch in enumerate(patches):
        area = patch.area_px
        h, w = patch.mask.shape
        x0, y0 = max(patch.left, 0), max(patch.top, 0)
        x1, y1 = min(patch.left + w, width), min(patch.top + h, height)
        if area == 0 or not vessels or x1 <= x0 or y1 <= y0:
            continue
        local = patch.mask[y0 - patch.top : y1 - patch.top, x0 - patch.left : x1 - patch.left]
        shares = [float((roi[y0:y1, x0:x1] & local).sum()) / area for roi in rois]
        best = int(np.argmax(shares))
        if shares[best] >= MIN_VESSEL_SHARE:
            assigned[vessels[best].id].append(i)
    return assigned


def iou(a: MaskPatch, b: MaskPatch) -> float:
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a.bbox, b.bbox
    if ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0:
        return 0.0
    x0, y0 = int(min(ax0, bx0)), int(min(ay0, by0))
    height, width = int(max(ay1, by1)) - y0, int(max(ax1, bx1)) - x0
    ma = a.shifted(-x0, -y0).to_canvas(height, width)
    mb = b.shifted(-x0, -y0).to_canvas(height, width)
    union = int((ma | mb).sum())
    return float((ma & mb).sum()) / union if union else 0.0


class TrackMatcher:
    """Stable keys "<label>:<concept>:<n>" from frame to frame, by mask overlap with the previous frame."""

    def __init__(self, min_iou: float = MIN_IOU) -> None:
        self.min_iou = min_iou
        self._previous: dict[tuple[str, str], dict[str, MaskPatch]] = {}
        self._count: dict[tuple[str, str], int] = {}

    def restore(self, vessel_id: str, concept: str, keyed: dict[str, MaskPatch]) -> None:
        """Continue from known keys (a new video chunk picks up where the last one ended)."""
        self._previous[(vessel_id, concept)] = dict(keyed)
        numbers = [int(k.rsplit(":", 1)[1]) for k in keyed if k.rsplit(":", 1)[1].isdigit()]
        self._count[(vessel_id, concept)] = max([self._count.get((vessel_id, concept), 0), *numbers])

    def match(self, vessel: Vessel, concept: str, patches: Sequence[MaskPatch]) -> list[str]:
        slot = (vessel.id, concept)
        previous = self._previous.get(slot, {})
        pairs = sorted(
            ((iou(p, q), i, key) for i, p in enumerate(patches) for key, q in previous.items()),
            key=lambda pair: pair[0],
            reverse=True,
        )
        keys: dict[int, str] = {}
        taken: set[str] = set()
        for score, i, key in pairs:
            if score < self.min_iou:
                break
            if i not in keys and key not in taken:
                keys[i] = key
                taken.add(key)
        result = []
        for i in range(len(patches)):
            if i not in keys:
                self._count[slot] = self._count.get(slot, 0) + 1
                keys[i] = f"{vessel.label}:{concept}:{self._count[slot]}"
            result.append(keys[i])
        self._previous[slot] = dict(zip(result, patches, strict=True))
        return result
