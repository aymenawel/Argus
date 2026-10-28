"""Live runs (spec §4.1) and the camera hub, the worker's single owner of webcams.

Cadence (D-56): every frame (at most 5 per second) goes through the quality gate and the watcher; every
`analysis_step_s` a frame is stored and its colour measured on the newest masks; SAM runs on the watcher's
first, change, check-in and tick triggers, never sooner than `segment_interval_s` after the last segmentation,
because a call takes seconds. A hand in the scene logs an intervention and pauses measuring until it leaves.
"""

from __future__ import annotations

import asyncio
import math
import threading
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import cv2
import numpy as np

from argus.calibration.run import RulerInput, calibrate, card_moved
from argus.capture.quality import DEFAULT_THRESHOLDS, REBASELINED, QualityGate, QualityThresholds
from argus.capture.webcam import CameraSettings, open_webcam
from argus.domain import CameraProperty, EventKind, RunStatus
from argus.pipeline.analyzer import RunContext, analyze_frame
from argus.pipeline.moves import after_card_moved
from argus.storage.repos import add_calibration, set_run_status
from argus.watcher import Watcher

EPSILON_S = 1e-6  # sums of frame intervals land a hair under the step (0.2 x 25 = 4.9999...)
SEGMENT_REASONS = frozenset({"first", "change", "checkin", "tick"})


class FrameSource(Protocol):
    def read(self) -> np.ndarray | None: ...

    def close(self) -> None: ...


class _Camera:
    """One open webcam with a thread that keeps reading, so the newest frame is always at hand. Frames are
    numbered, so a camera that stops delivering is noticed instead of its last frame being reused."""

    def __init__(self, capture: Any, properties: dict[str, CameraProperty]) -> None:
        self.capture, self.properties, self.refs = capture, properties, 0
        self._frame: np.ndarray | None = None
        self._seq, self._at = 0, 0.0  # the newest frame's number and when it arrived (monotonic)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if ok and frame is not None:
                with self._lock:
                    self._frame, self._seq, self._at = frame, self._seq + 1, time.monotonic()
            time.sleep(0.001 if ok else 0.05)

    def latest(self, *, after: int = 0, max_age_s: float = math.inf) -> tuple[int, np.ndarray] | None:
        """The newest frame and its number, if it is newer than frame `after` and younger than `max_age_s`."""
        with self._lock:
            if self._frame is None or self._seq <= after or time.monotonic() - self._at > max_age_s:
                return None
            return self._seq, self._frame.copy()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.capture.release()


class _HubSource:
    def __init__(self, hub: CameraHub, index: int) -> None:
        self.hub, self.index, self._closed, self._seq = hub, index, False, 0

    def read(self) -> np.ndarray | None:
        """The next new frame; None when none arrives within the hub's `stale_after_s` (the camera is lost)."""
        deadline = time.monotonic() + self.hub.stale_after_s
        while time.monotonic() < deadline:
            camera = self.hub._cameras.get(self.index)
            newest = camera.latest(after=self._seq) if camera else None
            if newest is not None:
                self._seq, frame = newest
                return frame
            time.sleep(0.02)
        return None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.hub.release(self.index)


class CameraHub:
    """Shares each webcam between previews and runs; it is opened once and closed when nobody uses it."""

    def __init__(
        self,
        *,
        opener: Callable[[int, CameraSettings], tuple[Any, dict[str, CameraProperty]]] = open_webcam,
        stale_after_s: float = 3.0,
    ) -> None:
        self._opener, self.stale_after_s = opener, stale_after_s
        self._cameras: dict[int, _Camera] = {}
        self._lock = threading.Lock()

    def acquire(
        self, index: int, settings: CameraSettings | None = None
    ) -> tuple[FrameSource, dict[str, CameraProperty]]:
        with self._lock:
            camera = self._cameras.get(index)
            if camera is None:
                capture, properties = self._opener(index, settings or CameraSettings())
                camera = self._cameras[index] = _Camera(capture, properties)
            camera.refs += 1
        return _HubSource(self, index), camera.properties

    def release(self, index: int) -> None:
        with self._lock:
            camera = self._cameras.get(index)
            if camera is None:
                return
            camera.refs -= 1
            if camera.refs > 0:
                return
            del self._cameras[index]
        camera.close()

    def open_indexes(self) -> list[int]:
        with self._lock:
            return sorted(self._cameras)

    def latest_jpeg(self, index: int, quality: int = 80) -> bytes | None:
        camera = self._cameras.get(index)
        newest = camera.latest(max_age_s=self.stale_after_s) if camera else None
        if newest is None:
            return None
        ok, encoded = cv2.imencode(".jpg", newest[1], [cv2.IMWRITE_JPEG_QUALITY, quality])
        return encoded.tobytes() if ok else None

    def close_all(self) -> None:
        with self._lock:
            cameras, self._cameras = list(self._cameras.values()), {}
        for camera in cameras:
            camera.close()


