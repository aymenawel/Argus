"""A published image sequence, frame by frame, as the import pipeline reads a video: frame i was taken at
i × the manifest's interval, so run time and "video" time are the same."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from argus.capture.video import VideoFrame
from argus.datasets.manifest import ManifestError, load_manifest


class ImageSequenceSource:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)

    def frames(self) -> Iterator[VideoFrame]:
        """Every frame in order; the manifest and every file are checked before the first is yielded."""
        manifest = load_manifest(self.manifest_path)
        for index, path in enumerate(manifest.frame_paths()):
            # imdecode, not imread: OpenCV can't open non-ASCII paths on Windows
            image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ManifestError(f"{path.name} can't be read as an image")
            t = index * manifest.interval_s
            yield VideoFrame(t, t, 0, image)
