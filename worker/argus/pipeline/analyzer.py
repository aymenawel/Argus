"""One frame through segmentation, tracking, measurement and storage (spec §4.1 steps 4-7, §4.3).

Shared by the live and import pipelines. A segmentation that fails (after retries) or is refused by the spend
cap leaves a gap, never a zero: zero is stored only when SAM answered and found nothing.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol

import cv2
import numpy as np

from argus.analyze.rules import RuleEvaluator
from argus.api.events import EventBroker
from argus.calibration.colour import ColourReference, PatchReading, neutral_drift, read_patches
from argus.calibration.detect import detect_card
from argus.calibration.run import RunCalibration
from argus.config import Settings
from argus.domain import Detection, EventKind, MeasurementDraft, ModelCallDraft, Run, Vessel, new_id
from argus.measure.engine import ColourBaseline, VesselMeasurements, measure_vessel
from argus.measure.uncertainty import format_measurement
from argus.pipeline.notes import NoteWriter
from argus.reason import Reasoner
from argus.recipes.model import MeasurementSpec, Recipe
from argus.segment import Clip, MaskPatch, SegmentError, SegmentResult, segment
from argus.segment.outline import outline_polygons
from argus.segment.sam import sam_client
from argus.segment.tracking import TrackMatcher, assign_to_vessels
from argus.storage.db import Database
from argus.storage.files import RunFiles
from argus.storage.repos import (
    add_calibration,
    add_detection_rows,
    add_event,
    add_frame,
    add_measurements,
    add_model_call,
    close_event,
    mark_frame_analyzed,
    run_spend_usd,
)

JPEG_QUALITY = 90
COLOUR_DRIFT_MAX = 6.0  # dE00 of the card's neutral patches beyond which correction is no longer trusted
COLOUR_DRIFT_RESUME = 5.0  # once paused, correction resumes only below this, so it doesn't flicker at the cut-off
SETTLE_READINGS = 3  # a run's colour reference is the median of its first card readings, not its first frame
GEOMETRY = frozenset({"size", "count"})
COLOUR = frozenset({"colour"})

KeyedPatches = Mapping[str, Mapping[str, Sequence[tuple[str, MaskPatch]]]]  # vessel id -> concept -> patches


class Segmenter(Protocol):
    async def image(self, image_bgr: np.ndarray, concept: str) -> SegmentResult: ...

    async def video(self, clip: Clip, concept: str) -> SegmentResult: ...


class SamSegmenter:
    """The worker's SAM 3.1 access: one client for every run, closed when the worker stops."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None  # only argus.segment.sam touches the SDK

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = sam_client(self.settings)
        return self._client

    async def image(self, image_bgr: np.ndarray, concept: str) -> SegmentResult:
        return await segment(image_bgr, concept, mode="image", settings=self.settings, client=self.client)

    async def video(self, clip: Clip, concept: str) -> SegmentResult:
        return await segment(clip, concept, mode="video", settings=self.settings, client=self.client)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


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
    reasoner: Reasoner | None = None  # None: no AI notes in this run
    matcher: TrackMatcher = field(default_factory=TrackMatcher)
    last_masks: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    baselines: dict[str, dict[str, ColourBaseline]] = field(default_factory=dict)
    retry_delays_s: tuple[float, ...] = (1.0, 4.0)
    cap_reported: bool = False
    calibration_reported: bool = False
    uncorrected_event: str | None = None  # the open event while colour can't be corrected against the card
    colour_reference: ColourReference | None = None  # the settled reference colour is corrected against
    settling: list[ColourReference] = field(default_factory=list)  # card readings until it settles
    semaphore: asyncio.Semaphore = field(init=False)
    rules: RuleEvaluator = field(init=False)  # the recipe's rule events, fired once per vessel
    spend_lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    reserved_usd: float = 0.0  # expected cost of the calls in flight, not yet logged
    limit_reported: set[str] = field(default_factory=set)  # concepts that hit SAM's object limit
    calibration_problem: str | None = None  # why the first frame without millimetres had none, when known
    notes: NoteWriter = field(init=False)

    def __post_init__(self) -> None:
        self.semaphore = asyncio.Semaphore(self.settings.sam_concurrency)
        self.rules = RuleEvaluator(self.recipe)
        self.notes = NoteWriter(self)

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
    ) -> str:
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
        return event.id


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


def _cancelled_call(settings: Settings, media: np.ndarray | Clip, cost: float, started: float) -> ModelCallDraft:
    billed = (
        {"images": 1}
        if isinstance(media, np.ndarray)
        else {"frames": max(media.frame_count, settings.sam_video_min_frames)}
    )
    return ModelCallDraft(
        function="segment",
        model=settings.segment_model,
        tier="segment",
        cost_usd=cost,
        latency_s=round(time.perf_counter() - started, 3),
        status="error",
        error="cancelled",
        **billed,
    )


