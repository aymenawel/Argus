"""Imported video: one or more files played in order, with t = video time x time scale (spec §4.2).

Time comes from each decoded frame's own timestamp, never from the container's frame count, which is
wrong or zero for many phone and fast-motion files. Split files continue where the previous one ended.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class VideoFrame:
    t: float  # real seconds since the run started
    video_s: float  # seconds into the (concatenated) video
    file_index: int
    image: np.ndarray


class VideoFileSource:
    def __init__(self, paths: Sequence[Path], *, time_scale: float) -> None:
        if time_scale <= 0:
            raise ValueError("the time scale must be positive")
        self.paths = [Path(p) for p in paths]
        self.time_scale = time_scale

    def frames(self) -> Iterator[VideoFrame]:
        """Every frame of every file, in order."""
        offset = 0.0
        for file_index, path in enumerate(self.paths):
            if not path.is_file():
                raise FileNotFoundError(f"video not found: {path}")
            capture = cv2.VideoCapture(str(path))
            if not capture.isOpened():
                capture.release()
                raise FileNotFoundError(f"cannot read video frames from {path}")
            fps = capture.get(cv2.CAP_PROP_FPS)
            step = 1.0 / fps if fps and fps > 0 else 0.0
            last: float | None = None
            count = 0
            try:
                while True:
                    ok, image = capture.read()
                    if not ok:
                        break
                    ms = capture.get(cv2.CAP_PROP_POS_MSEC)
                    local = ms / 1000.0 if ms > 0 or count == 0 else count * step
                    if last is not None and local <= last:  # timestamps that stall or go back: keep time moving
                        local = last + (step or 0.001)
                    last = local
                    count += 1
                    video_s = offset + local
                    yield VideoFrame(video_s * self.time_scale, video_s, file_index, image)
            finally:
                capture.release()
            if last is None:
                raise FileNotFoundError(f"cannot read video frames from {path}")
            offset += last + step
