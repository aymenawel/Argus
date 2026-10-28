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

from argus.calibration.run import RulerInput, calibrate
from argus.capture.quality import assess
from argus.capture.webcam import CameraSettings, open_webcam
from argus.domain import CameraProperty, EventKind, RunStatus
from argus.pipeline.analyzer import RunContext, analyze_frame
from argus.storage.repos import add_calibration, set_run_status
from argus.watcher import Watcher

EPSILON_S = 1e-6  # sums of frame intervals land a hair under the step (0.2 x 25 = 4.9999...)
SEGMENT_REASONS = frozenset({"first", "change", "checkin", "tick"})


class FrameSource(Protocol):
    def read(self) -> np.ndarray | None: ...

    def close(self) -> None: ...


class _Camera:
    """One open webcam with a thread that keeps reading, so the newest frame is always at hand."""

    def __init__(self, capture: Any, properties: dict[str, CameraProperty]) -> None:
        self.capture, self.properties, self.refs = capture, properties, 0
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok, frame = self.capture.read()
            if ok and frame is not None:
                with self._lock:
                    self._frame = frame
            time.sleep(0.001 if ok else 0.05)

    def latest(self) -> np.ndarray | None:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.capture.release()


class _HubSource:
    def __init__(self, hub: CameraHub, index: int) -> None:
        self.hub, self.index, self._closed = hub, index, False

    def read(self) -> np.ndarray | None:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            camera = self.hub._cameras.get(self.index)
            frame = camera.latest() if camera else None
            if frame is not None:
                return frame
            time.sleep(0.02)
        return None  # the camera stopped delivering frames

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self.hub.release(self.index)


class CameraHub:
    """Shares each webcam between previews and runs; it is opened once and closed when nobody uses it."""

    def __init__(
        self, *, opener: Callable[[int, CameraSettings], tuple[Any, dict[str, CameraProperty]]] = open_webcam
    ) -> None:
        self._opener = opener
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

    def latest_jpeg(self, index: int, quality: int = 80) -> bytes | None:
        camera = self._cameras.get(index)
        frame = camera.latest() if camera else None
        if frame is None:
            return None
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return encoded.tobytes() if ok else None

    def close_all(self) -> None:
        with self._lock:
            cameras, self._cameras = list(self._cameras.values()), {}
        for camera in cameras:
            camera.close()


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
) -> RunStatus:
    """Runs until Stop (cancel) or until the source stops delivering frames. The caller closes the source."""
    step, interval = ctx.recipe.analysis_step_s, ctx.settings.segment_interval_s
    t0: float | None = None
    last_store = last_segment = -math.inf
    previous_good: np.ndarray | None = None
    in_trouble: set[str] = set()  # quality problems already reported, until a good frame clears them
    while not cancel.is_set():
        image = await asyncio.to_thread(source.read)
        if image is None:
            break
        if t0 is None:
            t0 = clock()
        t = clock() - t0
        report = await asyncio.to_thread(assess, image, ctx.vessels, previous_good=previous_good)
        if not report.ok:
            problem = "occluded" if "occluded" in report.flags else "blurred"
            if problem not in in_trouble:
                in_trouble.add(problem)
                kind = EventKind.INTERVENTION if problem == "occluded" else EventKind.QUALITY
                await ctx.event(t, kind, "quality", {"flags": list(report.flags), "blur": round(report.blur, 1)})
            await sleep(1 / max_fps)
            continue
        in_trouble.clear()
        previous_good = image

        if ctx.calibration is None:
            cal = await asyncio.to_thread(calibrate, image, print_check_mm=print_check_mm, ruler=ruler)
            if cal is not None:
                ctx.calibration = cal
                draft = cal.to_draft(t, camera_properties or {})
                await asyncio.to_thread(add_calibration, ctx.db, ctx.run.id, draft)

        triggers = await asyncio.to_thread(watcher.observe, t, image)
        for trig in triggers:
            if trig.reason == "change":
                detail = {"ssim": round(trig.ssim or 0, 3), "colour_shift": round(trig.colour_shift or 0, 2)}
                await ctx.event(t, EventKind.CHANGE, "watcher", detail, vessel_id=trig.vessel_id)
        wants_segment = any(trig.reason in SEGMENT_REASONS for trig in triggers) and (
            t - last_segment >= interval - EPSILON_S
        )
        if wants_segment or t - last_store >= step - EPSILON_S:
            outcome = await analyze_frame(ctx, t, image, segment=wants_segment, quality_flags=report.flags)
            last_store = t
            if wants_segment:
                last_segment = t
                if outcome.segmented:
                    watcher.mark_analyzed(t, image)
        await sleep(1 / max_fps)
    await asyncio.to_thread(set_run_status, ctx.db, ctx.run.id, RunStatus.STOPPED)
    ctx.publish("run_status", {"status": str(RunStatus.STOPPED)})
    return RunStatus.STOPPED