async def segment_with_retries(
    ctx: RunContext, media: np.ndarray | Clip, concept: str, *, t: float, frame_ids: Sequence[str] = ()
) -> SegmentResult | Skipped:
    """Every attempt is logged. Skipped("cap") when the spend cap refuses the call, Skipped("failed") when every
    attempt failed (with a segment_failed event)."""
    attempts = 1 + len(ctx.retry_delays_s)
    error = ""
    expected, cap = _expected_cost(ctx.settings, media), ctx.settings.run_spend_cap_usd
    for attempt in range(attempts):
        async with ctx.semaphore:
            # Check and reserve together, so calls in flight at once can't all pass the same check.
            async with ctx.spend_lock:
                spent = await asyncio.to_thread(run_spend_usd, ctx.db, ctx.run.id)
                refused = spent + ctx.reserved_usd + expected > cap
                if not refused:
                    ctx.reserved_usd += expected
            if refused:
                if not ctx.cap_reported:
                    ctx.cap_reported = True
                    detail = {"spent_usd": round(spent, 4), "cap_usd": cap, "message": "segmentation paused: spend cap"}
                    await ctx.event(t, EventKind.SPEND, "pipeline", detail)
                    ctx.publish("spend", {"t": t, "spent_usd": round(spent, 4), "cap_usd": cap})
                return Skipped("cap")
            result: SegmentResult | None = None
            started = time.perf_counter()
            try:
                try:
                    if isinstance(media, np.ndarray):
                        result = await ctx.segmenter.image(media, concept)
                    else:
                        result = await ctx.segmenter.video(media, concept)
                    logged = result.call
                except SegmentError as failure:
                    error, logged = str(failure), failure.call
                except asyncio.CancelledError:  # a forced stop: the request may be billed, so it is logged
                    add_model_call(ctx.db, ctx.run.id, t, _cancelled_call(ctx.settings, media, expected, started))
                    raise
                await asyncio.to_thread(add_model_call, ctx.db, ctx.run.id, t, logged)
            finally:
                ctx.reserved_usd -= expected
        if result is not None:
            limit = ctx.settings.sam_max_objects
            if len(result.tracks) >= limit and concept not in ctx.limit_reported:
                ctx.limit_reported.add(concept)  # SAM keeps the first `limit`: there may be more than it found
                message = (
                    f"SAM 3.1 returns at most {limit} objects per request: there may be more '{concept}' than found"
                )
                detail = {"message": message, "concept": concept, "objects": len(result.tracks)}
                await ctx.event(t, EventKind.QUALITY, "quality", detail, frame_ids=frame_ids)
            return result
        if attempt < attempts - 1:
            await asyncio.sleep(ctx.retry_delays_s[attempt])
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


def due_measurements(recipe: Recipe, segmented: set[str]) -> list[MeasurementSpec]:
    """The geometry a vessel can be measured for on this frame: every concept a measurement reads was segmented
    here (a touching count needs both its objects and what they touch)."""
    return [m for m in recipe.measurements if m.source in segmented and (m.touching is None or m.touching in segmented)]


def _union(patches: Sequence[tuple[str, MaskPatch]], shape: tuple[int, int]) -> np.ndarray:
    canvas = np.zeros(shape, bool)
    for _, patch in patches:
        canvas |= patch.to_canvas(*shape)
    return canvas


def correction_paused(drift: float | None, *, paused: bool) -> bool:
    """Whether colour is left uncorrected on this frame: beyond 6 dE00 of drift (or no neutral to compare), and
    once paused until the drift is back under 5."""
    return drift is None or drift > (COLOUR_DRIFT_RESUME if paused else COLOUR_DRIFT_MAX)


def _median_reference(readings: Sequence[ColourReference]) -> ColourReference:
    names = sorted({p.name for reading in readings for p in reading.patches})
    patches = []
    for name in names:
        labs = np.array([p.lab for reading in readings for p in reading.patches if p.name == name])
        median = np.median(labs, axis=0)
        patches.append(PatchReading(name, (float(median[0]), float(median[1]), float(median[2]))))
    return ColourReference(tuple(patches))


