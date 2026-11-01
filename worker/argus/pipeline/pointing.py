"""Point SAM again where a vessel changed since its start (D-92).

SAM traces almost anything it is pointed at but recognises few lab words, so a faint colony it can't find by name is
often found once a box says where it is. For a concept marked `appears` (not there at the start), each vessel keeps a
start reference: the median of its first kept crops. When SAM's answer by name is empty, the change since the start
gives regions; SAM is asked again with a box on each and its strongest point. Each region keeps SAM's outline when
that outline keeps to it; otherwise (SAM found nothing there, traced far more such as the whole dish, or
couldn't be asked: the spend cap, a failure) the region itself is the outline, drawn by code. Every patch says who
drew it (D-93). Without a change, nothing is asked: the empty answer stands, a gap after a first sighting (D-90).
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import cv2
import numpy as np

from argus.domain import Vessel
from argus.pipeline.analyzer import RunContext, segment_with_retries
from argus.recipes.model import Recipe
from argus.rois import roi_box
from argus.segment import MaskPatch, ObjectPrompt, SegmentResult
from argus.segment.change import (
    CODE,
    REFERENCE_FRAMES,
    ChangeReference,
    ChangeRegion,
    change_reference,
    change_regions,
)

POINTED = "sam-3.1/pointed"  # SAM, prompted with boxes on what changed
CROP_MARGIN_PX = 8  # around a vessel's region when SAM is shown that vessel alone
BOX_PAD = 0.15  # of a region's size, on each side: a faint edge just outside the change is still in the box
VESSEL_SIZED = 0.85  # a SAM mask covering this much of the vessel outlined the vessel, unless...
MOSTLY_CHANGED = 0.5  # ...the change covers at least this much of it
# A SAM outline up to twice its region's size fills in faint parts the change map missed; bigger, and SAM traced
# something else than the change it was pointed at: from a box around a swarm, sometimes the whole dish.
MAX_GROWTH = 2.0


def pointing_concepts(recipe: Recipe) -> set[str]:
    return {c.name for c in recipe.concepts if c.appears}


def vessel_crop(vessel: Vessel, image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    """The vessel's region with a margin, the vessel's mask in it, and the crop's corner in the frame."""
    height, width = image_bgr.shape[:2]
    x0, y0, x1, y1 = roi_box(vessel, height, width, margin=CROP_MARGIN_PX)
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [np.round(np.asarray(vessel.roi, np.float64) - (x0, y0)).astype(np.int32)], 1)
    return image_bgr[y0:y1, x0:x1], mask.astype(bool), (x0, y0)


def _roi(vessel: Vessel) -> tuple[tuple[float, float], ...]:
    return tuple((float(x), float(y)) for x, y in vessel.roi)


def observe(ctx: RunContext, vessel: Vessel, concept: str, image_bgr: np.ndarray) -> ChangeReference | None:
    """Take this kept frame into the vessel's start reference while it is being taken; once it is, return it. A
    reference taken where the vessel was before a camera move is dropped, and a new one is taken, unless the object
    was already seen there: a start taken now would hold it, and its change would be only the growth since the move."""
    key = (vessel.id, concept)
    if key in ctx.change_off:
        return None
    reference = ctx.change_refs.get(key)
    if reference is not None and reference.roi == _roi(vessel):
        return reference
    roi, crops = ctx.change_crops.get(key, (_roi(vessel), []))
    if reference is not None or roi != _roi(vessel):  # the vessel moved
        ctx.change_refs.pop(key, None)
        ctx.change_crops.pop(key, None)
        if concept in ctx.sighted.get(vessel.id, ()):
            ctx.change_off.add(key)
            return None
        roi, crops = _roi(vessel), []
    crop, mask, _ = vessel_crop(vessel, image_bgr)
    crops = [*crops, crop.copy()]
    if len(crops) < REFERENCE_FRAMES:
        ctx.change_crops[key] = (roi, crops)
    else:
        ctx.change_crops.pop(key, None)
        ctx.change_refs[key] = change_reference(crops, mask, roi)
    return None


def _prompt(region: ChangeRegion, width: int, height: int) -> ObjectPrompt:
    """The region's box padded on each side and clipped, corners inclusive, with its strongest point."""
    x0, y0, x1, y1 = region.box
    dx, dy = round(BOX_PAD * (x1 - x0)), round(BOX_PAD * (y1 - y0))
    box = (max(x0 - dx, 0), max(y0 - dy, 0), min(x1 + dx, width) - 1, min(y1 + dy, height) - 1)
    return ObjectPrompt(box, region.peak)


def _number(key: str) -> int | None:
    """The prompt a pointed track answers: SAM numbers prompted objects from 1, in the order they were sent."""
    digits = key.removeprefix("obj")
    return int(digits) if digits.isdigit() else None


def _drawn_by_code(region: ChangeRegion, x0: int, y0: int) -> MaskPatch:
    bx0, by0, bx1, by1 = region.box
    return MaskPatch(x0 + bx0, y0 + by0, region.mask[by0:by1, bx0:bx1], CODE)


async def point_again(
    ctx: RunContext,
    vessel: Vessel,
    concept: str,
    image_bgr: np.ndarray,
    reference: ChangeReference,
    *,
    t: float,
    frame_id: str,
) -> list[MaskPatch]:
    """After an empty answer by name, each region of change outlined by SAM when SAM's outline keeps to it, else by
    code, in frame pixels; [] when nothing changed (and SAM isn't asked)."""
    crop, _, (x0, y0) = vessel_crop(vessel, image_bgr)
    if crop.shape != reference.lab.shape:
        return []
    regions = await asyncio.to_thread(change_regions, reference, crop)
    if not regions:
        return []
    inside, changed = int(reference.inside.sum()), sum(int(r.mask.sum()) for r in regions)
    if changed >= VESSEL_SIZED * inside:
        return []  # the whole vessel changed at once (light, a fogged lid, drying agar): not growth to point at
    height, width = crop.shape[:2]
    prompts = [_prompt(r, width, height) for r in regions]
    result = await segment_with_retries(ctx, crop, concept, t=t, frame_ids=[frame_id], prompts=prompts)
    by_sam: dict[int, list[MaskPatch]] = {}
    if isinstance(result, SegmentResult):
        mostly_changed = changed >= MOSTLY_CHANGED * inside
        for track in result.tracks:
            number, patch = _number(track.key), track.frames[0].patch
            if number is None or not 1 <= number <= len(prompts):
                continue
            if patch.area_px >= VESSEL_SIZED * inside and not mostly_changed:
                continue  # SAM outlined the vessel, not what changed in it
            if patch.area_px > MAX_GROWTH * int(regions[number - 1].mask.sum()):
                continue  # SAM traced far more than the change it was pointed at
            by_sam.setdefault(number, []).append(replace(patch.shifted(x0, y0), source=POINTED))
    patches: list[MaskPatch] = []
    for number, region in enumerate(regions, start=1):
        patches += by_sam.get(number) or [_drawn_by_code(region, x0, y0)]
    return patches
