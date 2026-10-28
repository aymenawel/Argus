"""Import a recorded video through the same pipeline as a live run (spec §4.2), in three stages:

1. scan (in a thread): decode every frame; the watcher looks at all of them for changes between samples;
   frames are sampled every `analysis_step_s` of run time (plus at changes), checked by the quality gate,
   calibrated and stored;
2. segment: one H.264 crop clip per vessel and concept goes to SAM in video mode (image mode on the
   vessel's crop, frame by frame, if video mode fails);
3. measure: each sample goes through the frame analyzer with the masks from stage 2.
"""

from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from argus.calibration.run import RulerInput, RunCalibration, calibrate, card_moved
from argus.capture.quality import assess
from argus.capture.video import VideoFileSource
from argus.domain import EventKind, RunStatus, Vessel, new_id
from argus.pipeline.analyzer import KeyedPatches, RunContext, Skipped, _write_jpeg, analyze_frame, segment_with_retries
from argus.rois import roi_box
from argus.segment import Clip, MaskPatch, SegmentResult
from argus.segment.tracking import assign_to_vessels
from argus.storage.repos import add_calibration, add_event, add_frame, set_run_status
from argus.watcher import Watcher, WatcherSettings

CROP_MARGIN_PX = 8
CLIP_FPS = 10
CROP_JPEG_QUALITY = 95


@dataclass(frozen=True)
class ImportRequest:
    paths: list[Path]
    time_scale: float
    print_check_mm: float | None = None
    ruler: RulerInput | None = None


@dataclass(frozen=True)
class _Sample:
    frame_id: str
    t: float
    path: Path
    flags: tuple[str, ...]


def _event(
    ctx: RunContext,
    t: float,
    kind: EventKind,
    source: str,
    detail: dict,
    *,
    vessel_id: str | None = None,
    frame_ids: Sequence[str] = (),
) -> None:
    event = add_event(
        ctx.db, ctx.run.id, vessel_id=vessel_id, t_start=t, kind=kind, source=source, detail=detail, frame_ids=frame_ids
    )
    ctx.publish("event", {"t": t, "id": event.id, "kind": str(kind), "vessel_id": vessel_id, "detail": detail})


def _scan(
    ctx: RunContext, request: ImportRequest, cancel: asyncio.Event, started: float
) -> tuple[list[_Sample], list[tuple[float, RunCalibration]]] | None:
    step = ctx.recipe.analysis_step_s
    # Between samples the watcher only looks for change; samples come on the clock, so no check-ins.
    settings = WatcherSettings(mode="smart_trigger", interval_s=step, cooldown_s=step, checkin_s=math.inf)
    watcher = Watcher(ctx.vessels, ctx.recipe.watcher, settings)
    samples: list[_Sample] = []
    calibrations: list[tuple[float, RunCalibration]] = []
    next_sample = 0.0
    previous_good: np.ndarray | None = None
    for frame in VideoFileSource(request.paths, time_scale=request.time_scale).frames():
        if cancel.is_set():
            return None
        changes = [trig for trig in watcher.observe(frame.t, frame.image) if trig.reason == "change"]
        due = frame.t >= next_sample - 1e-9
        if not due and not changes:
            continue
        while next_sample <= frame.t + 1e-9:
            next_sample += step
        for trig in changes:
            detail = {"ssim": round(trig.ssim or 0, 3), "colour_shift": round(trig.colour_shift or 0, 2)}
            _event(ctx, frame.t, EventKind.CHANGE, "watcher", detail, vessel_id=trig.vessel_id)
        report = assess(frame.image, ctx.vessels, previous_good=previous_good)
        if not report.ok:
            kind = EventKind.INTERVENTION if "occluded" in report.flags else EventKind.QUALITY
            _event(ctx, frame.t, kind, "quality", {"flags": list(report.flags), "blur": round(report.blur, 1)})
            continue
        previous_good = frame.image
        watcher.mark_analyzed(frame.t, frame.image)

        current = calibrations[-1][1] if calibrations else None
        moved = current is not None and card_moved(current, frame.image) is True
        if current is None or moved:
            cal = calibrate(frame.image, print_check_mm=request.print_check_mm, ruler=request.ruler)
            if cal is not None:
                calibrations.append((frame.t, cal))
                add_calibration(ctx.db, ctx.run.id, cal.to_draft(frame.t, {}))
                if moved:
                    _event(ctx, frame.t, EventKind.CAMERA_MOVED, "quality", {"message": "card moved: recalibrated"})

        frame_id = new_id("frm")
        path = ctx.files.frame_path(frame_id)
        _write_jpeg(path, frame.image)
        add_frame(
            ctx.db,
            ctx.run.id,
            frame.t,
            path.relative_to(ctx.settings.data_dir).as_posix(),
            report.flags,
            frame_id=frame_id,
        )
        samples.append(_Sample(frame_id, frame.t, path, report.flags))
        elapsed = max(time.perf_counter() - started, 1e-6)
        ctx.publish(
            "run_progress", {"stage": "scan", "t": frame.t, "t_end": None, "speed": round(frame.t / elapsed, 2)}
        )
    return samples, calibrations