async def _colour_reference(
    ctx: RunContext, t: float, image_bgr: np.ndarray, frame_id: str
) -> tuple[ColourReference | None, bool]:
    """The card's patches in this frame to correct colour with (None: uncorrected), and whether colour is measured
    on this frame at all. A camera still settling its exposure and white balance when a run starts would skew
    every reading after it, so the run's reference is the median of the card's first readings, and colour waits
    for it. Each stretch without correction is one quality event, open until correction is possible again."""
    cal = ctx.calibration
    if cal is None or cal.detection is None or cal.reference is None:
        return None, True  # no card at the start: colour is never corrected in this run, and every reading says so
    card = await asyncio.to_thread(detect_card, image_bgr, (cal.detection.spec,))
    current = await asyncio.to_thread(read_patches, image_bgr, card) if card is not None else None
    if ctx.colour_reference is None:
        if current is not None:
            ctx.settling.append(current)
        if len(ctx.settling) < SETTLE_READINGS:
            return None, False
        ctx.colour_reference = _median_reference(ctx.settling)
        settled = replace(cal, reference=ctx.colour_reference).to_draft(t, {})
        await asyncio.to_thread(add_calibration, ctx.db, ctx.run.id, settled)
    drift = neutral_drift(ctx.colour_reference, current) if current is not None else None
    if correction_paused(drift, paused=ctx.uncorrected_event is not None):
        if ctx.uncorrected_event is None:
            if card is None:
                detail: dict = {"message": "colour not corrected: the card is not in view"}
            elif drift is None:
                detail = {"message": "colour not corrected: no neutral patch of the card can be read"}
            else:  # beyond correction: colour stays uncorrected rather than wrongly corrected
                detail = {
                    "message": "colour not corrected: the card's neutrals drifted",
                    "colour_drift": round(drift, 2),
                }
            ctx.uncorrected_event = await ctx.event(t, EventKind.QUALITY, "quality", detail, frame_ids=[frame_id])
        return None, True
    if ctx.uncorrected_event is not None:
        event = await asyncio.to_thread(close_event, ctx.db, ctx.uncorrected_event, t)
        ctx.uncorrected_event = None
        ctx.publish(
            "event",
            {
                "t": event.t_start,
                "t_end": t,
                "id": event.id,
                "kind": str(event.kind),
                "vessel_id": None,
                "detail": event.detail,
            },
        )
    return current, True


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
            problem = ctx.calibration_problem or "no Argus Card or ruler in view"
            detail = {"message": f"{problem}: frames are recorded but not measured until a scale is found"}
            await ctx.event(t, EventKind.NO_CALIBRATION, "pipeline", detail, frame_ids=[frame_id])
        await asyncio.to_thread(mark_frame_analyzed, ctx.db, frame_id)
        ctx.publish("frame_analyzed", {"frame_id": frame_id, "t": t, "quality_flags": list(quality_flags)})
        return AnalysisOutcome(frame_id, False, 0, [])

    current_reference, measure_colour = await _colour_reference(ctx, t, image_bgr, frame_id)
    cal = ctx.calibration if ctx.colour_reference is None else replace(ctx.calibration, reference=ctx.colour_reference)

    # Segmentation: injected (video mode, per vessel) or one image call per concept (covers every vessel).
    # `keyed` holds what came back per vessel and concept; an empty list means SAM answered and found nothing.
    keyed: dict[str, dict[str, list[tuple[str, MaskPatch]]]] = {}
    confidence: dict[int, float | None] = {}
    failed: list[str] = []
    backend = "sam-3.1/video"
    if masks is not None:
        for vessel_id, by_concept in masks.items():
            for concept, patches in by_concept.items():
                keyed.setdefault(vessel_id, {})[concept] = list(patches)
    elif segment:
        backend = "sam-3.1/image"
        concepts = [c.name for c in ctx.recipe.concepts]
        results = await asyncio.gather(  # every concept at once; the semaphore bounds the calls
            *(segment_with_retries(ctx, image_bgr, concept, t=t, frame_ids=[frame_id]) for concept in concepts)
        )
        for concept, result in zip(concepts, results, strict=True):
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
    # Something in front of a vessel (the quality gate saw its surroundings change): what SAM found there may be
    # the hand, so nothing of that vessel is kept from this frame. A gap, not a reading.
    blocked = {flag.split(":", 1)[1] for flag in quality_flags if flag.startswith("occluded:")}
    keyed = {vessel_id: by_concept for vessel_id, by_concept in keyed.items() if vessel_id not in blocked}
    if keyed:
        await asyncio.to_thread(_store_detections, ctx, frame_id, keyed, confidence, backend)
    for vessel_id, by_concept in keyed.items():
        for concept, patches in by_concept.items():
            ctx.last_masks.setdefault(vessel_id, {})[concept] = _union(patches, shape)

    # Measurement: geometry only where this vessel's concept was segmented on this frame (a vessel missing from
    # `keyed` is a gap, not a zero); colour on the newest masks there are.
    drafts: list[MeasurementDraft] = []
    for vessel in (v for v in ctx.vessels if v.id not in blocked):
        segmented_here = set(keyed.get(vessel.id, {}))
        geometry_recipe = ctx.recipe.model_copy(update={"measurements": due_measurements(ctx.recipe, segmented_here)})
        vessel_masks = ctx.last_masks.get(vessel.id, {})
        baselines = ctx.baselines.setdefault(vessel.id, {})
        common = dict(t=t, frame_id=frame_id, current_reference=current_reference, baselines=baselines)
        geometry = await asyncio.to_thread(
            measure_vessel,
            geometry_recipe,
            vessel,
            vessel_masks,
            image_bgr,
            cal,
            families=GEOMETRY,
            **common,
        )
        colour = VesselMeasurements([], {})  # while the colour reference settles, colour waits
        if measure_colour:
            colour = await asyncio.to_thread(
                measure_vessel, ctx.recipe, vessel, vessel_masks, image_bgr, cal, families=COLOUR, **common
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
    for rule, row in ctx.rules.fired(rows):
        detail = {"rule": rule.id, "metric": rule.metric, "measurement_id": row.id}
        await ctx.event(row.t, EventKind.RULE, "rule", detail, vessel_id=row.vessel_id, frame_ids=[frame_id])
    return AnalysisOutcome(frame_id, bool(keyed), len(rows), failed)
