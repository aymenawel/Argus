"""Keyframe comparison per vessel (KB 03): each vessel's ROI is compared with the last *analyzed* frame, not
the previous one, so slow change adds up until it crosses a threshold.

Two light-normalized signals:
- structure: SSIM of the ROI's grey levels after z-scoring (immune to brightness gain and offset; with
  strong normalization each tile of a 4 x 4 grid is z-scored on its own, for uneven light);
- colour: the ROI's mean rg-chromaticity relative to the scene outside every vessel, in percentage points
  (immune to brightness gain and to a lamp of another colour; a vessel changing colour doesn't move the
  others' signal, as it would if the reference included the vessels).
A change must last `debounce` observations, then the vessel rests for `cooldown_s`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np
from skimage.metrics import structural_similarity

from argus.domain import Vessel
from argus.recipes.model import Recipe, WatcherSpec
from argus.rois import roi_box, roi_mask

Mode = Literal["continuous", "smart_trigger", "hybrid"]
TILES = 4


@dataclass(frozen=True)
class WatcherSettings:
    mode: Mode
    interval_s: float
    ssim_min: float = 0.90
    colour_shift_max: float = 1.5  # rg-chromaticity, percentage points, relative to the scene outside the vessels
    debounce: int = 3
    cooldown_s: float = 60.0
    checkin_s: float = 3600.0
    hybrid_active_s: float = 120.0
    roi_max_px: int = 256

    @classmethod
    def from_recipe(cls, recipe: Recipe) -> WatcherSettings:
        return cls(mode=recipe.default_mode, interval_s=recipe.analysis_step_s)


@dataclass(frozen=True)
class Trigger:
    vessel_id: str | None
    reason: Literal["first", "change", "checkin", "tick"]
    ssim: float | None = None
    colour_shift: float | None = None


@dataclass(frozen=True)
class _Signature:
    grey: np.ndarray  # z-scored, float32
    chroma: np.ndarray  # (r, g) chromaticity minus the scene's outside the vessels, in percentage points


def _chromaticity(bgr: np.ndarray, where: np.ndarray | None = None) -> np.ndarray:
    pixels = bgr.reshape(-1, 3) if where is None else bgr[where]
    means = pixels.astype(np.float64).mean(axis=0)
    total = means.sum() or 1.0
    return np.array([means[2] / total, means[1] / total]) * 100.0


def _zscore(grey: np.ndarray, tiles: int) -> np.ndarray:
    out = np.empty_like(grey, dtype=np.float32)
    rows = np.array_split(np.arange(grey.shape[0]), tiles)
    cols = np.array_split(np.arange(grey.shape[1]), tiles)
    for r in rows:
        for c in cols:
            block = grey[r[0] : r[-1] + 1, c[0] : c[-1] + 1].astype(np.float32)
            out[r[0] : r[-1] + 1, c[0] : c[-1] + 1] = (block - block.mean()) / (block.std() + 1e-6)
    return out


class Watcher:
    def __init__(self, vessels: Sequence[Vessel], spec: WatcherSpec, settings: WatcherSettings) -> None:
        self.vessels = list(vessels)
        self.spec = spec
        self.settings = settings
        self._keyframes: dict[str, _Signature] = {}
        self._streak = {v.id: 0 for v in self.vessels}
        self._last_change: dict[str, float] = {}
        self._last_change_any = -math.inf
        self._last_analyzed = 0.0
        self._last_checkin = 0.0
        self._last_tick = 0.0
        self._started = False
        self._outside: tuple[tuple[int, int], np.ndarray | None] | None = None

    def _outside_vessels(self, height: int, width: int, small: tuple[int, int]) -> np.ndarray | None:
        """The scene outside every ROI at the small size; None (use the whole frame) when the vessels fill it."""
        if self._outside is None or self._outside[0] != (height, width):
            inside = np.zeros((height, width), np.uint8)
            for vessel in self.vessels:
                inside |= roi_mask(vessel, height, width).astype(np.uint8)
            outside = cv2.resize(inside, small, interpolation=cv2.INTER_NEAREST) == 0
            self._outside = ((height, width), outside if outside.mean() >= 0.02 else None)
        return self._outside[1]

    def _signatures(self, image_bgr: np.ndarray) -> dict[str, _Signature]:
        height, width = image_bgr.shape[:2]
        size = (max(width // 4, 1), max(height // 4, 1))
        small = cv2.resize(image_bgr, size, interpolation=cv2.INTER_AREA)
        frame_chroma = _chromaticity(small, self._outside_vessels(height, width, size))
        tiles = TILES if self.spec.light_normalization == "strong" else 1
        signatures = {}
        for vessel in self.vessels:
            x0, y0, x1, y1 = roi_box(vessel, height, width)
            crop = image_bgr[y0:y1, x0:x1]
            scale = self.settings.roi_max_px / max(crop.shape[:2])
            if scale < 1:
                crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            grey = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            signatures[vessel.id] = _Signature(_zscore(grey, tiles), _chromaticity(crop) - frame_chroma)
        return signatures

    def mark_analyzed(self, t: float, image_bgr: np.ndarray) -> None:
        """This frame was analyzed: it becomes every vessel's keyframe."""
        self._keyframes = self._signatures(image_bgr)
        self._last_analyzed = t
        self._streak = {v.id: 0 for v in self.vessels}

    def _compare(self, key: _Signature, now: _Signature) -> tuple[float, float]:
        low = min(float(key.grey.min()), float(now.grey.min()))
        high = max(float(key.grey.max()), float(now.grey.max()))
        ssim = float(structural_similarity(key.grey, now.grey, data_range=max(high - low, 1e-6)))
        shift = float(np.linalg.norm(now.chroma - key.chroma))
        return ssim, shift

    def observe(self, t: float, image_bgr: np.ndarray) -> list[Trigger]:
        s = self.settings
        if not self._started:
            self._started = True
            self.mark_analyzed(t, image_bgr)
            self._last_checkin = self._last_tick = t
            return [Trigger(None, "first")]

        triggers: list[Trigger] = []
        if s.mode != "continuous":
            for vessel_id, now in self._signatures(image_bgr).items():
                ssim, shift = self._compare(self._keyframes[vessel_id], now)
                changed = ("ssim" in self.spec.signals and ssim < s.ssim_min) or (
                    "colour" in self.spec.signals and shift > s.colour_shift_max
                )
                self._streak[vessel_id] = self._streak[vessel_id] + 1 if changed else 0
                rested = t - self._last_change.get(vessel_id, -math.inf) >= s.cooldown_s
                if self._streak[vessel_id] >= s.debounce and rested:
                    triggers.append(Trigger(vessel_id, "change", ssim, shift))
                    self._last_change[vessel_id] = self._last_change_any = t
                    self._streak[vessel_id] = 0

        ticking = s.mode == "continuous" or (s.mode == "hybrid" and t - self._last_change_any <= s.hybrid_active_s)
        if triggers:
            self._last_tick = t
        elif ticking and t - self._last_tick >= s.interval_s:
            triggers.append(Trigger(None, "tick"))
            self._last_tick = t
        elif (
            s.mode != "continuous" and t - self._last_analyzed >= s.checkin_s and t - self._last_checkin >= s.checkin_s
        ):
            triggers.append(Trigger(None, "checkin"))
            self._last_checkin = t
        return triggers
