"""segment(): SAM 3.1 image and video segmentation (spec §7.1). The only way into the segmentation model."""

from __future__ import annotations

from dataclasses import dataclass

from argus.domain import ModelCallDraft
from argus.segment.sam import SegmentError, segment
from argus.segment.types import Clip, MaskPatch, Track, TrackFrame


@dataclass(frozen=True)
class SegmentResult:
    """The tracks found, with the model call to log against the run (spec §7.1's list[Track] is `.tracks`)."""

    tracks: list[Track]
    call: ModelCallDraft


__all__ = ["Clip", "MaskPatch", "SegmentError", "SegmentResult", "Track", "TrackFrame", "segment"]
