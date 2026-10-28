"""One frame through segmentation, tracking, measurement and storage (spec §4.1 steps 4-7, §4.3).

Shared by the live and import pipelines. A segmentation that fails (after retries) or is refused by the spend
cap leaves a gap, never a zero: zero is stored only when SAM answered and found nothing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

import cv2
import numpy as np

from argus.api.events import EventBroker
from argus.calibration.colour import ColourReference, neutral_drift, read_patches
from argus.calibration.detect import detect_card
from argus.calibration.run import RunCalibration
from argus.config import Settings
from argus.domain import Detection, EventKind, MeasurementDraft, Run, Vessel, new_id
from argus.measure.engine import ColourBaseline, measure_vessel
from argus.measure.uncertainty import format_measurement
from argus.recipes.model import Recipe
from argus.segment import Clip, MaskPatch, SegmentError, SegmentResult, segment
from argus.segment.outline import outline_polygons
from argus.segment.tracking import TrackMatcher, assign_to_vessels
from argus.storage.db import Database
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_detection_rows,
    add_event,
    add_frame,
    add_measurements,
    add_model_call,
    mark_frame_analyzed,
    run_spend_usd,
)

JPEG_QUALITY = 90
COLOUR_DRIFT_MAX = 6.0  # dE00 of the card's neutral patches beyond which correction is no longer trusted
GEOMETRY = frozenset({"size", "count"})
COLOUR = frozenset({"colour"})

KeyedPatches = Mapping[str, Mapping[str, Sequence[tuple[str, MaskPatch]]]]  # vessel id -> concept -> patches


class Segmenter(Protocol):
    async def image(self, image_bgr: np.ndarray, concept: str) -> SegmentResult: ...

    async def video(self, clip: Clip, concept: str) -> SegmentResult: ...


class SamSegmenter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def image(self, image_bgr: np.ndarray, concept: str) -> SegmentResult:
        return await segment(image_bgr, concept, mode="image", settings=self.settings)

    async def video(self, clip: Clip, concept: str) -> SegmentResult:
        return await segment(clip, concept, mode="video", settings=self.settings)


@dataclass
class RunContext:
    db: Database
    broker: EventBroker
    settings: Settings
    files: RunFiles
    recipe: Recipe
    run: Run
    vessels: list[Vessel]
    segmenter: Segmenter
    calibration: RunCalibration | None = None
    matcher: TrackMatcher = field(default_factory=TrackMatcher)
    last_masks: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    baselines: dict[str, dict[str, ColourBaseline]] = field(default_factory=dict)
    retry_delays_s: tuple[float, ...] = (1.0, 4.0)
    cap_reported: bool = False
    calibration_reported: bool = False
    drift_reported: bool = False
    semaphore: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self.semaphore = asyncio.Semaphore(self.settings.sam_concurrency)

    def publish(self, kind: str, data: dict) -> None:
        self.broker.publish(kind, {"run_id": self.run.id, **data})

    async def event(
        self,
        t: float,
        kind: EventKind,
        source: str,
        detail: dict,
        *,
        vessel_id: str | None = None,
        frame_ids: Sequence[str] = (),
    ) -> None:
        event = await asyncio.to_thread(
            add_event,
            self.db,
            self.run.id,
            vessel_id=vessel_id,
            t_start=t,
            kind=kind,
            source=source,
            detail=detail,
            frame_ids=frame_ids,
        )
        self.publish("event", {"t": t, "id": event.id, "kind": str(kind), "vessel_id": vessel_id, "detail": detail})


@dataclass(frozen=True)
class Skipped:
    """No segmentation: the spend cap refused the call, or every attempt failed."""

    reason: Literal["cap", "failed"]


@dataclass(frozen=True)
class AnalysisOutcome:
    frame_id: str
    segmented: bool
    measurements: int
    failed_concepts: list[str]


def _expected_cost(settings: Settings, media: np.ndarray | Clip) -> float:
    if isinstance(media, np.ndarray):
        return settings.sam_image_usd
    return max(media.frame_count, settings.sam_video_min_frames) * settings.sam_video_frame_usd


async def segment_with_retries(
    ctx: RunContext, media: np.ndarray | Clip, concept: str, *, t: float, frame_ids: Sequence[str] = ()
) -> SegmentResult | Skipped:
    """Every attempt is logged. Skipped("cap") when the spend cap refuses the call, Skipped("failed") when every
    attempt failed (with a segment_failed event)."""
    attempts = 1 + len(ctx.retry_delays_s)
    error = ""
    for attempt in range(attempts):
        spent = await asyncio.to_thread(run_spend_usd, ctx.db, ctx.run.id)
        cap = ctx.settings.run_spend_cap_usd
        if spent + _expected_cost(ctx.settings, media) > cap:
            if not ctx.cap_reported:
                ctx.cap_reported = True
                detail = {"spent_usd": round(spent, 4), "cap_usd": cap, "message": "segmentation paused: spend cap"}
                await ctx.event(t, EventKind.SPEND, "pipeline", detail)
                ctx.publish("spend", {"t": t, "spent_usd": round(spent, 4), "cap_usd": cap})
            return Skipped("cap")
        try:
            async with ctx.semaphore:
                if isinstance(media, np.ndarray):
                    result = await ctx.segmenter.image(media, concept)
                else:
                    result = await ctx.segmenter.video(media, concept)
        except SegmentError as failure:
            error = str(failure)
            await asyncio.to_thread(add_model_call, ctx.db, ctx.run.id, t, failure.call)
            if attempt < attempts - 1:
                await asyncio.sleep(ctx.retry_delays_s[attempt])
            continue
        await asyncio.to_thread(add_model_call, ctx.db, ctx.run.id, t, result.call)
        return result
    detail = {"concept": concept, "attempts": attempts, "error": error}
    await ctx.event(t, EventKind.SEGMENT_FAILED, "pipeline", detail, frame_ids=frame_ids)
    return Skipped("failed")


def _write_jpeg(path, image_bgr: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image_bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]):
        raise OSError(f"could not write {path}")


def _store_detections(
    ctx: RunContext,
    frame_id: str,
    keyed: Mapping[str, Mapping[str, Sequence[tuple[str, MaskPatch]]]],
    confidence: Mapping[int, float | None],
    backend: str,
) -> list[Detection]:
    rows = []
    for vessel_id, by_concept in keyed.items():
        for concept, patches in by_concept.items():
            for key, patch in patches:
                detection_id = new_id("det")
                mask_path = ctx.files.mask_path(detection_id)
                cv2.imwrite(str(mask_path), patch.mask.astype(np.uint8) * 255)
                rows.append(
                    Detection(
                        id=detection_id,
                        frame_id=frame_id,
                        vessel_id=vessel_id,
                        track_key=key,
                        concept=concept,
                        outline=outline_polygons(patch),
                        bbox=patch.bbox,
                        area_px=patch.area_px,
                        confidence=confidence.get(id(patch)),
                        backend=backend,
                        mask_path=mask_path.relative_to(ctx.settings.data_dir).as_posix(),
                    )
                )
    return add_detection_rows(ctx.db, rows)


def _union(patches: Sequence[tuple[str, MaskPatch]], shape: tuple[int, int]) -> np.ndarray:
    canvas = np.zeros(shape, bool)
    for _, patch in patches:
        canvas |= patch.to_canvas(*shape)
    return canvas


async def _colour_reference(ctx: RunContext, t: float, image_bgr: np.ndarray, frame_id: str) -> ColourReference | None:
    cal = ctx.calibration
    if cal is None or cal.detection is None or cal.reference is None:
        return None
    card = await asyncio.to_thread(detect_card, image_bgr, (cal.detection.spec,))
    if card is None:
        return None
    current = await asyncio.to_thread(read_patches, image_bgr, card)
    drift = neutral_drift(cal.reference, current)
    if drift is None:
        return None
    if drift > COLOUR_DRIFT_MAX:
        if not ctx.drift_reported:
            ctx.drift_reported = True
            await ctx.event(t, EventKind.QUALITY, "quality", {"colour_drift": round(drift, 2)}, frame_ids=[frame_id])
        return None  # beyond correction: colour stays uncorrected rather than wrongly corrected
    ctx.drift_reported = False
    return current


async def analyze_frame(
    ctx: RunContext,
    t: float,
    image_bgr: np.ndarray,
    *,
    frame_id: str | None = None,
    segment: bool,
    masks: KeyedPatches | None = None,
    quality_flags: Sequence[str] = (),
) -> AnalysisOutcome:
    shape = image_bgr.shape[:2]
    if frame_id is None:
        frame_id = new_id("frm")
        path = ctx.files.frame_path(frame_id)
        await asyncio.to_thread(_write_jpeg, path, image_bgr)
        relative = path.relative_to(ctx.settings.data_dir).as_posix()
        await asyncio.to_thread(add_frame, ctx.db, ctx.run.id, t, relative, quality_flags, frame_id=frame_id)

    if ctx.calibration is None:
        if not ctx.calibration_reported:
            ctx.calibration_reported = True
            detail = {"message": "no Argus Card or ruler: frames are recorded, nothing is measured"}
            await ctx.event(t, EventKind.NO_CALIBRATION, "pipeline", detail, frame_ids=[frame_id])
        await asyncio.to_thread(mark_frame_analyzed, ctx.db, frame_id)
        ctx.publish("frame_analyzed", {"frame_id": frame_id, "t": t, "quality_flags": list(quality_flags)})
        return AnalysisOutcome(frame_id, False, 0, [])

    current_reference = await _colour_reference(ctx, t, image_bgr, frame_id)

    # Segmentation: injected (video mode) or one image call per concept.
    keyed: dict[str, dict[str, list[tuple[str, MaskPatch]]]] = {}
    confidence: dict[int, float | None] = {}
    segmented_concepts: set[str] = set()
    failed: list[str] = []
    backend = "sam-3.1/video"
    if masks is not None:
        for vessel_id, by_concept in masks.items():
            for concept, patches in by_concept.items():
                keyed.setdefault(vessel_id, {})[concept] = list(patches)
                segmented_concepts.add(concept)
    elif segment:
        backend = "sam-3.1/image"
        for concept in (c.name for c in ctx.recipe.concepts):
            result = await segment_with_retries(ctx, image_bgr, concept, t=t, frame_ids=[frame_id])
            if isinstance(result, Skipped):
                if result.reason == "failed":  # a call the spend cap refused isn't a failure of SAM
                    failed.append(concept)
                continue
            patches = [track.frames[0].patch for track in result.tracks]
            for track in result.tracks:
                confidence[id(track.frames[0].patch)] = track.frames[0].confidence
            assignment = assign_to_vessels(patches, ctx.vessels, shape)
            for vessel in ctx.vessels:
                own = [patches[i] for i in assignment[vessel.id]]
                keys = ctx.matcher.match(vessel, concept, own)
                keyed.setdefault(vessel.id, {})[concept] = list(zip(keys, own, strict=True))
            segmented_concepts.add(concept)
    if keyed:
        await asyncio.to_thread(_store_detections, ctx, frame_id, keyed, confidence, backend)
    for vessel_id, by_concept in keyed.items():
        for concept, patches in by_concept.items():
            ctx.last_masks.setdefault(vessel_id, {})[concept] = _union(patches, shape)

    # Measurement: geometry only for concepts segmented on this frame; colour on the newest masks there are.
    geometry_recipe = ctx.recipe.model_copy(
        update={"measurements": [m for m in ctx.recipe.measurements if m.source in segmented_concepts]}
    )
    drafts: list[MeasurementDraft] = []
    for vessel in ctx.vessels:
        vessel_masks = ctx.last_masks.get(vessel.id, {})
        baselines = ctx.baselines.setdefault(vessel.id, {})
        common = dict(t=t, frame_id=frame_id, current_reference=current_reference, baselines=baselines)
        geometry = await asyncio.to_thread(
            measure_vessel,
            geometry_recipe,
            vessel,
            vessel_masks,
            image_bgr,
            ctx.calibration,
            families=GEOMETRY,
            **common,
        )
        colour = await asyncio.to_thread(
            measure_vessel, ctx.recipe, vessel, vessel_masks, image_bgr, ctx.calibration, families=COLOUR, **common
        )
        drafts += geometry.drafts + colour.drafts
        for measurement_id, reading in colour.lab.items():
            baselines.setdefault(measurement_id, reading)  # the first reading is the ΔE baseline

    rows = await asyncio.to_thread(add_measurements, ctx.db, ctx.run.id, drafts) if drafts else []
    await asyncio.to_thread(mark_frame_analyzed, ctx.db, frame_id)
    ctx.publish("frame_analyzed", {"frame_id": frame_id, "t": t, "quality_flags": list(quality_flags)})
    for row in rows:
        ctx.publish(
            "measurement",
            {
                "id": row.id,
                "vessel_id": row.vessel_id,
                "frame_id": row.frame_id,
                "t": row.t,
                "metric": row.metric,
                "value": row.value,
                "uncertainty": row.uncertainty,
                "unit": row.unit,
                "display": format_measurement(row.value, row.uncertainty, row.unit),
            },
        )
    return AnalysisOutcome(frame_id, bool(segmented_concepts), len(rows), failed)