def _write_clip(
    ctx: RunContext, vessel: Vessel, concept: str, chunk: Sequence[_Sample], index: int, box: tuple[int, int, int, int]
) -> Clip:
    """Crop the vessel's box from each sample, pad to even sides (yuv420p), and encode H.264 with ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is not on PATH; it is needed to send video to SAM")
    x0, y0, x1, y1 = box
    target = ctx.files.crop_path(vessel.label, concept)
    if index:
        target = target.with_name(f"{target.stem}-{index}{target.suffix}")
    folder = target.with_suffix("")
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    width, height = x1 - x0, y1 - y0
    for i, sample in enumerate(chunk):
        crop = cv2.imread(str(sample.path))[y0:y1, x0:x1]
        crop = cv2.copyMakeBorder(crop, 0, height % 2, 0, width % 2, cv2.BORDER_REPLICATE)
        cv2.imwrite(str(folder / f"{i:06d}.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, CROP_JPEG_QUALITY])
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(CLIP_FPS),
            "-i",
            str(folder / "%06d.jpg"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "12",
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(folder, ignore_errors=True)
    return Clip(target, len(chunk), width + width % 2, height + height % 2)


def _keep(
    ctx: RunContext, vessel: Vessel, concept: str, patches: list[MaskPatch], shape: tuple[int, int]
) -> list[tuple[str, MaskPatch]]:
    own = [patches[i] for i in assign_to_vessels(patches, [vessel], shape)[vessel.id]]
    return list(zip(ctx.matcher.match(vessel, concept, own), own, strict=True))


async def _segment_vessel(
    ctx: RunContext,
    samples: list[_Sample],
    vessel: Vessel,
    concept: str,
    shape: tuple[int, int],
    masks: dict[str, dict[str, dict]],
) -> None:
    box = roi_box(vessel, *shape, margin=CROP_MARGIN_PX)
    x0, y0, x1, y1 = box
    size = ctx.settings.sam_max_video_frames
    for index, start in enumerate(range(0, len(samples), size)):
        chunk = samples[start : start + size]
        clip = await asyncio.to_thread(_write_clip, ctx, vessel, concept, chunk, index, box)
        result = await segment_with_retries(ctx, clip, concept, t=chunk[0].t, frame_ids=[s.frame_id for s in chunk])
        if isinstance(result, SegmentResult):
            per_frame: dict[int, list[MaskPatch]] = {i: [] for i in range(len(chunk))}
            for track in result.tracks:
                for frame in track.frames:
                    if frame.index in per_frame:
                        per_frame[frame.index].append(frame.patch.shifted(x0, y0))
            for i, sample in enumerate(chunk):
                masks[sample.frame_id].setdefault(vessel.id, {})[concept] = _keep(
                    ctx, vessel, concept, per_frame[i], shape
                )
            continue
        if result.reason == "cap":
            return
        for sample in chunk:  # video mode failed: image mode on the vessel's crop, frame by frame
            crop = (await asyncio.to_thread(cv2.imread, str(sample.path)))[y0:y1, x0:x1]
            single = await segment_with_retries(ctx, crop, concept, t=sample.t, frame_ids=[sample.frame_id])
            if isinstance(single, Skipped):
                if single.reason == "cap":
                    return
                continue
            patches = [track.frames[0].patch.shifted(x0, y0) for track in single.tracks]
            masks[sample.frame_id].setdefault(vessel.id, {})[concept] = _keep(ctx, vessel, concept, patches, shape)


def _finish(ctx: RunContext, status: RunStatus) -> RunStatus:
    set_run_status(ctx.db, ctx.run.id, status)
    ctx.publish("run_status", {"status": str(status)})
    return status


async def run_import(ctx: RunContext, request: ImportRequest, *, cancel: asyncio.Event) -> RunStatus:
    started = time.perf_counter()
    scanned = await asyncio.to_thread(_scan, ctx, request, cancel, started)
    if scanned is None or cancel.is_set():
        return await asyncio.to_thread(_finish, ctx, RunStatus.STOPPED)
    samples, calibrations = scanned
    if not samples:
        return await asyncio.to_thread(_finish, ctx, RunStatus.FINISHED)

    masks: dict[str, dict[str, dict]] = {s.frame_id: {} for s in samples}
    if calibrations:  # without millimetres there is nothing to segment for
        shape = (await asyncio.to_thread(cv2.imread, str(samples[0].path))).shape[:2]
        jobs = [(v, c.name) for v in ctx.vessels for c in ctx.recipe.concepts]
        done = 0

        async def job(vessel: Vessel, concept: str) -> None:
            nonlocal done
            await _segment_vessel(ctx, samples, vessel, concept, shape, masks)
            done += 1
            ctx.publish("run_progress", {"stage": "segment", "done": done, "total": len(jobs)})

        await asyncio.gather(*(job(v, c) for v, c in jobs))
        if cancel.is_set():
            return await asyncio.to_thread(_finish, ctx, RunStatus.STOPPED)

    t0, t_end = samples[0].t, samples[-1].t
    for sample in samples:
        if cancel.is_set():
            return await asyncio.to_thread(_finish, ctx, RunStatus.STOPPED)
        in_force = [cal for t, cal in calibrations if t <= sample.t]
        ctx.calibration = in_force[-1] if in_force else None
        image = await asyncio.to_thread(cv2.imread, str(sample.path))
        frame_masks: KeyedPatches = masks[sample.frame_id]
        await analyze_frame(
            ctx, sample.t, image, frame_id=sample.frame_id, segment=False, masks=frame_masks, quality_flags=sample.flags
        )
        elapsed = max(time.perf_counter() - started, 1e-6)
        ctx.publish(
            "run_progress",
            {"stage": "measure", "t": sample.t, "t_end": t_end, "speed": round((sample.t - t0) / elapsed, 2)},
        )
    return await asyncio.to_thread(_finish, ctx, RunStatus.FINISHED)