async def _follow_the_card(
    ctx: RunContext,
    gate: QualityGate,
    watcher: Watcher,
    watching: asyncio.Lock,
    t: float,
    image: np.ndarray,
    *,
    camera_moved: bool,
    print_check_mm: float | None,
    ruler: RulerInput | None,
    camera_properties: dict[str, CameraProperty],
) -> bool:
    """Recalibrates when the card moved (and moves the vessels' regions when the camera did). Whether it did."""
    old = ctx.calibration
    if old is None or await asyncio.to_thread(card_moved, old, image) is not True:
        return False
    new = await asyncio.to_thread(calibrate, image, print_check_mm=print_check_mm, ruler=ruler)
    if new is None:
        return False
    vessels, detail = after_card_moved(ctx.vessels, old, new, camera_moved=camera_moved)
    if "rois" in detail:
        ctx.vessels = gate.vessels = vessels
        ctx.last_masks.clear()  # the old masks sit where the vessels used to be
        async with watching:
            watcher.follow(vessels)
    ctx.calibration = new
    await asyncio.to_thread(add_calibration, ctx.db, ctx.run.id, new.to_draft(t, camera_properties))
    await ctx.event(t, EventKind.CAMERA_MOVED, "quality", detail)
    return True


async def run_live(
    ctx: RunContext,
    source: FrameSource,
    watcher: Watcher,
    *,
    cancel: asyncio.Event,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    print_check_mm: float | None = None,
    ruler: RulerInput | None = None,
    camera_properties: dict[str, CameraProperty] | None = None,
    max_fps: float = 5.0,
    quality: QualityThresholds = DEFAULT_THRESHOLDS,
) -> RunStatus:
    """Runs until Stop (cancel) or until the source stops delivering frames. The caller closes the source.

    Capture never waits on the network (spec §4.3): frames are analyzed in background tasks, at most one of them
    segmenting. A segmentation that can't start yet (no calibration, one still in flight, too soon after the last)
    is owed, not dropped.
    """
    step, interval = ctx.recipe.analysis_step_s, ctx.settings.segment_interval_s
    properties = camera_properties or {}
    t0: float | None = None
    last_store = last_segment = -math.inf
    gate = QualityGate(ctx.vessels, quality)
    watching = asyncio.Lock()  # the watcher is read in a worker thread and updated when a segmentation lands
    pending: set[asyncio.Task] = set()
    segmenting: asyncio.Task | None = None
    owed = scene_moved = False
    in_trouble: set[str] = set()  # quality problems already reported, until a good frame clears them
    t = 0.0

    async def analyze(t: float, image: np.ndarray, segment: bool, flags: tuple[str, ...]) -> None:
        outcome = await analyze_frame(ctx, t, image, segment=segment, quality_flags=flags)
        if segment and outcome.segmented:
            async with watching:
                await asyncio.to_thread(watcher.mark_analyzed, t, image)

    try:
        while not cancel.is_set():
            for task in [task for task in pending if task.done()]:
                pending.discard(task)
                task.result()  # an analysis that crashed ends the run, as it would inline
            image = await asyncio.to_thread(source.read)
            if image is None:
                await ctx.event(t, EventKind.INTERRUPTED, "pipeline", {"reason": "camera_lost"})
                break
            if t0 is None:
                t0 = clock()
            t = clock() - t0
            report = await asyncio.to_thread(gate.check, t, image)
            if not report.ok:
                problem = "occluded" if "occluded" in report.flags else "blurred"
                if problem not in in_trouble:
                    in_trouble.add(problem)
                    kind = EventKind.INTERVENTION if problem == "occluded" else EventKind.QUALITY
                    await ctx.event(t, kind, "quality", {"flags": list(report.flags), "blur": round(report.blur, 1)})
                await sleep(1 / max_fps)
                continue
            in_trouble.clear()
            if "rebaselined" in report.flags:
                scene_moved = True
                await ctx.event(t, EventKind.QUALITY, "quality", {"flags": list(report.flags), "message": REBASELINED})

            due = t - last_store >= step - EPSILON_S
            if ctx.calibration is None:
                cal = await asyncio.to_thread(calibrate, image, print_check_mm=print_check_mm, ruler=ruler)
                if cal is not None:
                    ctx.calibration = cal
                    await asyncio.to_thread(add_calibration, ctx.db, ctx.run.id, cal.to_draft(t, properties))
            elif due or scene_moved:
                moved = await _follow_the_card(
                    ctx,
                    gate,
                    watcher,
                    watching,
                    t,
                    image,
                    camera_moved=scene_moved,
                    print_check_mm=print_check_mm,
                    ruler=ruler,
                    camera_properties=properties,
                )
                owed, scene_moved = owed or moved, False

            async with watching:
                triggers = await asyncio.to_thread(watcher.observe, t, image)
            for trig in triggers:
                if trig.reason == "change":
                    detail = {"ssim": round(trig.ssim or 0, 3), "colour_shift": round(trig.colour_shift or 0, 2)}
                    await ctx.event(t, EventKind.CHANGE, "watcher", detail, vessel_id=trig.vessel_id)
            owed = owed or any(trig.reason in SEGMENT_REASONS for trig in triggers)
            free = segmenting is None or segmenting.done()
            wants_segment = owed and free and ctx.calibration is not None and t - last_segment >= interval - EPSILON_S
            if wants_segment or due:
                task = asyncio.create_task(analyze(t, image, wants_segment, report.flags))
                pending.add(task)
                last_store = t
                if wants_segment:
                    owed, last_segment, segmenting = False, t, task
            await sleep(1 / max_fps)
        await asyncio.gather(*pending)  # what was captured is analyzed before the run ends
    except BaseException:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        raise
    await asyncio.to_thread(set_run_status, ctx.db, ctx.run.id, RunStatus.STOPPED)
    ctx.publish("run_status", {"status": str(RunStatus.STOPPED)})
    return RunStatus.STOPPED
