"""Which frames a bundle keeps (D-83): all of them up to the limit; past it, frames at even steps of t plus every
cited one. Every frame of the run maps to the kept frame shown in its place, so nothing points at a missing file."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Thinning:
    kept: list[str]  # in t order
    frame_map: dict[str, str]  # every frame id → the kept frame shown in its place


def _nearest(ts: Sequence[float], t: float) -> int:
    """The index of the value nearest t in sorted ts; a tie goes to the earlier one."""
    i = bisect_left(ts, t)
    if i == 0:
        return 0
    if i == len(ts):
        return len(ts) - 1
    return i - 1 if t - ts[i - 1] <= ts[i] - t else i


def thin_frames(frames: Sequence[tuple[str, float]], cited_t: Sequence[float], limit: int = 400) -> Thinning:
    ordered = sorted(frames, key=lambda f: f[1])
    if len(ordered) <= limit:
        return Thinning([f for f, _ in ordered], {f: f for f, _ in ordered})
    ts = [t for _, t in ordered]
    t0, t1 = ts[0], ts[-1]
    targets = [t0 + (t1 - t0) * k / (limit - 1) for k in range(limit)] if limit > 1 else [t0]
    kept_at = sorted({_nearest(ts, t) for t in [*targets, *cited_t]})
    kept_ts = [ts[i] for i in kept_at]
    frame_map = {frame_id: ordered[kept_at[_nearest(kept_ts, t)]][0] for frame_id, t in ordered}
    return Thinning([ordered[i][0] for i in kept_at], frame_map)
