"""What segment() returns: box-local masks placed in the media's pixel space, grouped into tracks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class MaskPatch:
    """A boolean mask covering only its bounding box; (left, top) is the box's corner in media pixels."""

    left: int
    top: int
    mask: np.ndarray
    source: str | None = None  # who drew it when it isn't SAM by name: "sam-3.1/pointed" or "change-map" (D-93)

    @property
    def area_px(self) -> int:
        return int(self.mask.sum())

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        height, width = self.mask.shape
        return (float(self.left), float(self.top), float(self.left + width), float(self.top + height))

    def shifted(self, dx: int, dy: int) -> MaskPatch:
        return MaskPatch(self.left + dx, self.top + dy, self.mask, self.source)

    def to_canvas(self, height: int, width: int) -> np.ndarray:
        """The mask on a full height x width canvas; parts outside the canvas are dropped."""
        canvas = np.zeros((height, width), bool)
        h, w = self.mask.shape
        x0, y0 = max(self.left, 0), max(self.top, 0)
        x1, y1 = min(self.left + w, width), min(self.top + h, height)
        if x1 > x0 and y1 > y0:
            canvas[y0:y1, x0:x1] = self.mask[y0 - self.top : y1 - self.top, x0 - self.left : x1 - self.left]
        return canvas


@dataclass(frozen=True)
class ObjectPrompt:
    """One object for SAM to trace from where it is, not what it is called (D-92): a box and, optionally, a point."""

    box: tuple[int, int, int, int]  # x0, y0, x1, y1 in the image's pixels, x1 and y1 inclusive
    point: tuple[int, int] | None = None  # x, y inside the object


@dataclass(frozen=True)
class TrackFrame:
    index: int  # 0 for an image; the clip's frame index for a video
    patch: MaskPatch
    confidence: float | None


@dataclass(frozen=True)
class Track:
    key: str
    concept: str
    frames: tuple[TrackFrame, ...]


@dataclass(frozen=True)
class Clip:
    """An H.264 MP4 for SAM's video mode, with its frame count and pixel size."""

    path: Path
    frame_count: int
    width: int
    height: int
