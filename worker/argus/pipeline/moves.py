"""What a moved card means for a run (KB 09: re-run the homography, flag the measurements).

The card is recalibrated either way. When the whole scene moved with it (the quality gate took a new reference),
the camera moved, and the vessels' regions follow the card through the bench plane. When only the card moved,
the vessels stay where they were drawn.
"""

from __future__ import annotations

from collections.abc import Sequence

from argus.calibration.run import RunCalibration, plane_shift
from argus.domain import Vessel
from argus.rois import follow


def after_card_moved(
    vessels: Sequence[Vessel], old: RunCalibration, new: RunCalibration, *, camera_moved: bool
) -> tuple[list[Vessel], dict]:
    """The vessels to measure from now on, and the camera_moved event's detail (with the new regions, if any)."""
    shift = plane_shift(old, new) if camera_moved else None
    if shift is None:
        return list(vessels), {"message": "card moved: recalibrated"}
    moved = [follow(v, shift) for v in vessels]
    rois = {v.id: [list(point) for point in v.roi] for v in moved}
    return moved, {"message": "camera moved: recalibrated; the vessel regions follow the card", "rois": rois}
